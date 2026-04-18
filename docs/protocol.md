# TV-Bridge WebSocket-Protokoll Spezifikation

**Version**: 1.0  
**Datum**: 2026-04-17  
**Status**: MVP

## 1. Übersicht

Das TV-Bridge-Protokoll ist ein JSON-basiertes WebSocket-Protokoll für bidirektionale Kommunikation zwischen Client (Smartphone) und Server (Raspberry Pi).

### 1.1 Designprinzipien

- **JSON-Format**: Alle Nachrichten sind JSON-Objekte
- **Typisiert**: Jede Nachricht hat ein `type`-Feld
- **Versioniert**: Protokollversion in jeder Nachricht
- **Timestamps**: Alle Events mit Zeitstempel (Client-Zeit)
- **Kompakt**: Minimale Payloads für niedrige Latenz
- **Erweiterbar**: Reservierte Felder für zukünftige Features

### 1.2 WebSocket-Verbindung

**Endpoint**: `ws://<pi-ip>:8080/ws`  
**Subprotocol**: `tvbridge.v1`

## 2. Nachrichtenstruktur

### 2.1 Basis-Format

Alle Nachrichten haben diese Grundstruktur:

```json
{
  "type": "<message_type>",
  "protocol_version": "1.0",
  "timestamp": 1713369600000,
  "payload": { ... }
}
```

**Felder**:
- `type` (string, required): Nachrichtentyp (siehe unten)
- `protocol_version` (string, required): Protokollversion "1.0"
- `timestamp` (integer, required): Unix-Timestamp in Millisekunden
- `payload` (object, optional): Typ-spezifische Daten

### 2.2 Timestamp-Validierung

Server validiert Timestamps:
- **Max Age**: 5 Sekunden in der Vergangenheit
- **Max Future**: 1 Sekunde in der Zukunft
- **Zweck**: Replay-Attack-Prevention

## 3. Verbindungs-Lifecycle

### 3.1 Connection Flow

```
Client                           Server
  │                                │
  ├─── [WebSocket Connect] ───────>│
  │<─────── hello ─────────────────┤
  ├─────── auth ──────────────────>│
  │                                ├─ [Validate Token]
  │<─────── auth_ok ───────────────┤
  │                                │
  │<══════ [Operational] ═══════>│
  │                                │
  ├─────── input_* ───────────────>│
  │<─────── ping ───────────────────┤
  ├─────── pong ──────────────────>│
  │                                │
```

### 3.2 State Machine

**States**:
1. **CONNECTED**: WebSocket verbunden, warte auf Auth
2. **AUTHENTICATED**: Auth erfolgreich, kann Input senden
3. **DISCONNECTED**: Verbindung geschlossen

**Transitions**:
- CONNECTED → AUTHENTICATED: `auth_ok` empfangen
- AUTHENTICATED → CONNECTED: `auth_failed` empfangen
- * → DISCONNECTED: WebSocket close

## 4. Nachrichtentypen

### 4.1 Server → Client

#### 4.1.1 `hello`

Server begrüßt Client nach Verbindungsaufbau.

```json
{
  "type": "hello",
  "protocol_version": "1.0",
  "timestamp": 1713369600000,
  "payload": {
    "server_version": "1.0.0",
    "capabilities": ["mouse", "keyboard", "scroll"],
    "requires_auth": true
  }
}
```

#### 4.1.2 `auth_ok`

Authentifizierung erfolgreich.

```json
{
  "type": "auth_ok",
  "protocol_version": "1.0",
  "timestamp": 1713369600100,
  "payload": {
    "device_id": "device_550e8400-e29b-41d4-a716-446655440000",
    "device_name": "My Phone",
    "session_id": "session_7c9e6679-7425-40de-944b-e07fc1f90ae7"
  }
}
```

#### 4.1.3 `auth_failed`

Authentifizierung fehlgeschlagen.

```json
{
  "type": "auth_failed",
  "protocol_version": "1.0",
  "timestamp": 1713369600100,
  "payload": {
    "reason": "invalid_token",
    "message": "Device token is invalid or revoked"
  }
}
```

**Reason Codes**:
- `invalid_token`: Token ungültig oder unbekannt
- `device_revoked`: Gerät wurde widerrufen
- `rate_limited`: Zu viele Auth-Versuche
- `pairing_required`: Gerät muss erst gepaart werden

