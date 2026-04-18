# TV-Bridge Deployment Guide

## 1. Raspberry Pi Vorbereitung

### 1.1 Hardware-Anforderungen

- **Raspberry Pi Zero 2 W**
- microSD-Karte (min. 8 GB, empfohlen 16 GB Class 10)
- USB-Kabel (Micro-USB OTG-fähig für Datenverbindung)
- Stromversorgung (5V, min. 1.2A)
- Optional: USB-Hub für Setup (Tastatur/Maus)

### 1.2 Betriebssystem-Installation

**1. Raspberry Pi OS Lite Image herunterladen**:
- Download: [Raspberry Pi OS Lite (64-bit)](https://www.raspberrypi.com/software/operating-systems/)
- Version: Bullseye oder neuer

**2. Image auf microSD schreiben**:
```powershell
# Mit Raspberry Pi Imager (empfohlen)
# Oder dd/Win32DiskImager
```

**3. Headless Setup konfigurieren**:

Erstelle auf der Boot-Partition folgende Dateien:

**`wpa_supplicant.conf`**:
```conf
country=DE
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YOUR_WIFI_SSID"
    psk="YOUR_WIFI_PASSWORD"
    key_mgmt=WPA-PSK
}
```

**`ssh`** (leere Datei):
```bash
# Einfach leere Datei erstellen um SSH zu aktivieren
touch ssh
```

**`config.txt`** (am Ende hinzufügen):
```ini
# USB OTG Mode aktivieren
dtoverlay=dwc2
```

**`cmdline.txt`** (NACH rootwait einfügen):
```
modules-load=dwc2
```

Beispiel:
```
console=serial0,115200 console=tty1 root=PARTUUID=... rootfstype=ext4 fsck.repair=yes rootwait modules-load=dwc2 quiet init=/usr/lib/raspi-config/init_resize.sh
```

### 1.3 Erster Boot

1. microSD in Pi einlegen
2. Pi mit Strom versorgen (NICHT USB-Datenport!)
3. Warten bis Boot abgeschlossen (~2 Minuten)
4. SSH-Verbindung testen:

```bash
ssh pi@raspberrypi.local
# Default-Passwort: raspberry
```

**Falls raspberrypi.local nicht funktioniert**: IP im Router nachschlagen.

### 1.4 Grundkonfiguration

```bash
# Passwort ändern
passwd

# System aktualisieren
sudo apt update
sudo apt upgrade -y

# Hostname ändern
sudo hostnamectl set-hostname tv-bridge

# Reboot
sudo reboot
```

Nach Reboot:
```bash
ssh pi@tv-bridge.local
```

## 2. USB Gadget Setup

### 2.1 Kernel-Module aktivieren

**`/etc/modules`** (hinzufügen):
```
libcomposite
```

### 2.2 Gadget-Setup-Skript erstellen

Das Setup-Skript wird später vom Installer erstellt, aber hier die manuelle Variante:

```bash
sudo mkdir -p /usr/local/bin
sudo nano /usr/local/bin/setup_gadget.sh
```

Inhalt siehe: [setup_gadget.sh](../backend/scripts/setup_gadget.sh)

```bash
sudo chmod +x /usr/local/bin/setup_gadget.sh
```

### 2.3 Gadget-Service erstellen

```bash
sudo nano /etc/systemd/system/tvbridge-gadget.service
```

Inhalt siehe: [tvbridge-gadget.service](../backend/systemd/tvbridge-gadget.service)

```bash
sudo systemctl daemon-reload
sudo systemctl enable tvbridge-gadget.service
```

### 2.4 Test

```bash
sudo systemctl start tvbridge-gadget.service
sudo systemctl status tvbridge-gadget.service

# HID-Devices prüfen
ls -l /dev/hidg*
# Sollte zeigen: /dev/hidg0 (Mouse), /dev/hidg1 (Keyboard)
```

## 3. Backend-Installation

### 3.1 Dependencies installieren

```bash
# Python 3 und pip
sudo apt install -y python3 python3-pip python3-venv

# System-Dependencies
sudo apt install -y sqlite3 libsqlite3-dev
```

### 3.2 Projekt-Setup

```bash
# Projekt-Verzeichnis
sudo mkdir -p /opt/tvbridge
sudo chown pi:pi /opt/tvbridge

# Repository klonen
cd /opt/tvbridge
git clone <your-repo-url> .
# ODER: Dateien via SCP hochladen

# Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Python-Dependencies
pip install -r backend/requirements.txt
```

**`backend/requirements.txt`**:
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0
websockets==12.0
aiosqlite==0.19.0
```

### 3.3 Service-User erstellen

```bash
# Dedizierter Service-User (optional, empfohlen für Production)
sudo useradd -r -s /bin/false tvbridge
sudo usermod -a -G dialout tvbridge  # Für HID-Device-Zugriff
```

### 3.4 Datenbank-Verzeichnis

```bash
sudo mkdir -p /var/lib/tvbridge
sudo chown tvbridge:tvbridge /var/lib/tvbridge
sudo chmod 750 /var/lib/tvbridge
```

### 3.5 Backend-Service

```bash
sudo nano /etc/systemd/system/tvbridge-backend.service
```

Inhalt siehe: [tvbridge-backend.service](../backend/systemd/tvbridge-backend.service)

```bash
sudo systemctl daemon-reload
sudo systemctl enable tvbridge-backend.service
sudo systemctl start tvbridge-backend.service
sudo systemctl status tvbridge-backend.service
```

### 3.6 Logs prüfen

```bash
# journald
sudo journalctl -u tvbridge-backend.service -f

# App-Log
sudo tail -f /var/log/tvbridge/app.log
```

## 4. Automatische Installation

### 4.1 Install-Skript

```bash
cd /opt/tvbridge
sudo ./backend/scripts/install.sh
```

Das Skript führt alle obigen Schritte automatisch aus:
- System-Dependencies
- Python-Environment
- Gadget-Setup
- systemd-Services
- Berechtigungen
- Initial-Konfiguration

### 4.2 Install-Skript-Parameter

```bash
# Interaktive Installation
sudo ./backend/scripts/install.sh

# Automatisch (non-interactive)
sudo ./backend/scripts/install.sh --auto

# Mit Admin-Token
sudo ./backend/scripts/install.sh --admin-token "my-secret-token"
```

## 5. Web-App Deployment

Die Web-App wird vom Backend als statische Files ausgeliefert.

### 5.1 Web-App-Location

```
/opt/tvbridge/webapp/
├── index.html
├── styles/
├── scripts/
└── assets/
```

### 5.2 Backend-Konfiguration

Backend serviert Files unter `/`:
- `GET /` → `webapp/index.html`
- `GET /styles/*` → `webapp/styles/*`
- etc.

## 6. Netzwerk-Konfiguration

### 6.1 Modus A: Bestehendes WLAN (Standard)

Pi verbindet sich mit bestehendem WLAN (via `wpa_supplicant.conf`).

**mDNS aktivieren**:
```bash
sudo apt install -y avahi-daemon
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

Web-App erreichbar unter:
- `http://tv-bridge.local`
- `http://<pi-ip>:8080`

### 6.2 Modus B: Hotspot (Optional, Phase 5)

Pi erstellt eigenes Access Point.

**Dependencies**:
```bash
sudo apt install -y hostapd dnsmasq
```

**`/etc/hostapd/hostapd.conf`**:
```conf
interface=wlan0
driver=nl80211
ssid=TV-Bridge-XXXX
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=tvbridge123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
```

**`/etc/dnsmasq.conf`**:
```conf
interface=wlan0
dhcp-range=192.168.42.10,192.168.42.50,255.255.255.0,24h
```

**Service**:
```bash
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
```

Web-App unter: `http://192.168.42.1`

## 7. Firewall & Sicherheit

### 7.1 UFW (Optional)

```bash
sudo apt install -y ufw

# SSH erlauben
sudo ufw allow 22/tcp

# Backend (nur lokales Netz)
sudo ufw allow from 192.168.0.0/16 to any port 8080

# Aktivieren
sudo ufw enable
```

### 7.2 Admin-Token

Admin-Endpunkte sind per Token geschützt.

**Token setzen**:
```bash
# In .env oder Environment
export TVBRIDGE_ADMIN_TOKEN="your-secure-random-token"
```

**Nutzung**:
```bash
curl -H "Authorization: Bearer your-secure-random-token" \
     http://tv-bridge.local:8080/admin/devices
```

## 8. TV-Verbindung

### 8.1 Hardware-Verbindung

1. **USB-Kabel**: Micro-USB (am Pi) → USB-A (am TV)
2. **Wichtig**: Nutze den **Daten-Port** am Pi (mit OTG-Symbol), NICHT den Stromport
3. Optional: Zusätzliches Netzteil für Pi (empfohlen)

### 8.2 TV-Einstellungen

- TV sollte USB-HID-Geräte automatisch erkennen
- Keine speziellen Treiber nötig
- Cursor sollte nach ~2 Sekunden erscheinen

### 8.3 Troubleshooting USB

**TV erkennt Gerät nicht**:
```bash
# Gadget-Status prüfen
sudo systemctl status tvbridge-gadget.service

# USB-Konfiguration prüfen
ls -l /sys/kernel/config/usb_gadget/tvbridge/

# ConfigFS-Status
lsusb  # (auf einem anderen Linux-Gerät, wenn Pi als Gadget verbunden)
```

**HID-Devices nicht verfügbar**:
```bash
# Module geladen?
lsmod | grep libcomposite
lsmod | grep usb_f_hid

# Manuell laden
sudo modprobe libcomposite
```

## 9. Pairing

### 9.1 Pairing-Modus aktivieren

**Via Admin-API**:
```bash
curl -X POST \
  -H "Authorization: Bearer <admin-token>" \
  http://tv-bridge.local:8080/admin/pairing/start
```

**Response**:
```json
{
  "success": true,
  "pairing_code": "123456",
  "expires_in_seconds": 120
}
```

### 9.2 Device pairen

**Smartphone**:
1. Web-App öffnen: `http://tv-bridge.local`
2. Pairing-Code eingeben: `123456`
3. Device-Name eingeben: z.B. "My iPhone"
4. Token wird automatisch gespeichert

**Manual (curl)**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"pairing_code": "123456", "device_name": "Test Device"}' \
  http://tv-bridge.local:8080/pair
```

### 9.3 Geräte verwalten

**Liste**:
```bash
curl -H "Authorization: Bearer <admin-token>" \
     http://tv-bridge.local:8080/admin/devices
```

**Revoke**:
```bash
curl -X POST \
  -H "Authorization: Bearer <admin-token>" \
  http://tv-bridge.local:8080/admin/devices/<device-id>/revoke
```

## 10. Monitoring

### 10.1 Service-Status

```bash
# Alle Services
sudo systemctl status tvbridge-gadget.service
sudo systemctl status tvbridge-backend.service

# Logs
sudo journalctl -u tvbridge-backend.service -f
```

### 10.2 Health-Check

```bash
curl http://tv-bridge.local:8080/admin/health
```

**Response**:
```json
{
  "status": "healthy",
  "hid_mouse": "ok",
  "hid_keyboard": "ok",
  "database": "ok",
  "active_connections": 1,
  "uptime_seconds": 3600
}
```

### 10.3 Ressourcen

```bash
# CPU/RAM
htop

# Disk
df -h

# Netzwerk
ifconfig wlan0
```

## 11. Updates

### 11.1 System-Updates

```bash
sudo apt update
sudo apt upgrade -y
sudo reboot
```

### 11.2 App-Updates

```bash
cd /opt/tvbridge
git pull  # oder neue Files via SCP

# Backend neu starten
sudo systemctl restart tvbridge-backend.service
```

### 11.3 Backup

**Datenbank**:
```bash
sudo cp /var/lib/tvbridge/tvbridge.db /var/lib/tvbridge/tvbridge.db.backup
```

**Komplettes System** (microSD-Image):
```bash
# Auf anderem Rechner mit SD-Card-Reader
sudo dd if=/dev/sdX of=tvbridge-backup.img bs=4M status=progress
```

## 12. Troubleshooting

### 12.1 Backend startet nicht

**Logs prüfen**:
```bash
sudo journalctl -u tvbridge-backend.service -n 50
```

**Häufige Ursachen**:
- HID-Devices nicht verfügbar → Gadget-Service prüfen
- Port 8080 bereits belegt → `sudo lsof -i :8080`
- Python-Dependencies fehlen → `pip install -r requirements.txt`
- Berechtigungen falsch → `sudo chown -R tvbridge:tvbridge /var/lib/tvbridge`

### 12.2 WebSocket-Verbindung schlägt fehl

**Firewall**:
```bash
sudo ufw status
# Port 8080 erlauben
sudo ufw allow 8080/tcp
```

**Client-Side**:
- Browser-Console öffnen
- WebSocket-Fehler prüfen
- CORS-Probleme? (nur Development)

### 12.3 Input funktioniert nicht

**HID-Test**:
```bash
# Maus-Test (manuelle Bewegung)
echo -ne "\x00\x05\x05" | sudo tee /dev/hidg0 > /dev/null
# Cursor sollte sich bewegen

# Keyboard-Test (Taste 'a')
echo -ne "\x00\x00\x04\x00\x00\x00\x00\x00" | sudo tee /dev/hidg1 > /dev/null
echo -ne "\x00\x00\x00\x00\x00\x00\x00\x00" | sudo tee /dev/hidg1 > /dev/null
```

**TV erkennt Gerät nicht**:
- USB-Kabel wechseln (Daten-fähig!)
- Anderen USB-Port am TV testen
- Pi neu starten
- TV neu starten

### 12.4 mDNS funktioniert nicht

**Avahi prüfen**:
```bash
sudo systemctl status avahi-daemon

# Manuell resolven
avahi-browse -a
```

**Fallback: IP-Adresse**:
```bash
hostname -I
# Nutze erste IP
```

### 12.5 Performance-Probleme

**Latenz messen**:
```bash
# Ping zum Pi
ping tv-bridge.local

# WebSocket-Latenz in Browser-Console
```

**CPU-Last**:
```bash
top
# Python-Prozess sollte <30% sein
```

**Optimierungen**:
- Event Coalescing im Client erhöhen
- Sensitivität reduzieren
- WiFi-Kanal wechseln (weniger Interferenz)

## 13. Production Checklist

- [ ] Raspberry Pi OS aktualisiert
- [ ] Hostname auf `tv-bridge` gesetzt
- [ ] USB Gadget funktioniert (`/dev/hidg0`, `/dev/hidg1` existieren)
- [ ] Backend-Service läuft (`systemctl status tvbridge-backend`)
- [ ] Web-App erreichbar (`http://tv-bridge.local`)
- [ ] mDNS funktioniert (Avahi läuft)
- [ ] Admin-Token gesetzt und sicher
- [ ] Mindestens ein Gerät gepairt und getestet
- [ ] TV erkennt USB-HID-Gerät
- [ ] Input-Latenz akzeptabel (<50ms)
- [ ] Logs laufen sauber (keine Errors)
- [ ] Backup der Datenbank erstellt

## 14. Sicherheits-Hardening (Production)

### 14.1 SSH-Absicherung

```bash
# Key-based Auth only
sudo nano /etc/ssh/sshd_config
# PasswordAuthentication no
# PermitRootLogin no

sudo systemctl restart ssh
```

### 14.2 Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow from 192.168.0.0/16 to any port 8080
sudo ufw enable
```

### 14.3 Auto-Updates

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 14.4 Read-Only Filesystem (Optional)

Für maximale SD-Karten-Lebensdauer:
```bash
# OverlayFS für Root-Partition
# (Komplex, nur für embedded deployment)
```

## 15. FAQ

**Q: Kann ich mehrere Smartphones gleichzeitig nutzen?**  
A: MVP unterstützt ein Gerät zur Zeit. Multi-User kommt in Phase 6.

**Q: Funktioniert das mit jedem Smart TV?**  
A: Ja, solange der TV USB-HID unterstützt (die meisten modernen TVs).

**Q: Brauche ich Internet?**  
A: Nein, System funktioniert komplett offline (nur lokales WLAN nötig).

**Q: Kann ich das über Bluetooth machen?**  
A: Nicht im MVP. USB-HID ist zuverlässiger und hat niedrigere Latenz.

**Q: Was passiert bei Pi-Reboot?**  
A: Services starten automatisch. Client reconnect nach ~5 Sekunden.

**Q: Wie sichere ich den Admin-Zugang?**  
A: Admin-Token in Environment setzen, nur lokal exponieren, HTTPS nutzen.

## 16. Weiterführende Ressourcen

- [Linux USB Gadget Documentation](https://www.kernel.org/doc/html/latest/usb/gadget.html)
- [HID Usage Tables](https://usb.org/sites/default/files/hut1_3_0.pdf)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [WebSocket Protocol RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)
- [Raspberry Pi USB OTG Guide](https://www.raspberrypi.com/documentation/computers/compute-module.html#attaching-a-computer-to-a-compute-module)
