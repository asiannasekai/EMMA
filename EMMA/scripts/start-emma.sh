#!/bin/bash

# EMMA System Startup Script
# This script initializes and starts the complete EMMA emergency alert system

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
EMMA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$EMMA_DIR/logs"
TIMEOUT=300  # 5 minutes timeout for services

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

# Create logs directory
mkdir -p "$LOG_DIR"

# Header
echo -e "${PURPLE}"
echo "======================================================================"
echo "🚀 EMMA - Enhanced Multimedia Mobile Alerts System"
echo "======================================================================"
echo -e "${NC}"
echo "Starting up the complete EMMA emergency alert system..."
echo "System directory: $EMMA_DIR"
echo ""

# Function to check if Docker is running
check_docker() {
    log "Checking Docker installation and status..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log_success "Docker and Docker Compose are ready"
}

# Function to check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check available memory (minimum 4GB recommended)
    available_memory=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
    if (( $(echo "$available_memory < 2.0" | bc -l) )); then
        log_warning "Low available memory: ${available_memory}GB. Recommended: 4GB+"
    else
        log_success "Memory check passed: ${available_memory}GB available"
    fi
    
    # Check available disk space (minimum 10GB recommended)
    available_space=$(df -BG "$EMMA_DIR" | awk 'NR==2{print $4}' | sed 's/G//')
    if [[ $available_space -lt 10 ]]; then
        log_warning "Low available disk space: ${available_space}GB. Recommended: 10GB+"
    else
        log_success "Disk space check passed: ${available_space}GB available"
    fi
}

# Function to cleanup previous containers
cleanup_previous() {
    log "Cleaning up any previous EMMA containers..."
    
    cd "$EMMA_DIR"
    
    # Stop and remove containers if they exist
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # Remove any dangling volumes (optional, commented out for safety)
    # docker volume prune -f
    
    log_success "Cleanup completed"
}

# Function to pull/build images
build_images() {
    log "Building EMMA container images..."
    
    cd "$EMMA_DIR"
    
    # Build all images with progress tracking
    docker-compose build --parallel 2>&1 | tee "$LOG_DIR/build.log"
    
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_success "All container images built successfully"
    else
        log_error "Failed to build container images. Check $LOG_DIR/build.log for details."
        exit 1
    fi
}

# Function to start infrastructure services first
start_infrastructure() {
    log "Starting infrastructure services..."
    
    cd "$EMMA_DIR"
    
    # Start Redis first
    log "Starting Redis..."
    docker-compose up -d redis
    
    # Wait for Redis to be ready
    wait_for_service "redis" "redis-cli ping" "PONG"
    
    log_success "Infrastructure services started"
}

# Function to start core services
start_core_services() {
    log "Starting core EMMA services..."
    
    cd "$EMMA_DIR"
    
    # Start core services
    services=("cap-generator" "http-cdn" "alert-distributor")
    
    for service in "${services[@]}"; do
        log "Starting $service..."
        docker-compose up -d "$service"
    done
    
    # Wait for services to be healthy
    for service in "${services[@]}"; do
        wait_for_service_health "$service"
    done
    
    log_success "Core services started"
}

# Function to start simulation and emulation services
start_simulation_services() {
    log "Starting simulation and emulation services..."
    
    cd "$EMMA_DIR"
    
    # Start NS-3 simulator
    log "Starting NS-3 simulator..."
    docker-compose up -d ns3-sim
    
    # Start UE emulator (requires special handling for Android)
    log "Starting UE emulator..."
    docker-compose up -d ue-emulator
    
    # Start dashboard
    log "Starting monitoring dashboard..."
    docker-compose up -d dashboard
    
    wait_for_service_health "dashboard"
    
    log_success "Simulation and emulation services started"
}

# Function to wait for a service to be ready
wait_for_service() {
    local service_name="$1"
    local check_command="$2"
    local expected_output="$3"
    local timeout_duration=${4:-60}
    
    log "Waiting for $service_name to be ready..."
    
    local counter=0
    while [[ $counter -lt $timeout_duration ]]; do
        if docker-compose exec -T "$service_name" $check_command 2>/dev/null | grep -q "$expected_output"; then
            log_success "$service_name is ready"
            return 0
        fi
        
        counter=$((counter + 5))
        sleep 5
        echo -n "."
    done
    
    echo ""
    log_error "$service_name failed to start within $timeout_duration seconds"
    return 1
}

# Function to wait for service health check
wait_for_service_health() {
    local service_name="$1"
    local timeout_duration=${2:-120}
    
    log "Waiting for $service_name health check..."
    
    local counter=0
    while [[ $counter -lt $timeout_duration ]]; do
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "emma-$service_name" 2>/dev/null || echo "no-health-check")
        
        if [[ "$health_status" == "healthy" ]] || [[ "$health_status" == "no-health-check" ]]; then
            # If no health check, verify container is running
            if [[ "$health_status" == "no-health-check" ]]; then
                local container_status=$(docker inspect --format='{{.State.Running}}' "emma-$service_name" 2>/dev/null || echo "false")
                if [[ "$container_status" == "true" ]]; then
                    log_success "$service_name is running"
                    return 0
                fi
            else
                log_success "$service_name is healthy"
                return 0
            fi
        fi
        
        counter=$((counter + 5))
        sleep 5
        echo -n "."
    done
    
    echo ""
    log_warning "$service_name health check timeout (may still be starting)"
    return 0  # Don't fail startup for health check timeout
}

