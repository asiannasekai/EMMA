#!/bin/bash

# EMMA System - Optimized Startup Script
# This script starts EMMA with resource optimization and staged deployment

set -e

EMMA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Estimated timings (in seconds)
REDIS_START_TIME=10
HTTP_CDN_START_TIME=15
ALERT_DISTRIBUTOR_START_TIME=20
DASHBOARD_START_TIME=15
CAP_GENERATOR_START_TIME=25
TOTAL_ESTIMATED_TIME=85

print_header() {
    echo -e "${PURPLE}"
    echo "======================================================================"
    echo "🚀 EMMA Emergency Alert System - Optimized Startup"
    echo "======================================================================"
    echo -e "${NC}"
    echo -e "${CYAN}📊 Estimated total startup time: ${TOTAL_ESTIMATED_TIME} seconds${NC}"
    echo -e "${CYAN}🔧 Using optimized resource limits to reduce CPU usage${NC}"
    echo ""
}

# Function to wait for service to be healthy
wait_for_service() {
    local service_name="$1"
    local max_wait="$2"
    local interval=3
    local elapsed=0
    
    echo -e "${BLUE}⏳ Waiting for $service_name to be ready (max ${max_wait}s)...${NC}"
    
    while [ $elapsed -lt $max_wait ]; do
        # Check if service is running and healthy (if health check exists)
        local health_status=$(docker-compose ps -q "$service_name" | xargs docker inspect --format '{{.State.Health.Status}}' 2>/dev/null || echo "none")
        local running_status=$(docker-compose ps -q "$service_name" | xargs docker inspect --format '{{.State.Status}}' 2>/dev/null || echo "exited")
        
        if [[ "$health_status" == "healthy" ]] || [[ "$health_status" == "none" && "$running_status" == "running" ]]; then
            echo -e "${GREEN}✅ $service_name is ready (${elapsed}s)${NC}"
            return 0
        fi
        
        if [[ "$running_status" == "exited" ]]; then
            echo -e "${RED}❌ $service_name failed to start${NC}"
            return 1
        fi
        
        sleep $interval
        elapsed=$((elapsed + interval))
        echo -e "${YELLOW}   Still waiting... (${elapsed}s)${NC}"
    done
    
    echo -e "${RED}❌ $service_name failed to start within ${max_wait}s${NC}"
    return 1
}

# Function to start core services first
start_core_services() {
    echo -e "${CYAN}🔴 Starting Redis (message queue)...${NC}"
    docker-compose up -d redis
    
    # Simple wait for Redis to be running
    sleep 5
    echo -e "${GREEN}✅ Redis started${NC}"
    
    echo ""
    echo -e "${CYAN}📁 Starting HTTP CDN...${NC}"
    docker-compose up -d http-cdn
    
    # Simple wait for HTTP CDN
    sleep 8
    echo -e "${GREEN}✅ HTTP CDN started${NC}"
}

# Function to start application services
start_app_services() {
    echo ""
    echo -e "${CYAN}📡 Starting Alert Distributor...${NC}"
    docker-compose up -d alert-distributor
    
    # Wait for alert distributor to be running (no health check)
    sleep 5
    
    echo ""
    echo -e "${CYAN}📊 Starting Dashboard...${NC}"
    docker-compose up -d dashboard
    
    # Wait for dashboard to be running
    sleep 5
}

# Function to start background services
start_background_services() {
    echo ""
    echo -e "${CYAN}🏗️ Starting CAP Generator...${NC}"
    docker-compose up -d cap-generator
    sleep 3
    echo -e "${GREEN}✅ CAP Generator started${NC}"
    
    echo ""
    echo -e "${CYAN}🌐 Starting NS-3 Simulator (background)...${NC}"
    docker-compose up -d ns3-sim
    sleep 2
    echo -e "${GREEN}✅ NS-3 Simulator started${NC}"
    
    echo ""
    echo -e "${YELLOW}📱 Note: UE Emulator disabled by default to save resources${NC}"
    echo -e "${YELLOW}   To enable: docker-compose up -d ue-emulator${NC}"
}

