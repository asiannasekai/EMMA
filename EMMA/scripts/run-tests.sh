#!/bin/bash

# EMMA Integration Tests Script
# This script runs the complete integration test suite

set -e

EMMA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="$EMMA_DIR/tests"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

# Header
echo -e "${PURPLE}"
echo "======================================================================"
echo "🧪 EMMA Integration Tests"
echo "======================================================================"
echo -e "${NC}"

# Function to check if system is running
check_system_running() {
    log "Checking if EMMA system is running..."
    
    cd "$EMMA_DIR"
    
    # Check if containers are running
    local running_containers=$(docker-compose ps --services --filter "status=running" | wc -l)
    local total_services=6  # Adjust based on your services
    
    if [[ $running_containers -lt $total_services ]]; then
        log_error "EMMA system is not fully running. Please start it first with: ./scripts/start-emma.sh"
        exit 1
    fi
    
    log_success "EMMA system is running"
}

# Function to setup test environment
setup_test_environment() {
    log "Setting up test environment..."
    
    cd "$TEST_DIR"
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        log "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    source venv/bin/activate
    
    log "Installing test dependencies..."
    pip install -q -r requirements.txt
    
    log_success "Test environment ready"
}

# Function to run specific test categories
run_test_category() {
    local category="$1"
    local test_file="$2"
    
    log "Running $category tests..."
    
    cd "$TEST_DIR"
    source venv/bin/activate
    
    if [[ -f "$test_file" ]]; then
        python "$test_file"
        local result=$?
        
        if [[ $result -eq 0 ]]; then
            log_success "$category tests passed"
        else
            log_error "$category tests failed"
            return $result
        fi
    else
        log_error "Test file $test_file not found"
        return 1
    fi
}

# Function to run pytest tests
run_pytest_tests() {
    log "Running pytest test suite..."
    
    cd "$TEST_DIR"
    source venv/bin/activate
    
    pytest test_emma_integration.py -v --tb=short
    local result=$?
    
    if [[ $result -eq 0 ]]; then
        log_success "Pytest tests passed"
    else
        log_error "Pytest tests failed"
        return $result
    fi
}

# Function to generate test report
generate_test_report() {
    log "Generating test report..."
    
    local report_file="$EMMA_DIR/logs/test_report_$(date '+%Y%m%d_%H%M%S').json"
    
    # Get test results from Redis
    docker-compose exec -T redis redis-cli KEYS "emma:test_report:*" | while read -r key; do
        if [[ -n "$key" ]]; then
            docker-compose exec -T redis redis-cli GET "$key" > "$report_file"
            log_success "Test report saved to: $report_file"
            break
        fi
    done
}

# Function to run performance tests
run_performance_tests() {
    log "Running performance tests..."
    
    cd "$TEST_DIR"
    source venv/bin/activate
    
    # Run performance-specific tests
    python -c "
import asyncio
from integration_test import EmmaIntegrationTest

async def run_perf_tests():
    test_runner = EmmaIntegrationTest()
    await test_runner.setup()
    await test_runner.test_system_performance()
    await test_runner.test_multiple_ue_delivery()

asyncio.run(run_perf_tests())
"
    
    local result=$?
    
    if [[ $result -eq 0 ]]; then
        log_success "Performance tests passed"
    else
        log_error "Performance tests failed"
        return $result
    fi
}

# Function to show test summary
show_test_summary() {
    echo ""
    echo -e "${GREEN}"
    echo "======================================================================"
    echo "📊 Test Summary"
    echo "======================================================================"
    echo -e "${NC}"
    
    # Show container status
    cd "$EMMA_DIR"
    docker-compose ps
    
    echo ""
    echo "📝 Test logs are available in: $EMMA_DIR/logs/"
    echo "📊 View test reports in Redis or check the dashboard"
    echo "🌐 Dashboard: http://localhost:3002"
    echo ""
}

# Main execution function
main() {
    local test_type="${1:-all}"
    
    # Ensure logs directory exists
    mkdir -p "$EMMA_DIR/logs"
    
    # Check if system is running
    check_system_running
    
    # Setup test environment
    setup_test_environment
    
    case "$test_type" in
        "integration"|"all")
            run_test_category "Integration" "integration_test.py"
            ;;
        "pytest")
            run_pytest_tests
            ;;
        "performance"|"perf")
            run_performance_tests
            ;;
        "quick")
            # Run a subset of quick tests
            cd "$TEST_DIR"
            source venv/bin/activate
            python -c "
import asyncio
from integration_test import EmmaIntegrationTest

async def run_quick_tests():
    test_runner = EmmaIntegrationTest()
    await test_runner.setup()
    await test_runner.test_websocket_connection()
    await test_runner.test_basic_alert_generation()

asyncio.run(run_quick_tests())
"
            ;;
        *)
            echo "Unknown test type: $test_type"
            echo "Available types: integration, pytest, performance, quick, all"
            exit 1
            ;;
    esac
    
    # Generate test report
    generate_test_report
    
    # Show summary
    show_test_summary
    
    log_success "Test execution completed"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "EMMA Integration Tests Script"
        echo ""
        echo "Usage: $0 [TEST_TYPE]"
        echo ""
        echo "Test Types:"
        echo "  integration     Run full integration tests (default)"
        echo "  pytest          Run pytest test suite"
        echo "  performance     Run performance tests only"
        echo "  quick           Run quick smoke tests"
        echo "  all             Run all test categories"
        echo ""
        echo "Options:"
        echo "  --help, -h      Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                    # Run all integration tests"
        echo "  $0 quick             # Run quick smoke tests"
        echo "  $0 performance       # Run performance tests only"
        echo ""
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac