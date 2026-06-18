#!/usr/bin/env python3
"""
Blockchain Stress Test - All Wallets Send to Each Other
Each of the 2000 wallets sends 2 tokens to every other wallet
Total transactions: 2000 × 1999 = 3,998,000 transactions
"""

import pywaves as pw
import csv
import sys
import os
from dotenv import load_dotenv; load_dotenv()
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from threading import Lock
import random
from config import validate_config

# ── Validation ─────────────────────────────────────────────────
validate_config(require_private_key=True, require_node=True)

# Configuration
DECENTRALCHAIN_NODE = os.getenv('DCC_NODE') or resolve_node(silent=True)
CHAIN_ID = os.getenv('DCC_CHAIN_ID') or resolve_chain_id()


ASSET_ID = os.getenv('DCC_ASSET_ID', '')
AMOUNT_PER_TRANSFER = 0.001  # tokens

# Performance settings (tuned for higher throughput + adaptive backoff)
# NOTE: Increasing workers may hit node rate limits; controller will adapt
MAX_WORKERS = 500  # aggressive concurrency (will be adaptively throttled)
INITIAL_DELAY = 0.001  # initial per-request delay (seconds)
MAX_DELAY = 2.0  # max backoff delay
MIN_DELAY = 0.0005
MAX_RETRIES = 3

# Global stats
stats_lock = Lock()
stats = {
    'success': 0,
    'failed': 0,
    'retries': 0,
    'start_time': None
}


class RateController:
    """Adaptive delay controller shared across workers to back off on node errors."""
    def __init__(self, initial=INITIAL_DELAY, minimum=MIN_DELAY, maximum=MAX_DELAY):
        self.delay = initial
        self.min = minimum
        self.max = maximum
        self.lock = Lock()

    def get_delay(self):
        with self.lock:
            return self.delay

    def increase(self):
        with self.lock:
            # multiplicative backoff
            self.delay = min(self.max, max(self.min, self.delay * 2))

    def decrease(self):
        with self.lock:
            # faster decay toward min on sustained success
            self.delay = max(self.min, self.delay * 0.6)


rate_controller = RateController()

def send_transfer(sender_address, recipient_address, asset, transfer_num, total_transfers):
    """Send individual transfer from one wallet to another.
    `recipient_address` must be a `pw.Address` object (pre-created).
    Uses `rate_controller` to adapt to node rate limits.
    """
    amount = int(AMOUNT_PER_TRANSFER * 100000000)

    retries = 0
    while retries < MAX_RETRIES:
        try:
            # Respect adaptive delay before sending
            delay = rate_controller.get_delay()
            if delay:
                time.sleep(delay)

            result = sender_address.sendAsset(
                recipient=recipient_address,
                asset=asset,
                amount=amount,
                attachment=''
            )

            # On success, slightly reduce global delay
            rate_controller.decrease()

            with stats_lock:
                stats['success'] += 1
                elapsed = time.time() - stats['start_time']
                progress = (stats['success'] / total_transfers) * 100
                tx_per_sec = stats['success'] / elapsed if elapsed > 0 else 0

            tx_id = result.get('id', 'N/A')

            # Print progress every 1000 transactions to reduce IO overhead
            if stats['success'] % 1000 == 0:
                print(f"✓ TX #{stats['success']}/{total_transfers} ({progress:.1f}%) | "
                      f"{tx_per_sec:.1f} tx/sec | Failed: {stats['failed']} | Retries: {stats['retries']} | Delay: {rate_controller.get_delay():.4f}s")

            return True

        except Exception as e:
            error_msg = str(e)

            # Fatal errors: don't retry
            if "Insufficient" in error_msg or "Asset not issued" in error_msg or "not found" in error_msg.lower():
                with stats_lock:
                    stats['failed'] += 1
                return False

            # Node rate-limit / state errors -> increase global delay
            if any(x in error_msg.lower() for x in ["state check failed", "rate limit", "too many requests", "failed to decode", "connection reset", "temporary" ]):
                rate_controller.increase()

            retries += 1
            with stats_lock:
                stats['retries'] += 1

            # Shorter retry waits (adaptive)
            time.sleep(rate_controller.get_delay() or 0.5)

    # Exhausted retries
    with stats_lock:
        stats['failed'] += 1
    if stats['failed'] % 100 == 0:
        print(f"✗ Failed: {stats['failed']} total | Recent error: {error_msg[:50]}")
    return False

def no_aliases(self):
    """Dummy function to prevent alias fetching"""
    return []

