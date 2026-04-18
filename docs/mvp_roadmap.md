# TV-Bridge MVP Roadmap

## Phase 1: Architektur & Dokumentation ✅

**Status**: Abgeschlossen

**Deliverables**:
- [x] Architecture.md - Systemarchitektur und Designentscheidungen
- [x] Protocol.md - WebSocket-Protokoll-Spezifikation
- [x] Deployment.md - Raspberry Pi Setup und Installation
- [x] README.md - Projektübersicht

**Erkenntnisse**:
- Klare Trennung zwischen USB-HID-Schicht und Netzwerk-Schicht
- WebSocket für niedrige Latenz
- SQLite für einfache Persistenz
- Token-basierte Auth (Migration zu Key-Pair später möglich)

---

## Phase 2: Pi Setup ✅

**Status**: Abgeschlossen

**Deliverables**:
- [x] setup_gadget.sh - USB HID Gadget ConfigFS-Setup
- [x] install.sh - Automatisches Installationsskript
- [x] tvbridge-gadget.service - systemd Service für USB-Gadget
- [x] tvbridge-backend.service - systemd Service für Backend
- [x] requirements.txt - Python-Dependencies

**Technische Details**:
- Composite HID Device (Mouse + Keyboard)
- Boot Protocol für maximale TV-Kompatibilität
- Automatischer Start beim Boot
- Robustes Error-Handling

---

## Phase 3: Backend MVP ✅

**Status**: Abgeschlossen

**Deliverables**:
- [x] models.py - Pydantic-Datenmodelle
- [x] settings.py - Konfiguration
- [x] config_store.py - SQLite-Datenbankzugriff
- [x] hid_service.py - USB HID Interface
- [x] input_engine.py - Input-Event-Processing
- [x] auth_service.py - Authentifizierung
- [x] pairing_service.py - Pairing-Logik
- [x] ws_gateway.py - WebSocket-Server
- [x] admin_api.py - Admin REST API
- [x] main.py - FastAPI App

**Features**:
- WebSocket-basierte Kommunikation
- Device-Pairing mit zeitbegrenzten Codes
- Profil-System (Sensitivität, Scroll, etc.)
- Rate Limiting
- Audit-Logging
- HID Mouse + Keyboard Support
- Event Coalescing für niedrige Latenz

**Offene Punkte**:
- [ ] Unit Tests (Phase 5)
- [ ] Scroll via Mouse Wheel statt Arrow-Keys (erfordert Extended HID Descriptor)

---

## Phase 4: Web-App MVP ✅

**Status**: Abgeschlossen

**Deliverables**:
- [x] index.html - Single-Page-App
- [x] app.css - Mobile-first Styling
- [x] storage.js - LocalStorage-Wrapper
- [x] ws-client.js - WebSocket-Client mit Reconnect
- [x] touchpad.js - Touch-Event-Handling
- [x] keyboard.js - Virtuelle Tastatur
- [x] pairing.js - Pairing-Flow
- [x] settings.js - Einstellungen-UI
- [x] main.js - App-Lifecycle

**Features**:
- Touch-basierte Mausbewegung
- Tap-to-Click (1 Finger = Links, 2 Finger = Rechts)
- Zwei-Finger-Scroll
- Virtuelle Tastatur für Text-Eingabe
- Spezielle Tasten (Enter, Arrows, etc.)
- Profil-Einstellungen
- Auto-Reconnect
- PWA-fähig vorbereitet

**UX-Optimierungen**:
- Event Coalescing für smooth Movement
- Adaptive Send-Rate (~60 Hz)
- Visuelles Feedback bei Connection-Status
- Mobile-optimiertes Design

---

## Phase 5: Hardening 🚧

**Status**: Geplant

**Ziele**:
- [ ] Admin-UI (Web-basiert)
  - Pairing-Modus starten/stoppen
  - Geräte-Liste anzeigen
  - Geräte revoken/erlauben
  - Logs anzeigen
- [ ] Bessere Fehlerbehandlung
  - TV erkennt USB-Gerät nicht → Diagnose-UI
  - WebSocket-Fehler → Klare User-Messages
  - HID-Write-Fehler → Fallback/Retry
- [ ] Token-Rotation
  - Automatisches Refresh von Device-Tokens
  - Revoke-Mechanismus verbessern
