#!/bin/bash
# Service Deployment Script
# Ensures the systemd service points to the correct directory

echo "========================================================================"
echo "AI Dropshipping ERP - Service Deployment"
echo "========================================================================"
echo ""

# Get the absolute path to the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "[INFO] Script directory: $SCRIPT_DIR"
echo "[INFO] This will be set as WorkingDirectory"
echo ""

# Service file path
SERVICE_FILE="/etc/systemd/system/webapp.service"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "[ERROR] This script must be run as root (use sudo)"
    echo "Usage: sudo bash $0"
    exit 1
fi

# Backup existing service file if it exists
if [ -f "$SERVICE_FILE" ]; then
    BACKUP_FILE="${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "[BACKUP] Creating backup: $BACKUP_FILE"
    cp "$SERVICE_FILE" "$BACKUP_FILE"
fi

# Create new service file
echo "[CREATE] Creating systemd service file..."
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=AI Dropshipping ERP System
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="FLASK_SECRET_KEY=production-secret-key-change-me"
ExecStart=$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=append:$SCRIPT_DIR/logs/server.log
StandardError=append:$SCRIPT_DIR/logs/server.log

[Install]
WantedBy=multi-user.target
EOF

echo "[SUCCESS] Service file created at: $SERVICE_FILE"
echo ""

# Show the created service file
echo "Service file contents:"
echo "========================================================================"
cat "$SERVICE_FILE"
echo "========================================================================"
echo ""

# Create logs directory if it doesn't exist
if [ ! -d "$SCRIPT_DIR/logs" ]; then
    echo "[CREATE] Creating logs directory..."
    mkdir -p "$SCRIPT_DIR/logs"
    chown $SUDO_USER:$SUDO_USER "$SCRIPT_DIR/logs"
fi

# Ensure venv exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "[WARNING] Virtual environment not found at $SCRIPT_DIR/venv"
    echo "[INFO] Creating virtual environment..."
    sudo -u $SUDO_USER python3 -m venv "$SCRIPT_DIR/venv"
    sudo -u $SUDO_USER "$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"
fi

# Reload systemd
echo "[RELOAD] Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "[ENABLE] Enabling service to start on boot..."
systemctl enable webapp.service

# Show service status
echo ""
echo "========================================================================"
echo "DEPLOYMENT COMPLETE"
echo "========================================================================"
echo ""
echo "Service Commands:"
echo "  Start:   sudo systemctl start webapp"
echo "  Stop:    sudo systemctl stop webapp"
echo "  Restart: sudo systemctl restart webapp"
echo "  Status:  sudo systemctl status webapp"
echo "  Logs:    sudo journalctl -u webapp -f"
echo ""
echo "Direct Logs:"
echo "  tail -f $SCRIPT_DIR/logs/server.log"
echo ""

# Ask if user wants to start the service now
read -p "Start the service now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "[START] Starting webapp service..."
    systemctl start webapp
    sleep 2
    systemctl status webapp
fi

echo ""
echo "Deployment complete!"
