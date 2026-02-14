#!/bin/bash

# Schedule Mass Transfer Script using Cron
# This script helps you set up automated execution on a schedule

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_PATH="$SCRIPT_DIR/mass_transfer_pywaves.py"
CSV_PATH="$SCRIPT_DIR/recipients.csv"
LOG_PATH="$SCRIPT_DIR/cron.log"

echo "=================================="
echo "Cron Job Setup for Mass Transfer"
echo "=================================="
echo ""
echo "Script location: $SCRIPT_PATH"
echo "CSV file: $CSV_PATH"
echo "Log file: $LOG_PATH"
echo ""
echo "Available schedules:"
echo "  1) Every hour"
echo "  2) Every day at 9:00 AM"
echo "  3) Every day at midnight"
echo "  4) Every Monday at 9:00 AM"
echo "  5) Every 30 minutes"
echo "  6) Custom (enter your own)"
echo "  7) View current cron jobs"
echo "  8) Remove mass transfer cron job"
echo ""
read -p "Select option (1-8): " choice

case $choice in
    1)
        CRON_SCHEDULE="0 * * * *"
        DESCRIPTION="every hour"
        ;;
    2)
        CRON_SCHEDULE="0 9 * * *"
        DESCRIPTION="every day at 9:00 AM"
        ;;
    3)
        CRON_SCHEDULE="0 0 * * *"
        DESCRIPTION="every day at midnight"
        ;;
    4)
        CRON_SCHEDULE="0 9 * * 1"
        DESCRIPTION="every Monday at 9:00 AM"
        ;;
    5)
        CRON_SCHEDULE="*/30 * * * *"
        DESCRIPTION="every 30 minutes"
        ;;
    6)
        read -p "Enter cron schedule (e.g., '0 9 * * *'): " CRON_SCHEDULE
        DESCRIPTION="custom schedule"
        ;;
    7)
        echo ""
        echo "Current cron jobs:"
        crontab -l 2>/dev/null || echo "No cron jobs found"
        exit 0
        ;;
    8)
        echo ""
        echo "Removing mass transfer cron jobs..."
        crontab -l 2>/dev/null | grep -v "mass_transfer_pywaves.py" | crontab -
        echo "✓ Cron job removed"
        exit 0
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

# Create the cron command
CRON_COMMAND="cd $SCRIPT_DIR && /usr/local/bin/python3 $SCRIPT_PATH $CSV_PATH >> $LOG_PATH 2>&1"

# Add to crontab
echo ""
echo "Adding cron job..."
echo "Schedule: $DESCRIPTION"
echo "Command: $CRON_COMMAND"
echo ""

# Backup existing crontab
crontab -l 2>/dev/null > /tmp/crontab_backup.txt

# Add new job
(crontab -l 2>/dev/null; echo "# DecentralChain Mass Transfer - $DESCRIPTION"; echo "$CRON_SCHEDULE $CRON_COMMAND") | crontab -

echo "✓ Cron job added successfully!"
echo ""
echo "To view logs: tail -f $LOG_PATH"
echo "To edit cron: crontab -e"
echo "To remove: Run this script again and select option 8"
echo ""
