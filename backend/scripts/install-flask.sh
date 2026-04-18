#!/bin/bash
#
# TV-Bridge Flask Installation (Ultra-schnell!)
#
# Installiert Flask-Version auf Pi Zero 2 W
# Keine Kompilierung, nur piwheels!

set -e

echo "=========================================="
echo "TV-Bridge Flask Installation"
echo "=========================================="
echo ""

# 1. Service stoppen falls läuft
echo "[1/6] Stopping existing service..."
sudo systemctl stop tvbridge-backend 2>/dev/null || true

# 2. Python Virtual Environment
echo "[2/6] Creating Python virtual environment..."
cd /opt/tvbridge/backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# 3. Dependencies installieren (SCHNELL!)
echo "[3/6] Installing dependencies (this will be fast!)..."
pip install --upgrade pip
pip install -r requirements-flask.txt

echo "[4/6] Activating Flask version..."
cd app
cp -f main_flask.py main.py

# 5. Service-Datei anpassen
echo "[5/6] Updating systemd service..."
sudo tee /etc/systemd/system/tvbridge-backend.service > /dev/null << 'EOF'
[Unit]
Description=TV-Bridge Backend Server (Flask)
Documentation=https://github.com/kusholino/tv-bridge
After=network-online.target tvbridge-gadget.service
Wants=network-online.target
Requires=tvbridge-gadget.service

[Service]
Type=simple
User=kusho
Group=kusho
WorkingDirectory=/opt/tvbridge/backend
ExecStart=/opt/tvbridge/backend/venv/bin/python3 app/main.py
Restart=always
RestartSec=10

MemoryMax=256M
CPUQuota=80%

NoNewPrivileges=true
PrivateTmp=true

SupplementaryGroups=input

ReadWritePaths=/var/lib/tvbridge
ReadWritePaths=/dev/hidg0
ReadWritePaths=/dev/hidg1

[Install]
WantedBy=multi-user.target
EOF

# 6. Service starten
echo "[6/6] Starting service..."
sudo systemctl daemon-reload
sudo systemctl start tvbridge-backend

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Check status:"
echo "  systemctl status tvbridge-backend"
echo ""
echo "Test:"
echo "  curl http://localhost:8080"
echo ""
echo "Admin token:"
echo "  grep ADMIN /opt/tvbridge/backend/app/main_flask.py | head -1"
echo ""
