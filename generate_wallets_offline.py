#!/usr/bin/env python3
"""
Generate new DecentralChain wallet addresses offline (no node queries).
"""
import base58
import hashlib
import os
from dotenv import load_dotenv; load_dotenv()
from config import resolve_node, resolve_chain_id, resolve_private_key
import csv
import sys
from Crypto.Hash import keccak

def generate_address_from_seed(seed, chain_id=None):
    if chain_id is None:
        chain_id = int(os.getenv('DCC_CHAIN_ID') or resolve_chain_id().encode()[0])
    """Generate a DecentralChain address from a seed phrase"""
    # Generate private key from seed
    seed_bytes = seed.encode('utf-8') if isinstance(seed, str) else seed
    account_seed = hashlib.sha256(b'\x00\x00\x00\x00' + seed_bytes).digest()
    private_key = hashlib.sha256(account_seed).digest()
    
    # Generate public key (simplified - using hash for demo)
    public_key = hashlib.sha256(private_key).digest()
    
    # Generate address
    k = keccak.new(digest_bits=256)
    k.update(public_key)
    public_key_hash = k.digest()[:20]
    
    # Add version byte (1) and chain_id
    address_bytes = bytes([1, chain_id]) + public_key_hash
    
    # Add checksum
    checksum = hashlib.sha256(hashlib.sha256(address_bytes).digest()).digest()[:4]
    address_with_checksum = address_bytes + checksum
    
    # Encode to base58
    address = base58.b58encode(address_with_checksum).decode('utf-8')
    
    return {
        'address': address,
        'seed': seed if isinstance(seed, str) else seed.hex(),
        'private_key': base58.b58encode(private_key).decode('utf-8'),
        'public_key': base58.b58encode(public_key).decode('utf-8')
    }

def generate_wallets(count, output_file, amount_per_wallet):
    """Generate new wallet addresses offline and save to CSV"""
    print(f"Generating {count} new DecentralChain wallets (offline)...")
    
    wallets = []
    for i in range(count):
        # Generate random seed
        random_bytes = os.urandom(32)
        seed = hashlib.sha256(random_bytes).hexdigest()
        
        try:
            wallet = generate_address_from_seed(seed)
            wallets.append(wallet)
            
            if (i + 1) % 100 == 0:
                print(f"Generated {i + 1}/{count} wallets...")
        except Exception as e:
            print(f"Error generating wallet {i+1}: {e}")
            continue
    
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
    
    print(f"\n✓ Generated {len(wallets)} wallets")
    print(f"✓ Recipient list: {output_file}")
    print(f"✓ Wallet details: {details_file}")
    print(f"\nTotal tokens to distribute: {len(wallets) * amount_per_wallet}")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python3 generate_wallets_offline.py <count> <output_csv> <amount_per_wallet>")
        print("Example: python3 generate_wallets_offline.py 2000 test_wallets.csv 0.01")
        sys.exit(1)
    
    count = int(sys.argv[1])
    output_file = sys.argv[2]
    amount = float(sys.argv[3])
    
    generate_wallets(count, output_file, amount)
