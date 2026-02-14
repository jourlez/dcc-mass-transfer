#!/usr/bin/env python3
"""
Verify all 2000 wallets received their DCC payments
"""
import csv
import subprocess
import json
import time

def check_wallet_balance(address):
    """Check balance of a wallet on the blockchain"""
    try:
        result = subprocess.run(
            ['curl', '-s', f'https://mainnet-node.decentralchain.io/addresses/balance/{address}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        data = json.loads(result.stdout)
        return data.get('balance', 0) / 100000000  # Convert to DCC
    except Exception as e:
        return None

def verify_all_wallets(csv_file):
    """Verify all wallets in the CSV file"""
    print(f"Verifying all wallets in {csv_file}...")
    print("=" * 80)
    
    wallets = []
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        next(reader)  # Skip second header line
        for row in reader:
            if row and len(row) > 0:
                wallets.append(row[0])
    
    print(f"Total wallets to check: {len(wallets)}")
    print("=" * 80)
    print()
    
    success_count = 0
    fail_count = 0
    total_balance = 0
    
    for i, address in enumerate(wallets, 1):
        balance = check_wallet_balance(address)
        
        if balance is not None and balance > 0:
            status = "✅"
            success_count += 1
            total_balance += balance
        elif balance == 0:
            status = "⚠️ "
            fail_count += 1
        else:
            status = "❌"
            fail_count += 1
        
        print(f"{status} Wallet #{i:4d}: {address} → {balance if balance is not None else 'ERROR'} DCC")
        
        # Progress indicator every 100 wallets
        if i % 100 == 0:
            print(f"\n--- Progress: {i}/{len(wallets)} ({i/len(wallets)*100:.1f}%) ---")
            print(f"    Success: {success_count}, Failed: {fail_count}")
            print(f"    Total DCC distributed so far: {total_balance:.2f}\n")
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    print()
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"Total wallets checked: {len(wallets)}")
    print(f"✅ Successfully funded: {success_count}")
    print(f"❌ Failed/Zero balance: {fail_count}")
    print(f"Success rate: {success_count/len(wallets)*100:.2f}%")
    print(f"Total DCC distributed: {total_balance:.2f} DCC")
    print(f"Average per wallet: {total_balance/len(wallets):.4f} DCC")
    print("=" * 80)

if __name__ == '__main__':
    verify_all_wallets('real_wallets_2000.csv')
