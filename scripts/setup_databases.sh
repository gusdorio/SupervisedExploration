#!/bin/bash

# Database Setup Script
# This script starts the databases and runs the initial migration

set -e  # Exit on error

echo "=========================================="
echo "   ICB DATABASE SETUP SCRIPT"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 1: Starting database containers...${NC}"
docker-compose -f docker-compose.db.yml up -d

echo -e "\n${YELLOW}Step 2: Waiting for databases to be ready...${NC}"

# Wait for MySQL to be ready
echo -n "Waiting for MySQL..."
for i in {1..30}; do
    if docker exec icb_mysql mysqladmin ping -h localhost -u root -proot_password123 --silent 2>/dev/null; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

# Wait for MongoDB to be ready
echo -n "Waiting for MongoDB..."
for i in {1..30}; do
    if docker exec icb_mongodb mongosh --eval "db.adminCommand('ping')" --quiet 2>/dev/null; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

echo -e "\n${YELLOW}Step 3: Database containers status:${NC}"
docker ps --filter "name=icb_mysql" --filter "name=icb_mongodb" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n${GREEN}✅ Databases are ready!${NC}"
echo ""
echo "Connection details:"
echo "  MySQL:    mysql://icb_user:icb_password123@localhost:3306/icb_db"
echo "  MongoDB:  mongodb://root:root_password123@localhost:27017/icb_ml"
echo ""
echo "To run the data migration:"
echo "  python migrations/migrate_clean_data.py"
echo ""
echo "To stop the databases:"
echo "  docker-compose -f docker-compose.db.yml down"
echo ""
echo "To view logs:"
echo "  docker-compose -f docker-compose.db.yml logs -f"