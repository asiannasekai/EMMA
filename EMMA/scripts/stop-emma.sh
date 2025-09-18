#!/bin/bash

# EMMA System Stop Script
# This script safely stops all EMMA system components

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

EMMA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

# Header
echo -e "${PURPLE}"
echo "======================================================================"
echo "🛑 EMMA System Shutdown"
echo "======================================================================"
echo -e "${NC}"

# Function to gracefully stop services
stop_services() {
    log "Stopping EMMA services gracefully..."
    
    cd "$EMMA_DIR"
    
    # Stop services in reverse order of dependencies
    services=("ue-emulator" "dashboard" "ns3-sim" "alert-distributor" "http-cdn" "cap-generator" "redis")
    
    for service in "${services[@]}"; do
        log "Stopping $service..."
        docker-compose stop "$service" 2>/dev/null || log_warning "Service $service was not running"
    done
    
    log_success "All services stopped"
}

# Function to remove containers
remove_containers() {
    log "Removing EMMA containers..."
    
    cd "$EMMA_DIR"
    
    docker-compose down --remove-orphans 2>/dev/null || true
    
    log_success "Containers removed"
}

# Function to clean up resources (optional)
cleanup_resources() {
    if [[ "${1:-}" == "--clean" ]]; then
        log "Cleaning up Docker resources..."
        
        # Remove unused networks
        docker network prune -f 2>/dev/null || true
        
        # Remove dangling images
        docker image prune -f 2>/dev/null || true
        
        log_success "Resources cleaned up"
    fi
}

# Function to show final status
show_final_status() {
    echo ""
    echo -e "${GREEN}"
    echo "======================================================================"
    echo "✅ EMMA System Stopped Successfully"
    echo "======================================================================"
    echo -e "${NC}"
    echo "All EMMA services have been stopped and containers removed."
    echo ""
    echo "To start the system again, run: ./scripts/start-emma.sh"
    echo ""
}

# Main execution
main() {
    local force_stop="${1:-}"
    
    if [[ "$force_stop" == "--force" ]]; then
        log "Force stopping all EMMA containers..."
        cd "$EMMA_DIR"
        docker-compose kill 2>/dev/null || true
    else
        stop_services
    fi
    
    remove_containers
    cleanup_resources "$1"
    show_final_status
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "EMMA System Stop Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --force         Force kill all containers immediately"
        echo "  --clean         Clean up Docker resources after stopping"
        echo "  --help, -h      Show this help message"
        echo ""
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac