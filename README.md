# TV-Bridge - Raspberry Pi USB HID Remote Control

Ein Eingabesystem für Smart TVs: Raspberry Pi Zero 2 W als USB-HID-Bridge zwischen Smartphone und TV.

## Überblick

Der Pi fungiert als:
- **USB HID Gadget** (Maus + Tastatur) für den TV
- **WebSocket-Server** für Smartphone-Clients
- **Pairing- und Auth-Service** für sichere Geräteverwaltung

## Hauptfeatures

- Touch-basierte Maus- und Tastatursteuerung vom Smartphone
- Sicheres Pairing mit Geräteautorisierung und Revocation
- Anpassbare Profile (Sensitivität, Scroll-Speed, Acceleration)
- Low-latency Input-Processing für smooth UX
- Web-App + spätere Flutter-App-Unterstützung
- Headless-Betrieb auf Raspberry Pi

## Dokumentation

- [Architecture](docs/architecture.md) - Systemarchitektur und Designentscheidungen
- [Protocol](docs/protocol.md) - WebSocket-Protokoll-Spezifikation
- [Deployment](docs/deployment.md) - Raspberry Pi Setup und Installation

## Tech Stack

### Backend
- **Python 3.9+** mit FastAPI & Uvicorn
- **WebSockets** für bidirektionale Kommunikation
- **SQLite** für Device- und Profil-Persistenz
- **USB HID Gadget** (ConfigFS/libcomposite)

### Frontend
- **Vanilla JavaScript** (ES6+, keine Frameworks)
- **WebSocket API** für Realtime-Kommunikation
- **Mobile-first Design** mit Touch-optimiertem UI
- **LocalStorage** für Client-Konfiguration

### System
- **Raspberry Pi OS Lite** (Headless)
- **systemd** für Service-Management
- **Avahi** für mDNS (tv-bridge.local)

## Schnellstart

### 1. Hardware vorbereiten

- Raspberry Pi Zero 2 W
- MicroSD-Karte (min. 8 GB)
- USB-Kabel (Data + Power) zum TV

### 2. Installation

```bash
# Auf dem Raspberry Pi
git clone <repository-url> /opt/tvbridge
cd /opt/tvbridge

# Automatische Installation
sudo ./backend/scripts/install.sh --auto

# Reboot für USB-Gadget-Aktivierung
sudo reboot
```

### 3. Pairing

```bash
# Admin CLI für Pairing-Code
cd /opt/tvbridge/backend
source venv/bin/activate
python3 scripts/admin_cli.py pair

# Notiere den 6-stelligen Code (gültig für 120 Sekunden)
```

### 4. Web-App verwenden

1. Smartphone mit gleichem Netzwerk verbinden
2. Browser öffnen: `http://tv-bridge.local:8080`
3. Pairing-Code eingeben
4. Gerät mit Namen versehen
5. Touchpad verwenden!

## Projektstruktur

```
tv-controll/
├── backend/                   # Python Backend
│   ├── app/                   # FastAPI-Module
│   │   ├── main.py            # Entry Point
│   │   ├── ws_gateway.py      # WebSocket-Server
│   │   ├── hid_service.py     # USB HID Interface
│   │   └── ...
│   ├── scripts/               # Setup & Admin-Tools
│   │   ├── install.sh         # Installer
│   │   ├── setup_gadget.sh    # USB-Gadget-Setup
│   │   └── admin_cli.py       # CLI-Tool
│   ├── systemd/               # Service-Units
│   └── requirements.txt       # Python-Dependencies
│
├── webapp/                    # Web-App
│   ├── index.html             # SPA
│   ├── styles/app.css         # Styling
│   └── scripts/               # JavaScript-Module
│       ├── main.js            # App-Lifecycle
│       ├── touchpad.js        # Touch-Handling
│       ├── pairing.js         # Pairing-Flow
│       └── ...
│
└── docs/                      # Dokumentation
    ├── architecture.md        # System-Design
    ├── protocol.md            # WebSocket-Protokoll
    ├── deployment.md          # Setup-Anleitung
    └── mvp_roadmap.md         # Roadmap

```

## Admin-CLI

```bash
# Geräte verwalten
python3 scripts/admin_cli.py list             # Alle Geräte anzeigen
python3 scripts/admin_cli.py revoke <id>      # Gerät widerrufen
python3 scripts/admin_cli.py allow <id>       # Gerät erlauben

# Pairing
python3 scripts/admin_cli.py pair             # Pairing starten
python3 scripts/admin_cli.py unpair           # Pairing stoppen

# Logs
python3 scripts/admin_cli.py logs -n 100      # Letzte 100 Log-Einträge
```

## Troubleshooting

### USB-Gerät wird nicht erkannt
```bash
# Prüfe USB-Gadget-Status
ls -la /dev/hidg*

# Prüfe ob Gadget-Service läuft
systemctl status tvbridge-gadget

# Manuell neu laden
sudo systemctl restart tvbridge-gadget
```

### WebSocket-Verbindung schlägt fehl
```bash
# Prüfe Backend-Service
systemctl status tvbridge-backend

# Prüfe Logs
journalctl -u tvbridge-backend -f

# Prüfe Firewall
sudo ufw status
```

### Mehr Details
Siehe [Deployment Guide](docs/deployment.md#troubleshooting)

## Lizenz

Privates Projekt