# Function to run integration tests
run_integration_tests() {
    log "Running integration tests..."
    
    cd "$EMMA_DIR"
    
    # Install test dependencies if not already installed
    if [[ ! -d "tests/venv" ]]; then
        log "Setting up test environment..."
        cd tests
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cd ..
    fi
    
    # Run tests
    cd tests
    source venv/bin/activate
    
    log "Executing integration tests..."
    python integration_test.py 2>&1 | tee "$LOG_DIR/integration_tests.log"
    
    local test_result=${PIPESTATUS[0]}
    
    if [[ $test_result -eq 0 ]]; then
        log_success "Integration tests passed"
    else
        log_warning "Some integration tests failed. Check $LOG_DIR/integration_tests.log for details."
    fi
    
    cd "$EMMA_DIR"
}

# Function to display system status
show_system_status() {
    log "Gathering system status..."
    
    cd "$EMMA_DIR"
    
    echo ""
    echo -e "${CYAN}======================================================================"
    echo "📊 EMMA System Status"
    echo -e "======================================================================${NC}"
    
    # Show container status
    echo -e "${YELLOW}Container Status:${NC}"
    docker-compose ps
    echo ""
    
    # Show service endpoints
    echo -e "${YELLOW}Service Endpoints:${NC}"
    echo "🌐 Monitoring Dashboard: http://localhost:3002"
    echo "📡 Alert Distributor API: http://localhost:3001"
    echo "📁 HTTP CDN: http://localhost:3000"
    echo "🔗 WebSocket Alerts: ws://localhost:8080"
    echo "📊 Dashboard WebSocket: ws://localhost:3002"
    echo ""
    
    # Show logs location
    echo -e "${YELLOW}Logs:${NC}"
    echo "📝 Build logs: $LOG_DIR/build.log"
    echo "🧪 Test logs: $LOG_DIR/integration_tests.log"
    echo "📋 Service logs: docker-compose logs [service-name]"
    echo ""
    
    # Show useful commands
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "📊 View all logs: docker-compose logs -f"
    echo "🔍 View specific service: docker-compose logs -f [service-name]"
    echo "⏹️  Stop system: ./scripts/stop-emma.sh"
    echo "🔄 Restart system: ./scripts/restart-emma.sh"
    echo "🧪 Run tests: ./scripts/run-tests.sh"
    echo ""
}

# Function to create a simple test alert
create_test_alert() {
    log "Creating a test alert to verify system functionality..."
    
    sleep 10  # Wait for all services to fully initialize
    
    # Try to create a test alert via the alert distributor API
    local test_alert='{
        "identifier": "TEST-STARTUP-001",
        "sender": "startup-script",
        "sent": "'$(date -Iseconds)'",
        "status": "Actual",
        "msgType": "Alert",
        "scope": "Public",
        "category": "Safety",
        "event": "System Startup Test",
        "urgency": "Expected",
        "severity": "Minor",
        "certainty": "Observed",
        "headline": "EMMA System Started Successfully",
        "description": "This is a test alert generated during system startup to verify functionality."
    }'
    
    if curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$test_alert" \
        "http://localhost:3001/distribute-alert" > /dev/null 2>&1; then
        log_success "Test alert sent successfully"
    else
        log_warning "Failed to send test alert (system may still be initializing)"
    fi
}

# Main execution
main() {
    local start_time=$(date +%s)
    
    # Check prerequisites
    check_docker
    check_requirements
    
    # Cleanup any previous deployment
    cleanup_previous
    
    # Build images
    build_images
    
    # Start services in order
    start_infrastructure
    start_core_services
    start_simulation_services
    
    # Create test alert
    create_test_alert
    
    # Run integration tests (optional)
    if [[ "${1:-}" == "--with-tests" ]]; then
        run_integration_tests
    fi
    
    # Show final status
    show_system_status
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo -e "${GREEN}"
    echo "======================================================================"
    echo "🎉 EMMA System Started Successfully!"
    echo "======================================================================"
    echo -e "${NC}"
    echo "⏱️  Total startup time: ${duration} seconds"
    echo "🌐 Access the monitoring dashboard at: http://localhost:3002"
    echo ""
    echo "The EMMA emergency alert system is now running and ready to process alerts."
    echo "Check the dashboard for real-time system status and metrics."
    echo ""
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "EMMA System Startup Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --with-tests    Run integration tests after startup"
        echo "  --help, -h      Show this help message"
        echo ""
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac