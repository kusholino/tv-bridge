#!/bin/bash
#
# TV-Bridge Autostart Configuration
#
# Ensures all services start automatically on boot

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "TV-Bridge Autostart Configuration"
echo "========================================"
echo ""

# 1. Check USB Gadget Service
echo "[1/2] Checking USB Gadget Service..."
if systemctl list-unit-files | grep -q tvbridge-gadget; then
    if systemctl is-enabled tvbridge-gadget >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} tvbridge-gadget.service is enabled (starts on boot)"
    else
        echo -e "${YELLOW}⚠${NC} tvbridge-gadget.service is NOT enabled"
        echo "      Enabling now..."
        sudo systemctl enable tvbridge-gadget
        echo -e "${GREEN}✓${NC} tvbridge-gadget.service enabled"
    fi
else
    echo -e "${RED}✗${NC} tvbridge-gadget.service NOT found!"
    echo "      You need to create and install it first."
    exit 1
fi
echo ""

# 2. Check Backend Service
echo "[2/2] Checking Backend Service..."
if systemctl list-unit-files | grep -q tvbridge-backend; then
    if systemctl is-enabled tvbridge-backend >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} tvbridge-backend.service is enabled (starts on boot)"
    else
        echo -e "${YELLOW}⚠${NC} tvbridge-backend.service is NOT enabled"
        echo "      Enabling now..."
        sudo systemctl enable tvbridge-backend
        echo -e "${GREEN}✓${NC} tvbridge-backend.service enabled"
    fi
else
    echo -e "${RED}✗${NC} tvbridge-backend.service NOT found!"
    echo "      You need to create and install it first."
    exit 1
fi
echo ""

# 3. Check current status
echo "Current Status:"
echo "----------------------------------------"
systemctl status tvbridge-gadget --no-pager -l | head -3
echo ""
systemctl status tvbridge-backend --no-pager -l | head -3
echo ""

# 4. Summary
echo "========================================"
echo "Autostart Configuration Complete!"
echo "========================================"
echo ""
echo "When you reboot the Raspberry Pi:"
echo ""
echo "1. ${GREEN}tvbridge-gadget${NC} starts first"
echo "   → Sets up USB gadget (HID devices)"
echo ""
echo "2. ${GREEN}tvbridge-backend${NC} starts after"
echo "   → Flask API server on port 8080"
echo ""
echo "Test reboot:"
echo "  sudo reboot"
echo ""
echo "After reboot, check:"
echo "  systemctl status tvbridge-gadget"
echo "  systemctl status tvbridge-backend"
echo "  curl http://localhost:8080"
echo ""
