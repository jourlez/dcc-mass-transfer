#!/usr/bin/env python3
"""
Generate valid DecentralChain wallets by disabling PyWaves node queries.
"""
import pywaves as pw
import csv
import sys
import hashlib
import os

# Configure DecentralChain but we'll work offline
DECENTRALCHAIN_NODE = 'https://mainnet-node.decentralchain.io'
pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id='?')

# Monkey patch to disable alias fetching which causes node queries
def no_aliases(self):
    return []

pw.Address.aliases = no_aliases

def generate_wallets(count, output_file, amount_per_wallet):
    """Generate valid wallet addresses without node queries"""
    print(f"Generating {count} valid DecentralChain wallets...")
    
    wallets = []
    for i in range(count):
        try:
            # Generate random seed
            random_bytes = os.urandom(32)
            seed = hashlib.sha256(random_bytes).hexdigest()
            
            # Create address - aliases are disabled so no node query
            address_obj = pw.Address(seed=seed)
            
            wallets.append({
                'address': address_obj.address,
                'seed': seed,
                'private_key': address_obj.privateKey,
                'public_key': address_obj.publicKey
            })
            
            if (i + 1) % 100 == 0:
                print(f"Generated {i + 1}/{count} wallets...")
                
        except Exception as e:
            print(f"Error generating wallet {i+1}: {e}")
            continue
    
    print(f"\n✓ Successfully generated {len(wallets)} wallets")
    
    # Save recipient CSV for mass transfer
    print(f"Saving recipient list to {output_file}...")
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['# DecentralChain mass transfer recipients - Valid addresses'])
        writer.writerow(['# address,amount (in whole token units)'])
        for wallet in wallets:
            writer.writerow([wallet['address'], amount_per_wallet])
    
    # Save wallet details
    details_file = output_file.replace('.csv', '_details.csv')
    print(f"Saving wallet details to {details_file}...")
    with open(details_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['address', 'seed', 'private_key', 'public_key'])
        writer.writeheader()
        writer.writerows(wallets)
    
    print(f"\n✓ Recipient list: {output_file}")
    print(f"✓ Wallet details: {details_file}")
    print(f"✓ Total tokens to distribute: {len(wallets) * amount_per_wallet}")
    
    # Show sample address
    if wallets:
        print(f"\nSample address: {wallets[0]['address']}")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python3 generate_real_wallets.py <count> <output_csv> <amount_per_wallet>")
        print("Example: python3 generate_real_wallets.py 2000 wallets.csv 0.01")
        sys.exit(1)
    
    count = int(sys.argv[1])
    output_file = sys.argv[2]
    amount = float(sys.argv[3])
    
    generate_wallets(count, output_file, amount)
