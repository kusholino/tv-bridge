"""
TV-Bridge Config Store

SQLite-basierte persistente Speicherung für Geräte, Profile,
Pairing-Sessions und Audit-Logs.
"""

import aiosqlite
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path
import logging

from .models import Device, DeviceProfile, PairingSession, AuditLogEntry, ProfileSettings
from .settings import settings

logger = logging.getLogger(__name__)


class ConfigStore:
    """Persistente Konfigurationsspeicherung"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.db_path
        self._ensure_db_dir()
    
    def _ensure_db_dir(self):
        """Stellt sicher, dass DB-Verzeichnis existiert"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialisiert Datenbank-Schema"""
        async with aiosqlite.connect(self.db_path) as db:
            # Devices-Tabelle
            await db.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT,
                    allowed INTEGER NOT NULL DEFAULT 1,
                    revoked_at TEXT,
                    notes TEXT
                )
            """)
            
            # Profiles-Tabelle
            await db.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    device_id TEXT NOT NULL,
                    profile_name TEXT NOT NULL,
                    settings_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (device_id, profile_name),
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
            """)
            
            # Pairing-Sessions-Tabelle
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pairing_sessions (
                    code TEXT PRIMARY KEY,
                    token TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0,
                    device_id TEXT,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL
                )
            """)
            
            # Audit-Log-Tabelle
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    device_id TEXT,
                    details_json TEXT,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE SET NULL
                )
            """)
            
            # Indizes
            await db.execute("CREATE INDEX IF NOT EXISTS idx_devices_allowed ON devices(allowed)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_pairing_expires ON pairing_sessions(expires_at)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
            
            await db.commit()
        
        logger.info(f"Database initialized: {self.db_path}")
    
    # ========================================================================
    # Device Management
    # ========================================================================
    
    async def create_device(self, device: Device) -> Device:
        """Erstellt neues Gerät"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO devices (id, name, token_hash, created_at, allowed)
                VALUES (?, ?, ?, ?, ?)
            """, (
                device.id,
                device.name,
                device.token_hash,
                device.created_at.isoformat(),
                1 if device.allowed else 0
            ))
            await db.commit()
        
        await self.audit_log("device_created", device.id, {"name": device.name})
        logger.info(f"Device created: {device.id} ({device.name})")
        return device
    
    async def get_device(self, device_id: str) -> Optional[Device]:
        """Holt Gerät nach ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM devices WHERE id = ?", (device_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Device(
                        id=row["id"],
                        name=row["name"],
                        token_hash=row["token_hash"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        last_seen_at=datetime.fromisoformat(row["last_seen_at"]) if row["last_seen_at"] else None,
                        allowed=bool(row["allowed"]),
                        revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
                        notes=row["notes"]
                    )
        return None
    
    async def get_device_by_token_hash(self, token_hash: str) -> Optional[Device]:
        """Holt Gerät nach Token-Hash"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM devices WHERE token_hash = ?", (token_hash,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Device(
                        id=row["id"],
                        name=row["name"],
                        token_hash=row["token_hash"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        last_seen_at=datetime.fromisoformat(row["last_seen_at"]) if row["last_seen_at"] else None,
                        allowed=bool(row["allowed"]),
                        revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
                        notes=row["notes"]
                    )
        return None
    
    async def list_devices(self, allowed_only: bool = False) -> List[Device]:
        """Listet alle Geräte"""
        query = "SELECT * FROM devices"
        params = []
        
        if allowed_only:
            query += " WHERE allowed = 1"
        
        query += " ORDER BY created_at DESC"
        
        devices = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    devices.append(Device(
                        id=row["id"],
                        name=row["name"],
                        token_hash=row["token_hash"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        last_seen_at=datetime.fromisoformat(row["last_seen_at"]) if row["last_seen_at"] else None,
                        allowed=bool(row["allowed"]),
                        revoked_at=datetime.fromisoformat(row["revoked_at"]) if row["revoked_at"] else None,
                        notes=row["notes"]
                    ))
        
        return devices
    
    async def update_device_last_seen(self, device_id: str):
        """Aktualisiert Last-Seen-Timestamp"""
        now = datetime.utcnow()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE devices SET last_seen_at = ? WHERE id = ?",
                (now.isoformat(), device_id)
            )
            await db.commit()
    
    async def revoke_device(self, device_id: str, reason: str = None) -> bool:
        """Widerruft Gerät"""
        now = datetime.utcnow()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE devices SET allowed = 0, revoked_at = ?, notes = ? WHERE id = ?",
                (now.isoformat(), reason, device_id)
            )
            await db.commit()
        
        await self.audit_log("device_revoked", device_id, {"reason": reason})
        logger.warning(f"Device revoked: {device_id} (reason: {reason})")
        return True
    
    async def allow_device(self, device_id: str) -> bool:
        """Erlaubt Gerät wieder"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE devices SET allowed = 1, revoked_at = NULL WHERE id = ?",
                (device_id,)
            )
            await db.commit()
        
        await self.audit_log("device_allowed", device_id)
        logger.info(f"Device allowed: {device_id}")
        return True
    
    async def update_device(self, device_id: str, name: str = None, notes: str = None) -> bool:
        """Aktualisiert Gerät"""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        
        if not updates:
            return False
        
        params.append(device_id)
        query = f"UPDATE devices SET {', '.join(updates)} WHERE id = ?"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, params)
            await db.commit()
        
        await self.audit_log("device_updated", device_id, {"name": name, "notes": notes})
        return True
    
    async def delete_device(self, device_id: str) -> bool:
        """Löscht Gerät komplett"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            await db.commit()
        
        await self.audit_log("device_deleted", device_id)
        logger.warning(f"Device deleted: {device_id}")
        return True
    
    # ========================================================================
    # Profile Management
    # ========================================================================
    
    async def get_profile(self, device_id: str, profile_name: str = "default") -> Optional[DeviceProfile]:
        """Holt Profil"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM profiles WHERE device_id = ? AND profile_name = ?",
                (device_id, profile_name)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    settings_dict = json.loads(row["settings_json"])
                    return DeviceProfile(
                        device_id=row["device_id"],
                        profile_name=row["profile_name"],
                        settings=ProfileSettings(**settings_dict),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"])
                    )
        
        # Fallback: Default-Profil erstellen
        if profile_name == "default":
            return await self.create_profile(device_id, profile_name, ProfileSettings())
        
        return None
    
    async def create_profile(self, device_id: str, profile_name: str, settings: ProfileSettings) -> DeviceProfile:
        """Erstellt Profil"""
        now = datetime.utcnow()
        profile = DeviceProfile(
            device_id=device_id,
            profile_name=profile_name,
            settings=settings,
            created_at=now,
            updated_at=now
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO profiles (device_id, profile_name, settings_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                device_id,
                profile_name,
                json.dumps(settings.model_dump()),
                now.isoformat(),
                now.isoformat()
            ))
            await db.commit()
        
        return profile
    
    async def update_profile(self, device_id: str, profile_name: str, settings: ProfileSettings) -> DeviceProfile:
        """Aktualisiert Profil"""
        now = datetime.utcnow()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE profiles
                SET settings_json = ?, updated_at = ?
                WHERE device_id = ? AND profile_name = ?
            """, (
                json.dumps(settings.model_dump()),
                now.isoformat(),
                device_id,
                profile_name
            ))
            await db.commit()
        
        return await self.get_profile(device_id, profile_name)
    
    # ========================================================================
    # Pairing Management
    # ========================================================================
    
    async def create_pairing_session(self, code: str, token: str, timeout_seconds: int) -> PairingSession:
        """Erstellt Pairing-Session"""
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=timeout_seconds)
        
        session = PairingSession(
            code=code,
            token=token,
            created_at=now,
            expires_at=expires_at,
            used=False
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO pairing_sessions (code, token, created_at, expires_at, used)
                VALUES (?, ?, ?, ?, 0)
            """, (code, token, now.isoformat(), expires_at.isoformat()))
            await db.commit()
        
        await self.audit_log("pairing_session_created", None, {"code": code})
        logger.info(f"Pairing session created: {code}")
        return session
    
    async def get_pairing_session(self, code: str) -> Optional[PairingSession]:
        """Holt Pairing-Session"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM pairing_sessions WHERE code = ?", (code,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return PairingSession(
                        code=row["code"],
                        token=row["token"],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        expires_at=datetime.fromisoformat(row["expires_at"]),
                        used=bool(row["used"]),
                        device_id=row["device_id"]
                    )
        return None
    
    async def mark_pairing_used(self, code: str, device_id: str):
        """Markiert Pairing als verwendet"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE pairing_sessions SET used = 1, device_id = ? WHERE code = ?",
                (device_id, code)
            )
            await db.commit()
    
    async def cleanup_expired_pairing_sessions(self):
        """Löscht abgelaufene Pairing-Sessions"""
        now = datetime.utcnow()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM pairing_sessions WHERE expires_at < ?",
                (now.isoformat(),)
            )
            await db.commit()
    
    # ========================================================================
    # Audit Log
    # ========================================================================
    
    async def audit_log(self, event_type: str, device_id: str = None, details: dict = None):
        """Schreibt Audit-Log-Eintrag"""
        now = datetime.utcnow()
        details_json = json.dumps(details) if details else None
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO audit_log (timestamp, event_type, device_id, details_json)
                VALUES (?, ?, ?, ?)
            """, (now.isoformat(), event_type, device_id, details_json))
            await db.commit()
    
    async def get_audit_log(self, limit: int = 100, device_id: str = None) -> List[AuditLogEntry]:
        """Holt Audit-Log"""
        query = "SELECT * FROM audit_log"
        params = []
        
        if device_id:
            query += " WHERE device_id = ?"
            params.append(device_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        entries = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    details = json.loads(row["details_json"]) if row["details_json"] else None
                    entries.append(AuditLogEntry(
                        id=row["id"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        event_type=row["event_type"],
                        device_id=row["device_id"],
                        details=details
                    ))
        
        return entries
    
    # ========================================================================
    # Utilities
    # ========================================================================
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Erstellt SHA-256-Hash von Token"""
        return hashlib.sha256(token.encode()).hexdigest()


# Singleton-Instanz
config_store = ConfigStore()
