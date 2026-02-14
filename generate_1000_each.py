#!/usr/bin/env python3
"""
Generate CSV with 1000 transactions per recipient
"""

import csv

recipients = [
    '3DYQySnwhmvC7qMHoUzxpCkc4ak2qfvETMw',
    '3DQXdEtof2ZBgrE2AkpSuRe4EwU1WVbbbrh',
    '3DXwypPikJTM3FJLKdS7fccPaUbpdao7t43',
    '3DNbU8rAmcLa8tnTxYuhg7b4gTzuUTk7tYh'
]

amount = 1  # 1 token per transaction

output_file = 'recipients_1000_each.csv'

with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['# DecentralChain mass transfer - 1000 transactions per recipient'])
    writer.writerow(['# address,amount'])
    
    for recipient in recipients:
        for _ in range(1000):
            writer.writerow([recipient, amount])

total = len(recipients) * 1000
print(f"✓ Generated {output_file}")
print(f"  Recipients: {len(recipients)}")
print(f"  Transactions per recipient: 1000")
print(f"  Total transactions: {total}")
print(f"  Amount per transaction: {amount} token")
print(f"  Total tokens: {total * amount}")
