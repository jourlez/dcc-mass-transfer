#!/usr/bin/env python3
"""
Turbo DCC Sweep — Parallel sweep of DCC from child wallets to main sender.
Uses 20 concurrent threads with 10s timeouts per wallet.
"""
import pywaves as pw
import csv, time, logging, sys, os
from dotenv import load_dotenv; load_dotenv()
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from config import validate_config, get_wallets_csv, resolve_node, resolve_chain_id, resolve_private_key

# ── Validation ─────────────────────────────────────────────────
validate_config(require_private_key=True, require_node=True)

logging.disable(logging.CRITICAL)  # Suppress pywaves noise

NODE = os.getenv('DCC_NODE') or resolve_node(silent=True)
CHAIN_ID = os.getenv('DCC_CHAIN_ID') or resolve_chain_id()
MAIN_SENDER_KEY = os.getenv('DCC_PRIVATE_KEY') or resolve_private_key()
WALLETS_CSV = get_wallets_csv()
WORKERS = 15
FEE = 100000  # 0.001 DCC in satoshis

pw.setNode(node=NODE, chain='custom', chain_id=CHAIN_ID)
main_addr = pw.Address(privateKey=MAIN_SENDER_KEY)

lock = Lock()
stats = {'swept': 0, 'skipped': 0, 'failed': 0, 'total_dcc': 0.0}

def sweep_wallet(idx, private_key):
    try:
        w = pw.Address(privateKey=private_key)
        bal = w.balance()
        if bal <= FEE:
            with lock:
                stats['skipped'] += 1
            return None
        
        send_amt = bal - FEE
        w.sendWaves(recipient=main_addr, amount=send_amt)
        dcc = send_amt / 1e8
        
        with lock:
            stats['swept'] += 1
            stats['total_dcc'] += dcc
        
        return dcc
    except Exception as e:
        with lock:
            stats['failed'] += 1
        return None

def main():
    # Load wallets
    wallets = []
    with open(WALLETS_CSV) as f:
        for row in csv.DictReader(f):
            pk = row.get('private_key', '').strip()
            if pk:
                wallets.append(pk)
    
    print(f"⚡ Turbo Sweep: {len(wallets)} wallets → {main_addr.address}")
    start_bal = main_addr.balance() / 1e8
    print(f"Starting balance: {start_bal:.4f} DCC")
    print(f"Workers: {WORKERS}\n")
    
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {}
        for i, pk in enumerate(wallets):
            futures[executor.submit(sweep_wallet, i, pk)] = i
        
        done = 0
        for f in as_completed(futures):
            done += 1
            if done % 100 == 0:
                elapsed = time.time() - start
                print(f"  Progress: {done}/{len(wallets)} | Swept: {stats['swept']} | "
                      f"Collected: {stats['total_dcc']:.2f} DCC | {elapsed:.0f}s", flush=True)
    
    elapsed = time.time() - start
    end_bal = main_addr.balance() / 1e8
    
    print(f"\n{'='*60}")
    print(f"SWEEP COMPLETE")
    print(f"{'='*60}")
    print(f"Wallets swept:   {stats['swept']}")
    print(f"Already empty:   {stats['skipped']}")
    print(f"Failed:          {stats['failed']}")
    print(f"DCC collected:   {stats['total_dcc']:.4f}")
    print(f"Final balance:   {end_bal:.4f} DCC")
    print(f"Time:            {elapsed:.1f}s")
    print(f"Batches affordable: {int(end_bal / 0.051):,}")
    print(f"TX capacity:     {int(end_bal / 0.051) * 100:,}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
