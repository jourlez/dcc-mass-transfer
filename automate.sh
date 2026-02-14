#!/bin/bash

# Quick start script for automation

echo "=================================="
echo "Mass Transfer Automation Options"
echo "=================================="
echo ""
echo "1) Start File Watcher Daemon"
echo "   Automatically processes CSV files dropped in 'pending' folder"
echo ""
echo "2) Start REST API Server"
echo "   HTTP endpoint for triggering transfers"
echo ""
echo "3) Setup Cron Job"
echo "   Schedule automatic execution"
echo ""
echo "4) Run Once Now"
echo "   Execute mass transfer immediately"
echo ""
read -p "Select option (1-4): " choice

case $choice in
    1)
        echo ""
        echo "Starting File Watcher Daemon..."
        python3 automate_daemon.py
        ;;
    2)
        echo ""
        echo "Starting REST API Server..."
        python3 api_server.py
        ;;
    3)
        echo ""
        bash setup_cron.sh
        ;;
    4)
        echo ""
        read -p "Enter CSV file path (default: recipients.csv): " csv_file
        csv_file=${csv_file:-recipients.csv}
        
        if [ ! -f "$csv_file" ]; then
            echo "Error: File not found: $csv_file"
            exit 1
        fi
        
        echo "Running mass transfer with $csv_file..."
        python3 mass_transfer_pywaves.py "$csv_file"
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac
