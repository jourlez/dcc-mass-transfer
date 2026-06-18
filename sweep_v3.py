#!/usr/bin/env python3
"""
Sweep DCC from child wallets to main sender.
Uses requests directly for balance checks to avoid pywaves hanging.
"""
import csv, time, os, sys, logging
from dotenv import load_dotenv; load_dotenv()
from config import resolve_node, resolve_chain_id, resolve_private_key

logging.disable(logging.CRITICAL)

import pywaves as pw
import requests

NODE = os.getenv('DCC_NODE') or resolve_node(silent=True)
CHAIN_ID = os.getenv('DCC_CHAIN_ID') or resolve_chain_id()
MAIN_KEY = os.getenv('DCC_PRIVATE_KEY') or resolve_private_key()
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'real_wallets_2000_details.csv')
FEE = 100000        # 0.001 DCC
MIN_BAL = 200000    # only sweep if > 0.002 DCC
SESSION = requests.Session()
SESSION.timeout = 5  # 5 second timeout for HTTP calls


def get_balance_fast(address):
    """Get DCC balance via direct HTTP (avoids pywaves hanging)"""
    try:
        r = SESSION.get(f'{NODE}/addresses/balance/{address}', timeout=5)
        if r.status_code == 200:
            return r.json().get('balance', 0)
    except:
        pass
    return 0


def main():
    pw.setNode(node=NODE, chain='custom', chain_id=CHAIN_ID)
    pw.Address.aliases = lambda self: []  # prevent alias fetch

    main_wallet = pw.Address(privateKey=MAIN_KEY)
    main_addr = main_wallet.address
    start_bal = get_balance_fast(main_addr) / 1e8

    print(f"{'='*65}")
    print(f"  💰 DCC SWEEP v3 — fast, no-hang")
    print(f"{'='*65}")
    print(f"  Target:   {main_addr}")
    print(f"  Balance:  {start_bal:.4f} DCC")
    print(f"{'='*65}")

    # Load wallets
    wallets = []
    with open(CSV_FILE, 'r') as f:
        for row in csv.DictReader(f):
            wallets.append(row)
    print(f"  Wallets:  {len(wallets)}")
    print()

    swept = 0
    skipped = 0
    failed = 0
    total_dcc = 0.0
    t0 = time.time()

    for i, row in enumerate(wallets, 1):
        addr = row.get('address', '').strip()
        privkey = row.get('private_key', '').strip()

        if not addr or not privkey or len(privkey) < 20:
            skipped += 1
            continue

        # Fast balance check via HTTP
        bal = get_balance_fast(addr)
        if bal <= MIN_BAL:
            skipped += 1
            if i % 200 == 0:
                print(f"  [{i:>4}/{len(wallets)}] scanning... swept {swept}, "
                      f"collected {total_dcc:.2f} DCC  [{time.time()-t0:.0f}s]")
            continue

        # Has funds — sweep using pywaves
        send_amt = bal - FEE
        try:
            w = pw.Address(privateKey=privkey)
            result = w.sendWaves(
                recipient=pw.Address(main_addr),
                amount=send_amt,
                txFee=FEE
            )
            dcc = send_amt / 1e8
            total_dcc += dcc
            swept += 1

            if swept <= 5 or swept % 25 == 0:
                tx_id = result.get('id', '?')[:20]
                print(f"  ✓ [{i:>4}] +{dcc:.4f} DCC | total: {total_dcc:.2f} | "
                      f"swept: {swept}  TX: {tx_id}...")
        except Exception as e:
            failed += 1
            if failed <= 3:
                print(f"  ✗ [{i}] {str(e)[:70]}")

    elapsed = time.time() - t0

    # Final balance
    time.sleep(1)
    end_bal = get_balance_fast(main_addr) / 1e8

    print(f"\n{'='*65}")
    print(f"  SWEEP COMPLETE")
    print(f"{'='*65}")
    print(f"  Swept:      {swept}")
    print(f"  Skipped:    {skipped}")
    print(f"  Failed:     {failed}")
    print(f"  Collected:  {total_dcc:.4f} DCC")
    print(f"  Time:       {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"")
    print(f"  Balance:  {start_bal:.4f} → {end_bal:.4f} DCC  (+{end_bal-start_bal:.4f})")
    batches = int(end_bal / 0.051)
    print(f"  Capacity: {batches:,} mass transfers = {batches*100:,} TX")
    print(f"{'='*65}")


if __name__ == '__main__':
    main()
