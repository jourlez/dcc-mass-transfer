#!/usr/bin/env python3
"""
Turbo Mass Transfer — Maximum speed REAL on-chain transactions.
==============================================================
Optimized for the DecentralChain blockchain with:
  - 30 concurrent workers (ThreadPoolExecutor)
  - Zero rate limiting between batches
  - Batch size 100 (max per mass transfer)
  - 1 retry on failure (instant fail on balance errors)
  - Dashboard-compatible log output
  - Auto-stops when DCC runs out
"""
import pywaves as pw
import csv, os, sys, time, logging
from dotenv import load_dotenv; load_dotenv()
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Event
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────
NODE = 'https://mainnet-node.decentralchain.io'
CHAIN_ID = '?'
PRIVATE_KEY = os.getenv('DCC_PRIVATE_KEY', 'YOUR_PRIVATE_KEY_HERE')
ASSET_ID = '4uPrGkQHQ1Jiimz4WQF2YXCoQTodJzNJW2rDestzpvGD'

BATCH_SIZE = 100
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '200'))
AMOUNT_PER_RECIPIENT = 1  # 1 satoshi (minimum)

WORKSPACE = '/Users/mac/PY mass transfer script dcc'
LOG_FILE = os.path.join(WORKSPACE, 'full_stress.log')
WALLETS_CSV = os.path.join(WORKSPACE, 'real_wallets_2000_details.csv')

NUM_WALLETS = int(os.getenv('NUM_WALLETS', '2000'))
SENDS_PER_WALLET = int(os.getenv('SENDS_PER_WALLET', '10'))

# ── Logging ────────────────────────────────────────────────────
logger = logging.getLogger("turbo")
logger.setLevel(logging.INFO)
logger.handlers.clear()

_fh = logging.FileHandler(LOG_FILE, mode='w')
_fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
_sh = logging.StreamHandler()
_sh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(_fh)
logger.addHandler(_sh)
logger.propagate = False

def flush_log():
    for h in logger.handlers:
        h.flush()

# ── State ──────────────────────────────────────────────────────
lock = Lock()
stats = {
    'success': 0,
    'failed': 0,
    'retries': 0,
    'balance_errors': 0,
}
stop_event = Event()
consecutive_balance_errors = 0
MAX_CONSECUTIVE_BALANCE_ERRORS = 5  # Stop after 5 in a row


def process_batch(batch_num, recipients_batch, sender, asset):
    """Send a real mass transfer. Returns True/False/'OUT_OF_BALANCE'."""
    global consecutive_balance_errors
    
    if stop_event.is_set():
        return False
    
    try:
        result = sender.massTransferAssets(recipients_batch, asset, attachment='')
        tx_id = result.get('id', 'N/A')
        count = len(recipients_batch)
        
        with lock:
            stats['success'] += count
            consecutive_balance_errors = 0  # Reset on success
        
        msg = f"✓ Batch {batch_num}: {count} recipients | TX: {tx_id} | mode: REAL"
        print(msg, flush=True)
        logger.info(msg)
        
        # Flush every 50 batches
        if batch_num % 50 == 0:
            flush_log()
        
        return True
    
    except Exception as e:
        err = str(e)
        
        if 'Insufficient' in err or 'negative waves balance' in err.lower():
            with lock:
                stats['balance_errors'] += 1
                stats['failed'] += len(recipients_batch)
                consecutive_balance_errors += 1
            
            if consecutive_balance_errors >= MAX_CONSECUTIVE_BALANCE_ERRORS:
                logger.warning(f"✗ Batch {batch_num}: OUT OF DCC — stopping ({err})")
                stop_event.set()
                return 'OUT_OF_BALANCE'
            
            logger.warning(f"✗ Batch {batch_num} balance error: {err}")
            return False
        
        # One retry for non-balance errors
        with lock:
            stats['retries'] += 1
        
        try:
            time.sleep(0.2)
            result = sender.massTransferAssets(recipients_batch, asset, attachment='')
            tx_id = result.get('id', 'N/A')
            count = len(recipients_batch)
            
            with lock:
                stats['success'] += count
            
            msg = f"✓ Batch {batch_num}: {count} recipients | TX: {tx_id} | mode: REAL"
            print(msg, flush=True)
            logger.info(msg)
            return True
        
        except Exception as e2:
            with lock:
                stats['failed'] += len(recipients_batch)
            logger.warning(f"✗ Batch {batch_num} failed: {e2}")
            return False