#### 4.1.4 `ping`

Server-Heartbeat (alle 30 Sekunden).

```json
{
  "type": "ping",
  "protocol_version": "1.0",
  "timestamp": 1713369630000,
  "payload": {}
}
```

#### 4.1.5 `error`

Generischer Fehler.

```json
{
  "type": "error",
  "protocol_version": "1.0",
  "timestamp": 1713369600200,
  "payload": {
    "code": "invalid_message",
    "message": "Message format invalid",
    "details": "Missing required field: type"
  }
}
```

**Error Codes**:
- `invalid_message`: Nachricht kann nicht geparst werden
- `unknown_type`: Unbekannter Nachrichtentyp
- `not_authenticated`: Nachricht erfordert Authentifizierung
- `rate_limited`: Rate Limit überschritten
- `hid_error`: Fehler beim Senden an HID-Device

#### 4.1.6 `profile_data`

Profildaten vom Server.

```json
{
  "type": "profile_data",
  "protocol_version": "1.0",
  "timestamp": 1713369600300,
  "payload": {
    "profile_name": "default",
    "settings": {
      "pointer_sensitivity": 1.0,
      "pointer_acceleration": false,
      "scroll_sensitivity": 1.0,
      "natural_scroll": false,
      "tap_to_click": true
    }
  }
}
```

#### 4.1.7 `device_revoked`

Gerät wurde widerrufen (während aktiver Session).

```json
{
  "type": "device_revoked",
  "protocol_version": "1.0",
  "timestamp": 1713369600400,
  "payload": {
    "reason": "Device revoked by administrator",
    "disconnect_in_seconds": 5
  }
}
```

### 4.2 Client → Server

#### 4.2.1 `auth`

Client authentifiziert sich.

```json
{
  "type": "auth",
  "protocol_version": "1.0",
  "timestamp": 1713369600050,
  "payload": {
    "device_token": "device_550e8400-e29b-41d4-a716-446655440000_abc123...xyz"
  }
}
```

#### 4.2.2 `pong`

Antwort auf `ping`.

```json
{
  "type": "pong",
  "protocol_version": "1.0",
  "timestamp": 1713369630010,
  "payload": {}
}
```

#### 4.2.3 `input_move`

Mausbewegung (relative Deltas).

```json
{
  "type": "input_move",
  "protocol_version": "1.0",
  "timestamp": 1713369600150,
  "payload": {
    "dx": 10.5,
    "dy": -5.2
  }
}
```

**Felder**:
- `dx` (float): Relative X-Bewegung in Pixel (Client-Koordinaten)
- `dy` (float): Relative Y-Bewegung in Pixel (Client-Koordinaten)

**Empfehlung**:
- Client sollte Events coalescing betreiben
- Sende max. 60-120 Events/Sekunde
- Normalisiere auf Touch-Fläche

#### 4.2.4 `input_click`

Mausklick.

```json
{
  "type": "input_click",
  "protocol_version": "1.0",
  "timestamp": 1713369600200,
  "payload": {
    "button": "left",
    "action": "down"
  }
}
```

**Felder**:
- `button` (string): "left", "right", "middle"
- `action` (string): "down", "up", "click" (down+up)

**Wichtig**: Sende `down` und `up` separat für präzise Kontrolle.

#### 4.2.5 `input_scroll`

Scroll-Event.

```json
{
  "type": "input_scroll",
  "protocol_version": "1.0",
  "timestamp": 1713369600250,
  "payload": {
    "vertical": -3.5,
    "horizontal": 0.0
  }
}
```

**Felder**:
- `vertical` (float): Vertikale Scroll-Richtung (negativ = nach oben)
- `horizontal` (float): Horizontale Scroll-Richtung (negativ = nach links)

**Normalisierung**: Werte repräsentieren "Scroll-Lines" (1.0 = 1 Zeile).

#### 4.2.6 `input_key`

Tastendruck (einzelne Taste).

```json
{
  "type": "input_key",
  "protocol_version": "1.0",
  "timestamp": 1713369600300,
  "payload": {
    "key": "Enter",
    "action": "press"
  }
}
```

