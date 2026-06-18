#!/usr/bin/env python3
"""
Refill all 2000 wallets with additional tokens for stress testing
"""

import os
from dotenv import load_dotenv; load_dotenv()
import pywaves as pw
import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import validate_config

# ── Validation ─────────────────────────────────────────────────
validate_config(require_private_key=True, require_node=True)

# Configuration
DECENTRALCHAIN_NODE = os.getenv('DCC_NODE') or resolve_node(silent=True)
CHAIN_ID = os.getenv('DCC_CHAIN_ID') or resolve_chain_id()
ASSET_ID = os.getenv('DCC_ASSET_ID', '')
AMOUNT_PER_WALLET = 0.002  # tokens to add to each wallet (enough for 10+ transactions)

# All sender private keys for distribution (set via environment variables)
SENDER_PRIVATE_KEYS = [
    os.getenv('DCC_PRIVATE_KEY_1', 'YOUR_PRIVATE_KEY_1_HERE'),  # Sender 1
    os.getenv('DCC_PRIVATE_KEY_2', 'YOUR_PRIVATE_KEY_2_HERE'),  # Sender 2
    os.getenv('DCC_PRIVATE_KEY_3', 'YOUR_PRIVATE_KEY_3_HERE'),  # Sender 3
    os.getenv('DCC_PRIVATE_KEY_4', 'YOUR_PRIVATE_KEY_4_HERE'),  # Sender 4
    os.getenv('DCC_PRIVATE_KEY_5', 'YOUR_PRIVATE_KEY_5_HERE'),  # Sender 5
]

# Performance settings
MAX_WORKERS = 50
RATE_LIMIT_DELAY = 0.02

def no_aliases(self):
    """Dummy function to prevent alias fetching"""
    return []

def send_to_wallet(sender, recipient_address, asset, amount, wallet_num, total_wallets, sender_num):
    """Send tokens to a single wallet"""
    try:
        if ASSET_ID:  # Send tokens
            result = sender.sendAsset(
                recipient=pw.Address(recipient_address),
                asset=asset,
                amount=amount,
                attachment=''
            )
        else:  # Send native DCC
            result = sender.sendWaves(
                recipient=pw.Address(recipient_address),
                amount=amount,
                attachment=''
            )
        
        tx_id = result.get('id', 'N/A')
        
        if wallet_num % 100 == 0:
            progress = (wallet_num / total_wallets) * 100
            print(f"✓ Wallet #{wallet_num}/{total_wallets} ({progress:.1f}%) | Sender {sender_num} | TX: {tx_id[:30]}...")
        
        time.sleep(RATE_LIMIT_DELAY)
        return True, None
        
    except Exception as e:
        return False, str(e)

def main():
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)
    pw.Address.aliases = no_aliases
    
    print(f"{'='*80}")
    print(f"WALLET REFILL OPERATION")
    print(f"{'='*80}")
    print(f"Asset ID: {ASSET_ID}")
    print(f"Amount per wallet: {AMOUNT_PER_WALLET} tokens")
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
                    # Format: address,amount
                    parts = line.split(',')
                    if len(parts) >= 1:
                        recipients.append(parts[0])
    except FileNotFoundError:
        print(f"Error: File '{wallet_file}' not found")
        sys.exit(1)
    
    print(f"Loaded {len(recipients)} recipient wallets\n")
    
    # Initialize all senders
    senders = [pw.Address(privateKey=key) for key in SENDER_PRIVATE_KEYS]
    asset = pw.Asset(ASSET_ID) if ASSET_ID else None
    amount = int(AMOUNT_PER_WALLET * 100000000)
    
    print(f"Using {len(senders)} senders for distribution")
    print(f"Currency: {'Native DCC' if not ASSET_ID else 'Token ' + ASSET_ID}")
    print(f"Total to distribute: {AMOUNT_PER_WALLET * len(recipients):,.0f} {'DCC' if not ASSET_ID else 'tokens'}")
    print(f"Per sender: ~{(AMOUNT_PER_WALLET * len(recipients) / len(senders)):,.0f} {'DCC' if not ASSET_ID else 'tokens'}")
    print(f"Estimated time: ~{(len(recipients) * RATE_LIMIT_DELAY / 60):.1f} minutes\n")
    
    response = input("Start refill operation? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        sys.exit(0)
    
    print("\nStarting refill operation...\n")
    start_time = time.time()
    
    success_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        
        for i, recipient in enumerate(recipients, 1):
            # Distribute workload among senders in round-robin fashion
            sender_index = (i - 1) % len(senders)
            sender = senders[sender_index]
            
            future = executor.submit(
                send_to_wallet,
                sender,
                recipient,
                asset,
                amount,
                i,
                len(recipients),
                sender_index + 1
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
    print(f"REFILL SUMMARY")
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