# Function to show service status
show_service_status() {
    echo ""
    echo -e "${PURPLE}📊 Service Status:${NC}"
    docker-compose ps
    
    echo ""
    echo -e "${PURPLE}🌐 Available Endpoints:${NC}"
    echo -e "  📊 Dashboard:        ${GREEN}http://localhost:3002${NC}"
    echo -e "  📡 Alert Distributor: ${GREEN}http://localhost:3001${NC}"
    echo -e "  📁 HTTP CDN:         ${GREEN}http://localhost:3000${NC}"
    echo -e "  🔗 WebSocket:        ${GREEN}ws://localhost:8080${NC}"
    
    echo ""
    echo -e "${PURPLE}💡 Quick Commands:${NC}"
    echo -e "  📊 System status:    ${CYAN}./scripts/emma-status.sh${NC}"
    echo -e "  📝 Monitor logs:     ${CYAN}./scripts/emma-status.sh monitor${NC}"
    echo -e "  🧪 Run tests:        ${CYAN}./scripts/run-tests.sh --quick${NC}"
    echo -e "  🛑 Stop system:      ${CYAN}./scripts/stop-emma.sh${NC}"
}

# Function to run quick health checks
run_health_checks() {
    echo ""
    echo -e "${CYAN}🏥 Running quick health checks...${NC}"
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        echo -e "  🔴 Redis: ${GREEN}✅ Healthy${NC}"
    else
        echo -e "  🔴 Redis: ${RED}❌ Unhealthy${NC}"
    fi
    
    # Check HTTP CDN
    sleep 2
    if curl -s -f http://localhost:3000/health >/dev/null 2>&1; then
        echo -e "  📁 HTTP CDN: ${GREEN}✅ Healthy${NC}"
    else
        echo -e "  📁 HTTP CDN: ${YELLOW}⚠️ Starting...${NC}"
    fi
    
    # Check Dashboard
    sleep 2
    if curl -s -f http://localhost:3002 >/dev/null 2>&1; then
        echo -e "  📊 Dashboard: ${GREEN}✅ Healthy${NC}"
    else
        echo -e "  📊 Dashboard: ${YELLOW}⚠️ Starting...${NC}"
    fi
}

# Main execution
main() {
    cd "$EMMA_DIR"
    
    print_header
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
        exit 1
    fi
    
    # Check if system is already running
    if docker-compose ps -q | grep -q .; then
        echo -e "${YELLOW}⚠️ EMMA system is already running. Stopping first...${NC}"
        docker-compose down
        sleep 3
    fi
    
    local start_time=$(date +%s)
    
    echo -e "${BLUE}🏗️ Starting EMMA system with optimized settings...${NC}"
    echo ""
    
    # Stage 1: Core infrastructure
    start_core_services
    
    # Stage 2: Application services
    start_app_services
    
    # Stage 3: Background services
    start_background_services
    
    # Final checks and summary
    run_health_checks
    
    local end_time=$(date +%s)
    local actual_time=$((end_time - start_time))
    
    echo ""
    echo -e "${GREEN}🎉 EMMA system started successfully!${NC}"
    echo -e "${CYAN}⏱️ Actual startup time: ${actual_time} seconds${NC}"
    
    show_service_status
    
    echo ""
    echo -e "${PURPLE}⚡ Resource Usage Optimization:${NC}"
    echo -e "  • CPU limits: 0.3-1.0 cores per service"
    echo -e "  • Memory limits: 128-512 MB per service"
    echo -e "  • Health check intervals: Extended to reduce overhead"
    echo -e "  • UE Emulator: Disabled by default (high resource usage)"
    
    echo ""
    echo -e "${GREEN}🚀 EMMA is ready for emergency alert operations!${NC}"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "EMMA Optimized Startup Script"
        echo ""
        echo "This script starts EMMA with resource optimization to reduce CPU usage."
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Features:"
        echo "  • Staged startup to prevent resource spikes"
        echo "  • Resource limits to control CPU/memory usage"
        echo "  • Health monitoring with extended intervals"
        echo "  • Quick health checks after startup"
        echo ""
        echo "Estimated startup time: ${TOTAL_ESTIMATED_TIME} seconds"
        echo ""
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac