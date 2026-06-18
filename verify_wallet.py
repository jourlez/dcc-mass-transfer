#!/usr/bin/env python3
"""
Verify wallet balances and transaction status
"""

import pywaves as pw
import requests
import sys, os
from dotenv import load_dotenv; load_dotenv()
from config import resolve_node, resolve_chain_id, resolve_private_key

# Configuration
DECENTRALCHAIN_NODE = os.getenv('DCC_NODE') or resolve_node(silent=True)
CHAIN_ID = os.getenv('DCC_CHAIN_ID') or resolve_chain_id()
ASSET_ID = os.getenv('DCC_ASSET_ID', '')

# Sender private keys (set via environment variables)
SENDER_KEYS = [
    os.getenv('DCC_PRIVATE_KEY') or resolve_private_key(),
    os.getenv('DCC_PRIVATE_KEY_2', ''),
    os.getenv('DCC_PRIVATE_KEY_3', ''),
    os.getenv('DCC_PRIVATE_KEY_4', ''),
    os.getenv('DCC_PRIVATE_KEY_5', ''),
]

# Test recipient address
TEST_RECIPIENT = '3DYQySnwhmvC7qMHoUzxpCkc4ak2qfvETMw'

def check_balance(address, asset_id):
    """Check asset balance for an address"""
    try:
        url = f"{DECENTRALCHAIN_NODE}/assets/balance/{address}/{asset_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            balance = data.get('balance', 0)
            return balance / 100000000  # Convert to whole units
        else:
            return None
    except Exception as e:
        print(f"Error checking balance: {e}")
        return None

def check_transaction(tx_id):
    """Check transaction status"""
    try:
        url = f"{DECENTRALCHAIN_NODE}/transactions/info/{tx_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'status': 'confirmed',
                'type': data.get('type'),
                'sender': data.get('sender'),
                'transfers': data.get('transfers', [])
            }
        else:
            return {'status': 'not_found'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def main():
    print("="*60)
    print("DecentralChain Wallet Verification")
    print("="*60)
    print(f"\nAsset ID: {ASSET_ID}")
    print(f"Node: {DECENTRALCHAIN_NODE}\n")
    
    # Initialize PyWaves
    pw.setNode(node=DECENTRALCHAIN_NODE, chain='custom', chain_id=CHAIN_ID)
    
    # Check sender balances
    print("Checking Sender Balances:")
    print("-"*60)
    
    total_balance = 0
    for i, private_key in enumerate(SENDER_KEYS, 1):
        try:
            address_obj = pw.Address(privateKey=private_key)
            address = address_obj.address
            
            balance = check_balance(address, ASSET_ID)
            
            if balance is not None:
                total_balance += balance
                print(f"Sender {i} ({address[:15]}...): {balance:,.2f} tokens")
            else:
                print(f"Sender {i} ({address[:15]}...): Could not fetch balance")
        except Exception as e:
            print(f"Sender {i}: Error - {e}")
    
    print(f"\nTotal balance across all senders: {total_balance:,.2f} tokens")
    
    # Check test recipient
    print(f"\n\nChecking Recipient Balance:")
    print("-"*60)
    recipient_balance = check_balance(TEST_RECIPIENT, ASSET_ID)
    if recipient_balance is not None:
        print(f"Recipient ({TEST_RECIPIENT[:15]}...): {recipient_balance:,.2f} tokens")
    else:
        print(f"Could not fetch recipient balance")
    
    # Check a recent transaction if provided
    if len(sys.argv) > 1:
        tx_id = sys.argv[1]
        print(f"\n\nChecking Transaction: {tx_id}")
        print("-"*60)
        tx_info = check_transaction(tx_id)
        print(f"Status: {tx_info.get('status')}")
        if tx_info.get('status') == 'confirmed':
            print(f"Type: {tx_info.get('type')}")
            print(f"Sender: {tx_info.get('sender')}")
            if 'transfers' in tx_info:
                print(f"Transfers: {len(tx_info['transfers'])} recipients")
    
    print("\n" + "="*60)
    print("\nTo check a specific transaction:")
    print("  python3 verify_wallet.py <transaction_id>")
    print("\nTo view on explorer:")
    print(f"  https://decentralscan.com/tx/<transaction_id>")
    print("="*60)

if __name__ == '__main__':
    main()
