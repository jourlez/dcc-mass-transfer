#!/usr/bin/env python3
"""
Single Transfer Engine — Individual 1-to-1 Transactions
=========================================================
Sends individual sendAsset() transactions (Type 4) to each recipient
instead of mass transfer batches. Dashboard-integrated with proper
logging to full_stress.log.

Fee: 0.001 DCC per transaction (vs 0.051 per 100-recipient batch).
Use when you need individual on-chain TX IDs per recipient.
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

MAX_WORKERS = int(os.getenv('MAX_WORKERS', '200'))
NUM_WALLETS = int(os.getenv('NUM_WALLETS', '100'))
SENDS_PER_WALLET = int(os.getenv('SENDS_PER_WALLET', '1'))
AMOUNT_PER_TX = 1  # base units
MAX_RETRIES = 3
RATE_LIMIT_DELAY = float(os.getenv('RATE_LIMIT_DELAY', '0'))

WORKSPACE = '/Users/mac/PY mass transfer script dcc'
LOG_FILE = os.path.join(WORKSPACE, 'full_stress.log')
WALLETS_CSV = os.path.join(WORKSPACE, 'real_wallets_2000_details.csv')

# ── Logging ────────────────────────────────────────────────────
with open(LOG_FILE, 'w') as f:
    pass

logger = logging.getLogger("single")
logger.setLevel(logging.INFO)
logger.handlers.clear()

_fh = logging.FileHandler(LOG_FILE, mode='a')
_fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logger.addHandler(_fh)
logger.propagate = False


def flush_log():
    for h in logger.handlers:
        h.flush()


# ── Shared State ───────────────────────────────────────────────
lock = Lock()
stats = {
    'success': 0,
    'failed': 0,
    'retries': 0,
    'balance_errors': 0,
}
stop_event = Event()


# ── Single TX Worker ───────────────────────────────────────────
def send_single(tx_num, total_tx, recipient_addr, sender, asset, start_time):
    """Send one individual transfer (Type 4)"""
    if stop_event.is_set():
        return

    retries = 0
    while retries < MAX_RETRIES:
        if stop_event.is_set():
            return
        try:
            result = sender.sendAsset(
                recipient=pw.Address(recipient_addr),
                asset=asset,
                amount=AMOUNT_PER_TX,
                attachment=''
            )
            tx_id = result.get('id', 'N/A')
            with lock:
                stats['success'] += 1
                current = stats['success'] + stats['failed']
                elapsed = time.time() - start_time
                rate = stats['success'] / elapsed if elapsed > 0 else 0

            # Log in dashboard-parseable format
            # Uses "TX #N" format that parse_log_line already handles
            logger.info(
                f"✓ TX #{current}/{total_tx} ({current/total_tx*100:.1f}%) | "
                f"{rate:.1f} tx/sec | to: {recipient_addr[:12]}… | "
                f"TX: {tx_id} | mode: REAL"
            )

            if current % 50 == 0:
                flush_log()
            return True

        except Exception as e:
            retries += 1
            err = str(e)

            if 'Insufficient' in err or 'negative waves balance' in err.lower():
                with lock:
                    stats['balance_errors'] += 1
                    stats['failed'] += 1
                logger.info(
                    f"✗ TX #{tx_num} failed | {recipient_addr[:12]}… | "
                    f"Insufficient balance | mode: REAL"
                )
                if stats['balance_errors'] >= 10:
                    logger.info("⚠ Too many balance errors — stopping")
                    stop_event.set()
                return False

            with lock:
                stats['retries'] += 1

            if retries < MAX_RETRIES:
                logger.info(
                    f"⚠ TX #{tx_num} retry {retries}/{MAX_RETRIES}: {err[:60]}"
                )
                time.sleep(0.5 * retries)
            else:
                with lock:
                    stats['failed'] += 1
                logger.info(
                    f"✗ TX #{tx_num} failed after {MAX_RETRIES} attempts: {err[:60]} | mode: REAL"
                )
                return False

    return False


# ── Main ───────────────────────────────────────────────────────
def main():
    pw.setNode(node=NODE, chain='custom', chain_id=CHAIN_ID)

    sender = pw.Address(privateKey=PRIVATE_KEY)
    asset = pw.Asset(ASSET_ID)

    # Cache isSmart() and script() results to avoid network calls per TX.
    # Without this, every sendAsset() call makes 3+ API requests,
    # overwhelming the node and causing SSL EOF errors.
    _cached_is_smart = asset.isSmart()
    _cached_script = sender.script()
    asset.isSmart = lambda: _cached_is_smart
    sender.script = lambda: _cached_script
    # Skip per-TX balance/asset checks (node rejects bad TX anyway)
    pw.OFFLINE = True

    # Load wallets
    addresses = []
    with open(WALLETS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            addr = row.get('address', '').strip()
            if addr:
                addresses.append(addr)

    if not addresses:
        logger.info("ERROR: No addresses found in CSV")
        return

    # Limit to NUM_WALLETS
    addresses = addresses[:NUM_WALLETS]

    # Build transfer list: each address × SENDS_PER_WALLET
    transfers = []
    for addr in addresses:
        for _ in range(SENDS_PER_WALLET):
            transfers.append(addr)

    total_tx = len(transfers)
    fee_per_tx = 0.001  # DCC
    total_fee = total_tx * fee_per_tx

    logger.info("=" * 70)
    logger.info("SINGLE TRANSFER ENGINE — Individual Type 4 Transactions")
    logger.info("=" * 70)
    logger.info(f"Sender: {sender.address}")
    logger.info(f"Asset:  {ASSET_ID}")
    logger.info(f"Wallets: {len(addresses)} | Sends/wallet: {SENDS_PER_WALLET}")
    logger.info(f"Total transfers: {total_tx:,}")
    logger.info(f"Workers: {MAX_WORKERS} | Rate delay: {RATE_LIMIT_DELAY}s")
    logger.info(f"Est. fee cost: {total_fee:.3f} DCC ({fee_per_tx} × {total_tx:,})")
    logger.info(f"Total recipients: {total_tx}")
    logger.info("=" * 70)
    flush_log()

    start_time = time.time()

    # Submit all transfers via thread pool
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i, addr in enumerate(transfers, 1):
            if stop_event.is_set():
                break
            future = executor.submit(
                send_single, i, total_tx, addr, sender, asset, start_time
            )
            futures.append(future)
            if RATE_LIMIT_DELAY > 0:
                time.sleep(RATE_LIMIT_DELAY)

        # Wait for completion
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                pass

    elapsed = time.time() - start_time
    rate = stats['success'] / elapsed if elapsed > 0 else 0
    success_rate = (stats['success'] / total_tx * 100) if total_tx > 0 else 0

    # Progress line for dashboard parser
    logger.info(
        f"📊 Progress: {stats['success'] + stats['failed']}/{total_tx} "
        f"({(stats['success'] + stats['failed'])/total_tx*100:.1f}%) | "
        f"{rate:,.1f} tx/sec | ETA: 0s"
    )

    # Summary (parsed by dashboard)
    logger.info("")
    logger.info("=" * 70)
    logger.info("SINGLE TRANSFER SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total recipients:     {total_tx}")
    logger.info(f"Successful:           {stats['success']}")
    logger.info(f"Failed:               {stats['failed']}")
    logger.info(f"Retries:              {stats['retries']}")
    logger.info(f"Balance errors:       {stats['balance_errors']}")
    logger.info(f"Time elapsed:         {elapsed:.2f} seconds")
    logger.info(f"Throughput:           {rate:.1f} tx/sec")
    logger.info(f"Success rate:         {success_rate:.1f}%")
    logger.info(f"Fee spent:            ~{stats['success'] * fee_per_tx:.3f} DCC")
    logger.info("=" * 70)
    flush_log()

    if stats['failed'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
