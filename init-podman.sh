#!/bin/bash

# This script automates the process of cleaning up Podman containers, pulling the latest code from the default branch of a Git repository, and rebuilding and restarting the Podman environment.
# It includes the following features:
# - A "--prune" flag to perform a complete cleanup of Podman resources, including images, volumes, and orphaned containers.
# - A "--reset" flag to perform the git reset operation separately.
# - Automatic detection of the default branch of the Git repository.
# - Logging of success and error messages for each operation.
# - Error handling to ensure the script exits on failure and provides meaningful feedback.

# Usage:
# - Run the script without arguments to update and restart the Podman environment.
# - Use the "--prune" flag to perform a full cleanup before updating and restarting.
# - Use the "--reset" flag to reset the repository without affecting the Podman environment.

SUCCESS='\e[39m\e[42m[SUCCESS]\e[49m \e[32m'
ERROR='\e[39m\e[41m[ERROR]\e[49m \e[31m'

log() {
    echo -e "$1 $2"
}

prune() {
    log "$SUCCESS" "Starting cleanup..."
    if podman compose down --volumes --remove-orphans; then
        log "$SUCCESS" "Podman cleanup successful"
    else
        log "$ERROR" "Podman cleanup failed"; exit 1
    fi
    log "$SUCCESS" "Cleanup completed"
}

reset_git() {
    log "$SUCCESS" "Starting git reset..."
    default_branch=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')
    if git fetch --all && git reset --hard "origin/$default_branch"; then
        log "$SUCCESS" "Git reset to latest commit successful"
    else
        log "$ERROR" "Git reset failed"; exit 1
    fi
}

# Check for --prune flag
if [[ "$1" == "--prune" ]]; then
    prune
    exit 0
fi

# Check for --reset flag
if [[ "$1" == "--reset" ]]; then
    reset_git
    exit 0
fi

# Clean old version
if podman compose down; then
    log "$SUCCESS" "Container removed"
else
    log "$ERROR" "Failed to remove containers"; exit 1
fi

# Pull latest version
if git fetch --all; then
    log "$SUCCESS" "Updated to latest commit"
else
    log "$ERROR" "Git update failed"; exit 1
fi

# Build and start new version
if podman compose build --pull && podman compose up -d; then
    log "$SUCCESS" "Build and start successful"
else
    log "$ERROR" "Build/start failed"; exit 1
fi
