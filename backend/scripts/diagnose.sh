#!/bin/bash
#
# TV-Bridge Diagnostic Script
#
# Checks if everything is set up correctly

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

echo "========================================"
echo "TV-Bridge System Diagnostic"
echo "========================================"
echo ""

# Helper functions
check_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# 1. USB Gadget Module
echo "[1/10] Checking USB Gadget Module..."
if lsmod | grep -q libcomposite; then
    check_ok "libcomposite module loaded"
else
    check_fail "libcomposite module NOT loaded"
    echo "       Fix: sudo modprobe libcomposite"
fi
echo ""

# 2. ConfigFS mounted
echo "[2/10] Checking ConfigFS..."
if mount | grep -q configfs; then
    check_ok "configfs mounted at /sys/kernel/config"
else
    check_fail "configfs NOT mounted"
    echo "       Fix: sudo mount -t configfs none /sys/kernel/config"
fi
echo ""

# 3. USB Gadget configured
echo "[3/10] Checking USB Gadget Configuration..."
if [ -d "/sys/kernel/config/usb_gadget/tvbridge" ]; then
    check_ok "USB Gadget 'tvbridge' exists"
    
    # Check if gadget is enabled
    if [ -e "/sys/kernel/config/usb_gadget/tvbridge/UDC" ]; then
        UDC_CONTENT=$(cat /sys/kernel/config/usb_gadget/tvbridge/UDC 2>/dev/null || echo "")
        if [ -n "$UDC_CONTENT" ]; then
            check_ok "USB Gadget enabled (UDC: $UDC_CONTENT)"
        else
            check_warn "USB Gadget exists but NOT enabled"
        fi
    fi
else
    check_fail "USB Gadget 'tvbridge' NOT configured"
    echo "       Fix: Run backend/scripts/setup-usb-gadget.sh"
fi
echo ""

# 4. HID Devices
echo "[4/10] Checking HID Devices..."
if [ -c "/dev/hidg0" ]; then
    check_ok "/dev/hidg0 exists (Mouse)"
    
    # Check permissions
    HIDG0_PERMS=$(stat -c "%a" /dev/hidg0 2>/dev/null || echo "000")
    HIDG0_GROUP=$(stat -c "%G" /dev/hidg0 2>/dev/null || echo "unknown")
    
    if [ "$HIDG0_PERMS" = "660" ] || [ "$HIDG0_PERMS" = "666" ]; then
        check_ok "/dev/hidg0 permissions: $HIDG0_PERMS (group: $HIDG0_GROUP)"
    else
        check_warn "/dev/hidg0 permissions: $HIDG0_PERMS (should be 660 or 666)"
        echo "       Fix: sudo chmod 660 /dev/hidg0"
    fi
else
    check_fail "/dev/hidg0 NOT found"
fi

if [ -c "/dev/hidg1" ]; then
    check_ok "/dev/hidg1 exists (Keyboard)"
    
    HIDG1_PERMS=$(stat -c "%a" /dev/hidg1 2>/dev/null || echo "000")
    HIDG1_GROUP=$(stat -c "%G" /dev/hidg1 2>/dev/null || echo "unknown")
    
    if [ "$HIDG1_PERMS" = "660" ] || [ "$HIDG1_PERMS" = "666" ]; then
        check_ok "/dev/hidg1 permissions: $HIDG1_PERMS (group: $HIDG1_GROUP)"
    else
        check_warn "/dev/hidg1 permissions: $HIDG1_PERMS (should be 660 or 666)"
        echo "       Fix: sudo chmod 660 /dev/hidg1"
    fi
else
    check_fail "/dev/hidg1 NOT found"
fi
echo ""

# 5. User groups
echo "[5/10] Checking User Groups..."
CURRENT_USER=$(whoami)
if groups $CURRENT_USER | grep -q input; then
    check_ok "User '$CURRENT_USER' in 'input' group"
else
    check_warn "User '$CURRENT_USER' NOT in 'input' group"
    echo "       Fix: sudo usermod -a -G input $CURRENT_USER"
    echo "       Then logout/login or reboot"
fi
echo ""

# 6. Python Virtual Environment
echo "[6/10] Checking Python Environment..."
if [ -d "/opt/tvbridge/backend/venv" ]; then
    check_ok "Virtual environment exists"
    
    if [ -f "/opt/tvbridge/backend/venv/bin/python3" ]; then
        PYTHON_VERSION=$(/opt/tvbridge/backend/venv/bin/python3 --version 2>&1)
        check_ok "Python: $PYTHON_VERSION"
    fi
    
    # Check Flask installation
    if /opt/tvbridge/backend/venv/bin/python3 -c "import flask" 2>/dev/null; then
        FLASK_VERSION=$(/opt/tvbridge/backend/venv/bin/python3 -c "import flask; print(flask.__version__)")
        check_ok "Flask installed: $FLASK_VERSION"
    else
        check_fail "Flask NOT installed"
        echo "       Fix: cd /opt/tvbridge/backend && source venv/bin/activate && pip install -r requirements-flask.txt"
    fi
else
    check_fail "Virtual environment NOT found at /opt/tvbridge/backend/venv"
fi
echo ""

