# TV-Bridge Systemarchitektur

## 1. Systemüberblick

### 1.1 Gesamtarchitektur

```
┌─────────────┐         ┌──────────────────┐         ┌──────────┐
│  Smartphone │◄───────►│  Raspberry Pi    │◄───────►│ Smart TV │
│  (Web-App)  │  WiFi   │  Zero 2 W        │   USB   │          │
└─────────────┘ WS+HTTP └──────────────────┘  Gadget └──────────┘
                                 │
                         ┌───────┴────────┐
                         │                │
                    WebSocket          USB HID
                    Server             Composite
                         │                │
                    ┌────▼────┐      ┌────▼─────┐
                    │ Backend │      │  Mouse   │
                    │ Services│      │ Keyboard │
                    └─────────┘      └──────────┘
```

### 1.2 Datenfluss

1. **Input Path**: Smartphone → WebSocket → Input Engine → HID Service → TV
2. **Control Path**: Admin UI → Admin API → Pairing/Auth Service → Config Store
3. **Auth Path**: Client → WebSocket → Auth Service → Device Registry

## 2. Komponentenarchitektur

### 2.1 Backend-Module (Python)

#### 2.1.1 `hid_service.py`
**Verantwortlichkeit**: USB HID Gadget Interface

- Initialisiert und verwaltet ConfigFS-basiertes USB Composite Device
- Öffnet `/dev/hidg0` (Mouse) und `/dev/hidg1` (Keyboard)
- Sendet binäre HID Reports
- Kapselt HID Report Descriptor Details
- Fehlerbehandlung bei USB-Verbindungsproblemen

**Technische Details**:
- Composite HID mit 2 Funktionen (Mouse + Keyboard)
- Relative Mouse Bewegungen (3-Byte Reports: Buttons, X-Delta, Y-Delta)
- Keyboard mit Standard 104-Key Layout
- Boot Protocol Support

**Abhängigkeiten**: Keine (niedrigste Schicht)

#### 2.1.2 `input_engine.py`
**Verantwortlichkeit**: Input-Event-Processing

- Empfängt normalisierte Events (move, click, scroll, key)
- Wendet Profil-Settings an:
  - Pointer-Sensitivität (Multiplikator 0.1 - 5.0)
  - Pointer-Acceleration (optional)
  - Scroll-Sensitivität
  - Natural Scroll (Invertierung)
- Event Coalescing (mehrere Move-Events zusammenfassen)
- Rate Limiting (max. 120 Events/Sekunde pro Client)
- Konvertiert in HID-spezifische Aktionen

**Abhängigkeiten**: `hid_service`, `config_store` (für Profile)

#### 2.1.3 `ws_gateway.py`
**Verantwortlichkeit**: WebSocket-Server und Session-Management

- FastAPI WebSocket Endpoint (`/ws`)
- Verbindungs-Lifecycle:
  1. Accept → Hello → Auth → Operational → Disconnect
- Nachrichtenprotokoll-Parsing (JSON)
- Heartbeat/Ping (alle 30s, Timeout nach 60s)
- Session-State-Machine
- Event-Routing an `input_engine`
- Broadcast-Fähigkeit für Admin-Messages (z.B. Device Revoked)

**Abhängigkeiten**: `auth_service`, `input_engine`

#### 2.1.4 `auth_service.py`
**Verantwortlichkeit**: Authentifizierung und Autorisierung

- Validiert Auth-Messages von Clients
- Prüft Device-Token gegen Device Registry
- Prüft Revocation-Status
- Rate Limiting auf Auth-Versuche (max. 5/Minute pro IP)
- Audit-Logging aller Auth-Events
- Token-Format: `device_<uuid>_<random_secret>`

**Abhängigkeiten**: `config_store`

#### 2.1.5 `pairing_service.py`
**Verantwortlichkeit**: Device-Pairing-Logik

- Pairing-Modus-Verwaltung (zeitbegrenzt, default 120s)
- Pairing-Code-Generierung (6-stellig, numerisch)
- Pairing-URL mit Einmal-Token generieren
- Device-Registrierung:
  - Generiert eindeutige Device-ID
  - Generiert starkes Device-Token (256 Bit)
  - Speichert Device-Metadata
