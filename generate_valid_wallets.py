#!/usr/bin/env python3
"""
Generate valid DecentralChain wallet addresses without querying node for each wallet.
"""
import pywaves as pw
import csv
import sys
import hashlib
import os

# Configure DecentralChain
DECENTRALCHAIN_NODE = 'https://mainnet-node.decentralchain.io'
pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id='?')

def generate_wallets_batch(count, output_file, amount_per_wallet):
    """Generate valid wallet addresses"""
    print(f"Generating {count} valid DecentralChain wallets...")
    
    wallets = []
    for i in range(count):
        try:
            # Generate random seed
            random_bytes = os.urandom(32)
            seed = hashlib.sha256(random_bytes).hexdigest()
            
            # Create address object - this will validate the address format
            # We'll use the seed directly to create private key
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
            # Try to continue with a simpler approach
            continue
    
    if len(wallets) == 0:
        print("Failed to generate any valid wallets!")
        sys.exit(1)
    
    # Save recipient CSV for mass transfer
    print(f"\nSaving recipient list to {output_file}...")
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['# DecentralChain mass transfer recipients'])
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
    
    print(f"\n✓ Generated {len(wallets)} valid wallets")
    print(f"✓ Recipient list: {output_file}")
    print(f"✓ Wallet details: {details_file}")
    print(f"\nTotal tokens to distribute: {len(wallets) * amount_per_wallet}")
    
    return len(wallets)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python3 generate_valid_wallets.py <count> <output_csv> <amount_per_wallet>")
        print("Example: python3 generate_valid_wallets.py 100 test_wallets.csv 0.01")
        sys.exit(1)
    
    count = int(sys.argv[1])
    output_file = sys.argv[2]
    amount = float(sys.argv[3])
    
    # Start with smaller batch to test
    if count > 100:
        print(f"Note: Generating {count} wallets may take time due to node queries.")
        print("Consider starting with 100 wallets first to test.")
    
    generated = generate_wallets_batch(count, output_file, amount)
    if generated < count:
        print(f"\nWarning: Only generated {generated}/{count} wallets")
