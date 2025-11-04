#!/bin/bash
# Script to ensure docker group GID is 993 on multiple systems
# Usage: ./ensure_docker_gid_993.sh [check|fix]

set -euo pipefail

REQUIRED_GID=993
SYSTEMS=("forest1" "nuc1.local" "nuc2.local" "nuc3.local")
MODE="${1:-check}"

check_docker_gid() {
    local system="$1"
    echo "Checking $system..."
    
    if [ "$system" = "$(hostname)" ] || [ "$system" = "$(hostname -f)" ]; then
        # Local system
        current_gid=$(getent group docker | cut -d: -f3)
        echo "  Current docker GID: $current_gid"
        
        if [ "$current_gid" -eq "$REQUIRED_GID" ]; then
            echo "  ✓ GID is correct ($REQUIRED_GID)"
            return 0
        else
            echo "  ✗ GID needs to be changed from $current_gid to $REQUIRED_GID"
            return 1
        fi
    else
        # Remote system
        if ssh -o ConnectTimeout=5 "$system" "exit" 2>/dev/null; then
            current_gid=$(ssh "$system" "getent group docker | cut -d: -f3")
            echo "  Current docker GID: $current_gid"
            
            if [ "$current_gid" -eq "$REQUIRED_GID" ]; then
                echo "  ✓ GID is correct ($REQUIRED_GID)"
                return 0
            else
                echo "  ✗ GID needs to be changed from $current_gid to $REQUIRED_GID"
                return 1
            fi
        else
            echo "  ⚠ Cannot connect to $system"
            return 2
        fi
    fi
}

fix_docker_gid() {
    local system="$1"
    echo "Fixing docker GID on $system..."
    
    if [ "$system" = "$(hostname)" ] || [ "$system" = "$(hostname -f)" ]; then
        # Local system - requires sudo
        echo "  Stopping docker service..."
        sudo systemctl stop docker.socket docker.service
        
        echo "  Changing docker group GID to $REQUIRED_GID..."
        sudo groupmod -g "$REQUIRED_GID" docker
        
        echo "  Starting docker service..."
        sudo systemctl start docker.service
        
        echo "  ✓ Docker GID updated on local system"
    else
        # Remote system
        echo "  Connecting to $system..."
        ssh "$system" "sudo systemctl stop docker.socket docker.service && \
                       sudo groupmod -g $REQUIRED_GID docker && \
                       sudo systemctl start docker.service && \
                       echo '  ✓ Docker GID updated on $system'"
    fi
}

echo "Docker GID Verification/Fix Tool"
echo "================================="
echo "Target GID: $REQUIRED_GID"
echo "Mode: $MODE"
echo ""

case "$MODE" in
    check)
        echo "Running check mode (read-only)..."
        echo ""
        all_good=true
        for system in "${SYSTEMS[@]}"; do
            if ! check_docker_gid "$system"; then
                all_good=false
            fi
            echo ""
        done
        
        if [ "$all_good" = true ]; then
            echo "✓ All systems have correct docker GID ($REQUIRED_GID)"
            exit 0
        else
            echo "⚠ Some systems need docker GID adjustment"
            echo "Run with 'fix' argument to update: $0 fix"
            exit 1
        fi
        ;;
    
    fix)
        echo "Running fix mode (will modify systems)..."
        echo "⚠ This will stop and restart docker service on each system"
        echo "⚠ Running containers will be stopped"
        echo ""
        read -p "Continue? (yes/no): " confirm
        
        if [ "$confirm" != "yes" ]; then
            echo "Aborted."
            exit 1
        fi
        
        echo ""
        for system in "${SYSTEMS[@]}"; do
            check_docker_gid "$system" || {
                status=$?
                if [ $status -eq 1 ]; then
                    fix_docker_gid "$system"
                else
                    echo "  Skipping $system (cannot connect)"
                fi
            }
            echo ""
        done
        
        echo "✓ Docker GID fix complete"
        echo ""
        echo "Verifying changes..."
        echo ""
        for system in "${SYSTEMS[@]}"; do
            check_docker_gid "$system"
            echo ""
        done
        ;;
    
    *)
        echo "Error: Invalid mode '$MODE'"
        echo "Usage: $0 [check|fix]"
        echo "  check - Verify docker GID on all systems (default)"
        echo "  fix   - Update docker GID to $REQUIRED_GID where needed"
        exit 1
        ;;
esac
