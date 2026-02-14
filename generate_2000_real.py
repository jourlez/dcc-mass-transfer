#!/usr/bin/env python3
"""
Generate 2000 transactions to real DecentralChain addresses
"""
import csv

# Real DecentralChain addresses (from previous successful tests)
RECIPIENTS = [
    '3DQXdEtof2ZBgrE2AkpSuRe4EwU1WVbbbrh',
    '3DXwypPikJTM3FJLKdS7fccPaUbpdao7t43',
    '3DNbU8rAmcLa8tnTxYuhg7b4gTzuUTk7tYh',
    '3DYQySnwhmvC7qMHoUzxpCkc4ak2qfvETMw'
]

def generate_csv(count, output_file, amount):
    """Generate CSV with count transactions distributed across recipients"""
    print(f"Generating {count} transactions to {len(RECIPIENTS)} real addresses...")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['# DecentralChain mass transfer - Real addresses'])
        writer.writerow(['# address,amount (in whole token units)'])
        
        for i in range(count):
            # Distribute evenly across recipients
            recipient = RECIPIENTS[i % len(RECIPIENTS)]
            writer.writerow([recipient, amount])
    
    print(f"✓ Generated {output_file}")
    print(f"✓ Each address will receive {count // len(RECIPIENTS)} transactions of {amount} tokens")
    print(f"✓ Total per address: {(count // len(RECIPIENTS)) * amount} tokens")
    print(f"✓ Total all addresses: {count * amount} tokens")

if __name__ == '__main__':
    generate_csv(2000, 'blockchain_test_2000_real.csv', 0.01)
