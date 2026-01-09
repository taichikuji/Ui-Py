#!/bin/sh

SUCCESS='\033[32m[SUCCESS]\033[0m \033[32m'
ERROR='\033[31m[ERROR]\033[0m \033[31m'
INFO='\033[34m[INFO]\033[0m \033[34m'
RESET='\033[0m'

log() {
    printf "%s %b %s%b\n" "$(date)" "$1" "$2" "$RESET"
}

check_dependencies() {
    if [ ! -f "/.dockerenv" ]; then
         log "$ERROR" "This script is intended to be run inside the Docker container only."
         exit 1
    fi
    if ! command -v docker > /dev/null 2>&1 || ! command -v docker-compose > /dev/null 2>&1; then
        log "$ERROR" "Docker or Docker Compose is not installed."
        exit 1
    fi
}

main() {
    check_dependencies
    
    # 1. Get Project Name (to ensure we only update *this* stack)
    PROJECT=$(docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' "$(hostname)" 2>/dev/null)
    
    if [ -n "$PROJECT" ]; then
        export COMPOSE_PROJECT_NAME="$PROJECT"
    else
        log "$ERROR" "Could not detect project name."
        exit 1
    fi

    # 2. Extract unique Service Names directly from containers with the specific label
    SERVICES=$(docker ps -a \
        --filter "label=com.taichikuji.ui-py.enable=true" \
        --filter "label=com.docker.compose.project=$PROJECT" \
        --format '{{.Label "com.docker.compose.service"}}' \
        | sort -u)

    if [ -z "$SERVICES" ]; then
        log "$INFO" "No enabled services found."
        exit 0
    fi

    # 3. Let Docker Compose handle the update logic
    for SERVICE in $SERVICES; do
        log "$INFO" "Updating service: $SERVICE"
        
        # Pull latest image
        docker-compose pull -q "$SERVICE"
        
        # Recreates container ONLY if image has changed
        docker-compose up -d "$SERVICE"
    done
    
    # Cleanup
    log "$INFO" "Cleaning up old images..."
    if docker image prune -f > /dev/null 2>&1; then
        log "$SUCCESS" "Old images removed."
    fi
}

main
