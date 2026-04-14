#!/bin/bash

# CookRag Backend Startup Script
# This script starts the FastAPI backend server

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  CookRag Backend Server Startup${NC}"
echo -e "${GREEN}=====================================${NC}"

# Change to backend directory
cd "$(dirname "$0")/backend" || exit 1

echo -e "${YELLOW}Checking Python dependencies...${NC}"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo -e "${RED}Error: pip is not installed${NC}"
    exit 1
fi

# Use pip3 if available, otherwise pip
PIP_CMD="pip3"
if ! command -v pip3 &> /dev/null; then
    PIP_CMD="pip"
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
$PIP_CMD install -r requirements.txt --quiet

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Using .env.example as template.${NC}"
    echo -e "${YELLOW}Please create .env file with your configuration.${NC}"
    if [ -f "../.env.example" ]; then
        cp ../.env.example ../.env
        echo -e "${GREEN}Created .env file from template. Please review and update it.${NC}"
    fi
fi

# Load environment variables
if [ -f "../.env" ]; then
    echo -e "${YELLOW}Loading environment variables from .env...${NC}"
    set -a
    source ../.env
    set +a
fi

echo -e "${GREEN}Starting backend server...${NC}"
echo -e "${GREEN}Server will be available at: http://localhost:8000${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
