#!/bin/bash
# memory-watchdog.sh
# Host-side watchdog that kills the Docker stack when memory gets critically low.
#
# PURPOSE:
#   Prevents OOM (Out of Memory) conditions that can make the system completely
#   unresponsive. When memory gets critically low, the Linux OOM killer may
#   kill random processes, and by that point the system is often too degraded
#   to log anything useful. This watchdog intervenes earlier, cleanly stopping
#   the Docker stack while the system is still responsive.
#
# INSTALLATION:
#   Run: sudo ./install-memory-watchdog.sh
#   This sets up a systemd timer that runs every 10 seconds.
#
# HOW IT WORKS:
#   1. Checks available memory every 10 seconds (via systemd timer)
#   2. If available < WARN_THRESHOLD_MB: logs warning + container stats
#   3. If available < KILL_THRESHOLD_MB: kills Docker stack immediately
#
# LOG FILE:
#   /var/log/weppcloud-watchdog.log
#   Contains warnings, kills, and forensic data (top memory consumers)
#
# TUNING:
#   Adjust thresholds below based on your system's total RAM and workload.
#   Current defaults assume a 128GB system where 25GB free is critical.
#
# COMMON CAUSES OF HIGH MEMORY:
#   - Multiple wbt_abstract_watershed processes with high-res DEMs
#   - Set PERIDOT_CPU env var in rq-worker-batch to limit CPU/memory per process
#   - Reduce worker pool size (-n flag) for batch processing
#
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