- QR-Code-Daten erzeugen (optional)

**Pairing-Flow**:
1. Admin aktiviert Pairing-Modus via Admin API
2. Service generiert Pairing-Code + Einmal-Token
3. Client ruft `/pair?code=XXXXXX` auf
4. Client sendet Device-Name
5. Service registriert Device, gibt Token zurück
6. Client speichert Token in LocalStorage

**Abhängigkeiten**: `config_store`

#### 2.1.6 `config_store.py`
**Verantwortlichkeit**: Persistente Datenhaltung

- SQLite-Datenbank (`/var/lib/tvbridge/tvbridge.db`)
- Schema:
  - `devices` (id, name, token_hash, created_at, last_seen, allowed, revoked_at, notes)
  - `profiles` (device_id, name, settings_json)
  - `pairing_sessions` (code, token, created_at, expires_at, used)
  - `audit_log` (timestamp, event_type, device_id, details)

- Transaktionale Operationen
- Device CRUD
- Profile CRUD
- Audit-Logging

**Abhängigkeiten**: Keine

#### 2.1.7 `admin_api.py`
**Verantwortlichkeit**: Admin REST API

- FastAPI Router (`/admin/*`)
- Endpunkte:
  - `POST /admin/pairing/start` - Pairing-Modus starten
  - `POST /admin/pairing/stop` - Pairing-Modus stoppen
  - `GET /admin/pairing/status` - Aktueller Pairing-Status
  - `GET /admin/devices` - Liste aller Geräte
  - `POST /admin/devices/{id}/revoke` - Gerät widerrufen
  - `POST /admin/devices/{id}/allow` - Gerät erlauben
  - `PUT /admin/devices/{id}/name` - Gerät umbenennen
  - `DELETE /admin/devices/{id}` - Gerät löschen
  - `GET /admin/health` - System-Health-Check

- Auth: Lokaler Zugriff oder Admin-Token (ENV)

**Abhängigkeiten**: `pairing_service`, `config_store`, `ws_gateway`

#### 2.1.8 `models.py`
**Verantwortlichkeit**: Datenmodelle

- Pydantic Models für:
  - Device
  - Profile
  - PairingSession
  - WebSocket Messages (alle Typen)
  - HID Events
  - Config Settings

#### 2.1.9 `settings.py`
**Verantwortlichkeit**: Konfiguration

- Pydantic BaseSettings
- Environment-basierte Config
- Defaults:
  - `HOST=0.0.0.0`
  - `PORT=8080`
  - `DB_PATH=/var/lib/tvbridge/tvbridge.db`
  - `HID_MOUSE_DEV=/dev/hidg0`
  - `HID_KEYBOARD_DEV=/dev/hidg1`
  - `PAIRING_TIMEOUT=120`
  - `ADMIN_TOKEN=<random>`

#### 2.1.10 `main.py`
**Verantwortlichkeit**: FastAPI App Entry Point

- FastAPI App Setup
- Router-Registrierung
- Static File Serving für Web-App
- CORS (nur für Development)
- Lifecycle Events:
  - Startup: HID Service Init, DB Migration
  - Shutdown: Graceful Cleanup
- Logging-Setup

### 2.2 Frontend (Web-App)

#### Struktur
```
webapp/
├── index.html          # Single-Page-App
├── styles/
│   └── app.css         # Mobile-first, touch-optimized
├── scripts/
│   ├── main.js         # App Lifecycle
│   ├── ws-client.js    # WebSocket Client + Reconnect
│   ├── touchpad.js     # Touch-Event-Handling
│   ├── keyboard.js     # Virtual Keyboard UI
│   ├── pairing.js      # Pairing Flow
│   ├── settings.js     # Settings UI
│   └── storage.js      # LocalStorage Wrapper
└── assets/
    └── icons/          # Touch-optimized Icons
```

#### Screens

**1. Connect Screen**
- Anzeige: Connection Status
- Pairing-Code-Input
- Auto-Connect mit gespeichertem Token
- Reconnect-Logik

**2. Remote Screen**
- Fullscreen-Touchpad
- Click-Buttons (L/R)
- Scroll-Mode Toggle
- Keyboard-Button
- Connection-Indicator
- Settings-Icon

