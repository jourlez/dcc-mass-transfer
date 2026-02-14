#!/usr/bin/env python3
"""
Limited Blockchain Stress Test
Each wallet sends to a limited number of random recipients (as many as they can afford)
"""

import pywaves as pw
import csv
import sys
import os
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Configuration
DECENTRALCHAIN_NODE = 'https://mainnet-node.decentralchain.io'
CHAIN_ID = '?'
ASSET_ID = '4uPrGkQHQ1Jiimz4WQF2YXCoQTodJzNJW2rDestzpvGD'
AMOUNT_PER_TRANSFER = 0.1  # tokens
SENDS_PER_WALLET = 100  # Each wallet sends to 100 random others (needs 10 tokens)

# Performance settings
MAX_WORKERS = 30
RATE_LIMIT_DELAY = 0.03
MAX_RETRIES = 3

# Global stats
stats_lock = Lock()
stats = {
    'success': 0,
    'failed': 0,
    'retries': 0,
    'skipped': 0,
    'start_time': None
}

def no_aliases(self):
    """Dummy function to prevent alias fetching"""
    return []

def send_transfer(sender_address, recipient_address, asset, transfer_num, total_transfers):
    """Send individual transfer from one wallet to another"""
    amount = int(AMOUNT_PER_TRANSFER * 100000000)
    
    retries = 0
    while retries < MAX_RETRIES:
        try:
            result = sender_address.sendAsset(
                recipient=pw.Address(recipient_address),
                asset=asset,
                amount=amount,
                attachment=''
            )
            
            with stats_lock:
                stats['success'] += 1
                elapsed = time.time() - stats['start_time']
                progress = (stats['success'] / total_transfers) * 100
                tx_per_sec = stats['success'] / elapsed if elapsed > 0 else 0
            
            # Print progress every 50 transactions
            if stats['success'] % 50 == 0:
                print(f"✓ TX #{stats['success']}/{total_transfers} ({progress:.1f}%) | "
                      f"{tx_per_sec:.1f} tx/sec | Failed: {stats['failed']} | Skipped: {stats['skipped']}")
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            
            # Don't retry on insufficient balance or invalid addresses
            if "Insufficient" in error_msg or "Invalid address" in error_msg or "checksum" in error_msg:
                with stats_lock:
                    stats['skipped'] += 1
                return False
            
            retries += 1
            with stats_lock:
                stats['retries'] += 1
            
            if retries < MAX_RETRIES:
                time.sleep(1)
            else:
                with stats_lock:
                    stats['failed'] += 1
                if stats['failed'] % 50 == 0:
                    print(f"✗ Failed: {stats['failed']} total")
                return False
    
    return False

def main():
    # Set DecentralChain node
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)
    
    # Disable alias fetching
    pw.Address.aliases = no_aliases
    
    print(f"{'='*80}")
    print(f"LIMITED BLOCKCHAIN STRESS TEST")
    print(f"{'='*80}")
    print(f"Asset ID: {ASSET_ID}")
    print(f"Amount per transfer: {AMOUNT_PER_TRANSFER} tokens")
    print(f"Sends per wallet: {SENDS_PER_WALLET}")
    print(f"Max concurrent workers: {MAX_WORKERS}")
    print(f"{'='*80}\n")
    
    # Read wallet details
    wallet_details_file = 'real_wallets_2000_details.csv'
    
    if not os.path.exists(wallet_details_file):
        print(f"Error: File '{wallet_details_file}' not found")
        sys.exit(1)
    
    print(f"Reading wallet details...")
    wallets = []
    
    with open(wallet_details_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            wallets.append({
                'address': row['address'],
                'private_key': row['private_key']
            })
    
    num_wallets = len(wallets)
    print(f"Loaded {num_wallets} wallets")
    
    # Calculate total transactions
    total_transfers = num_wallets * SENDS_PER_WALLET
    print(f"\n{'='*80}")
    print(f"TEST PLAN:")
    print(f"  Each wallet sends to {SENDS_PER_WALLET} random other wallets")
    print(f"  Total transactions: {num_wallets} × {SENDS_PER_WALLET} = {total_transfers:,}")
    print(f"  Tokens needed per wallet: {SENDS_PER_WALLET * AMOUNT_PER_TRANSFER}")
    print(f"  Estimated time: ~{(total_transfers * RATE_LIMIT_DELAY / MAX_WORKERS / 60):.1f} minutes")
    print(f"{'='*80}\n")
    
    response = input("Start stress test? (yes/no): ")
    if response.lower() != 'yes':
        print("Test cancelled.")
        sys.exit(0)
    
    # Create Asset object
    asset = pw.Asset(ASSET_ID)
    
    print(f"\nStarting stress test...\n")
    
    stats['start_time'] = time.time()
    
    # Create list of all transfers
    transfers = []
    transfer_num = 0
    
    for sender_wallet in wallets:
        # Select random recipients for this sender
        other_wallets = [w for w in wallets if w['address'] != sender_wallet['address']]
        recipients = random.sample(other_wallets, min(SENDS_PER_WALLET, len(other_wallets)))
        
        sender_address = pw.Address(privateKey=sender_wallet['private_key'])
        
        for recipient_wallet in recipients:
            transfer_num += 1
            transfers.append({
                'num': transfer_num,
                'sender': sender_address,
                'recipient': recipient_wallet['address']
            })
    
    # Shuffle for better distribution
    random.shuffle(transfers)
    
    # Process transfers
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for transfer in transfers:
                future = executor.submit(
                    send_transfer,
                    transfer['sender'],
                    transfer['recipient'],
                    asset,
                    transfer['num'],
                    total_transfers
                )
                futures.append(future)
                time.sleep(RATE_LIMIT_DELAY)
            
            # Wait for completion
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"⚠️  Error: {e}")
                    
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Test interrupted!")
    
    end_time = time.time()
    elapsed = end_time - stats['start_time']
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"STRESS TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total transactions attempted: {total_transfers:,}")
    print(f"Successful:                   {stats['success']:,}")
    print(f"Failed:                       {stats['failed']:,}")
    print(f"Skipped (insufficient funds): {stats['skipped']:,}")
    print(f"Retries:                      {stats['retries']:,}")
    print(f"Success rate:                 {(stats['success']/total_transfers*100):.2f}%")
    print(f"Time elapsed:                 {elapsed:.2f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Average throughput:           {stats['success']/elapsed:.1f} tx/sec")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