- [ ] Hotspot-Modus (Fallback)
  - Pi erstellt eigenes WLAN wenn kein Heimnetz verfügbar
  - SSID: TV-Bridge-XXXX
  - DHCP-Server auf Pi
  - Web-App unter 192.168.42.1
- [ ] Extended HID Descriptor
  - Mouse Wheel Support (statt Arrow-Keys für Scroll)
  - Optional: Media Keys (Play/Pause, Volume)
- [ ] Logging-Verbesserungen
  - Strukturiertes JSON-Logging
  - Log-Rotation
  - Debug-Modus per Admin-UI ein/aus
- [ ] Health-Monitoring
  - Uptime-Tracking
  - Latenz-Metriken (P50, P95, P99)
  - Event-Rate-Dashboard

**Sicherheit**:
- [ ] HTTPS/WSS (self-signed Cert)
- [ ] Rate-Limit-Verschärfung
- [ ] IP-Whitelisting (optional)

---

## Phase 6: Flutter Readiness 🔮

**Status**: Geplant (Post-MVP)

**Ziele**:
- [ ] Client-SDK-Dokumentation
  - WebSocket-Protokoll-Referenz
  - Beispiel-Implementierung
- [ ] Native App Features
  - Haptic Feedback
  - Native Keyboard
  - Bessere Touch-Gesten
  - Background-Reconnect
- [ ] Backend bleibt unverändert
  - Identisches WebSocket-Protokoll
  - Keine App-spezifische Logik

---

## Zusätzliche Features (Backlog)

### Media Keys
- Consumer Control HID Interface
- Play/Pause, Next, Previous, Volume
- Nur sinnvoll wenn TV-Browser unterstützt

### Multi-User
- Mehrere Clients gleichzeitig
- Arbitrierung bei Konflikten
- Session-Prioritäten

### Gestures
- Swipe-Gesten für Browser-Navigation (Back/Forward)
- Pinch-to-Zoom (wenn TV-Browser unterstützt)

### OTA-Updates
- Web-basiertes Update-Interface
- Automatische Updates (optional)
- Rollback-Funktion

### Key-Based Auth
- Public/Private-Key statt Token
- Challenge-Response-Signatur
- Migration von bestehenden Tokens

### Voice Input
- Speech-to-Text auf Smartphone
- Text an TV senden
- Nur über native App sinnvoll

---

## Deployment-Plan

### Development
1. Backend auf Development-Pi testen
2. Web-App lokal testen (WebSocket zu Pi)
3. USB-HID-Test mit echtem TV

### Staging
1. Installation auf Staging-Pi
2. End-to-End-Tests
3. Performance-Tests
4. Latenz-Messung

### Production
1. Installation nach Anleitung
2. Backup-Strategie
3. Monitoring einrichten
4. User-Dokumentation

---

## Metriken & KPIs

### Performance
- Input-Latenz: < 20ms (P95) ✅ Ziel
- WebSocket-RTT: < 10ms (lokales Netz) ✅ Ziel
- Event-Rate: 60-120 Hz ✅ Implementiert

### Stabilität
- Uptime: > 99% (7 Tage)
- Reconnect-Success-Rate: > 95%
- HID-Write-Error-Rate: < 1%

### Usability
- Pairing-Time: < 30 Sekunden ✅ Ziel
- Auth-after-Reconnect: < 2 Sekunden ✅ Ziel
- Touch-to-Cursor-Delay: < 50ms ✅ Ziel

---

## Lessons Learned

### Was gut funktioniert:
- ConfigFS für USB-Gadget ist stabil
- FastAPI/WebSocket ist performant
- Token-basierte Auth ist einfach
- Event Coalescing reduziert Latenz deutlich
- Mobile-first Design passt perfekt

### Herausforderungen:
- Boot Protocol Mouse hat kein Wheel → Arrow-Keys als Workaround
- TV-USB-Erkennung manchmal träge → Robustes Retry nötig
- WebSocket-Reconnect muss sanft sein → Exponential Backoff

### Nächste Iteration:
- Extended HID Descriptor für Wheel
- HTTPS für Production
- Admin-UI für bessere Verwaltung
- Hotspot-Fallback für Standalone-Betrieb
