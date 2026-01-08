#!/bin/bash
# install-memory-watchdog.sh
# Installs the WEPPcloud memory watchdog as a systemd timer
#
# Usage: sudo ./install-memory-watchdog.sh
#
# This script:
# 1. Copies systemd unit files to /etc/systemd/system/
# 2. Creates the log file with proper permissions
# 3. Enables and starts the watchdog timer
#
# The watchdog monitors system memory every 10 seconds and:
# - Logs warnings when available memory drops below 30GB
# - Kills the Docker stack when available memory drops below 25GB
#
# This prevents OOM conditions that can make the system unresponsive.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_SRC="$SCRIPT_DIR/systemd"
SYSTEMD_DEST="/etc/systemd/system"
LOGFILE="/var/log/weppcloud-watchdog.log"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Verify source files exist
if [[ ! -f "$SYSTEMD_SRC/weppcloud-watchdog.service" ]]; then
    echo "Error: weppcloud-watchdog.service not found in $SYSTEMD_SRC"
    exit 1
fi

if [[ ! -f "$SYSTEMD_SRC/weppcloud-watchdog.timer" ]]; then
    echo "Error: weppcloud-watchdog.timer not found in $SYSTEMD_SRC"
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/memory-watchdog.sh" ]]; then
    echo "Error: memory-watchdog.sh not found in $SCRIPT_DIR"
    exit 1
fi

echo "Installing WEPPcloud memory watchdog..."

# Copy systemd unit files
echo "  Copying systemd unit files..."
cp "$SYSTEMD_SRC/weppcloud-watchdog.service" "$SYSTEMD_DEST/"
cp "$SYSTEMD_SRC/weppcloud-watchdog.timer" "$SYSTEMD_DEST/"

# Ensure the watchdog script is executable
chmod +x "$SCRIPT_DIR/memory-watchdog.sh"

# Create log file with proper permissions
echo "  Creating log file..."
touch "$LOGFILE"
chmod 644 "$LOGFILE"

# Reload systemd
echo "  Reloading systemd daemon..."
systemctl daemon-reload

# Enable and start the timer
echo "  Enabling and starting watchdog timer..."
systemctl enable weppcloud-watchdog.timer
systemctl start weppcloud-watchdog.timer

# Verify
echo ""
echo "Installation complete. Verifying..."
echo ""
systemctl status weppcloud-watchdog.timer --no-pager || true
echo ""
echo "Watchdog timer is now active. It will check memory every 10 seconds."
echo "Log file: $LOGFILE"
echo ""
echo "Useful commands:"
echo "  View logs:     tail -f $LOGFILE"
echo "  Check status:  systemctl status weppcloud-watchdog.timer"
echo "  Stop:          sudo systemctl stop weppcloud-watchdog.timer"
echo "  Disable:       sudo systemctl disable weppcloud-watchdog.timer"
