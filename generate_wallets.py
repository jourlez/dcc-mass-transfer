#!/usr/bin/env python3
"""
Generate new DecentralChain wallet addresses for testing.
"""
import pywaves as pw
import csv
import sys
import os
from dotenv import load_dotenv; load_dotenv()
from config import resolve_node, resolve_chain_id, resolve_private_key
import hashlib

# Configure DecentralChain
DECENTRALCHAIN_NODE = os.getenv('DCC_NODE') or resolve_node(silent=True)
CHAIN_ID = os.getenv('DCC_CHAIN_ID') or resolve_chain_id()
pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)

def generate_wallets(count, output_file, amount_per_wallet):
    """Generate new wallet addresses and save to CSV"""
    print(f"Generating {count} new DecentralChain wallets...")
    
    wallets = []
    for i in range(count):
        # Generate new address with random seed phrase
        random_bytes = os.urandom(32)
        seed = hashlib.sha256(random_bytes).hexdigest()
        address = pw.Address(seed=seed)
        wallets.append({
            'address': address.address,
            'seed': address.seed,
            'private_key': address.privateKey,
            'public_key': address.publicKey
        })
        
        if (i + 1) % 100 == 0:
            print(f"Generated {i + 1}/{count} wallets...")
    
    # Save recipient CSV for mass transfer
    print(f"\nSaving recipient list to {output_file}...")
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['# DecentralChain mass transfer recipients'])
        writer.writerow(['# address,amount (in whole token units)'])
        for wallet in wallets:
            writer.writerow([wallet['address'], amount_per_wallet])
    
    # Save wallet details to separate file
    details_file = output_file.replace('.csv', '_details.csv')
    print(f"Saving wallet details to {details_file}...")
    with open(details_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['address', 'seed', 'private_key', 'public_key'])
        writer.writeheader()
        writer.writerows(wallets)
    
    print(f"\n✓ Generated {count} wallets")
    print(f"✓ Recipient list: {output_file}")
    print(f"✓ Wallet details: {details_file}")
    print(f"\nTotal tokens to distribute: {count * amount_per_wallet}")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python3 generate_wallets.py <count> <output_csv> <amount_per_wallet>")
        print("Example: python3 generate_wallets.py 5000 test_wallets.csv 1.0")
        sys.exit(1)
    
    count = int(sys.argv[1])
    output_file = sys.argv[2]
    amount = float(sys.argv[3])
    
    generate_wallets(count, output_file, amount)
