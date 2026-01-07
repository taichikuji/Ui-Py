#!/bin/bash

# Default to daily at midnight if not set
CRON_SCHEDULE=${CRON_SCHEDULE:-"0 0 * * *"}

# Fix git safe directory issue
git config --global --add safe.directory /workspace

echo "Setting up updater cron with schedule: $CRON_SCHEDULE"

# Write to crontab
echo "$CRON_SCHEDULE /usr/local/bin/updater.sh >> /proc/1/fd/1 2>&1" | crontab -

# Run immediately? The user didn't ask, but good practice. Checking updates on start.
/usr/local/bin/updater.sh

echo "Starting crond..."
exec crond -f -l 2
