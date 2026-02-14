#!/usr/bin/env python3
"""
Automated Mass Transfer Daemon
Watches a folder for new CSV files and automatically processes them
"""

import os
import time
import shutil
from pathlib import Path
from datetime import datetime
import subprocess

# Configuration
WATCH_FOLDER = './pending'
PROCESSED_FOLDER = './processed'
FAILED_FOLDER = './failed'
SCRIPT_PATH = './mass_transfer_pywaves.py'
CHECK_INTERVAL = 5  # seconds
LOG_FILE = './automation.log'

def log(message):
    """Write log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')

def setup_folders():
    """Create necessary folders if they don't exist"""
    for folder in [WATCH_FOLDER, PROCESSED_FOLDER, FAILED_FOLDER]:
        Path(folder).mkdir(exist_ok=True)
    log(f"Folders ready: {WATCH_FOLDER}, {PROCESSED_FOLDER}, {FAILED_FOLDER}")

def process_csv_file(csv_file):
    """Process a CSV file with the mass transfer script"""
    log(f"Processing: {csv_file}")
    
    try:
        # Run the mass transfer script
        result = subprocess.run(
            ['python3', SCRIPT_PATH, csv_file],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            log(f"✓ Success: {csv_file}")
            log(f"Output: {result.stdout[-500:]}")  # Last 500 chars
            
            # Move to processed folder
            dest = os.path.join(PROCESSED_FOLDER, os.path.basename(csv_file))
            shutil.move(csv_file, dest)
            log(f"Moved to: {dest}")
            return True
        else:
            log(f"✗ Failed: {csv_file}")
            log(f"Error: {result.stderr[-500:]}")
            
            # Move to failed folder
            dest = os.path.join(FAILED_FOLDER, os.path.basename(csv_file))
            shutil.move(csv_file, dest)
            log(f"Moved to: {dest}")
            return False
            
    except subprocess.TimeoutExpired:
        log(f"✗ Timeout: {csv_file}")
        dest = os.path.join(FAILED_FOLDER, os.path.basename(csv_file))
        shutil.move(csv_file, dest)
        return False
        
    except Exception as e:
        log(f"✗ Exception processing {csv_file}: {e}")
        dest = os.path.join(FAILED_FOLDER, os.path.basename(csv_file))
        shutil.move(csv_file, dest)
        return False

def watch_folder():
    """Watch folder for new CSV files and process them"""
    log("=== Mass Transfer Daemon Started ===")
    log(f"Watching: {WATCH_FOLDER}")
    log(f"Check interval: {CHECK_INTERVAL} seconds")
    
    processed_files = set()
    
    while True:
        try:
            # Get all CSV files in watch folder
            csv_files = list(Path(WATCH_FOLDER).glob('*.csv'))
            
            # Process new files
            for csv_file in csv_files:
                file_path = str(csv_file)
                
                # Skip if already processed in this session
                if file_path in processed_files:
                    continue
                
                # Wait a moment to ensure file is fully written
                time.sleep(1)
                
                # Process the file
                process_csv_file(file_path)
                processed_files.add(file_path)
            
            # Sleep before next check
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("=== Daemon Stopped by User ===")
            break
        except Exception as e:
            log(f"Error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)

def main():
    setup_folders()
    
    print("=" * 60)
    print("DecentralChain Mass Transfer Daemon")
    print("=" * 60)
    print(f"Watch folder:     {WATCH_FOLDER}")
    print(f"Processed folder: {PROCESSED_FOLDER}")
    print(f"Failed folder:    {FAILED_FOLDER}")
    print(f"Log file:         {LOG_FILE}")
    print("=" * 60)
    print("\nDrop CSV files into the 'pending' folder to process them.")
    print("Press Ctrl+C to stop.\n")
    
    watch_folder()

if __name__ == '__main__':
    main()
