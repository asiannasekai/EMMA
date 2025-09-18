#!/bin/bash

# EMMA System Restart Script
# This script safely restarts the EMMA system

set -e

EMMA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}"
echo "======================================================================"
echo "🔄 EMMA System Restart"
echo "======================================================================"
echo -e "${NC}"

echo -e "${BLUE}Stopping EMMA system...${NC}"
"$EMMA_DIR/scripts/stop-emma.sh"

echo ""
echo -e "${BLUE}Starting EMMA system...${NC}"
"$EMMA_DIR/scripts/start-emma.sh" "$@"

echo -e "${GREEN}"
echo "======================================================================"
echo "✅ EMMA System Restarted Successfully"
echo "======================================================================"
echo -e "${NC}"