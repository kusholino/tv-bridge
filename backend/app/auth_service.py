"""
TV-Bridge Auth Service

Authentifizierung und Autorisierung von Clients.
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from .models import Device
from .config_store import config_store
from .settings import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Authentifizierungs-Service"""
    
    def __init__(self):
        # Rate Limiting für Auth-Versuche
        self._auth_attempts: dict[str, list[datetime]] = defaultdict(list)
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Prüft Auth-Rate-Limit"""
        now = datetime.utcnow()
        window = timedelta(minutes=1)
        
        # Alte Einträge entfernen
        self._auth_attempts[client_ip] = [
            ts for ts in self._auth_attempts[client_ip]
            if ts > now - window
        ]
        
        # Limit prüfen
        if len(self._auth_attempts[client_ip]) >= settings.auth_rate_limit:
            logger.warning(f"Auth rate limit exceeded for IP: {client_ip}")
            return False
        
        self._auth_attempts[client_ip].append(now)
        return True
    
    async def authenticate(self, device_token: str, client_ip: str) -> tuple[bool, Optional[Device], Optional[str]]:
        """
        Authentifiziert Device via Token.
        
        Returns:
            (success, device, error_reason)
        """
        # Rate Limiting
        if not self._check_rate_limit(client_ip):
            return False, None, "rate_limited"
        
        # Token hashen
        token_hash = config_store.hash_token(device_token)
        
        # Device suchen
        device = await config_store.get_device_by_token_hash(token_hash)
        
        if not device:
            logger.warning(f"Authentication failed: Unknown token from {client_ip}")
            await config_store.audit_log("auth_failed", None, {
                "reason": "invalid_token",
                "client_ip": client_ip
            })
            return False, None, "invalid_token"
        
        # Revocation prüfen
        if not device.allowed:
            logger.warning(f"Authentication failed: Revoked device {device.id} from {client_ip}")
            await config_store.audit_log("auth_failed", device.id, {
                "reason": "device_revoked",
                "client_ip": client_ip
            })
            return False, device, "device_revoked"
        
        # Erfolg
        logger.info(f"Authentication successful: {device.id} ({device.name}) from {client_ip}")
        
        # Last-Seen aktualisieren
        await config_store.update_device_last_seen(device.id)
        
        await config_store.audit_log("auth_success", device.id, {
            "client_ip": client_ip
        })
        
        return True, device, None
    
    async def validate_admin_token(self, token: str) -> bool:
        """Validiert Admin-Token"""
        if not settings.admin_token:
            logger.warning("Admin token not configured")
            return False
        
        return token == settings.admin_token


# Singleton-Instanz
auth_service = AuthService()