**3. Settings Screen**
- Profil-Auswahl
- Sensitivität-Slider
- Scroll-Speed-Slider
- Tap-to-Click Toggle
- Natural Scroll Toggle
- Acceleration Toggle
- Device-Info

**4. Admin Screen** (optional)
- Pairing Start/Stop
- Device List
- Revoke/Allow Actions

### 2.3 System Services (systemd)

#### `tvbridge-gadget.service`
- Führt `/usr/local/bin/setup_gadget.sh` aus
- Muss vor `tvbridge-backend.service` starten
- Type: oneshot
- RemainAfterExit: yes

#### `tvbridge-backend.service`
- Startet FastAPI mit Uvicorn
- Depends: tvbridge-gadget.service, network-online.target
- Restart: always
- User: tvbridge (dedicated service user)

#### `tvbridge-hotspot.service` (optional, Phase 5)
- Startet Access Point wenn kein WLAN verfügbar
- Fallback-Netzwerk

## 3. Designentscheidungen

### 3.1 Warum Python + FastAPI?
- **Rapid Development**: Schnelle Iteration für MVP
- **Async Support**: Native WebSocket-Unterstützung
- **HID Access**: Direkter File-Zugriff auf `/dev/hidgX`
- **Deployment**: Einfach auf Raspberry Pi OS
- **Libraries**: Reiches Ecosystem (Uvicorn, Pydantic, SQLite)

### 3.2 Warum ConfigFS statt uinput?
- **Standardkonform**: Offizielle USB Gadget API
- **Composite Device**: Mouse + Keyboard in einem Gerät
- **Boot Protocol**: Bessere TV-Kompatibilität
- **Stabil**: Kernel-maintained, keine User-Space-Hacks

### 3.3 Warum SQLite?
- **Embedded**: Keine separate DB-Server
- **Transaktional**: ACID-Garantien
- **Low Overhead**: Perfekt für Pi Zero
- **Backup**: Einfaches File-Copy

### 3.4 Warum WebSocket?
- **Low Latency**: Persistente Verbindung, kein HTTP-Overhead
- **Bidirektional**: Server kann Client informieren (Revocation)
- **Mobile Support**: Breite Browser-Unterstützung
- **Simple Protocol**: JSON-basiert, debuggable

### 3.5 Warum relative Mouse-Bewegung?
- **Bildschirmunabhängig**: Keine Auflösungsabhängigkeit
- **Natürliches Gefühl**: Wie Touchpad
- **Glättung**: Einfacher zu implementieren
- **HID Standard**: Boot-Protocol-kompatibel

## 4. Sicherheitsarchitektur

### 4.1 Threat Model

**Bedrohungen**:
1. Unautorisierte Geräte im WLAN senden Input
2. MITM-Attacke auf WebSocket
3. Token-Diebstahl
4. Pairing-Code Bruteforce
5. Replay-Attacken

**Mitigations**:
1. **Device Registry**: Nur gepaarte Geräte erlaubt (Default Deny)
2. **HTTPS/WSS**: Verschlüsselung (für Production)
3. **Token Storage**: HTTPOnly-Cookies oder Secure LocalStorage
4. **Rate Limiting**: Max. 5 Pairing-Versuche/Minute
5. **Timestamp Validation**: Events mit veralteten Timestamps ablehnen

### 4.2 Auth-Flow

```
Client                    Server
  │                         │
  ├──── WS Connect ────────>│
  │<──── Hello ─────────────┤
  ├──── Auth (Token) ──────>│
  │                         ├─ Validate Token
  │                         ├─ Check Device Allowed
  │<──── Auth OK ───────────┤
  ├──── Input Events ──────>│  [authorized]
  │                         │
```

### 4.3 Pairing-Security

- **Zeitbegrenzung**: Pairing-Modus automatisch deaktiviert nach 120s
- **Einmal-Token**: Pairing-Token nur einmal verwendbar
- **Code-Komplexität**: 6-stelliger numerischer Code (1M Kombinationen)
- **Rate Limiting**: Max. 10 Pairing-Versuche pro IP
- **Audit-Log**: Alle Pairing-Events geloggt

## 5. Performance-Optimierungen

### 5.1 Input-Latenz-Ziele
- **Touch → HID**: < 20ms (P95)
- **WebSocket RTT**: < 10ms (lokales Netz)
- **Input Processing**: < 5ms

### 5.2 Optimierungstechniken

**Event Coalescing**:
- Mehrere `input_move` Events innerhalb 16ms (60 Hz) zusammenfassen
- Reduziert HID-Schreiboperationen

**Adaptive Senderate**:
- Client passt Send-Frequenz an Touch-Geschwindigkeit an
- Schnelle Bewegung: 60-120 Hz
- Langsame Bewegung: 30 Hz

**Priority Queue**:
- Click/Key-Events haben Vorrang vor Move-Events
- Verhindert verzögerte Clicks bei vielen Move-Events

**Zero-Copy**:
- HID Reports direkt in Byte-Buffer schreiben
- Minimale Allokationen

## 6. Erweiterbarkeit

### 6.1 Flutter-App-Integration
- Identisches WebSocket-Protokoll
- Keine Backend-Änderungen nötig
- Selbe Auth-Mechanismen
- Native Touch-Handling für bessere Latenz

### 6.2 Zukünftige Features (Post-MVP)
- **Media Keys**: Consumer Control HID Interface
- **Multi-User**: Mehrere gleichzeitige Clients
- **Gestures**: Swipe-Gesten für Browser-Navigation
- **Hotspot-Modus**: Automatischer AP-Fallback
- **OTA Updates**: Web-basierte Firmware-Updates
- **Key-Based Auth**: Public/Private-Key statt Token
- **TLS/HTTPS**: Verschlüsselte Verbindungen

## 7. Testing-Strategie

### 7.1 Unit Tests
- `hid_service`: Mock `/dev/hidgX`, teste Report-Generierung
- `input_engine`: Teste Sensitivität, Coalescing, Rate Limiting
- `auth_service`: Teste Token-Validation, Revocation
- `pairing_service`: Teste Code-Generation, Timeout

### 7.2 Integration Tests
- WebSocket-Protokoll: Kompletter Auth-Flow
- End-to-End: Simulated Touch → HID Output
- Error Scenarios: Device Revocation, Connection Loss

### 7.3 Manual Testing
- Real Device: Pi Zero → TV
- Latency Measurement: Touch → Cursor Move
- UX Testing: Smoothness, Responsiveness

## 8. Monitoring & Debugging

### 8.1 Logging
- **Level**: INFO (Production), DEBUG (Development)
- **Outputs**: journald + `/var/log/tvbridge/app.log`
- **Structured**: JSON-Format mit Context

### 8.2 Metrics
- WebSocket Connections (aktiv)
- Input Events/Sekunde
- HID Write Errors
- Auth Failures
- Latency Histogramme (P50, P95, P99)

### 8.3 Health Endpoint
```json
GET /admin/health
{
  "status": "healthy",
  "hid_mouse": "ok",
  "hid_keyboard": "ok",
  "database": "ok",
  "active_connections": 2,
  "uptime_seconds": 86400
}
```

## 9. Deployment-Topologien

### 9.1 Mode A: Home Network
```
[Internet] ─── [Router/WiFi] ─┬─ [Smartphone]
                               │
                               └─ [Raspberry Pi] ── USB ─ [TV]
```
- Pi und Smartphone im selben WLAN
- mDNS: `tv-bridge.local`

### 9.2 Mode B: Hotspot (Phase 5)
```
[Smartphone] ── WiFi ── [Raspberry Pi (AP)] ── USB ── [TV]
```
- Pi erstellt eigenes WLAN
- SSID: `TV-Bridge-<MAC-Suffix>`
- DHCP auf Pi
- Web-App unter `192.168.42.1`

## 10. Dateigrößen und Ressourcen

**Backend**:
- Compiled Size: ~50 MB (Python + Dependencies)
- RAM Usage: ~50-100 MB
- CPU: ~5-10% (idle), ~20-30% (active input)

**Frontend**:
- Total: ~500 KB (HTML + CSS + JS + Assets)
- Gzipped: ~150 KB

**Database**:
- Initial: ~100 KB
- Growth: ~1 KB pro Device + Profile

**Gesamt-Footprint**: ~200 MB (mit OS-Dependencies)
