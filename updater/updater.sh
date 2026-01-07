#!/bin/bash

SUCCESS='\e[39m\e[42m[SUCCESS]\e[49m \e[32m'
ERROR='\e[39m\e[41m[ERROR]\e[49m \e[31m'
INFO='\e[39m\e[44m[INFO]\e[49m \e[34m'
RESET='\e[0m'

log() {
    echo -e "$(date) $1 $2$RESET"
}

check_updates() {
    log "$INFO" "Checking for updates..."
    
    # updater.sh needs to be executed from /workspace, otherwise it will not work.
    if [ ! -d ".git" ]; then
        log "$ERROR" "Not a git repository. Is the volume mounted?"
        exit 1
    fi

    # Fetch latest changes
    git fetch origin

    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse @{u})

    if [ "$LOCAL" != "$REMOTE" ]; then
        log "$INFO" "Updates detected. Pulling changes..."
        
        if git pull; then
            log "$SUCCESS" "Git pull successful."
            
            # Instead of using ./init-docker.sh, we replicate the necessary parts here
            export COMPOSE_BAKE=true

            cleanup_buildkit() {
                if docker ps -a --filter "name=buildx_buildkit" --format "table {{.Names}}" | grep buildx_buildkit | xargs -r docker rm -f 2>/dev/null; then
                    log "$SUCCESS" "BuildKit containers removed"
                else
                    log "$ERROR" "No BuildKit containers to remove"
                fi
            }

            # Build and start new version
            if docker-compose build --force-rm discord && docker-compose up -d discord; then
                cleanup_buildkit
                log "$SUCCESS" "Build and start successful"
            else
                log "$ERROR" "Build/start failed"
            fi
        else
            log "$ERROR" "Git pull failed."
        fi
    else
        log "$INFO" "No updates found."
    fi
}

check_updates
