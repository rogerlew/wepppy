#!/bin/bash
# Script to ensure docker group GID is 993 on local system
# Must be run as root on each system separately
# Usage: sudo ./ensure_docker_gid_993.sh [check|fix]

set -euo pipefail

REQUIRED_GID=993
MODE="${1:-check}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root"
    echo "Usage: sudo $0 [check|fix]"
    exit 1
fi

check_docker_gid() {
    echo "Checking docker GID on $(hostname -f)..."
    
    if ! getent group docker >/dev/null 2>&1; then
        echo "  ✗ Docker group does not exist"
        return 2
    fi
    
    current_gid=$(getent group docker | cut -d: -f3)
    echo "  Current docker GID: $current_gid"
    
    if [ "$current_gid" -eq "$REQUIRED_GID" ]; then
        echo "  ✓ GID is correct ($REQUIRED_GID)"
        return 0
    else
        echo "  ✗ GID needs to be changed from $current_gid to $REQUIRED_GID"
        return 1
    fi
}

fix_docker_gid() {
    echo "Fixing docker GID on $(hostname -f)..."
    
    echo "  Stopping docker service..."
    systemctl stop docker.socket docker.service
    
    echo "  Changing docker group GID to $REQUIRED_GID..."
    groupmod -g "$REQUIRED_GID" docker
    
    echo "  Starting docker service..."
    systemctl start docker.service
    
    echo "  ✓ Docker GID updated successfully"
}

echo "Docker GID Verification/Fix Tool"
echo "================================="
echo "System: $(hostname -f)"
echo "Target GID: $REQUIRED_GID"
echo "Mode: $MODE"
echo ""

case "$MODE" in
    check)
        echo "Running check mode (read-only)..."
        echo ""
        if check_docker_gid; then
            echo ""
            echo "✓ Docker GID is correct ($REQUIRED_GID)"
            exit 0
        else
            echo ""
            echo "⚠ Docker GID needs adjustment"
            echo "Run with 'fix' argument to update: sudo $0 fix"
            exit 1
        fi
        ;;
    
    fix)
        echo "Running fix mode (will modify system)..."
        echo "⚠ This will stop and restart docker service"
        echo "⚠ Running containers will be stopped"
        echo ""
        
        if check_docker_gid; then
            echo ""
            echo "✓ Docker GID is already correct, no changes needed"
            exit 0
        fi
        
        echo ""
        read -p "Continue? (yes/no): " confirm
        
        if [ "$confirm" != "yes" ]; then
            echo "Aborted."
            exit 1
        fi
        
        echo ""
        fix_docker_gid
        
        echo ""
        echo "Verifying changes..."
        echo ""
        check_docker_gid
        
        echo ""
        echo "✓ Docker GID fix complete"
        echo ""
        echo "Note: Users may need to log out and back in for group changes to take effect"
        ;;
    
    *)
        echo "Error: Invalid mode '$MODE'"
        echo "Usage: sudo $0 [check|fix]"
        echo "  check - Verify docker GID on this system (default)"
        echo "  fix   - Update docker GID to $REQUIRED_GID if needed"
        exit 1
        ;;
esac
