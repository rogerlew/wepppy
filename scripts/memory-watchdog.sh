#!/bin/bash
# memory-watchdog.sh
# Host-side watchdog that kills the Docker stack when memory gets critically low
# Run via cron every minute: * * * * * /workdir/wepppy/scripts/memory-watchdog.sh
#
# This prevents OOM scenarios that make the system unresponsive before
# anything can be logged.

# Thresholds (in MB)
WARN_THRESHOLD_MB=30000   # Log warning when available < 30GB
KILL_THRESHOLD_MB=25000   # Kill stack when available < 25GB

LOGFILE="/var/log/weppcloud-watchdog.log"
COMPOSE_FILE="/workdir/wepppy/docker/docker-compose.dev.yml"
ENV_FILE="/workdir/wepppy/docker/.env"

# Get available memory in MB
AVAILABLE_MB=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOGFILE"
}

if [ "$AVAILABLE_MB" -lt "$KILL_THRESHOLD_MB" ]; then
    log "CRITICAL: Available memory ${AVAILABLE_MB}MB < ${KILL_THRESHOLD_MB}MB threshold. Killing Docker stack."
    
    # Get top memory consumers for forensics
    log "Top memory consumers:"
    ps aux --sort=-%mem | head -10 >> "$LOGFILE"
    
    # Kill the stack hard and fast
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" kill 2>> "$LOGFILE"
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down 2>> "$LOGFILE"
    
    log "Docker stack killed. System should recover."
    
    # Optional: send notification
    # curl -X POST "https://your-webhook-url" -d "WEPPcloud stack killed due to low memory"
    
elif [ "$AVAILABLE_MB" -lt "$WARN_THRESHOLD_MB" ]; then
    log "WARNING: Available memory ${AVAILABLE_MB}MB < ${WARN_THRESHOLD_MB}MB. Monitoring closely."
    
    # Log current container memory usage
    docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" >> "$LOGFILE" 2>/dev/null
fi
