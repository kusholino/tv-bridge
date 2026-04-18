"""
TV-Bridge Settings

Konfiguration via Environment-Variablen oder .env-Datei.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import secrets


class Settings(BaseSettings):
    """Anwendungseinstellungen"""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    server_version: str = "1.0.0"
    
    # Paths
    data_dir: str = "/var/lib/tvbridge"
    log_dir: str = "/var/log/tvbridge"
    webapp_dir: str = "./webapp"
    
    # Database
    db_path: str = "/var/lib/tvbridge/tvbridge.db"
    
    # HID Devices
    hid_mouse_device: str = "/dev/hidg0"
    hid_keyboard_device: str = "/dev/hidg1"
    
    # Pairing
    pairing_timeout_seconds: int = 120
    pairing_code_length: int = 6
    
    # Auth
    admin_token: Optional[str] = None
    token_hash_algorithm: str = "sha256"
    
    # Rate Limiting
    auth_rate_limit: int = 5  # pro Minute pro IP
    pairing_rate_limit: int = 10  # pro Minute pro IP
    input_rate_limit: int = 120  # Events pro Sekunde pro Client
    
    # WebSocket
    ws_ping_interval: int = 30  # Sekunden
    ws_ping_timeout: int = 60  # Sekunden
    ws_max_connections: int = 10
    
    # Input Processing
    input_queue_size: int = 100
    event_coalescing_window_ms: int = 16  # ~60 Hz
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json oder text
    
    # Security
    timestamp_max_age_seconds: int = 5
    timestamp_max_future_seconds: int = 1
    
    # Development
    debug: bool = False
    cors_enabled: bool = False
    
    model_config = SettingsConfigDict(
        env_prefix="TVBRIDGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Admin-Token generieren falls nicht gesetzt
        if not self.admin_token:
            self.admin_token = secrets.token_hex(32)
    
    @property
    def db_url(self) -> str:
        """SQLite Connection URL"""
        return f"sqlite:///{self.db_path}"


# Singleton-Instanz
settings = Settings()
