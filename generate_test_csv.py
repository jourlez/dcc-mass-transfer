#!/usr/bin/env python3
"""
Generate a test CSV file with multiple recipients for testing mass transfers
"""

import csv
import sys

def generate_test_csv(output_file, num_recipients, test_address, amount_per_recipient):
    """Generate a CSV file with test recipients"""
    
    print(f"Generating {num_recipients} test recipients...")
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header comment
        writer.writerow(['# DecentralChain mass transfer recipients'])
        writer.writerow(['# address,amount (in whole token units)'])
        
        # Write recipients (all same address for testing)
        for i in range(num_recipients):
            writer.writerow([test_address, amount_per_recipient])
    
    print(f"✓ Generated {output_file} with {num_recipients} recipients")
    print(f"  Each receiving: {amount_per_recipient} tokens")
    print(f"  Total tokens to distribute: {num_recipients * amount_per_recipient}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 generate_test_csv.py <num_recipients> <output_file> [test_address] [amount]")
        print("\nExample:")
        print("  python3 generate_test_csv.py 5000 test_recipients.csv")
        print("  python3 generate_test_csv.py 100 small_test.csv 3DWaDrVosS9npYjd4DnQwkmMQdMfbixhggc 1.5")
        sys.exit(1)
    
    num_recipients = int(sys.argv[1])
    output_file = sys.argv[2]
    test_address = sys.argv[3] if len(sys.argv) > 3 else '3DWaDrVosS9npYjd4DnQwkmMQdMfbixhggc'
    amount = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    
    generate_test_csv(output_file, num_recipients, test_address, amount)
