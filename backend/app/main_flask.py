"""
TV-Bridge Flask Application

Ultra-leichte REST API für Pi Zero 2 W.
Kein Pydantic, keine WebSockets, nur einfache REST endpoints.
"""

import os
import logging
import sqlite3
import hashlib
import secrets
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from threading import Thread, Lock

# Settings (ohne Pydantic)
class Settings:
    def __init__(self):
        self.db_path = os.getenv("TVBRIDGE_DB_PATH", "/var/lib/tvbridge/tvbridge.db")
        self.hid_mouse_device = os.getenv("TVBRIDGE_HID_MOUSE_DEVICE", "/dev/hidg0")
        self.hid_keyboard_device = os.getenv("TVBRIDGE_HID_KEYBOARD_DEVICE", "/dev/hidg1")
        self.host = os.getenv("TVBRIDGE_HOST", "0.0.0.0")
        self.port = int(os.getenv("TVBRIDGE_PORT", "8080"))
        self.admin_token = os.getenv("TVBRIDGE_ADMIN_TOKEN") or secrets.token_hex(32)
        self.pairing_timeout = int(os.getenv("TVBRIDGE_PAIRING_TIMEOUT", "120"))

settings = Settings()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Global state
hid_mouse = None
hid_keyboard = None
db_lock = Lock()
pairing_sessions = {}
active_devices = {}  # device_id -> last_seen timestamp

# === Database Helper ===

def get_db():
    """Get database connection."""
    db = sqlite3.connect(settings.db_path)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database schema."""
    db = get_db()
    
    # Devices table
    db.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_seen_at TEXT,
            allowed INTEGER DEFAULT 1,
            revoked_at TEXT,
            notes TEXT
        )
    """)
    
    # Profiles table
    db.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            device_id TEXT NOT NULL,
            profile_name TEXT NOT NULL,
            settings_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (device_id, profile_name),
            FOREIGN KEY (device_id) REFERENCES devices(id)
        )
    """)
    
    # Audit log table
    db.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            device_id TEXT,
            details TEXT
        )
    """)
    
    db.commit()
    db.close()
    logger.info("Database initialized")

def hash_token(token: str) -> str:
    """Hash token with SHA-256."""
    return hashlib.sha256(token.encode()).hexdigest()

# === HID Service ===

def init_hid():
    """Initialize HID devices."""
    global hid_mouse, hid_keyboard
    
    import os
    import fcntl
    
    try:
        # Open in non-blocking mode
        fd = os.open(settings.hid_mouse_device, os.O_RDWR | os.O_NONBLOCK)
        hid_mouse = os.fdopen(fd, 'rb+', buffering=0)
        logger.info(f"HID Mouse opened (non-blocking): {settings.hid_mouse_device}")
    except Exception as e:
        logger.error(f"Failed to open HID mouse: {e}")
    
    try:
        # Open in non-blocking mode
        fd = os.open(settings.hid_keyboard_device, os.O_RDWR | os.O_NONBLOCK)
        hid_keyboard = os.fdopen(fd, 'rb+', buffering=0)
        logger.info(f"HID Keyboard opened (non-blocking): {settings.hid_keyboard_device}")
    except Exception as e:
        logger.error(f"Failed to open HID keyboard: {e}")

def send_mouse_report(buttons: int, x: int, y: int):
    """Send HID mouse report (3 bytes)."""
    if not hid_mouse:
        return False
    
    # Clamp values
    x = max(-127, min(127, x))
    y = max(-127, min(127, y))
    
    # Convert to unsigned bytes
    x_byte = x & 0xFF
    y_byte = y & 0xFF
    
    report = bytes([buttons, x_byte, y_byte])
    
    try:
        hid_mouse.write(report)
        hid_mouse.flush()
        return True
    except BlockingIOError:
        # No USB host connected, data would block - this is OK
        logger.debug("HID mouse write would block (no USB host connected)")
        return True  # Return True because it's not really an error
    except Exception as e:
        logger.error(f"Failed to write mouse report: {e}")
        return False

def send_keyboard_report(modifier: int, keys: list):
    """Send HID keyboard report (8 bytes)."""
    if not hid_keyboard:
        return False
    
    # Ensure we have exactly 6 key codes
    keys = (keys + [0, 0, 0, 0, 0, 0])[:6]
    
    report = bytes([modifier, 0] + keys)
    
    try:
        hid_keyboard.write(report)
        hid_keyboard.flush()
        return True
    except BlockingIOError:
        # No USB host connected, data would block - this is OK
        logger.debug("HID keyboard write would block (no USB host connected)")
        return True  # Return True because it's not really an error
    except Exception as e:
        logger.error(f"Failed to write keyboard report: {e}")
        return False