def main():
    # Set DecentralChain node
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)
    
    # Disable alias fetching to avoid node timeouts
    pw.Address.aliases = no_aliases
    
    print(f"{'='*80}")
    print(f"BLOCKCHAIN STRESS TEST - ALL WALLETS SENDING TO EACH OTHER")
    print(f"{'='*80}")
    print(f"Asset ID: {ASSET_ID}")
    print(f"Amount per transfer: {AMOUNT_PER_TRANSFER} tokens")
    print(f"Max concurrent workers: {MAX_WORKERS}")
    print(f"{'='*80}\n")
    
    # Read wallet details (with private keys)
    wallet_details_file = 'real_wallets_2000_details.csv'
    
    if not os.path.exists(wallet_details_file):
        print(f"Error: File '{wallet_details_file}' not found")
        print("This file should contain wallet addresses with their private keys")
        sys.exit(1)
    
    print(f"Reading wallet details from {wallet_details_file}...")
    wallets = []
    
    with open(wallet_details_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            wallets.append({
                'address': row['address'],
                'private_key': row['private_key']
            })
    
    num_wallets = len(wallets)
    print(f"Loaded {num_wallets} wallets with private keys")
    
    # Calculate total transactions
    total_transfers = num_wallets * (num_wallets - 1)
    print(f"\n{'='*80}")
    print(f"STRESS TEST PLAN:")
    print(f"  Each wallet sends to {num_wallets - 1} other wallets")
    print(f"  Total transactions: {num_wallets} × {num_wallets - 1} = {total_transfers:,}")
    # Use initial delay estimate for the rough estimate printed here
    print(f"  Estimated time at {MAX_WORKERS} concurrent (rough): ~{(total_transfers * INITIAL_DELAY / MAX_WORKERS / 60):.1f} minutes")
    print(f"  Total tokens to be transferred: {total_transfers * AMOUNT_PER_TRANSFER:,}")
    print(f"{'='*80}\n")
    
    print("⚠️  WARNING: This is a massive blockchain stress test!")
    print("⚠️  Note: Some wallets may run out of tokens during the test.")
    print(f"⚠️  Each wallet needs {(num_wallets - 1) * AMOUNT_PER_TRANSFER:,} tokens to complete all sends.\n")
    
    response = input("This will create a massive number of transactions. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Stress test cancelled.")
        sys.exit(0)
    
    # Create Asset object - verify it exists
    try:
        asset = pw.Asset(ASSET_ID) if ASSET_ID else None
        print(f"Asset loaded: {asset.name if hasattr(asset, 'name') else 'Token'}")
    except Exception as e:
        print(f"Error loading asset: {e}")
        print("Continuing anyway...")
        asset = pw.Asset(ASSET_ID) if ASSET_ID else None
    
    print(f"\nStarting stress test...\n")
    
    stats['start_time'] = time.time()
    
    # Pre-create Address objects for all wallets (senders + recipients)
    wallet_addresses = {}
    for i, w in enumerate(wallets, 1):
        try:
            wallet_addresses[w['address']] = pw.Address(privateKey=w['private_key'])
        except Exception as e:
            print(f"⚠ Skipping wallet {w['address'][:12]}: {e}")

    # Recompute number of valid wallets and total transfers
    valid_wallets = list(wallet_addresses.keys())
    num_valid = len(valid_wallets)
    total_transfers = num_valid * (num_valid - 1)

    print(f"Using {num_valid} valid wallets -> total {total_transfers:,} transfers")

    # Process transfers with a ThreadPoolExecutor using a submission window
    running = set()
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            transfer_num = 0

            for sender_addr in valid_wallets:
                sender_obj = wallet_addresses[sender_addr]

                for recipient_addr in valid_wallets:
                    if sender_addr == recipient_addr:
                        continue

                    transfer_num += 1
                    recipient_obj = wallet_addresses[recipient_addr]

                    fut = executor.submit(
                        send_transfer,
                        sender_obj,
                        recipient_obj,
                        asset,
                        transfer_num,
                        total_transfers
                    )
                    running.add(fut)

                    # Keep a reasonable window of outstanding futures to avoid memory growth
                    # widen window to allow more pipelining when node accepts it
                    if len(running) >= MAX_WORKERS * 5:
                        done, running = wait(running, return_when='FIRST_COMPLETED')
                        # consume results of completed futures
                        for d in done:
                            try:
                                d.result()
                            except Exception:
                                pass

            # Wait for remaining futures
            for fut in as_completed(running):
                try:
                    fut.result()
                except Exception:
                    pass

    except KeyboardInterrupt:
        print(f"\n\n⚠️  Stress test interrupted by user!")
        print(f"Completed {stats['success']:,} transactions before stopping.")
    
    end_time = time.time()
    elapsed = end_time - stats['start_time']
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"STRESS TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total transactions attempted: {total_transfers:,}")
    print(f"Successful:                   {stats['success']:,}")
    print(f"Failed:                       {stats['failed']:,}")
    print(f"Retries:                      {stats['retries']:,}")
    print(f"Success rate:                 {(stats['success']/total_transfers*100):.2f}%")
    print(f"Time elapsed:                 {elapsed:.2f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Average throughput:           {stats['success']/elapsed:.1f} tx/sec")
    print(f"{'='*80}")
    
    if stats['failed'] > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
