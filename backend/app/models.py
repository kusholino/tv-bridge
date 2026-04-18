"""
TV-Bridge Pydantic Models

Definiert alle Datenmodelle für WebSocket-Nachrichten, 
Datenbankentitäten und API-Requests/Responses.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# WebSocket Message Models
# ============================================================================

class MessageType(str, Enum):
    """WebSocket-Nachrichtentypen"""
    # Server -> Client
    HELLO = "hello"
    AUTH_OK = "auth_ok"
    AUTH_FAILED = "auth_failed"
    PING = "ping"
    ERROR = "error"
    PROFILE_DATA = "profile_data"
    DEVICE_REVOKED = "device_revoked"
    
    # Client -> Server
    AUTH = "auth"
    PONG = "pong"
    INPUT_MOVE = "input_move"
    INPUT_CLICK = "input_click"
    INPUT_SCROLL = "input_scroll"
    INPUT_KEY = "input_key"
    TEXT_COMMIT = "text_commit"
    PROFILE_GET = "profile_get"
    PROFILE_SET = "profile_set"


class WSMessage(BaseModel):
    """Basis WebSocket-Nachricht"""
    type: MessageType
    protocol_version: str = "1.0"
    timestamp: int  # Unix timestamp in ms
    payload: Dict[str, Any] = Field(default_factory=dict)


# Client -> Server Messages

class AuthPayload(BaseModel):
    """Auth-Payload"""
    device_token: str
    debug: bool = False


class InputMovePayload(BaseModel):
    """Mouse Move Payload"""
    dx: float
    dy: float


class InputClickPayload(BaseModel):
    """Mouse Click Payload"""
    button: Literal["left", "right", "middle"]
    action: Literal["down", "up", "click"]


class InputScrollPayload(BaseModel):
    """Scroll Payload"""
    vertical: float = 0.0
    horizontal: float = 0.0


class InputKeyPayload(BaseModel):
    """Key Press Payload"""
    key: str
    action: Literal["press", "release"]


class TextCommitPayload(BaseModel):
    """Text Input Payload"""
    text: str = Field(max_length=1000)


class ProfileGetPayload(BaseModel):
    """Profile Get Request"""
    profile_name: str = "default"


class ProfileSetPayload(BaseModel):
    """Profile Set Request"""
    profile_name: str
    settings: "ProfileSettings"


# Server -> Client Messages

class HelloPayload(BaseModel):
    """Hello Payload"""
    server_version: str
    capabilities: list[str] = ["mouse", "keyboard", "scroll"]
    requires_auth: bool = True


class AuthOkPayload(BaseModel):
    """Auth Success Payload"""
    device_id: str
    device_name: str
    session_id: str


class AuthFailedPayload(BaseModel):
    """Auth Failed Payload"""
    reason: Literal["invalid_token", "device_revoked", "rate_limited", "pairing_required"]
    message: str


class ErrorPayload(BaseModel):
    """Error Payload"""
    code: str
    message: str
    details: Optional[str] = None


class ProfileDataPayload(BaseModel):
    """Profile Data Payload"""
    profile_name: str
    settings: "ProfileSettings"


class DeviceRevokedPayload(BaseModel):
    """Device Revoked Payload"""
    reason: str
    disconnect_in_seconds: int = 5


# ============================================================================
# Profile Models
# ============================================================================

class ProfileSettings(BaseModel):
    """Profil-Einstellungen"""
    pointer_sensitivity: float = Field(default=1.0, ge=0.1, le=5.0)
    pointer_acceleration: bool = False
    scroll_sensitivity: float = Field(default=1.0, ge=0.1, le=5.0)
    natural_scroll: bool = False
    tap_to_click: bool = True
    handedness: Optional[Literal["left", "right"]] = "right"


# ============================================================================
# Database Models
# ============================================================================

class Device(BaseModel):
    """Geräte-Modell"""
    id: str  # device_<uuid>
    name: str
    token_hash: str  # SHA-256 hash
    created_at: datetime
    last_seen_at: Optional[datetime] = None
    allowed: bool = True
    revoked_at: Optional[datetime] = None
    notes: Optional[str] = None


class DeviceProfile(BaseModel):
    """Geräte-Profil"""
    device_id: str
    profile_name: str
    settings: ProfileSettings
    created_at: datetime
    updated_at: datetime


class PairingSession(BaseModel):
    """Pairing-Session"""
    code: str  # 6-stellig
    token: str  # Einmal-Token
    created_at: datetime
    expires_at: datetime
    used: bool = False
    device_id: Optional[str] = None


class AuditLogEntry(BaseModel):
    """Audit-Log-Eintrag"""
    id: int
    timestamp: datetime
    event_type: str
    device_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# API Models (REST)
# ============================================================================

class PairingStartRequest(BaseModel):
    """Pairing-Start-Request"""
    timeout_seconds: int = Field(default=120, ge=30, le=600)


class PairingStartResponse(BaseModel):
    """Pairing-Start-Response"""
    success: bool
    pairing_code: str
    expires_in_seconds: int
    qr_data: Optional[str] = None


class PairingStatusResponse(BaseModel):
    """Pairing-Status-Response"""
    pairing_enabled: bool
    expires_in_seconds: Optional[int] = None


class PairRequest(BaseModel):
    """Pair-Request (vom Client)"""
    pairing_code: str
    device_name: str = Field(max_length=100)


class PairResponse(BaseModel):
    """Pair-Response"""
    success: bool
    device_id: Optional[str] = None
    device_token: Optional[str] = None
    device_name: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None


class DeviceListResponse(BaseModel):
    """Device-List-Response"""
    devices: list[Device]


class DeviceRevokeRequest(BaseModel):
    """Device-Revoke-Request"""
    reason: Optional[str] = None


class DeviceUpdateRequest(BaseModel):
    """Device-Update-Request"""
    name: Optional[str] = None
    notes: Optional[str] = None


class HealthResponse(BaseModel):
    """Health-Check-Response"""
    status: Literal["healthy", "degraded", "unhealthy"]
    hid_mouse: Literal["ok", "error"]
    hid_keyboard: Literal["ok", "error"]
    database: Literal["ok", "error"]
    active_connections: int
    uptime_seconds: int


# ============================================================================
# Internal Models
# ============================================================================

class HIDMouseReport(BaseModel):
    """HID Mouse Report (3 Bytes)"""
    buttons: int = 0  # Bit 0=Left, 1=Right, 2=Middle
    dx: int = 0  # -127 to 127
    dy: int = 0  # -127 to 127
    
    def to_bytes(self) -> bytes:
        """Konvertiert zu 3-Byte HID Report"""
        # Clamp values
        dx = max(-127, min(127, self.dx))
        dy = max(-127, min(127, self.dy))
        
        # Convert to unsigned bytes
        dx_byte = dx & 0xFF
        dy_byte = dy & 0xFF
        
        return bytes([self.buttons, dx_byte, dy_byte])


class HIDKeyboardReport(BaseModel):
    """HID Keyboard Report (8 Bytes)"""
    modifier: int = 0  # Bit-Mask (Ctrl, Shift, Alt, GUI)
    reserved: int = 0
    keys: list[int] = Field(default_factory=lambda: [0, 0, 0, 0, 0, 0])  # 6 Keys
    
    def to_bytes(self) -> bytes:
        """Konvertiert zu 8-Byte HID Report"""
        keys_padded = (self.keys + [0] * 6)[:6]
        return bytes([self.modifier, self.reserved] + keys_padded)


class SessionState(str, Enum):
    """WebSocket-Session-Status"""
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    DISCONNECTED = "disconnected"


class ClientSession(BaseModel):
    """Client-Session-State"""
    session_id: str
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    state: SessionState = SessionState.CONNECTED
    connected_at: datetime
    last_seen: datetime
    debug: bool = False


# Forward references updaten
ProfileSetPayload.model_rebuild()
ProfileDataPayload.model_rebuild()
