#!/usr/bin/env python3
"""
Limited Stress Test - Orchestrates mass transfers using mass_transfer.py
"""

import os
import sys
import csv
import subprocess
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from config import get_log_file

LOG_FILE = get_log_file('limited_stress_test')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("stress_test")

NUM_WALLETS = int(os.getenv('NUM_WALLETS', '100'))
SENDS_PER_WALLET = int(os.getenv('SENDS_PER_WALLET', '5'))
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))
RATE_LIMIT_DELAY = float(os.getenv('RATE_LIMIT_DELAY', '0.01'))

def generate_recipients_csv(num_recipients, output_file):
    """Generate CSV with recipient addresses from real_wallets"""
    real_wallets_file = os.path.join(WORKSPACE, 'real_wallets_2000_details.csv')
    
    if not os.path.exists(real_wallets_file):
        logger.error(f"Real wallets file not found: {real_wallets_file}")
        return False
    
    recipients = []
    try:
        with open(real_wallets_file, 'r') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= num_recipients:
                    break
                address = row.get('address', '').strip()
                if address:
                    recipients.append(address)
    except Exception as e:
        logger.error(f"Error reading wallets: {e}")
        return False
    
    if not recipients:
        logger.error("No valid recipients found")
        return False
    
    # Write CSV with repeated recipients for multiple sends
    try:
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            for recipient in recipients:
                for _ in range(SENDS_PER_WALLET):
                    writer.writerow([recipient, '1'])  # 1 DCC per transfer
        total_txs = len(recipients) * SENDS_PER_WALLET
        logger.info(f"Generated {output_file} with {len(recipients)} recipients, {total_txs} total transfers")
        return True
    except Exception as e:
        logger.error(f"Error writing recipients CSV: {e}")
        return False

def run_mass_transfer(recipients_file):
    """Execute mass_transfer_pywaves.py with given recipients"""
    script_path = os.path.join(WORKSPACE, 'mass_transfer_pywaves.py')
    
    if not os.path.exists(script_path):
        # Fall back to mass_transfer.py if pywaves version not found
        script_path = os.path.join(WORKSPACE, 'mass_transfer.py')
    
    if not os.path.exists(script_path):
        logger.error(f"No mass transfer script found in: {WORKSPACE}")
        return False
    
    logger.info(f"Starting mass transfers from {recipients_file}")
    
    try:
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['CONCURRENCY'] = str(MAX_WORKERS)
        
        # Run mass_transfer.py and capture output
        proc = subprocess.Popen(
            [sys.executable, script_path, recipients_file],
            cwd=WORKSPACE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )
        
        # Stream output to both console and log
        for line in proc.stdout:
            line = line.strip()
            if line:
                print(line)
                logger.info(line)
        
        proc.wait()
        
        if proc.returncode == 0:
            logger.info("Mass transfer completed successfully")
            return True
        else:
            logger.error(f"Mass transfer failed with return code {proc.returncode}")
            return False
    except Exception as e:
        logger.error(f"Error running mass_transfer: {e}")
        return False

def main():
    logger.info("="*60)
    logger.info("Decentralchain Stress Test Started")
    logger.info(f"Configuration: {NUM_WALLETS} wallets, {SENDS_PER_WALLET} sends each, {MAX_WORKERS} workers")
    logger.info("="*60)
    
    recipients_file = os.path.join(WORKSPACE, 'stress_test_recipients.csv')
    
    # Generate recipients CSV
    logger.info("Generating recipients list...")
    if not generate_recipients_csv(NUM_WALLETS, recipients_file):
        logger.error("Failed to generate recipients CSV")
        sys.exit(1)
    
    # Run mass transfer
    logger.info("Executing mass transfers...")
    if not run_mass_transfer(recipients_file):
        logger.error("Mass transfer execution failed")
        sys.exit(1)
    
    logger.info("="*60)
    logger.info("Stress test completed successfully")
    logger.info("="*60)

if __name__ == '__main__':
    main()
