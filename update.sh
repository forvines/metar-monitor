#!/bin/bash
# Auto-update metar-monitor from git and restart service if changed

REPO_DIR="$HOME/metar_monitor"
LOG_FILE="$REPO_DIR/logs/update.log"

cd "$REPO_DIR" || exit 1

# Fetch and check for changes
git fetch origin 2>>"$LOG_FILE"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): Updating from $LOCAL to $REMOTE" >> "$LOG_FILE"
    git pull origin main >> "$LOG_FILE" 2>&1
    sudo systemctl restart metar-monitor.service
    echo "$(date): Service restarted" >> "$LOG_FILE"
fi
