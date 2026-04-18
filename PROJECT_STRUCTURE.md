# TV-Bridge Projektstruktur

```
tv-controll/
│
├── README.md                      # Projektübersicht
├── .gitignore                     # Git Ignore-Regeln
│
├── docs/                          # Dokumentation
│   ├── architecture.md            # Systemarchitektur
│   ├── protocol.md                # WebSocket-Protokoll-Spezifikation
│   ├── deployment.md              # Deployment-Guide
│   └── mvp_roadmap.md             # MVP-Roadmap und Status
│
├── backend/                       # Python Backend
│   ├── README.md                  # Backend-Dokumentation
│   ├── requirements.txt           # Python-Dependencies
│   │
│   ├── app/                       # Hauptanwendung
│   │   ├── main.py                # FastAPI App Entry Point
│   │   ├── models.py              # Pydantic-Datenmodelle
│   │   ├── settings.py            # Konfiguration (Environment)
│   │   ├── config_store.py        # SQLite-Datenbank-Zugriff
│   │   ├── hid_service.py         # USB HID Interface
│   │   ├── input_engine.py        # Input-Event-Processing
│   │   ├── auth_service.py        # Authentifizierung
│   │   ├── pairing_service.py     # Pairing-Logik
│   │   ├── ws_gateway.py          # WebSocket-Server
│   │   └── admin_api.py           # Admin REST API
│   │
│   ├── scripts/                   # Setup-Skripte
│   │   ├── setup_gadget.sh        # USB HID Gadget ConfigFS-Setup
│   │   ├── install.sh             # Automatisches Installationsskript
│   │   └── init_db.py             # Datenbank-Initialisierung
│   │
│   ├── systemd/                   # systemd Service-Units
│   │   ├── tvbridge-gadget.service    # USB-Gadget-Service
│   │   └── tvbridge-backend.service   # Backend-Service
│   │
│   └── tests/                     # Unit Tests (TODO)
│       └── ...
│
└── webapp/                        # Web-App (Frontend)
    ├── index.html                 # Single-Page-App
    │
    ├── styles/                    # CSS
    │   └── app.css                # Haupt-Stylesheet
    │
    ├── scripts/                   # JavaScript
    │   ├── main.js                # App-Lifecycle
    │   ├── storage.js             # LocalStorage-Wrapper
    │   ├── ws-client.js           # WebSocket-Client
    │   ├── touchpad.js            # Touch-Event-Handling
    │   ├── keyboard.js            # Virtuelle Tastatur
    │   ├── pairing.js             # Pairing-Flow
    │   └── settings.js            # Einstellungen-UI
    │
    └── assets/                    # Assets (Icons, etc.)
        └── ...
```

## Dateigrößen-Übersicht

```
Backend:
  Python-Code:        ~15 KB (komprimiert)
  Dependencies:       ~50 MB
  Runtime (RAM):      50-100 MB

Web-App:
  HTML/CSS/JS:        ~100 KB
  Gzipped:            ~30 KB

Datenbank:
  Initial:            ~100 KB
  Pro Device:         ~1 KB

Gesamt-Installation: ~200 MB (inkl. OS-Dependencies)
```

## Laufzeit-Dateien

```
/opt/tvbridge/                    # Installation
├── backend/
├── webapp/
└── venv/                         # Python Virtual Environment

/var/lib/tvbridge/                # Daten
└── tvbridge.db                   # SQLite-Datenbank

/var/log/tvbridge/                # Logs
└── app.log                       # Anwendungslog

/usr/local/bin/                   # System-Binaries
└── setup_gadget.sh               # Gadget-Setup-Skript

/etc/systemd/system/              # systemd Services
├── tvbridge-gadget.service
└── tvbridge-backend.service

/dev/                             # HID-Devices (nach Gadget-Setup)
├── hidg0                         # Mouse
└── hidg1                         # Keyboard
```

## Technologie-Stack

### Backend
- **Sprache**: Python 3.9+
- **Web-Framework**: FastAPI
- **WebSocket**: uvicorn[standard]
- **Datenbank**: SQLite (aiosqlite)
- **Validation**: Pydantic
- **Deployment**: systemd

### Frontend
- **HTML5**: Single-Page-App
- **CSS3**: Mobile-first, Touch-optimiert
- **JavaScript**: Vanilla ES6+
- **Storage**: LocalStorage
- **Kommunikation**: WebSocket API

### System
- **OS**: Raspberry Pi OS Lite
- **USB**: ConfigFS/libcomposite
- **HID**: Boot Protocol (Mouse + Keyboard)
- **Networking**: WiFi (WLAN0)

## Abhängigkeiten

### Python-Packages
```
fastapi              # Web-Framework
uvicorn[standard]    # ASGI-Server
pydantic             # Datenvalidierung
pydantic-settings    # Konfiguration
websockets           # WebSocket-Support
aiosqlite            # Async SQLite
python-multipart     # Form-Daten
```

### System-Packages
```
python3              # Python-Runtime
python3-pip          # Package-Manager
python3-venv         # Virtual Environment
sqlite3              # SQLite-CLI
libsqlite3-dev       # SQLite-Entwicklungsbibliotheken
avahi-daemon         # mDNS (tv-bridge.local)
```

### Optionale Packages (Hotspot-Modus)
```
hostapd              # Access Point
dnsmasq              # DHCP-Server
```

## Ports und Endpunkte

### Backend (Port 8080)
```
HTTP/WebSocket:
  GET  /                    → Web-App
  GET  /ws                  → WebSocket-Endpunkt
  POST /pair                → Public Pairing-API

Admin-API (mit Token):
  POST   /admin/pairing/start      → Pairing starten
  POST   /admin/pairing/stop       → Pairing stoppen
  GET    /admin/pairing/status     → Pairing-Status
  GET    /admin/devices            → Geräte-Liste
  POST   /admin/devices/{id}/revoke → Gerät widerrufen
  POST   /admin/devices/{id}/allow  → Gerät erlauben
  PUT    /admin/devices/{id}        → Gerät aktualisieren
  DELETE /admin/devices/{id}        → Gerät löschen
  GET    /admin/health              → Health-Check
```

### mDNS
```
Hostname: tv-bridge.local
Service:  http://tv-bridge.local:8080
```

## Sicherheitsmodell

### Authentifizierung
- Device-Token (256-Bit Entropie)
- Token-Hash (SHA-256) in Datenbank
- Admin-Token (Environment-Variable)

### Autorisierung
- Device-Whitelist (nach Pairing)
- Revocation-Status wird bei jedem Auth-Versuch geprüft
- Sessions werden bei Revocation sofort geschlossen

### Rate Limiting
- Auth: 5 Versuche/Minute/IP
- Pairing: 10 Versuche/Minute/IP
- Input: 120 Events/Sekunde/Client

### Netzwerk
- Standard: HTTP/WS (lokales Netz)
- Optional: HTTPS/WSS (self-signed)
- Firewall: Nur Port 8080 exponieren

## Performance-Charakteristik

### Latenz
- Touch → WebSocket: < 5ms
- WebSocket → HID: < 10ms
- HID → TV: < 5ms
- **Gesamt (P95)**: ~20ms

### Durchsatz
- Input-Events: 60-120 Hz
- WebSocket-Bandwidth: ~10 KB/s (idle), ~50 KB/s (aktiv)
- CPU-Last: ~5-10% (idle), ~20-30% (aktiv)
- RAM-Nutzung: 50-100 MB

### Skalierbaren
- Max. Connections: 10 (konfigurierbar)
- Max. Devices: Unbegrenzt (Datenbank)
- Max. Profiles/Device: Unbegrenzt
