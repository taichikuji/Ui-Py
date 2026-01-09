#!/bin/sh

if [ ! -f "/.dockerenv" ]; then
    echo "This script is intended to be run inside the Docker container only."
    exit 1
fi

# Defaults to daily at 00:00
CRON_SCHEDULE=${CRON_SCHEDULE:-"0 0 * * *"}

echo "Setting up updater cron with schedule: $CRON_SCHEDULE"

# CRON_SCHEDULE written to crontab
echo "$CRON_SCHEDULE /usr/local/bin/updater.sh >> /proc/1/fd/1 2>&1" | crontab -

# Initiate first run, then hand over to cron
/usr/local/bin/updater.sh

echo "Starting crond..."
exec crond -f -l 2
