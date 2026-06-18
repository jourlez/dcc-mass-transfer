#!/usr/bin/env python3
"""
Individual Transfer Script
Sends individual transactions to each recipient (not mass transfer batches)
"""

import pywaves as pw
import csv
import sys
import os
from dotenv import load_dotenv; load_dotenv()
from config import resolve_node, resolve_chain_id, resolve_private_key
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Configuration
DECENTRALCHAIN_NODE = os.getenv('DCC_NODE') or resolve_node(silent=True)
CHAIN_ID = os.getenv('DCC_CHAIN_ID') or resolve_chain_id()


# Sender configuration
SENDER_PRIVATE_KEY = os.getenv('DCC_PRIVATE_KEY') or resolve_private_key()
ASSET_ID = os.getenv('DCC_ASSET_ID', '')

# Performance settings
MAX_WORKERS = 50  # Concurrent transfers
RATE_LIMIT_DELAY = 0.02  # Delay between transfers in seconds
MAX_RETRIES = 3

# Global stats
stats_lock = Lock()
stats = {
    'success': 0,
    'failed': 0,
    'retries': 0
}

def send_individual_transfer(sender_address, recipient_info, asset, transfer_num):
    """Send individual transfer to one recipient"""
    recipient_address = recipient_info['recipient']
    amount = recipient_info['amount']
    
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
            
            tx_id = result.get('id', 'N/A')
            print(f"✓ Transfer #{transfer_num}: {recipient_address} → {amount/100000000} tokens | TX: {tx_id}")
            return True
            
        except Exception as e:
            retries += 1
            with stats_lock:
                stats['retries'] += 1
            
            if retries < MAX_RETRIES:
                print(f"⚠ Transfer #{transfer_num} to {recipient_address} failed (attempt {retries}/{MAX_RETRIES}): {e}")
                time.sleep(1)
            else:
                print(f"✗ Transfer #{transfer_num} to {recipient_address} failed after {MAX_RETRIES} attempts: {e}")
                with stats_lock:
                    stats['failed'] += 1
                return False
    
    return False

def main():
    # Set DecentralChain node
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)
    
    # Display configuration
    print(f"{'='*70}")
    print(f"INDIVIDUAL TRANSFER SCRIPT")
    print(f"{'='*70}")
    
    sender_address = pw.Address(privateKey=SENDER_PRIVATE_KEY)
    print(f"Sender: {sender_address.address}")
    print(f"Asset ID: {ASSET_ID}")
    print(f"Max concurrent workers: {MAX_WORKERS}")
    print(f"{'='*70}\n")
    
    # Get CSV file
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'recipients.csv'
    
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    
    # Read recipients
    print(f"Reading recipients from {csv_file}...")
    recipients = []
    with open(csv_file, 'r', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].strip().startswith('#'):
                continue
            
            if len(row) >= 2:
                recipient_address = row[0].strip()
                amount = float(row[1].strip())
                amount_base_units = int(amount * 100000000)
                
                recipients.append({
                    'recipient': recipient_address,
                    'amount': amount_base_units
                })
    
    if not recipients:
        print("No recipients found in CSV file")
        sys.exit(1)
    
    total_recipients = len(recipients)
    print(f"Loaded {total_recipients} recipients")
    
    # Create Asset object
    asset = pw.Asset(ASSET_ID) if ASSET_ID else None

    # Cache isSmart() and script() to avoid redundant API calls per TX
    _cached_is_smart = asset.isSmart()
    _cached_script = sender_address.script()
    asset.isSmart = lambda: _cached_is_smart
    sender_address.script = lambda: _cached_script
    pw.OFFLINE = True
    
    print(f"\nStarting individual transfers...")
    print(f"Estimated time: ~{(total_recipients * RATE_LIMIT_DELAY):.1f} seconds\n")
    
    start_time = time.time()
    
    # Process transfers with thread pool
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        
        for i, recipient in enumerate(recipients, 1):
            future = executor.submit(
                send_individual_transfer,
                sender_address,
                recipient,
                asset,
                i
            )
            futures.append(future)
            time.sleep(RATE_LIMIT_DELAY)
        
        # Wait for all transfers to complete
        for future in as_completed(futures):
            future.result()
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total recipients:     {total_recipients}")
    print(f"Successful:           {stats['success']}")
    print(f"Failed:               {stats['failed']}")
    print(f"Retries:              {stats['retries']}")
    print(f"Time elapsed:         {elapsed:.2f} seconds")
    print(f"Throughput:           {stats['success']/elapsed:.1f} tx/sec")
    print(f"{'='*70}")
    
    if stats['failed'] > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
