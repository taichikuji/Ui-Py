#!/bin/bash

# Configuration
CONTAINER_NAME="ui"
DEFAULT_SERVICE_NAME="discord"

# Colors
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

main() {
    check_dependencies
    
    # Check if target container is running
    # We filter by exact name match /ui to find the ID
    CONTAINER_ID=$(docker ps -q --filter "name=^/${CONTAINER_NAME}$")
    
    if [ -z "$CONTAINER_ID" ]; then
        # Try to find stopped container
        CONTAINER_ID=$(docker ps -a -q --filter "name=^/${CONTAINER_NAME}$")
    fi

    if [ -z "$CONTAINER_ID" ]; then
         log "$ERROR" "Container '${CONTAINER_NAME}' not found. Cannot determine image to update."
         return 1
    fi

    log "$INFO" "Inspecting container '${CONTAINER_NAME}' (${CONTAINER_ID})..."
    
    # 1. Detect Project Name
    PROJECT_NAME=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$CONTAINER_ID")
    if [ -n "$PROJECT_NAME" ]; then
        export COMPOSE_PROJECT_NAME="$PROJECT_NAME"
        log "$INFO" "Detected Compose Project: $PROJECT_NAME"
    fi

    # 2. Detect Service Name
    SERVICE_NAME=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.service" }}' "$CONTAINER_ID")
    if [ -z "$SERVICE_NAME" ]; then
        SERVICE_NAME="$DEFAULT_SERVICE_NAME"
        log "$INFO" "Service name not detected. Using default: $SERVICE_NAME"
    else
        log "$INFO" "Detected Service Name: $SERVICE_NAME"
    fi

    # 3. Detect Image Name
    IMAGE_NAME=$(docker inspect --format '{{.Config.Image}}' "$CONTAINER_ID")
    if [ -z "$IMAGE_NAME" ]; then
        log "$ERROR" "Could not detect image name for container."
        return 1
    fi

    log "$INFO" "Checking updates for image: $IMAGE_NAME"

    # 4. Compare IDs
    # Get Current Image ID from the container
    CURRENT_ID=$(docker inspect --format '{{.Image}}' "$CONTAINER_ID")
    
    # Pull latest image to check for new digest
    log "$INFO" "Pulling latest manifest..."
    if ! docker pull "$IMAGE_NAME" > /dev/null 2>&1; then
        log "$ERROR" "Failed to pull image $IMAGE_NAME"
        return 1
    fi
    
    # Get New Image ID from the local registry (after pull)
    LATEST_ID=$(docker inspect --format '{{.Id}}' "$IMAGE_NAME")
    
    if [ "$CURRENT_ID" != "$LATEST_ID" ]; then
        log "$INFO" "Update available!"
        log "$INFO" "Current: $CURRENT_ID"
        log "$INFO" "Latest:  $LATEST_ID"
        
        log "$INFO" "Updating service '$SERVICE_NAME'..."
        if docker-compose up -d "$SERVICE_NAME"; then
            log "$SUCCESS" "Service updated successfully."
            
            # Cleanup dangling images
            if docker image prune -f > /dev/null 2>&1; then
                log "$INFO" "Cleaned up old images."
            fi
        else
            log "$ERROR" "Failed to update service."
            return 1
        fi
    else
        log "$INFO" "Image is up to date."
    fi
}

main
