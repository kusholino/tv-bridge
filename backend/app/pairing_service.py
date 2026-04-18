"""
TV-Bridge Pairing Service

Verwaltet Pairing-Prozess für neue Geräte.
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from .models import Device, PairingSession
from .config_store import config_store
from .settings import settings

logger = logging.getLogger(__name__)


class PairingService:
    """Pairing-Service"""
    
    def __init__(self):
        self._pairing_active = False
        self._current_session: Optional[PairingSession] = None
    
    def is_pairing_active(self) -> bool:
        """Prüft ob Pairing aktiv ist"""
        if not self._pairing_active or not self._current_session:
            return False
        
        # Ablauf prüfen
        if datetime.utcnow() > self._current_session.expires_at:
            self._pairing_active = False
            self._current_session = None
            return False
        
        return True
    
    def get_pairing_status(self) -> tuple[bool, Optional[int]]:
        """
        Gibt Pairing-Status zurück.
        
        Returns:
            (pairing_active, expires_in_seconds)
        """
        if not self.is_pairing_active():
            return False, None
        
        expires_in = (self._current_session.expires_at - datetime.utcnow()).total_seconds()
        return True, int(expires_in)
    
    async def start_pairing(self, timeout_seconds: int = None) -> tuple[str, str]:
        """
        Startet Pairing-Modus.
        
        Returns:
            (pairing_code, pairing_token)
        """
        timeout = timeout_seconds or settings.pairing_timeout_seconds
        
        # Pairing-Code generieren (6-stellig numerisch)
        pairing_code = ''.join(
            secrets.choice('0123456789')
            for _ in range(settings.pairing_code_length)
        )
        
        # Einmal-Token generieren
        pairing_token = secrets.token_urlsafe(32)
        
        # Session in DB speichern
        session = await config_store.create_pairing_session(
            code=pairing_code,
            token=pairing_token,
            timeout_seconds=timeout
        )
        
        self._pairing_active = True
        self._current_session = session
        
        logger.info(f"Pairing mode started: code={pairing_code}, expires in {timeout}s")
        
        return pairing_code, pairing_token
    
    async def stop_pairing(self):
        """Stoppt Pairing-Modus"""
        self._pairing_active = False
        self._current_session = None
        logger.info("Pairing mode stopped")
    
    async def pair_device(self, pairing_code: str, device_name: str) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Pairt neues Gerät.
        
        Args:
            pairing_code: Pairing-Code vom Admin
            device_name: Name des Geräts
        
        Returns:
            (success, device_id, device_token, error_message)
        """
        # Cleanup alte Sessions
        await config_store.cleanup_expired_pairing_sessions()
        
        # Session holen
        session = await config_store.get_pairing_session(pairing_code)
        
        if not session:
            logger.warning(f"Pairing failed: Invalid code {pairing_code}")
            return False, None, None, "Invalid or expired pairing code"
        
        # Ablauf prüfen
        if datetime.utcnow() > session.expires_at:
            logger.warning(f"Pairing failed: Expired code {pairing_code}")
            return False, None, None, "Pairing code expired"
        
        # Bereits verwendet?
        if session.used:
            logger.warning(f"Pairing failed: Code already used {pairing_code}")
            return False, None, None, "Pairing code already used"
        
        # Device erstellen
        device_id = f"device_{uuid.uuid4()}"
        device_token = f"{device_id}_{secrets.token_urlsafe(32)}"
        token_hash = config_store.hash_token(device_token)
        
        device = Device(
            id=device_id,
            name=device_name,
            token_hash=token_hash,
            created_at=datetime.utcnow(),
            allowed=True
        )
        
        await config_store.create_device(device)
        
        # Session als verwendet markieren
        await config_store.mark_pairing_used(pairing_code, device_id)
        
        # Pairing-Modus beenden (Einmal-Pairing pro Code)
        await self.stop_pairing()
        
        logger.info(f"Device paired successfully: {device_id} ({device_name})")
        
        return True, device_id, device_token, None


# Singleton-Instanz
pairing_service = PairingService()
