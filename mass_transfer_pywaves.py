#!/usr/bin/env python3
"""
DecentralChain Mass Transfer Script using PyWaves-CE
Sends assets to multiple recipients from a CSV file
High-performance version for processing 5000+ transactions
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

PRIVATE_KEY = os.getenv('DCC_PRIVATE_KEY') or resolve_private_key()
ASSET_ID = os.getenv('DCC_ASSET_ID', '')

# Performance settings
USE_MASS_TRANSFER = True  # Use mass transfer for efficiency
BATCH_SIZE = 100  # Recipients per mass transfer transaction (max is typically 100)
MAX_WORKERS = 10  # Concurrent transactions
RATE_LIMIT_DELAY = 0.1  # Delay between batches in seconds
MAX_RETRIES = 3  # Retry failed transactions

# Global counters
stats_lock = Lock()
stats = {
    'success': 0,
    'failed': 0,
    'retries': 0
}

def process_batch(batch_num, recipients_batch, myAddress, asset):
    """Process a batch of recipients with mass transfer"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            result = myAddress.massTransferAssets(recipients_batch, asset, attachment='')
            
            with stats_lock:
                stats['success'] += len(recipients_batch)
            
            tx_id = result.get('id', 'N/A')
            print(f"✓ Batch {batch_num}: {len(recipients_batch)} recipients | TX: {tx_id}")
            return True
            
        except Exception as e:
            retries += 1
            with stats_lock:
                stats['retries'] += 1
            
            if retries < MAX_RETRIES:
                print(f"⚠ Batch {batch_num} failed (attempt {retries}/{MAX_RETRIES}): {e}")
                time.sleep(1)  # Wait before retry
            else:
                print(f"✗ Batch {batch_num} failed after {MAX_RETRIES} attempts: {e}")
                with stats_lock:
                    stats['failed'] += len(recipients_batch)
                return False
    
    return False


def main():
    # Set DecentralChain node with custom chain ID (63 = '?', DecentralChain uses 3D prefix)
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)
    
    # Create address from private key
    myAddress = pw.Address(privateKey=PRIVATE_KEY)
    print(f"Sender address: {myAddress.address}")
    print(f"Configuration: Batch size={BATCH_SIZE}, Workers={MAX_WORKERS}")
    
    # Get CSV file path from command line or use default
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'recipients.csv'
    
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    
    # Read recipients from CSV
    print(f"\nReading recipients from {csv_file}...")
    recipients = []
    with open(csv_file, 'r', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            # Skip empty lines and comments
            if not row or row[0].strip().startswith('#'):
                continue
            
            if len(row) >= 2:
                recipient_address = row[0].strip()
                amount = float(row[1].strip())
                # Convert to smallest units (multiply by 10^8 for 8 decimals)
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

    # Cache isSmart() and script() to avoid redundant API calls per batch
    _cached_is_smart = asset.isSmart()
    _cached_script = myAddress.script()
    asset.isSmart = lambda: _cached_is_smart
    myAddress.script = lambda: _cached_script
    pw.OFFLINE = True
    
    # Split recipients into batches
    batches = []
    for i in range(0, total_recipients, BATCH_SIZE):
        batch = recipients[i:i + BATCH_SIZE]
        batches.append(batch)
    
    total_batches = len(batches)
    print(f"Split into {total_batches} batches of up to {BATCH_SIZE} recipients each")
    print(f"\nStarting mass transfer to {total_recipients} recipients...")
    print(f"Estimated time: ~{(total_batches * RATE_LIMIT_DELAY):.1f} seconds\n")
    
    start_time = time.time()
    
    if USE_MASS_TRANSFER:
        # Process batches concurrently
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for batch_num, batch in enumerate(batches, 1):
                future = executor.submit(process_batch, batch_num, batch, myAddress, asset)
                futures.append(future)
                
                # Rate limiting: add delay between batch submissions
                if batch_num % MAX_WORKERS == 0:
                    time.sleep(RATE_LIMIT_DELAY)
            
            # Wait for all batches to complete
            for future in as_completed(futures):
                future.result()
    else:
        # Individual sends (slower, for compatibility)
        print("Sending assets individually...")
        for i, transfer in enumerate(recipients, 1):
            recipient_addr = pw.Address(transfer['recipient'])
            amount = transfer['amount']
            
            try:
                result = myAddress.sendAsset(recipient_addr, asset, amount, attachment='')
                with stats_lock:
                    stats['success'] += 1
                
                if i % 10 == 0:
                    print(f"Progress: {i}/{total_recipients}")
            except Exception as e:
                print(f"✗ Failed {i}: {transfer['recipient']}: {e}")
                with stats_lock:
                    stats['failed'] += 1
    
    elapsed_time = time.time() - start_time
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total recipients:     {total_recipients}")
    print(f"Successful:           {stats['success']}")
    print(f"Failed:               {stats['failed']}")
    print(f"Retries:              {stats['retries']}")
    print(f"Time elapsed:         {elapsed_time:.2f} seconds")
    print(f"Throughput:           {stats['success'] / elapsed_time:.1f} tx/sec")
    print(f"{'='*60}")
    
    if stats['failed'] > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
