#!/usr/bin/env python3
"""
Sweep DCC from all 2000 child wallets back to the main sender.
Each child wallet has ~1.44 DCC. This collects it all for tx fees.
Fee: 0.001 DCC per transfer, so net ~1.443 DCC per wallet.
"""

import pywaves as pw
import csv
import time
import sys
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Suppress noisy pywaves warnings (invalid address logs)
logging.getLogger().setLevel(logging.ERROR)

# ── Configuration ──────────────────────────────────────────────
DECENTRALCHAIN_NODE = 'https://mainnet-node.decentralchain.io'
CHAIN_ID = '?'
MAIN_SENDER_ADDRESS = '3DXWAcdwiHFmW9xj4FWdso8Ea3eQb1cfKpH'
WALLETS_CSV = 'real_wallets_2000_details.csv'

MAX_WORKERS = 20          # concurrent sweeps (conservative to avoid node throttle)
TRANSFER_FEE = 100000     # 0.001 DCC in satoshis
MIN_BALANCE = 200000      # only sweep if > 0.002 DCC (enough to cover fee + send something)

# ── State ──────────────────────────────────────────────────────
lock = Lock()
stats = {'swept': 0, 'skipped': 0, 'failed': 0, 'total_dcc': 0}


def sweep_wallet(row, index, total):
    """Sweep DCC from one child wallet to main sender"""
    priv_key = row['private_key']
    try:
        wallet = pw.Address(privateKey=priv_key)
        balance = wallet.balance()  # in satoshis

        if balance <= MIN_BALANCE:
            with lock:
                stats['skipped'] += 1
            return

        send_amount = balance - TRANSFER_FEE  # keep fee for the tx itself

        if send_amount <= 0:
            with lock:
                stats['skipped'] += 1
            return

        result = wallet.sendWaves(
            recipient=pw.Address(MAIN_SENDER_ADDRESS),
            amount=send_amount,
            txFee=TRANSFER_FEE
        )

        tx_id = result.get('id', 'N/A')
        dcc_amount = send_amount / 1e8

        with lock:
            stats['swept'] += 1
            stats['total_dcc'] += dcc_amount

        if index % 50 == 0 or index <= 5:
            print(f"  ✓ Wallet {index}/{total}: {dcc_amount:.4f} DCC | TX: {tx_id[:20]}...")

    except Exception as e:
        with lock:
            stats['failed'] += 1
        err = str(e)
        if index <= 10 or 'Insufficient' not in err:
            print(f"  ✗ Wallet {index}: {err[:80]}")


def main():
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)

    print("=" * 70)
    print("💰 DCC SWEEP — Collecting fees from child wallets")
    print("=" * 70)
    print(f"Target:      {MAIN_SENDER_ADDRESS}")
    print(f"Source:      {WALLETS_CSV}")
    print(f"Workers:     {MAX_WORKERS}")
    print(f"Fee/wallet:  {TRANSFER_FEE / 1e8} DCC")
    print("=" * 70)

    # Load wallets
    wallets = []
    with open(WALLETS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            wallets.append(row)

    print(f"\nLoaded {len(wallets)} child wallets")

    # Check main sender starting balance
    sender = pw.Address(MAIN_SENDER_ADDRESS)
    start_balance = sender.balance() / 1e8
    print(f"Main sender starting balance: {start_balance:.8f} DCC\n")

    print("Starting sweep...\n")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i, row in enumerate(wallets, 1):
            future = executor.submit(sweep_wallet, row, i, len(wallets))
            futures.append(future)
            # Small stagger to avoid overwhelming the node
            if i % MAX_WORKERS == 0:
                time.sleep(0.05)

        for future in as_completed(futures):
            future.result()

    elapsed = time.time() - start_time

    # Check final balance
    time.sleep(2)  # wait for blockchain to settle
    try:
        end_balance = sender.balance() / 1e8
    except:
        end_balance = start_balance + stats['total_dcc']

    print(f"\n{'=' * 70}")
    print(f"SWEEP COMPLETE")
    print(f"{'=' * 70}")
    print(f"Wallets swept:     {stats['swept']}")
    print(f"Wallets skipped:   {stats['skipped']}")
    print(f"Wallets failed:    {stats['failed']}")
    print(f"DCC collected:     {stats['total_dcc']:.4f} DCC")
    print(f"Time:              {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Rate:              {stats['swept'] / elapsed:.1f} wallets/sec")
    print(f"")
    print(f"Main sender balance:")
    print(f"  Before: {start_balance:.8f} DCC")
    print(f"  After:  {end_balance:.8f} DCC")
    print(f"  Gained: {end_balance - start_balance:.8f} DCC")
    print(f"{'=' * 70}")

    # Estimate capacity
    fee_per_batch = 0.051  # 100-recipient mass transfer
    batches = int(end_balance / fee_per_batch)
    print(f"\n📊 Capacity with {end_balance:.2f} DCC:")
    print(f"  Mass transfer batches (100 recipients): {batches:,}")
    print(f"  Total transactions possible:            {batches * 100:,}")


if __name__ == '__main__':
    main()