# 7. Database
echo "[7/10] Checking Database..."
if [ -f "/var/lib/tvbridge/tvbridge.db" ]; then
    check_ok "Database exists at /var/lib/tvbridge/tvbridge.db"
    
    DB_SIZE=$(stat -c "%s" /var/lib/tvbridge/tvbridge.db)
    check_ok "Database size: $DB_SIZE bytes"
    
    DB_PERMS=$(stat -c "%a" /var/lib/tvbridge/tvbridge.db)
    DB_OWNER=$(stat -c "%U:%G" /var/lib/tvbridge/tvbridge.db)
    check_ok "Database owner: $DB_OWNER, permissions: $DB_PERMS"
else
    check_warn "Database NOT found (will be created on first start)"
fi

if [ -d "/var/lib/tvbridge" ]; then
    DIR_OWNER=$(stat -c "%U:%G" /var/lib/tvbridge)
    DIR_PERMS=$(stat -c "%a" /var/lib/tvbridge)
    check_ok "Database directory: $DIR_OWNER, permissions: $DIR_PERMS"
else
    check_fail "Database directory /var/lib/tvbridge NOT found"
    echo "       Fix: sudo mkdir -p /var/lib/tvbridge && sudo chown $CURRENT_USER:$CURRENT_USER /var/lib/tvbridge"
fi
echo ""

# 8. Systemd Service
echo "[8/10] Checking Systemd Service..."
if systemctl list-unit-files | grep -q tvbridge-backend; then
    check_ok "tvbridge-backend.service exists"
    
    if systemctl is-enabled tvbridge-backend >/dev/null 2>&1; then
        check_ok "Service is enabled (starts on boot)"
    else
        check_warn "Service is NOT enabled"
        echo "       Fix: sudo systemctl enable tvbridge-backend"
    fi
    
    if systemctl is-active tvbridge-backend >/dev/null 2>&1; then
        check_ok "Service is running"
        
        # Check how long it's been running
        UPTIME=$(systemctl show tvbridge-backend -p ActiveEnterTimestamp --value)
        check_ok "Service started: $UPTIME"
    else
        check_fail "Service is NOT running"
        echo "       Fix: sudo systemctl start tvbridge-backend"
        echo "       Logs: journalctl -u tvbridge-backend -n 50"
    fi
else
    check_fail "tvbridge-backend.service NOT found"
fi
echo ""

# 9. Network/Port
echo "[9/10] Checking Network..."
if systemctl is-active tvbridge-backend >/dev/null 2>&1; then
    if curl -s http://localhost:8080 >/dev/null 2>&1; then
        check_ok "Backend responds on port 8080"
        
        # Try to get admin token from logs
        ADMIN_TOKEN=$(journalctl -u tvbridge-backend --no-pager | grep -o "Admin token: [a-f0-9]*" | tail -1 | cut -d' ' -f3)
        if [ -n "$ADMIN_TOKEN" ]; then
            check_ok "Admin token found: ${ADMIN_TOKEN:0:16}..."
        fi
    else
        check_fail "Backend NOT responding on port 8080"
        echo "       Check logs: journalctl -u tvbridge-backend -n 50"
    fi
else
    check_warn "Service not running, skipping port check"
fi
echo ""

# 10. HID Write Test
echo "[10/10] Testing HID Write..."
if [ -c "/dev/hidg0" ]; then
    # Try to write a null packet
    if echo -ne '\x00\x00\x00\x00\x00\x00' > /dev/hidg0 2>/dev/null; then
        check_ok "Successfully wrote to /dev/hidg0"
    else
        check_fail "Cannot write to /dev/hidg0"
        echo "       Possible causes:"
        echo "       - User not in 'input' group (need logout/reboot)"
        echo "       - Incorrect permissions on /dev/hidg0"
        echo "       - Service needs SupplementaryGroups=input in systemd"
    fi
else
    check_warn "Skipping write test (device not found)"
fi
echo ""

# Summary
echo "========================================"
echo "Summary"
echo "========================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Your TV-Bridge is ready to use! 🎉"
    echo ""
    echo "Next steps:"
    echo "1. Start pairing session:"
    echo "   curl -X POST http://localhost:8080/admin/pairing/start \\"
    echo "     -H \"Authorization: Bearer \$ADMIN_TOKEN\""
    echo ""
    echo "2. Open web app: http://$(hostname -I | awk '{print $1}'):8080"
    echo "3. Enter pairing code and device name"
    echo "4. Start controlling your TV!"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warning(s) found${NC}"
    echo ""
    echo "System should work, but some optimizations are recommended."
else
    echo -e "${RED}✗ $ERRORS error(s) and $WARNINGS warning(s) found${NC}"
    echo ""
    echo "Please fix the errors above before using TV-Bridge."
    echo ""
    echo "Quick fixes:"
    echo "sudo mkdir -p /var/lib/tvbridge"
    echo "sudo chown $CURRENT_USER:$CURRENT_USER /var/lib/tvbridge"
    echo "sudo chmod 660 /dev/hidg0 /dev/hidg1"
    echo "sudo usermod -a -G input $CURRENT_USER"
    echo "sudo systemctl restart tvbridge-backend"
fi
echo ""

exit $ERRORS
