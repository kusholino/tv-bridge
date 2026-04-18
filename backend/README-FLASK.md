# TV-Bridge Flask Version

## Ultra-leichte REST API statt WebSockets

Diese Version nutzt **Flask statt FastAPI** und **REST API statt WebSockets**:

✅ **Keine Pydantic** - keine Kompilierung nötig  
✅ **Installation in 1-2 Minuten** statt 30+  
✅ **Leichter auf Pi Zero 2 W** - weniger RAM  
✅ **Flutter-freundlich** - REST API ist einfacher als WebSockets  

## Installation auf Raspberry Pi

```bash
# 1. Repository klonen/pullen
cd /opt/tvbridge
git pull

# 2. Flask-Installer ausführen
cd backend/scripts
chmod +x install-flask.sh
sudo ./install-flask.sh

# 3. Status prüfen
systemctl status tvbridge-backend
curl http://localhost:8080

# Fertig! 🎉
```

## Web-App anpassen

Die Web-App muss die REST-Versionen der Skripte nutzen:

In `webapp/index.html` ersetze:
```html
<!-- ALT (WebSocket): -->
<script src="/scripts/ws-client.js"></script>
<script src="/scripts/touchpad.js"></script>
<script src="/scripts/keyboard.js"></script>
<script src="/scripts/pairing.js"></script>
<script src="/scripts/main.js"></script>

<!-- NEU (REST): -->
<script src="/scripts/rest-client.js"></script>
<script src="/scripts/touchpad-rest.js"></script>
<script src="/scripts/keyboard-rest.js"></script>
<script src="/scripts/pairing-rest.js"></script>
<script src="/scripts/main-rest.js"></script>
```

Ändere auch `wsClient` zu `restClient` in allen Skripten.

## API Endpoints

### Input
- `POST /input/move` - dx, dy
- `POST /input/click` - button, action
- `POST /input/scroll` - vertical, horizontal  
- `POST /input/key` - key, action
- `POST /input/text` - text

### Pairing
- `POST /pair` - pairing_code, device_name
- `GET /admin/pairing/status`
- `POST /admin/pairing/start` (Admin)

### Admin
- `GET /admin/devices` (Admin)
- `POST /admin/devices/{id}/revoke` (Admin)
- `GET /admin/health` (Admin)

## Auth

Alle Input-Endpoints brauchen:
```http
Authorization: Bearer <device_token>
```

## Vorteile gegenüber WebSocket-Version

1. **Installation**: 1-2 Min statt 30+ Min
2. **Dependencies**: 3 Pakete statt 7+
3. **RAM**: ~50 MB statt ~100 MB
4. **Komplexität**: Viel einfacher zu debuggen
5. **Flutter**: HTTP ist simpler als WebSocket
6. **Firewall**: Funktioniert überall

## Nachteile

1. **Latenz**: ~20ms statt ~10ms (immer noch okay!)
2. **Keine Push-Notifications**: Server kann nicht aktiv Nachrichten senden
3. **Mehr Requests**: Jeder Input = 1 HTTP Request

## Für TV-Remote völlig ausreichend!

Die leicht höhere Latenz (20ms vs 10ms) ist bei einer TV-Fernbedienung **nicht spürbar**.

Dafür: Viel einfacher, schneller installiert, weniger Probleme! 🚀
