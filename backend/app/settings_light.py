"""
TV-Bridge Settings (Light Version - ohne Pydantic)

Konfiguration via Environment-Variablen.
"""

import os
import secrets
from pathlib import Path


class Settings:
    """Application settings (ohne Pydantic)."""
    
    def __init__(self):
        # Datenbank
        self.db_path = os.getenv("TVBRIDGE_DB_PATH", "/var/lib/tvbridge/tvbridge.db")
        
        # HID Devices
        self.hid_mouse_device = os.getenv("TVBRIDGE_HID_MOUSE_DEVICE", "/dev/hidg0")
        self.hid_keyboard_device = os.getenv("TVBRIDGE_HID_KEYBOARD_DEVICE", "/dev/hidg1")
        
        # Server
        self.host = os.getenv("TVBRIDGE_HOST", "0.0.0.0")
        self.port = int(os.getenv("TVBRIDGE_PORT", "8080"))
        
        # Security
        self.admin_token = os.getenv("TVBRIDGE_ADMIN_TOKEN") or secrets.token_hex(32)
        self.pairing_timeout = int(os.getenv("TVBRIDGE_PAIRING_TIMEOUT", "120"))
        
        # Rate Limiting
        self.auth_rate_limit = int(os.getenv("TVBRIDGE_AUTH_RATE_LIMIT", "5"))
        self.input_rate_limit = int(os.getenv("TVBRIDGE_INPUT_RATE_LIMIT", "120"))
        
        # WebSocket
        self.ws_ping_interval = int(os.getenv("TVBRIDGE_WS_PING_INTERVAL", "30"))
        self.ws_ping_timeout = int(os.getenv("TVBRIDGE_WS_PING_TIMEOUT", "60"))
        
        # Logging
        self.log_level = os.getenv("TVBRIDGE_LOG_LEVEL", "INFO")
        
        # CORS (optional)
        cors_origins = os.getenv("TVBRIDGE_CORS_ORIGINS", "")
        self.cors_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]


# Singleton
settings = Settings()