**Felder**:
- `key` (string): Tasten-Name (siehe Key-Codes unten)
- `action` (string): "press", "release"

**Modifier**: Werden separat gesendet (z.B. "Shift", "Control").

#### 4.2.7 `text_commit`

Text-Eingabe (kompletter String).

```json
{
  "type": "text_commit",
  "protocol_version": "1.0",
  "timestamp": 1713369600350,
  "payload": {
    "text": "Hello World!"
  }
}
```

**Felder**:
- `text` (string): Zu sendender Text (max. 1000 Zeichen)

**Verarbeitung**: Server konvertiert Text in Keyboard-Events mit korrektem Layout.

#### 4.2.8 `profile_get`

Profil vom Server abrufen.

```json
{
  "type": "profile_get",
  "protocol_version": "1.0",
  "timestamp": 1713369600400,
  "payload": {
    "profile_name": "default"
  }
}
```

#### 4.2.9 `profile_set`

Profil-Einstellungen setzen.

```json
{
  "type": "profile_set",
  "protocol_version": "1.0",
  "timestamp": 1713369600450,
  "payload": {
    "profile_name": "custom",
    "settings": {
      "pointer_sensitivity": 1.5,
      "scroll_sensitivity": 0.8,
      "natural_scroll": true
    }
  }
}
```

**Validierung**: Server validiert Wertebereich (siehe Profile-Spec).

## 5. Key-Codes

### 5.1 Spezielle Tasten

**Navigation**:
- `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`
- `Home`, `End`, `PageUp`, `PageDown`

**Editing**:
- `Enter`, `Backspace`, `Delete`, `Tab`, `Escape`
- `Insert`

**Modifier**:
- `Shift`, `Control`, `Alt`, `Meta` (Windows/Command)

**Funktion**:
- `F1` - `F12`

**Media** (optional, Post-MVP):
- `MediaPlayPause`, `MediaStop`, `MediaNext`, `MediaPrevious`
- `VolumeUp`, `VolumeDown`, `VolumeMute`

### 5.2 Alphanumerische Tasten

Für normale Zeichen (A-Z, 0-9, Sonderzeichen): Nutze `text_commit` statt `input_key`.

### 5.3 Key-Mapping

Server mappt Key-Namen auf USB HID Usage IDs (siehe HID Usage Tables).

Beispiel:
- `Enter` → 0x28
- `Backspace` → 0x2A
- `ArrowUp` → 0x52

## 6. Profile-Spezifikation

### 6.1 Settings-Felder

```typescript
interface ProfileSettings {
  pointer_sensitivity: number;      // 0.1 - 5.0, default: 1.0
  pointer_acceleration: boolean;    // default: false
  scroll_sensitivity: number;       // 0.1 - 5.0, default: 1.0
  natural_scroll: boolean;          // default: false (macOS-style wenn true)
  tap_to_click: boolean;            // default: true
  handedness?: "left" | "right";    // default: "right", optional
}
```

### 6.2 Validierung

Server validiert:
- Sensitivitäts-Werte im Bereich 0.1 - 5.0
- Boolean-Felder sind true/false
- Unbekannte Felder werden ignoriert

## 7. Pairing-Protokoll

Pairing erfolgt über HTTP, nicht WebSocket.

### 7.1 Pairing-Flow

**1. Pairing-Status abrufen**:
```
GET /pair/status

Response:
{
  "pairing_enabled": true,
  "expires_in_seconds": 95
}
```

**2. Pairing durchführen**:
```
POST /pair
Content-Type: application/json

{
  "pairing_code": "123456",
  "device_name": "My iPhone"
}

Response (Success):
{
  "success": true,
  "device_id": "device_550e8400-e29b-41d4-a716-446655440000",
  "device_token": "device_550e8400-e29b-41d4-a716-446655440000_abc123...xyz",
  "device_name": "My iPhone"
}

Response (Error):
{
  "success": false,
  "error": "invalid_code",
  "message": "Pairing code is invalid or expired"
}
```

**3. Token speichern**:
Client speichert `device_token` in LocalStorage/SecureStorage.

**4. WebSocket mit Token**:
Client verbindet sich und sendet `auth` mit gespeichertem Token.

## 8. Rate Limiting

