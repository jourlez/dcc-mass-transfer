#!/usr/bin/env python3
"""
Multi-Sender Mass Transfer with JSON Config
Load sender accounts from senders.json file
"""

import pywaves as pw
import csv
import sys
import os
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Configuration
DECENTRALCHAIN_NODE = 'https://mainnet-node.decentralchain.io'
CHAIN_ID = '?'
SENDERS_CONFIG_FILE = 'senders.json'
ASSET_ID = '4uPrGkQHQ1Jiimz4WQF2YXCoQTodJzNJW2rDestzpvGD'

# Performance settings
BATCH_SIZE = 100
MAX_WORKERS_PER_SENDER = 5
RATE_LIMIT_DELAY = 0.05
MAX_RETRIES = 3

# Global stats
stats_lock = Lock()
stats = {
    'success': 0,
    'failed': 0,
    'retries': 0,
    'by_sender': {}
}

def load_senders(config_file):
    """Load sender accounts from JSON config file"""
    if not os.path.exists(config_file):
        print(f"Error: Config file '{config_file}' not found")
        print(f"Creating template file...")
        
        template = [
            {
                "private_key": "YOUR_PRIVATE_KEY_HERE",
                "name": "Sender 1",
                "enabled": True
            }
        ]
        
        with open(config_file, 'w') as f:
            json.dump(template, f, indent=4)
        
        print(f"✓ Created {config_file}")
        print(f"Please edit it with your private keys and run again.")
        sys.exit(1)
    
    with open(config_file, 'r') as f:
        senders = json.load(f)
    
    # Filter only enabled senders
    enabled_senders = [s for s in senders if s.get('enabled', True)]
    
    if not enabled_senders:
        print("Error: No enabled senders found in config file")
        sys.exit(1)
    
    return enabled_senders

def init_sender_stats(senders):
    """Initialize stats for each sender"""
    with stats_lock:
        for sender in senders:
            stats['by_sender'][sender['name']] = {
                'success': 0,
                'failed': 0,
                'batches': 0
            }

def process_batch(sender_info, batch_num, recipients_batch, asset):
    """Process a batch of recipients with mass transfer from specific sender"""
    sender_name = sender_info['name']
    private_key = sender_info['private_key']
    
    myAddress = pw.Address(privateKey=private_key)
    
    retries = 0
    while retries < MAX_RETRIES:
        try:
            result = myAddress.massTransferAssets(recipients_batch, asset, attachment='')
            
            with stats_lock:
                stats['success'] += len(recipients_batch)
                stats['by_sender'][sender_name]['success'] += len(recipients_batch)
                stats['by_sender'][sender_name]['batches'] += 1
            
            tx_id = result.get('id', 'N/A')
            print(f"✓ [{sender_name}] Batch {batch_num}: {len(recipients_batch)} recipients | TX: {tx_id}")
            return True
            
        except Exception as e:
            retries += 1
            with stats_lock:
                stats['retries'] += 1
            
            if retries < MAX_RETRIES:
                print(f"⚠ [{sender_name}] Batch {batch_num} failed (attempt {retries}/{MAX_RETRIES}): {e}")
                time.sleep(1)
            else:
                print(f"✗ [{sender_name}] Batch {batch_num} failed after {MAX_RETRIES} attempts: {e}")
                with stats_lock:
                    stats['failed'] += len(recipients_batch)
                    stats['by_sender'][sender_name]['failed'] += len(recipients_batch)
                return False
    
    return False

def distribute_batches(batches, num_senders):
    """Distribute batches evenly across senders"""
    sender_batches = [[] for _ in range(num_senders)]
    
    for idx, batch in enumerate(batches):
        sender_idx = idx % num_senders
        sender_batches[sender_idx].append(batch)
    
    return sender_batches

def main():
    # Set DecentralChain node
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)
    
    # Load senders from config
    senders = load_senders(SENDERS_CONFIG_FILE)
    
    # Initialize stats
    init_sender_stats(senders)
    
    # Display sender information
    print(f"{'='*70}")
    print(f"MULTI-SENDER MASS TRANSFER")
    print(f"{'='*70}")
    print(f"Active senders: {len(senders)}")
    
    for i, sender in enumerate(senders, 1):
        addr = pw.Address(privateKey=sender['private_key'])
        print(f"  {i}. {sender['name']}: {addr.address}")
    
    print(f"\nConfiguration:")
    print(f"  Batch size: {BATCH_SIZE}")
    print(f"  Workers per sender: {MAX_WORKERS_PER_SENDER}")
    print(f"  Total concurrent workers: {len(senders) * MAX_WORKERS_PER_SENDER}")
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
    asset = pw.Asset(ASSET_ID)
    
    # Split into batches
    batches = []
    for i in range(0, total_recipients, BATCH_SIZE):
        batch = recipients[i:i + BATCH_SIZE]
        batches.append(batch)
    
    total_batches = len(batches)
    print(f"Split into {total_batches} batches of up to {BATCH_SIZE} recipients each")
    
    # Distribute batches across senders
    sender_batches = distribute_batches(batches, len(senders))
    
    print(f"\nBatch distribution:")
    for i, sender in enumerate(senders):
        print(f"  {sender['name']}: {len(sender_batches[i])} batches ({len(sender_batches[i]) * BATCH_SIZE} max recipients)")
    
    # Calculate theoretical throughput
    theoretical_throughput = (len(senders) * MAX_WORKERS_PER_SENDER * BATCH_SIZE) / RATE_LIMIT_DELAY
    print(f"\nTheoretical max throughput: ~{theoretical_throughput:.0f} tx/sec")
    print(f"Starting multi-sender mass transfer...\n")
    
    start_time = time.time()
    
    # Process all senders concurrently
    with ThreadPoolExecutor(max_workers=len(senders) * MAX_WORKERS_PER_SENDER) as executor:
        futures = []
        
        for sender_idx, sender in enumerate(senders):
            for batch_idx, batch in enumerate(sender_batches[sender_idx], 1):
                future = executor.submit(
                    process_batch,
                    sender,
                    f"{sender['name']}-{batch_idx}",
                    batch,
                    asset
                )
                futures.append(future)
                
                # Rate limiting
                if len(futures) % MAX_WORKERS_PER_SENDER == 0:
                    time.sleep(RATE_LIMIT_DELAY)
        
        # Wait for all to complete
        for future in as_completed(futures):
            future.result()
    
    elapsed_time = time.time() - start_time
    
    # Print detailed summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total recipients:     {total_recipients}")
    print(f"Successful:           {stats['success']}")
    print(f"Failed:               {stats['failed']}")
    print(f"Retries:              {stats['retries']}")
    print(f"Time elapsed:         {elapsed_time:.2f} seconds")
    print(f"Actual throughput:    {stats['success'] / elapsed_time:.1f} tx/sec")
    print(f"\nPer-Sender Statistics:")
    print(f"{'-'*70}")
    
    for sender in senders:
        sender_stats = stats['by_sender'][sender['name']]
        print(f"{sender['name']}:")
        print(f"  Batches processed: {sender_stats['batches']}")
        print(f"  Successful:        {sender_stats['success']}")
        print(f"  Failed:            {sender_stats['failed']}")
        if elapsed_time > 0:
            print(f"  Throughput:        {sender_stats['success'] / elapsed_time:.1f} tx/sec")
    
    print(f"{'='*70}")
    
    if stats['failed'] > 0:
        sys.exit(1)

if __name__ == '__main__':
    main()