# HID Key Codes
HID_KEY_CODES = {
    'Enter': 0x28, 'Escape': 0x29, 'Backspace': 0x2A, 'Tab': 0x2B, 'Space': 0x2C,
    'ArrowUp': 0x52, 'ArrowDown': 0x51, 'ArrowLeft': 0x50, 'ArrowRight': 0x4F,
    'Home': 0x4A, 'End': 0x4D, 'PageUp': 0x4B, 'PageDown': 0x4E,
}

# === Authentication ===

def verify_token(token: str) -> dict:
    """Verify device token."""
    if not token:
        return None
    
    token_hash = hash_token(token)
    
    with db_lock:
        db = get_db()
        device = db.execute(
            "SELECT * FROM devices WHERE token_hash = ? AND allowed = 1",
            (token_hash,)
        ).fetchone()
        db.close()
    
    if device:
        return dict(device)
    return None

def require_auth(f):
    """Decorator for endpoints requiring device authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization'}), 401
        
        token = auth_header.replace('Bearer ', '')
        device = verify_token(token)
        
        if not device:
            return jsonify({'error': 'Invalid or revoked token'}), 403
        
        # Update last_seen
        with db_lock:
            db = get_db()
            db.execute(
                "UPDATE devices SET last_seen_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), device['id'])
            )
            db.commit()
            db.close()
        
        # Add device to request context
        request.device = device
        
        return f(*args, **kwargs)
    
    return decorated

def require_admin(f):
    """Decorator for admin endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing authorization'}), 401
        
        token = auth_header.replace('Bearer ', '')
        
        if token != settings.admin_token:
            return jsonify({'error': 'Invalid admin token'}), 403
        
        return f(*args, **kwargs)
    
    return decorated

# === Input Endpoints ===

@app.route('/input/move', methods=['POST'])
@require_auth
def input_move():
    """Handle mouse move input."""
    data = request.json
    dx = int(data.get('dx', 0))
    dy = int(data.get('dy', 0))
    
    if send_mouse_report(0, dx, dy):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'HID write failed'}), 500

@app.route('/input/click', methods=['POST'])
@require_auth
def input_click():
    """Handle mouse click input."""
    data = request.json
    button = data.get('button', 'left')
    action = data.get('action', 'click')
    
    button_map = {'left': 1, 'right': 2, 'middle': 4}
    button_code = button_map.get(button, 1)
    
    if action == 'press':
        send_mouse_report(button_code, 0, 0)
    elif action == 'release':
        send_mouse_report(0, 0, 0)
    elif action == 'click':
        send_mouse_report(button_code, 0, 0)
        time.sleep(0.05)
        send_mouse_report(0, 0, 0)
    
    return jsonify({'success': True})

@app.route('/input/scroll', methods=['POST'])
@require_auth
def input_scroll():
    """Handle scroll input (using arrow keys)."""
    data = request.json
    vertical = int(data.get('vertical', 0))
    
    # Use arrow keys for scrolling
    if vertical > 0:
        send_keyboard_report(0, [HID_KEY_CODES['ArrowUp']])
        time.sleep(0.05)
        send_keyboard_report(0, [])
    elif vertical < 0:
        send_keyboard_report(0, [HID_KEY_CODES['ArrowDown']])
        time.sleep(0.05)
        send_keyboard_report(0, [])
    
    return jsonify({'success': True})

@app.route('/input/key', methods=['POST'])
@require_auth
def input_key():
    """Handle keyboard input."""
    data = request.json
    key = data.get('key', '')
    action = data.get('action', 'press')
    
    key_code = HID_KEY_CODES.get(key, 0)
    
    if not key_code:
        return jsonify({'error': 'Unknown key'}), 400
    
    if action == 'press':
        send_keyboard_report(0, [key_code])
    elif action == 'release':
        send_keyboard_report(0, [])
    
    return jsonify({'success': True})

