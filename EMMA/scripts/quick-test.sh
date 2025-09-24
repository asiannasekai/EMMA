#!/bin/bash

# EMMA Quick Test Script
# Runs essential tests without heavy load

set -e

EMMA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🧪 EMMA Quick Test Suite${NC}"
echo "Running essential tests only..."
echo ""

cd "$EMMA_DIR"

# Test 1: Service availability
echo -e "${CYAN}📊 Testing service availability...${NC}"

if docker-compose ps | grep -q "Up"; then
    echo -e "✅ Services are running"
else
    echo -e "❌ No services running"
    exit 1
fi

# Test 2: Redis connectivity
echo -e "${CYAN}🔴 Testing Redis connectivity...${NC}"
if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    echo -e "✅ Redis is responding"
else
    echo -e "❌ Redis connection failed"
fi

# Test 3: HTTP endpoints
echo -e "${CYAN}🌐 Testing HTTP endpoints...${NC}"

# Test HTTP CDN
if curl -s -f http://localhost:3000/health >/dev/null 2>&1; then
    echo -e "✅ HTTP CDN is responding"
else
    echo -e "⚠️ HTTP CDN not ready yet"
fi

# Test Dashboard
if curl -s -f http://localhost:3002 >/dev/null 2>&1; then
    echo -e "✅ Dashboard is accessible"
else
    echo -e "⚠️ Dashboard not ready yet"
fi

# Test 4: Container resource usage
echo -e "${CYAN}📈 Checking resource usage...${NC}"
echo "Container resource stats:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker-compose ps -q) 2>/dev/null || echo "Stats not available"

echo ""
echo -e "${GREEN}✅ Quick tests completed!${NC}"
echo -e "${YELLOW}💡 For full testing, run: ./scripts/run-tests.sh${NC}"