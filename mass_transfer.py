import pywaves as pw
import csv
import sys
import os
from dotenv import load_dotenv; load_dotenv()
from config import resolve_node, resolve_chain_id, resolve_private_key

NODE = os.getenv('DCC_NODE') or resolve_node(silent=True)
CHAIN_ID = os.getenv('DCC_CHAIN_ID') or resolve_chain_id()
pw.setNode(node=NODE, chain='custom', chain_id=CHAIN_ID)

# Sender's private key
PRIVATE_KEY = os.getenv('DCC_PRIVATE_KEY') or resolve_private_key()

# Asset ID to transfer
ASSET_ID = os.getenv('DCC_ASSET_ID', '')

# Path to recipients CSV file (accept from CLI or use default)
RECIPIENTS_FILE = sys.argv[1] if len(sys.argv) > 1 else 'recipients.csv'

if not os.path.exists(RECIPIENTS_FILE):
    print(f"Error: File '{RECIPIENTS_FILE}' not found")
    sys.exit(1)

# Read recipients and amounts from CSV file
recipients = []
with open(RECIPIENTS_FILE, newline='') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        # Skip empty lines and comments/headers
        if not row or row[0].strip().startswith('#') or row[0].strip().startswith('address'):
            continue
        if len(row) >= 2:
            try:
                address = row[0].strip()
                amount = int(float(row[1].strip()))
                recipients.append({'recipient': address, 'amount': amount})
            except (ValueError, IndexError):
                print(f"Skipping invalid row: {row}")
                continue

# Create sender address object using private key
myAddress = pw.Address(privateKey=PRIVATE_KEY)

# Create Asset object
asset = pw.Asset(ASSET_ID) if ASSET_ID else None

# Send mass transfer
if recipients:
    tx = myAddress.massTransferAssets(recipients, asset, attachment='')
    print('Mass transfer transaction ID:', tx['id'])
    print('Transaction details:', tx)
else:
    print('No recipients found in file.')
