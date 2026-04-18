#!/bin/bash
#
# TV-Bridge Installation Script
#
# Installiert alle Dependencies, konfiguriert Services und richtet
# das System produktionsreif ein.
#
# Usage:
#   sudo ./install.sh [--auto] [--admin-token TOKEN]
#

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Defaults
AUTO_MODE=false
ADMIN_TOKEN=""
INSTALL_DIR="/opt/tvbridge"
SERVICE_USER="tvbridge"
DATA_DIR="/var/lib/tvbridge"
LOG_DIR="/var/log/tvbridge"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto)
            AUTO_MODE=true
            shift
            ;;
        --admin-token)
            ADMIN_TOKEN="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--auto] [--admin-token TOKEN]"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

log_info "Starting TV-Bridge installation..."

# 1. System-Dependencies
log_info "Installing system dependencies..."
apt update
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    sqlite3 \
    libsqlite3-dev \
    avahi-daemon \
    git \
    curl

log_success "System dependencies installed"

# 2. Service-User erstellen
if ! id "${SERVICE_USER}" &>/dev/null; then
    log_info "Creating service user: ${SERVICE_USER}"
    useradd -r -s /bin/false -d /nonexistent "${SERVICE_USER}"
else
    log_info "Service user ${SERVICE_USER} already exists"
fi

# Gruppe für HID-Device-Zugriff
usermod -a -G dialout "${SERVICE_USER}"

# 3. Verzeichnisse erstellen
log_info "Creating directories..."
mkdir -p "${INSTALL_DIR}"
mkdir -p "${DATA_DIR}"
mkdir -p "${LOG_DIR}"

# Berechtigungen
chown "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}"
chown "${SERVICE_USER}:${SERVICE_USER}" "${LOG_DIR}"
chmod 750 "${DATA_DIR}"
chmod 755 "${LOG_DIR}"

log_success "Directories created"

# 4. Python Virtual Environment
log_info "Setting up Python virtual environment..."
cd "${INSTALL_DIR}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