@app.route('/input/text', methods=['POST'])
@require_auth
def input_text():
    """Handle text input."""
    data = request.json
    text = data.get('text', '')
    
    # This would need full text-to-HID implementation
    # For now, just accept it
    
    return jsonify({'success': True, 'message': 'Text input not yet implemented'})

# === Pairing Endpoints ===

@app.route('/admin/pairing/start', methods=['POST'])
@require_admin
def start_pairing():
    """Start pairing mode."""
    code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    token = secrets.token_hex(32)
    expires_at = time.time() + settings.pairing_timeout
    
    pairing_sessions[code] = {
        'token': token,
        'expires_at': expires_at
    }
    
    logger.info(f"Pairing started: code={code}")
    
    return jsonify({
        'success': True,
        'pairing_code': code,
        'device_token': token,
        'expires_in': settings.pairing_timeout
    })

@app.route('/admin/pairing/status', methods=['GET'])
def pairing_status():
    """Get pairing status (public)."""
    # Clean expired sessions
    now = time.time()
    expired = [code for code, sess in pairing_sessions.items() if sess['expires_at'] < now]
    for code in expired:
        del pairing_sessions[code]
    
    if pairing_sessions:
        return jsonify({'pairing_enabled': True})
    else:
        return jsonify({'pairing_enabled': False})

@app.route('/pair', methods=['POST'])
def pair_device():
    """Public pairing endpoint."""
    data = request.json
    code = data.get('pairing_code', '').strip()
    name = data.get('device_name', '').strip()
    
    if not code or not name:
        return jsonify({'success': False, 'message': 'Missing pairing_code or device_name'}), 400
    
    session = pairing_sessions.get(code)
    
    if not session:
        return jsonify({'success': False, 'message': 'Invalid or expired pairing code'}), 400
    
    if session['expires_at'] < time.time():
        del pairing_sessions[code]
        return jsonify({'success': False, 'message': 'Pairing code expired'}), 400
    
    # Create device
    device_id = secrets.token_hex(16)
    token = session['token']
    token_hash = hash_token(token)
    
    with db_lock:
        db = get_db()
        db.execute(
            "INSERT INTO devices (id, name, token_hash, created_at, allowed) VALUES (?, ?, ?, ?, 1)",
            (device_id, name, token_hash, datetime.utcnow().isoformat())
        )
        db.commit()
        db.close()
    
    # Remove session
    del pairing_sessions[code]
    
    logger.info(f"Device paired: {name} ({device_id})")
    
    return jsonify({
        'success': True,
        'device_id': device_id,
        'device_name': name,
        'device_token': token
    })

# === Admin Endpoints ===

@app.route('/admin/devices', methods=['GET'])
@require_admin
def list_devices():
    """List all devices."""
    with db_lock:
        db = get_db()
        devices = db.execute("SELECT * FROM devices ORDER BY created_at DESC").fetchall()
        db.close()
    
    return jsonify({
        'devices': [dict(d) for d in devices]
    })

@app.route('/admin/devices/<device_id>/revoke', methods=['POST'])
@require_admin
def revoke_device(device_id):
    """Revoke a device."""
    with db_lock:
        db = get_db()
        db.execute(
            "UPDATE devices SET allowed = 0, revoked_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), device_id)
        )
        db.commit()
        db.close()
    
    logger.info(f"Device revoked: {device_id}")
    
    return jsonify({'success': True, 'message': 'Device revoked'})

@app.route('/admin/health', methods=['GET'])
@require_admin
def health():
    """Health check."""
    return jsonify({
        'status': 'ok',
        'hid_mouse': hid_mouse is not None,
        'hid_keyboard': hid_keyboard is not None,
        'version': '2.0.0-flask'
    })

# === Static Files (Web App) ===

@app.route('/')
def index():
    """Serve web app."""
    webapp_dir = Path(__file__).parent.parent.parent / "webapp"
    return send_from_directory(webapp_dir, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """Serve static files."""
    webapp_dir = Path(__file__).parent.parent.parent / "webapp"
    return send_from_directory(webapp_dir, path)

# === Startup ===

def startup():
    """Initialize services."""
    logger.info("Starting TV-Bridge Flask backend...")
    
    # Ensure data directory exists
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize database
    init_db()
    
    # Initialize HID devices
    init_hid()
    
    logger.info(f"Admin token: {settings.admin_token}")
    logger.info("TV-Bridge ready!")

if __name__ == '__main__':
    startup()
    app.run(host=settings.host, port=settings.port, debug=False)
