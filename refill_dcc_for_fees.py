#!/usr/bin/env python3
"""
Refill all 2000 wallets with DCC for transaction fees
"""

import os
import pywaves as pw
import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
DECENTRALCHAIN_NODE = 'https://mainnet-node.decentralchain.io'
CHAIN_ID = '?'
AMOUNT_PER_WALLET = 0.02  # DCC for transaction fees (20 transactions worth)

# Main sender with sufficient DCC balance
SENDER_PRIVATE_KEY = os.getenv('DCC_PRIVATE_KEY', 'YOUR_PRIVATE_KEY_HERE')

# Performance settings
MAX_WORKERS = 30
RATE_LIMIT_DELAY = 0.03

def no_aliases(self):
    """Dummy function to prevent alias fetching"""
    return []

def send_dcc(sender, recipient_address, amount, wallet_num, total_wallets):
    """Send DCC to a single wallet"""
    try:
        result = sender.sendWaves(
            recipient=pw.Address(recipient_address),
            amount=amount,
            attachment=''
        )
        
        tx_id = result.get('id', 'N/A')
        
        if wallet_num % 100 == 0:
            progress = (wallet_num / total_wallets) * 100
            print(f"✓ Wallet #{wallet_num}/{total_wallets} ({progress:.1f}%) | TX: {tx_id[:30]}...")
        
        time.sleep(RATE_LIMIT_DELAY)
        return True, None
        
    except Exception as e:
        return False, str(e)

def main():
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)
    pw.Address.aliases = no_aliases
    
    print(f"{'='*80}")
    print(f"DCC FEE REFILL OPERATION")
    print(f"{'='*80}")
    print(f"Amount per wallet: {AMOUNT_PER_WALLET} DCC")
    print(f"Max concurrent workers: {MAX_WORKERS}")
    print(f"{'='*80}\n")
    
    # Read wallet addresses
    wallet_file = 'real_wallets_2000.csv'
    
    try:
        recipients = []
        with open(wallet_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(',')
                    if len(parts) >= 1:
                        recipients.append(parts[0])
    except FileNotFoundError:
        print(f"Error: File '{wallet_file}' not found")
        sys.exit(1)
    
    print(f"Loaded {len(recipients)} recipient wallets\n")
    
    # Initialize sender
    sender = pw.Address(privateKey=SENDER_PRIVATE_KEY)
    amount = int(AMOUNT_PER_WALLET * 100000000)
    
    print(f"Total DCC to distribute: {AMOUNT_PER_WALLET * len(recipients):,.1f} DCC")
    print(f"Estimated time: ~{(len(recipients) * RATE_LIMIT_DELAY / 60):.1f} minutes\n")
    
    # Check sender balance
    try:
        balance = sender.balance() / 100000000
        print(f"Sender balance: {balance:.2f} DCC")
        required = AMOUNT_PER_WALLET * len(recipients)
        if balance < required:
            print(f"⚠ WARNING: Insufficient balance! Need {required:.1f} DCC, have {balance:.2f} DCC")
            sys.exit(1)
    except Exception as e:
        print(f"Warning: Could not check balance: {e}")
    
    response = input("\nStart DCC refill operation? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        sys.exit(0)
    
    print("\nStarting DCC refill...\n")
    start_time = time.time()
    
    success_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        
        for i, recipient in enumerate(recipients, 1):
            future = executor.submit(
                send_dcc,
                sender,
                recipient,
                amount,
                i,
                len(recipients)
            )
            futures.append(future)
        
        for future in as_completed(futures):
            success, error = future.result()
            if success:
                success_count += 1
            else:
                failed_count += 1
                if failed_count <= 10:
                    print(f"✗ Failed: {error[:60]}")
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*80}")
    print(f"DCC REFILL SUMMARY")
    print(f"{'='*80}")
    print(f"Total wallets:     {len(recipients)}")
    print(f"Successful:        {success_count}")
    print(f"Failed:            {failed_count}")
    print(f"Success rate:      {(success_count/len(recipients)*100):.1f}%")
    print(f"Time elapsed:      {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Average rate:      {success_count/elapsed:.1f} tx/sec")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
