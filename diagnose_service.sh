#!/bin/bash
# Service Diagnostic and Fix Script
# This script checks and fixes systemd service configuration

echo "========================================================================"
echo "AI Dropshipping ERP - Service Diagnostic Tool"
echo "========================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check current working directory
echo "[1] Current Working Directory:"
pwd
echo ""

# 2. Check if service file exists
echo "[2] Checking for systemd service file..."
if [ -f "/etc/systemd/system/webapp.service" ]; then
    echo -e "${GREEN}✓ Found: /etc/systemd/system/webapp.service${NC}"
    echo ""
    echo "Current service configuration:"
    cat /etc/systemd/system/webapp.service
    echo ""
else
    echo -e "${RED}✗ Service file not found at /etc/systemd/system/webapp.service${NC}"
    echo ""
fi

# 3. Check if process is running
echo "[3] Checking for running Flask process..."
FLASK_PID=$(pgrep -f "python.*app.py" | head -1)
if [ ! -z "$FLASK_PID" ]; then
    echo -e "${GREEN}✓ Flask process found (PID: $FLASK_PID)${NC}"
    echo ""
    echo "Process details:"
    ps aux | grep "[p]ython.*app.py"
    echo ""
    echo "Working directory of process:"
    pwdx $FLASK_PID
    echo ""
else
    echo -e "${YELLOW}⚠ No Flask process running${NC}"
    echo ""
fi

# 4. Check Git repository status
echo "[4] Git Repository Status:"
if [ -d ".git" ]; then
    echo "Current commit:"
    git log --oneline -1
    echo ""
    echo "Repository status:"
    git status
    echo ""
else
    echo -e "${RED}✗ Not a git repository${NC}"
    echo ""
fi

# 5. Check app.py file
echo "[5] Checking app.py..."
if [ -f "app.py" ]; then
    echo -e "${GREEN}✓ app.py exists in current directory${NC}"
    echo ""
    echo "First 10 lines of app.py:"
    head -10 app.py
    echo ""
    echo "Checking for DB initialization marker:"
    if grep -q "DATABASE INITIALIZATION COMPLETE" app.py; then
        echo -e "${GREEN}✓ DB initialization marker FOUND in app.py${NC}"
    else
        echo -e "${RED}✗ DB initialization marker NOT FOUND in app.py${NC}"
    fi
    echo ""
else
    echo -e "${RED}✗ app.py not found in current directory${NC}"
    echo ""
fi

# 6. Check log files
echo "[6] Checking log files..."
if [ -d "logs" ]; then
    echo -e "${GREEN}✓ logs directory exists${NC}"
    if [ -f "logs/server.log" ]; then
        echo "Last 10 lines of logs/server.log:"
        tail -10 logs/server.log
        echo ""
        echo "Checking for DB verification marker in logs:"
        if grep -q "DATABASE INITIALIZATION COMPLETE" logs/server.log 2>/dev/null; then
            echo -e "${GREEN}✓ Marker FOUND in logs${NC}"
        else
            echo -e "${YELLOW}⚠ Marker NOT FOUND in logs (old version running?)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ logs/server.log does not exist${NC}"
    fi
else
    echo -e "${YELLOW}⚠ logs directory does not exist${NC}"
fi
echo ""

# 7. Check dropship.db
echo "[7] Checking database file..."
if [ -f "dropship.db" ]; then
    echo -e "${GREEN}✓ dropship.db exists${NC}"
    echo "Database size: $(ls -lh dropship.db | awk '{print $5}')"
    echo "Last modified: $(stat -c %y dropship.db)"
    echo ""
    echo "Tables in database:"
    sqlite3 dropship.db ".tables" 2>/dev/null || echo "Cannot read database"
else
    echo -e "${RED}✗ dropship.db not found${NC}"
fi
echo ""

# 8. Recommendations
echo "========================================================================"
echo "RECOMMENDATIONS:"
echo "========================================================================"
echo ""

if [ ! -f "/etc/systemd/system/webapp.service" ]; then
    echo -e "${YELLOW}⚠ No systemd service found. Running manually?${NC}"
    echo "  → Use: python3 app.py"
    echo ""
fi

if [ ! -z "$FLASK_PID" ]; then
    PROC_DIR=$(pwdx $FLASK_PID 2>/dev/null | awk '{print $2}')
    CURRENT_DIR=$(pwd)
    if [ "$PROC_DIR" != "$CURRENT_DIR" ]; then
        echo -e "${RED}✗ Process is running from different directory!${NC}"
        echo "  Process directory: $PROC_DIR"
        echo "  Current directory: $CURRENT_DIR"
        echo ""
        echo "  FIX: Kill the process and restart from correct directory"
        echo "  → pkill -9 -f 'python.*app.py'"
        echo "  → cd $CURRENT_DIR"
        echo "  → python3 app.py"
        echo ""
    fi
fi

if ! grep -q "DATABASE INITIALIZATION COMPLETE" app.py 2>/dev/null; then
    echo -e "${RED}✗ Old version of app.py detected!${NC}"
    echo "  FIX: Pull latest code"
    echo "  → git fetch origin"
    echo "  → git reset --hard origin/main"
    echo ""
fi

echo "========================================================================"
echo "END OF DIAGNOSTIC"
echo "========================================================================"
