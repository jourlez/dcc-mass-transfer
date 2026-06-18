#!/usr/bin/env python3
"""
Sweep DCC from child wallets to main sender — robust sequential version.
Skips already-empty wallets quickly, handles invalid addresses gracefully.
"""
import sys, os, csv, time, logging
from dotenv import load_dotenv; load_dotenv()

# Suppress all pywaves/urllib warnings
logging.disable(logging.CRITICAL)
os.environ['PYTHONWARNINGS'] = 'ignore'

import pywaves as pw
from config import validate_config, get_wallets_csv

# ── Validation ─────────────────────────────────────────────────
validate_config(require_private_key=True, require_node=True)

DECENTRALCHAIN_NODE = os.getenv('DCC_NODE') or resolve_node(silent=True)
CHAIN_ID = os.getenv('DCC_CHAIN_ID') or resolve_chain_id()
MAIN_SENDER_PRIVKEY = os.getenv('DCC_PRIVATE_KEY') or resolve_private_key()
WALLETS_CSV = os.path.join(os.path.dirname(__file__), 'real_wallets_2000_details.csv')
TRANSFER_FEE = 100000  # 0.001 DCC
MIN_BALANCE  = 200000  # 0.002 DCC minimum to bother sweeping


def main():
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)

    # Monkey-patch to prevent slow alias fetching
    pw.Address.aliases = lambda self: []

    main_sender = pw.Address(privateKey=MAIN_SENDER_PRIVKEY)
    start_bal = main_sender.balance() / 1e8
    print(f"{'='*65}")
    print(f"  💰 DCC SWEEP — sequential, robust")
    print(f"{'='*65}")
    print(f"  Main sender: {main_sender.address}")
    print(f"  Starting balance: {start_bal:.4f} DCC")
    print(f"{'='*65}\n")

    # Load wallets
    wallets = []
    with open(WALLETS_CSV, 'r') as f:
        for row in csv.DictReader(f):
            wallets.append(row)
    print(f"  Loaded {len(wallets)} wallets\n")

    swept = 0
    skipped = 0
    failed = 0
    total_collected = 0.0
    start = time.time()

    for i, row in enumerate(wallets, 1):
        privkey = row.get('private_key', '').strip()
        if not privkey or len(privkey) < 20:
            skipped += 1
            continue

        try:
            w = pw.Address(privateKey=privkey)
        except Exception:
            skipped += 1
            continue

        try:
            bal = w.balance()
        except Exception:
            failed += 1
            continue

        if bal <= MIN_BALANCE:
            skipped += 1
            if i % 200 == 0:
                elapsed = time.time() - start
                print(f"  [{i}/{len(wallets)}] skipped (empty) — "
                      f"collected {total_collected:.2f} DCC so far  [{elapsed:.0f}s]")
            continue

        send_amt = bal - TRANSFER_FEE
        try:
            result = w.sendWaves(
                recipient=pw.Address(main_sender.address),
                amount=send_amt,
                txFee=TRANSFER_FEE
            )
            dcc = send_amt / 1e8
            total_collected += dcc
            swept += 1

            if swept % 25 == 0 or swept <= 5 or i % 200 == 0:
                elapsed = time.time() - start
                print(f"  ✓ [{i}/{len(wallets)}] +{dcc:.4f} DCC | "
                      f"total: {total_collected:.2f} DCC | swept: {swept} [{elapsed:.0f}s]")

        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"  ✗ [{i}] {str(e)[:70]}")

    elapsed = time.time() - start

    # Final balance check
    time.sleep(2)
    try:
        end_bal = main_sender.balance() / 1e8
    except:
        end_bal = start_bal + total_collected

    print(f"\n{'='*65}")
    print(f"  SWEEP COMPLETE")
    print(f"{'='*65}")
    print(f"  Swept:      {swept} wallets")
    print(f"  Skipped:    {skipped} (empty or invalid)")
    print(f"  Failed:     {failed}")
    print(f"  Collected:  {total_collected:.4f} DCC")
    print(f"  Time:       {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"")
    print(f"  Sender balance: {start_bal:.4f} → {end_bal:.4f} DCC")
    print(f"  Net gain:       +{end_bal - start_bal:.4f} DCC")
    print(f"")
    batches = int(end_bal / 0.051)
    print(f"  📊 Capacity: {batches:,} mass transfers = {batches*100:,} transactions")
    print(f"{'='*65}")


if __name__ == '__main__':
    main()
