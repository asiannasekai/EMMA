#!/bin/bash

# EMMA System Status and Monitoring Script
# This script provides real-time status information about the EMMA system

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

# Function to show system overview
show_system_overview() {
    echo -e "${PURPLE}"
    echo "======================================================================"
    echo "📊 EMMA System Status Overview"
    echo "======================================================================"
    echo -e "${NC}"
    
    cd "$EMMA_DIR"
    
    # Container status
    echo -e "${CYAN}Container Status:${NC}"
    docker-compose ps
    echo ""
    
    # Resource usage
    echo -e "${CYAN}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" $(docker-compose ps -q)
    echo ""
}

# Function to show service endpoints
show_service_endpoints() {
    echo -e "${CYAN}Service Endpoints:${NC}"
    echo "🌐 Monitoring Dashboard: http://localhost:3002"
    echo "📡 Alert Distributor API: http://localhost:3001"
    echo "📁 HTTP CDN: http://localhost:3000"
    echo "🔗 WebSocket Alerts: ws://localhost:8080"
    echo "📊 Dashboard WebSocket: ws://localhost:3002"
    echo ""
}

# Function to check service health
check_service_health() {
    echo -e "${CYAN}Service Health Checks:${NC}"
    
    # HTTP CDN
    if curl -s -f http://localhost:3000/health >/dev/null 2>&1; then
        echo -e "📁 HTTP CDN: ${GREEN}✅ Healthy${NC}"
    else
        echo -e "📁 HTTP CDN: ${RED}❌ Unhealthy${NC}"
    fi
    
    # Alert Distributor
    if curl -s -f http://localhost:3001/health >/dev/null 2>&1; then
        echo -e "📡 Alert Distributor: ${GREEN}✅ Healthy${NC}"
    else
        echo -e "📡 Alert Distributor: ${RED}❌ Unhealthy${NC}"
    fi
    
    # Dashboard
    if curl -s -f http://localhost:3002/health >/dev/null 2>&1; then
        echo -e "📊 Dashboard: ${GREEN}✅ Healthy${NC}"
    else
        echo -e "📊 Dashboard: ${RED}❌ Unhealthy${NC}"
    fi
    
    # Redis
    if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        echo -e "🔴 Redis: ${GREEN}✅ Healthy${NC}"
    else
        echo -e "🔴 Redis: ${RED}❌ Unhealthy${NC}"
    fi
    
    echo ""
}

# Function to show recent logs
show_recent_logs() {
    echo -e "${CYAN}Recent Activity (last 20 lines):${NC}"
    cd "$EMMA_DIR"
    docker-compose logs --tail=20 --timestamps
    echo ""
}

# Function to show system metrics
show_system_metrics() {
    echo -e "${CYAN}System Metrics:${NC}"
    
    # Get metrics from Redis if available
    if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        echo "📊 Getting metrics from Redis..."
        
        # Total alerts
        local total_alerts=$(docker-compose exec -T redis redis-cli HLEN emma:alert_store 2>/dev/null || echo "0")
        echo "🚨 Total Alerts: $total_alerts"
        
        # Active UEs
        local active_ues=$(docker-compose exec -T redis redis-cli SCARD emma:active_ues 2>/dev/null || echo "0")
        echo "📱 Active UEs: $active_ues"
        
        # Check if there are any recent alerts
        local recent_alerts=$(docker-compose exec -T redis redis-cli HKEYS emma:alert_store 2>/dev/null | head -5)
        if [[ -n "$recent_alerts" ]]; then
            echo "📋 Recent Alert IDs:"
            echo "$recent_alerts" | sed 's/^/   - /'
        fi
    else
        echo "❌ Cannot retrieve metrics - Redis unavailable"
    fi
    
    echo ""
}

# Function to monitor logs in real-time
monitor_logs() {
    local service="${1:-}"
    
    echo -e "${CYAN}Monitoring logs in real-time (Ctrl+C to stop)...${NC}"
    echo ""
    
    cd "$EMMA_DIR"
    
    if [[ -n "$service" ]]; then
        echo "Monitoring logs for service: $service"
        docker-compose logs -f "$service"
    else
        echo "Monitoring logs for all services:"
        docker-compose logs -f
    fi
}

