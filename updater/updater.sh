#!/bin/bash

SUCCESS='\e[39m\e[42m[SUCCESS]\e[49m \e[32m'
ERROR='\e[39m\e[41m[ERROR]\e[49m \e[31m'
INFO='\e[39m\e[44m[INFO]\e[49m \e[34m'
RESET='\e[0m'

log() {
    echo -e "$(date) $1 $2$RESET"
}

check_dependencies() {
    if [ ! -f "/.dockerenv" ]; then
         log "$ERROR" "This script is intended to be run inside the Docker container only."
         exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log "$ERROR" "Docker is not installed or not in PATH."
        exit 1
    fi
    if ! command -v docker-compose &> /dev/null; then
        log "$ERROR" "Docker Compose is not installed or not in PATH."
        exit 1
    fi
}

detect_project_name() {
    local CONTAINER_ID
    CONTAINER_ID=$(hostname)
    
    local PROJECT_NAME
    PROJECT_NAME=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$CONTAINER_ID" 2>/dev/null)
    
    if [ -n "$PROJECT_NAME" ]; then
        export COMPOSE_PROJECT_NAME="$PROJECT_NAME"
        log "$INFO" "Detected Compose Project: $PROJECT_NAME"
    else
        log "$INFO" "Could not detect project name from self. Assuming default or env vars are set."
    fi
}

update_service() {
    local SERVICE_NAME="$1"
    
    log "$INFO" "Processing service: $SERVICE_NAME"
    
    # 1. Get Container ID via docker-compose
    local CONTAINER_ID
    CONTAINER_ID=$(docker-compose ps -q "$SERVICE_NAME")
    
    if [ -z "$CONTAINER_ID" ]; then
        log "$INFO" "Service '$SERVICE_NAME' is not running. Checking for updates by pulling..."
        if docker-compose pull -q "$SERVICE_NAME"; then
             # If successful pull, try to up it
             log "$INFO" "Pull successful. Ensuring service is up..."
             docker-compose up -d "$SERVICE_NAME"
        else
             log "$ERROR" "Failed to pull image for $SERVICE_NAME"
        fi
        return
    fi
    
    log "$INFO" "Found container ID: $CONTAINER_ID"

    # 2. Detect Image Name
    local IMAGE_NAME
    IMAGE_NAME=$(docker inspect --format '{{.Config.Image}}' "$CONTAINER_ID")
    
    if [ -z "$IMAGE_NAME" ]; then
        log "$ERROR" "Could not detect image name for service '$SERVICE_NAME'."
        return
    fi

    log "$INFO" "Image: $IMAGE_NAME"

    # 3. Compare IDs
    local CURRENT_ID
    CURRENT_ID=$(docker inspect --format '{{.Image}}' "$CONTAINER_ID")
    
    log "$INFO" "Pulling latest manifest..."
    if ! docker pull "$IMAGE_NAME" > /dev/null 2>&1; then
        log "$ERROR" "Failed to pull image $IMAGE_NAME"
        return
    fi
    
    local LATEST_ID
    LATEST_ID=$(docker inspect --format '{{.Id}}' "$IMAGE_NAME")
    
    if [ "$CURRENT_ID" != "$LATEST_ID" ]; then
        log "$INFO" "Update available for $SERVICE_NAME!"
        log "$INFO" "Current: $CURRENT_ID"
        log "$INFO" "Latest:  $LATEST_ID"
        
        log "$INFO" "Updating service '$SERVICE_NAME'..."
        if docker-compose up -d "$SERVICE_NAME"; then
            log "$SUCCESS" "Service '$SERVICE_NAME' updated successfully."
            
            # Cleanup dangling images
            if docker image prune -f > /dev/null 2>&1; then
                log "$INFO" "Cleaned up old images."
            fi
        else
            log "$ERROR" "Failed to update service '$SERVICE_NAME'."
        fi
    else
        log "$INFO" "Service '$SERVICE_NAME' is up to date."
    fi
}

main() {
    check_dependencies
    detect_project_name
    
    # Get all services defined in docker-compose
    local SERVICES
    SERVICES=$(docker-compose config --services 2>/dev/null)
    
    if [ -z "$SERVICES" ]; then
        log "$ERROR" "No services found in docker-compose project."
        exit 1
    fi
    
    for SERVICE in $SERVICES; do
        # Skip the updater service itself
        if [ "$SERVICE" == "updater" ]; then
            continue
        fi
        
        update_service "$SERVICE"
    done
}

main
