#!/bin/bash
# Quick Restart Script - Ensures latest code is running

echo "========================================================================"
echo "AI Dropshipping ERP - Quick Restart"
echo "========================================================================"
echo ""

# Get current directory
CURRENT_DIR="$(pwd)"
echo "[INFO] Working directory: $CURRENT_DIR"
echo ""

# 1. Pull latest code
echo "[GIT] Fetching latest code from GitHub..."
git fetch origin
echo ""

echo "[GIT] Resetting to latest origin/main..."
git reset --hard origin/main
echo ""

echo "[GIT] Current commit:"
git log --oneline -1
echo ""

# 2. Check for app.py
if [ ! -f "app.py" ]; then
    echo "[ERROR] app.py not found in current directory!"
    exit 1
fi

# 3. Verify latest version
if grep -q "DATABASE INITIALIZATION COMPLETE" app.py; then
    echo "[CHECK] ✓ Latest version confirmed (DB verification present)"
else
    echo "[WARNING] Old version detected - may need manual intervention"
fi
echo ""

# 4. Kill any existing Flask processes and free port 5000
echo "[KILL] Stopping any existing Flask processes..."
pkill -9 -f "python.*app.py" 2>/dev/null

echo "[PORT] Freeing port 5000..."
fuser -k 5000/tcp 2>/dev/null || true
sleep 2

# Double-check port is free
if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "[WARNING] Port 5000 still in use, force killing..."
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi
echo "[PORT] ✓ Port 5000 is free"
echo ""

# 5. Check if running via systemd
if systemctl is-active --quiet webapp 2>/dev/null; then
    echo "[SYSTEMD] Service detected. Restarting via systemctl..."
    sudo systemctl restart webapp
    sleep 2
    sudo systemctl status webapp --no-pager
    echo ""
    echo "[LOGS] Tail logs to see startup:"
    echo "  tail -f $CURRENT_DIR/logs/server.log"
else
    # 6. Start manually if no systemd service
    echo "[MANUAL] No systemd service found. Starting manually..."
    
    # Check for venv
    if [ -d "venv" ]; then
        echo "[VENV] Using virtual environment"
        source venv/bin/activate
    fi
    
    # Start in background and show initial logs
    python3 app.py > logs/server.log 2>&1 &
    APP_PID=$!
    echo "[START] Started app.py (PID: $APP_PID)"
    sleep 2
    
    echo ""
    echo "[LOGS] Initial startup logs:"
    tail -30 logs/server.log
    echo ""
    echo "[INFO] App is running in background"
    echo "[INFO] View logs: tail -f logs/server.log"
    echo "[INFO] Stop app: kill $APP_PID"
fi

echo ""
echo "========================================================================"
echo "RESTART COMPLETE"
echo "========================================================================"