# Function to show detailed service info
show_service_details() {
    local service="$1"
    
    echo -e "${CYAN}Detailed information for service: $service${NC}"
    echo ""
    
    cd "$EMMA_DIR"
    
    # Container info
    local container_name="emma-$service"
    echo "Container Details:"
    docker inspect --format='
Status: {{.State.Status}}
Started: {{.State.StartedAt}}
Health: {{.State.Health.Status}}
Image: {{.Config.Image}}
Ports: {{range $p, $conf := .NetworkSettings.Ports}}{{$p}} -> {{(index $conf 0).HostPort}} {{end}}
' "$container_name" 2>/dev/null || echo "Container not found"
    
    echo ""
    echo "Recent Logs (last 50 lines):"
    docker-compose logs --tail=50 "$service"
}

# Function to run quick diagnostics
run_diagnostics() {
    echo -e "${CYAN}Running EMMA System Diagnostics...${NC}"
    echo ""
    
    cd "$EMMA_DIR"
    
    # Check Docker
    echo "🐳 Docker Status:"
    if docker info >/dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Docker daemon running${NC}"
    else
        echo -e "   ${RED}❌ Docker daemon not running${NC}"
    fi
    
    # Check disk space
    echo "💾 Disk Space:"
    local disk_usage=$(df -h "$EMMA_DIR" | awk 'NR==2{print $5}')
    echo "   Current usage: $disk_usage"
    
    # Check memory
    echo "🧠 Memory Usage:"
    local memory_usage=$(free -h | awk 'NR==2{printf "Used: %s / %s (%.1f%%)", $3, $2, $3/$2*100}')
    echo "   $memory_usage"
    
    # Check network connectivity
    echo "🌐 Network Connectivity:"
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Internet connectivity OK${NC}"
    else
        echo -e "   ${YELLOW}⚠️ Limited internet connectivity${NC}"
    fi
    
    # Check ports
    echo "🔌 Port Status:"
    local ports=(3000 3001 3002 6379 8080)
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            echo -e "   Port $port: ${GREEN}✅ Open${NC}"
        else
            echo -e "   Port $port: ${YELLOW}⚠️ Not listening${NC}"
        fi
    done
    
    echo ""
}

# Main function
main() {
    local command="${1:-overview}"
    
    case "$command" in
        "overview"|"status")
            show_system_overview
            show_service_endpoints
            check_service_health
            show_system_metrics
            ;;
        "health")
            check_service_health
            ;;
        "metrics")
            show_system_metrics
            ;;
        "logs")
            if [[ -n "${2:-}" ]]; then
                show_service_details "$2"
            else
                show_recent_logs
            fi
            ;;
        "monitor")
            monitor_logs "${2:-}"
            ;;
        "diagnostics"|"diag")
            run_diagnostics
            ;;
        "endpoints")
            show_service_endpoints
            ;;
        *)
            echo "Unknown command: $command"
            echo ""
            echo "Available commands:"
            echo "  overview     Show system overview (default)"
            echo "  health       Check service health"
            echo "  metrics      Show system metrics"
            echo "  logs [svc]   Show recent logs (optionally for specific service)"
            echo "  monitor [svc] Monitor logs in real-time"
            echo "  diagnostics  Run system diagnostics"
            echo "  endpoints    Show service endpoints"
            echo ""
            exit 1
            ;;
    esac
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "EMMA System Status Script"
        echo ""
        echo "Usage: $0 [COMMAND] [OPTIONS]"
        echo ""
        echo "Commands:"
        echo "  overview     Show complete system overview (default)"
        echo "  health       Check service health status"
        echo "  metrics      Display system metrics and statistics"
        echo "  logs [svc]   Show recent logs (optionally for specific service)"
        echo "  monitor [svc] Monitor logs in real-time (optionally for specific service)"
        echo "  diagnostics  Run comprehensive system diagnostics"
        echo "  endpoints    Show all service endpoints"
        echo ""
        echo "Examples:"
        echo "  $0                        # Show system overview"
        echo "  $0 health                # Check service health"
        echo "  $0 logs alert-distributor # Show logs for alert distributor"
        echo "  $0 monitor               # Monitor all logs in real-time"
        echo "  $0 diagnostics           # Run system diagnostics"
        echo ""
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac