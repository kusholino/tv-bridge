# TV-Bridge Backend

Python-Backend für TV-Bridge System.

## Struktur

```
app/
├── main.py              # FastAPI App
├── models.py            # Pydantic Models
├── settings.py          # Konfiguration
├── config_store.py      # SQLite-Datenbank
├── hid_service.py       # USB HID Interface
├── input_engine.py      # Input-Processing
├── auth_service.py      # Authentifizierung
├── pairing_service.py   # Pairing-Logik
├── ws_gateway.py        # WebSocket-Server
└── admin_api.py         # Admin REST API
```

## Installation

Siehe [Deployment Guide](../docs/deployment.md).

## Development

```bash
# Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# Run (ohne HID-Devices für Testing)
export TVBRIDGE_HID_MOUSE_DEVICE=/tmp/hidg0
export TVBRIDGE_HID_KEYBOARD_DEVICE=/tmp/hidg1
touch /tmp/hidg0 /tmp/hidg1

python -m app.main
```

## Testing

```bash
# Unit Tests
pytest tests/

# WebSocket Test
wscat -c ws://localhost:8080/ws
```