### 8.1 Limits

**Auth**:
- 5 Versuche pro IP pro Minute
- 429 Response bei Überschreitung

**Pairing**:
- 10 Versuche pro IP pro Minute

**Input Events**:
- 120 Events pro Sekunde pro Client
- Events werden gedrosselt, nicht abgelehnt

### 8.2 Retry-Strategie

Client sollte bei Rate Limiting:
- Exponential Backoff verwenden
- Max. 5 Retry-Versuche
- Benutzer informieren

## 9. Fehlerbehandlung

### 9.1 WebSocket Disconnect

**Client**:
1. Verbindung verloren erkannt
2. Warte 1 Sekunde
3. Reconnect-Versuch
4. Exponential Backoff (max. 30 Sekunden)
5. Nach Reconnect: Sende `auth` erneut

**Server**:
- Cleanup von Session-State
- Gerät bleibt in Registry

### 9.2 Invalid Messages

Server sendet `error`-Nachricht, schließt Verbindung nicht (außer bei schweren Fehlern).

### 9.3 HID Errors

Wenn HID-Device nicht schreibbar:
- Server loggt Fehler
- Sendet `error` an Client
- System-Admin muss Gadget-Setup prüfen

## 10. Sicherheitsüberlegungen

### 10.1 Token-Sicherheit

- **Länge**: Mindestens 256 Bit Entropie
- **Format**: `device_<uuid>_<random_base64>`
- **Speicherung Server**: Nur Hash (SHA-256)
- **Speicherung Client**: Secure Storage (LocalStorage mit HTTPS)

### 10.2 Replay-Schutz

- Timestamp-Validierung (5s Window)
- Optional: Nonce pro Message (Post-MVP)

### 10.3 HTTPS/WSS

MVP: HTTP/WS (lokales Netz)  
Production: HTTPS/WSS mit self-signed Cert oder Let's Encrypt

## 11. Versionierung

### 11.1 Breaking Changes

Bei Protokoll-Breaking-Changes:
- Neue Version: `2.0`
- Server unterstützt beide Versionen parallel
- Client sendet bevorzugte Version in `protocol_version`

### 11.2 Backward Compatibility

Server ignoriert unbekannte Felder → ermöglicht Feature-Flags.

## 12. Erweiterungen (Post-MVP)

### 12.1 Multi-User

```json
{
  "type": "auth",
  "payload": {
    "device_token": "...",
    "request_exclusive": false  // erlaubt simultane Connections
  }
}
```

### 12.2 Gestures

```json
{
  "type": "input_gesture",
  "payload": {
    "gesture": "swipe_left",
    "fingers": 3
  }
}
```

### 12.3 Media Control

```json
{
  "type": "input_media",
  "payload": {
    "action": "play_pause"
  }
}
```

## 13. Beispiel-Session

```
// Client verbindet
→ WebSocket Connect ws://tv-bridge.local:8080/ws

// Server begrüßt
← { "type": "hello", ... }

// Client authentifiziert
→ { "type": "auth", "payload": { "device_token": "..." } }

// Server bestätigt
← { "type": "auth_ok", "payload": { "device_id": "...", ... } }

// Client sendet Input
→ { "type": "input_move", "payload": { "dx": 10, "dy": -5 } }
→ { "type": "input_click", "payload": { "button": "left", "action": "down" } }
→ { "type": "input_click", "payload": { "button": "left", "action": "up" } }

// Server pingt
← { "type": "ping", ... }

// Client antwortet
→ { "type": "pong", ... }

// Client sendet Text
→ { "type": "text_commit", "payload": { "text": "Hello!" } }

// Verbindung schließen
→ WebSocket Close
```

## 14. Debugging

### 14.1 Verbose Mode

Client kann `debug`-Flag in `auth` senden (nur Development):

```json
{
  "type": "auth",
  "payload": {
    "device_token": "...",
    "debug": true
  }
}
```

Server sendet dann zusätzliche `debug`-Messages mit Processing-Info.

### 14.2 Message Tracing

Jede Nachricht kann optionale `trace_id` haben:

```json
{
  "type": "input_move",
  "trace_id": "uuid-...",
  "payload": { ... }
}
```

Server loggt Trace-ID für Latenz-Analyse.