# Dependencies installieren
if [ -f "backend/requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r backend/requirements.txt
    log_success "Python dependencies installed"
else
    log_warn "backend/requirements.txt not found, skipping Python dependencies"
fi

deactivate

# 5. Gadget-Setup-Skript installieren
log_info "Installing USB gadget setup script..."
cp backend/scripts/setup_gadget.sh /usr/local/bin/setup_gadget.sh
chmod +x /usr/local/bin/setup_gadget.sh
log_success "Gadget script installed to /usr/local/bin/setup_gadget.sh"

# 6. systemd Services installieren
log_info "Installing systemd services..."

# Gadget Service
cp backend/systemd/tvbridge-gadget.service /etc/systemd/system/
chmod 644 /etc/systemd/system/tvbridge-gadget.service

# Backend Service
cp backend/systemd/tvbridge-backend.service /etc/systemd/system/
chmod 644 /etc/systemd/system/tvbridge-backend.service

# systemd reload
systemctl daemon-reload

log_success "systemd services installed"

# 7. Services enablen
log_info "Enabling services..."
systemctl enable tvbridge-gadget.service
systemctl enable tvbridge-backend.service
log_success "Services enabled"

# 8. libcomposite in /etc/modules
if ! grep -q "^libcomposite" /etc/modules; then
    log_info "Adding libcomposite to /etc/modules..."
    echo "libcomposite" >> /etc/modules
fi

# 9. mDNS (Avahi) aktivieren
log_info "Enabling mDNS (Avahi)..."
systemctl enable avahi-daemon
systemctl start avahi-daemon || true
log_success "mDNS enabled"

# 10. Admin-Token setzen (falls angegeben)
if [ -n "${ADMIN_TOKEN}" ]; then
    log_info "Setting admin token..."
    ENV_FILE="${INSTALL_DIR}/.env"
    
    if [ -f "${ENV_FILE}" ]; then
        # Update existing
        sed -i "s/^TVBRIDGE_ADMIN_TOKEN=.*/TVBRIDGE_ADMIN_TOKEN=${ADMIN_TOKEN}/" "${ENV_FILE}"
    else
        # Create new
        echo "TVBRIDGE_ADMIN_TOKEN=${ADMIN_TOKEN}" > "${ENV_FILE}"
    fi
    
    chmod 600 "${ENV_FILE}"
    chown "${SERVICE_USER}:${SERVICE_USER}" "${ENV_FILE}"
    log_success "Admin token configured"
else
    # Generiere zufälliges Token
    RANDOM_TOKEN=$(openssl rand -hex 32)
    log_warn "No admin token provided, generated random token:"
    echo -e "${YELLOW}${RANDOM_TOKEN}${NC}"
    echo -e "${YELLOW}Save this token! You'll need it to access admin endpoints.${NC}"
    
    ENV_FILE="${INSTALL_DIR}/.env"
    echo "TVBRIDGE_ADMIN_TOKEN=${RANDOM_TOKEN}" > "${ENV_FILE}"
    chmod 600 "${ENV_FILE}"
    chown "${SERVICE_USER}:${SERVICE_USER}" "${ENV_FILE}"
fi

# 11. Datenbank initialisieren
log_info "Initializing database..."
cd "${INSTALL_DIR}"
source venv/bin/activate

# DB-Init-Skript ausführen (wenn vorhanden)
if [ -f "backend/scripts/init_db.py" ]; then
    python3 backend/scripts/init_db.py
    log_success "Database initialized"
else
    log_warn "Database init script not found, will be created on first run"
fi

deactivate

# 12. Boot-Konfiguration prüfen
log_info "Checking boot configuration..."

CONFIG_TXT="/boot/config.txt"
CMDLINE_TXT="/boot/cmdline.txt"

# config.txt
if ! grep -q "^dtoverlay=dwc2" "${CONFIG_TXT}"; then
    log_warn "dtoverlay=dwc2 not found in ${CONFIG_TXT}"
    log_warn "Add the following line to ${CONFIG_TXT}:"
    echo -e "${YELLOW}dtoverlay=dwc2${NC}"
    
    if [ "${AUTO_MODE}" = true ]; then
        log_info "Auto-mode: Adding dtoverlay=dwc2..."
        echo "" >> "${CONFIG_TXT}"
        echo "# TV-Bridge USB OTG" >> "${CONFIG_TXT}"
        echo "dtoverlay=dwc2" >> "${CONFIG_TXT}"
    fi
fi

# cmdline.txt
if ! grep -q "modules-load=dwc2" "${CMDLINE_TXT}"; then
    log_warn "modules-load=dwc2 not found in ${CMDLINE_TXT}"
    log_warn "Add 'modules-load=dwc2' after 'rootwait' in ${CMDLINE_TXT}"
    
    if [ "${AUTO_MODE}" = true ]; then
        log_info "Auto-mode: Adding modules-load=dwc2..."
        sed -i 's/rootwait/rootwait modules-load=dwc2/' "${CMDLINE_TXT}"
    fi
fi

# 13. Test Gadget-Setup (dry-run)
log_info "Testing gadget setup..."
if /usr/local/bin/setup_gadget.sh; then
    log_success "Gadget setup test successful"
else
    log_error "Gadget setup test failed"
    log_error "Check if USB OTG is properly configured in boot config"
fi

# 14. Installation Summary
echo ""
echo "============================================="
log_success "TV-Bridge installation complete!"
echo "============================================="
echo ""
echo "Next steps:"
echo "  1. Reboot the system: sudo reboot"
echo "  2. After reboot, check services:"
echo "     sudo systemctl status tvbridge-gadget.service"
echo "     sudo systemctl status tvbridge-backend.service"
echo "  3. Access web app: http://tv-bridge.local:8080"
echo "  4. Check logs: sudo journalctl -u tvbridge-backend.service -f"
echo ""
echo "Admin API access:"
echo "  Token: ${ADMIN_TOKEN:-<see above>}"
echo "  Example: curl -H 'Authorization: Bearer <token>' http://tv-bridge.local:8080/admin/health"
echo ""
echo "Pairing a device:"
echo "  1. Start pairing: curl -X POST -H 'Authorization: Bearer <token>' http://tv-bridge.local:8080/admin/pairing/start"
echo "  2. Open web app on smartphone: http://tv-bridge.local:8080"
echo "  3. Enter pairing code"
echo ""

if [ "${AUTO_MODE}" = false ]; then
    read -p "Reboot now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Rebooting..."
        reboot
    fi
else
    log_info "Auto-mode: Rebooting in 5 seconds..."
    sleep 5
    reboot
fi