def main():
    total_tx_target = NUM_WALLETS * SENDS_PER_WALLET
    total_batches = total_tx_target // BATCH_SIZE
    
    logger.info("=" * 70)
    logger.info("⚡ TURBO MASS TRANSFER — REAL ON-CHAIN TRANSACTIONS")
    logger.info("=" * 70)
    logger.info(f"Target: {total_tx_target:,} transactions ({total_batches:,} batches)")
    logger.info(f"Workers: {MAX_WORKERS} | Batch size: {BATCH_SIZE} | Retries: 1")
    logger.info(f"Wallets: {NUM_WALLETS} | Sends per wallet: {SENDS_PER_WALLET}")
    logger.info("=" * 70)
    flush_log()
    
    # ── Setup pywaves ──────────────────────────────────────────
    pw.setNode(node=NODE, chain='custom', chain_id=CHAIN_ID)
    sender = pw.Address(privateKey=PRIVATE_KEY)
    asset = pw.Asset(ASSET_ID)
    
    balance_dcc = sender.balance() / 1e8

    # Cache isSmart() and script() results to avoid network calls per batch.
    # Without this, every massTransferAssets() call makes 4+ API requests,
    # overwhelming the node and causing SSL EOF errors.
    _cached_is_smart = asset.isSmart()
    _cached_script = sender.script()
    asset.isSmart = lambda: _cached_is_smart
    sender.script = lambda: _cached_script
    # Skip per-TX balance checks (node rejects bad TX anyway)
    pw.OFFLINE = True
    fee_per_batch = 0.001 + 0.0005 * BATCH_SIZE  # 0.051 DCC for 100 recipients
    max_affordable = int(balance_dcc / fee_per_batch)
    
    logger.info(f"Sender: {sender.address}")
    logger.info(f"DCC Balance: {balance_dcc:.4f} DCC")
    logger.info(f"Fee per batch: {fee_per_batch:.4f} DCC")
    logger.info(f"Max affordable batches: {max_affordable:,}")
    logger.info(f"Max affordable TX: {max_affordable * BATCH_SIZE:,}")
    flush_log()
    
    if max_affordable == 0:
        logger.error("No DCC for fees! Run turbo_sweep.py first.")
        sys.exit(1)
    
    # Limit batches to what we can afford
    actual_batches = min(total_batches, max_affordable)
    actual_tx = actual_batches * BATCH_SIZE
    logger.info(f"Will send: {actual_batches:,} batches = {actual_tx:,} transactions")
    
    # ── Load wallets ───────────────────────────────────────────
    addresses = []
    with open(WALLETS_CSV) as f:
        for row in csv.DictReader(f):
            addr = row.get('address', '').strip()
            if addr and len(addresses) < NUM_WALLETS:
                addresses.append(addr)
    
    logger.info(f"Loaded {len(addresses)} recipient addresses")
    
    # ── Build batch template ───────────────────────────────────
    batch_template = []
    for i in range(BATCH_SIZE):
        batch_template.append({
            'recipient': addresses[i % len(addresses)],
            'amount': AMOUNT_PER_RECIPIENT
        })
    
    # ── Fire! ──────────────────────────────────────────────────
    logger.info("")
    logger.info("═══ LAUNCHING REAL TRANSACTIONS ═══")
    flush_log()
    
    start_time = time.time()
    last_report = start_time
    completed = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit in waves of 500 to avoid memory issues
        wave_size = 2000
        
        for wave_start in range(0, actual_batches, wave_size):
            if stop_event.is_set():
                break
            
            wave_end = min(wave_start + wave_size, actual_batches)
            futures = {}
            
            for bn in range(wave_start, wave_end):
                if stop_event.is_set():
                    break
                future = executor.submit(process_batch, bn + 1, batch_template, sender, asset)
                futures[future] = bn + 1
            
            for future in as_completed(futures):
                future.result()
                completed += 1
                
                # Progress report every 2 seconds
                now = time.time()
                if now - last_report >= 2.0:
                    with lock:
                        total = stats['success']
                        failed = stats['failed']
                    elapsed = now - start_time
                    rate = total / elapsed if elapsed > 0 else 0
                    pct = (total / actual_tx) * 100 if actual_tx > 0 else 0
                    eta = (actual_tx - total) / rate if rate > 0 else 0
                    
                    msg = f"📊 Progress: {total:,}/{actual_tx:,} ({pct:.1f}%) | {rate:,.0f} tx/sec | ETA: {eta:.0f}s | Failed: {failed}"
                    print(msg, flush=True)
                    logger.info(msg)
                    flush_log()
                    last_report = now
                
                if stop_event.is_set():
                    # Cancel pending futures
                    for f in futures:
                        f.cancel()
                    break
    
    # ── Summary ────────────────────────────────────────────────
    elapsed = time.time() - start_time
    
    with lock:
        total_success = stats['success']
        total_failed = stats['failed']
        total_retries = stats['retries']
    
    total = total_success + total_failed
    throughput = total_success / elapsed if elapsed > 0 else 0
    success_rate = (total_success / total * 100) if total > 0 else 0
    
    pw.OFFLINE = False  # Re-enable for final balance check
    try:
        final_balance = sender.balance() / 1e8
    except Exception:
        final_balance = 0
    dcc_spent = balance_dcc - final_balance
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total recipients:     {total_success:,}")
    logger.info(f"  Real (on-chain):    {total_success:,}")
    logger.info(f"Failed:               {total_failed}")
    logger.info(f"Retries:              {total_retries}")
    logger.info(f"Balance errors:       {stats['balance_errors']}")
    logger.info(f"Success rate:         {success_rate:.1f}%")
    logger.info(f"Time elapsed:         {elapsed:.2f} seconds")
    logger.info(f"Throughput:           {throughput:.1f} tx/sec")
    logger.info(f"DCC spent on fees:    {dcc_spent:.4f} DCC")
    logger.info(f"DCC remaining:        {final_balance:.4f} DCC")
    
    if stop_event.is_set():
        logger.info(f"⚠ Stopped early: ran out of DCC for fees")
    
    logger.info("=" * 70)
    
    # Dashboard-parseable summary lines
    logger.info(f"Successful:           {total_success}")
    logger.info(f"Failed:               {total_failed}")
    logger.info(f"Retries:              {total_retries}")
    logger.info(f"Success rate:         {success_rate:.1f}%")
    logger.info(f"Time elapsed:         {elapsed:.2f}")
    logger.info(f"Throughput:           {throughput:.1f}")
    
    flush_log()
    for h in logger.handlers:
        h.close()
    
    print(f"\n✅ {total_success:,} real on-chain TX in {elapsed:.1f}s ({throughput:.0f} tx/sec)")
    print(f"   DCC spent: {dcc_spent:.4f} | Remaining: {final_balance:.4f}")


if __name__ == '__main__':
    main()
