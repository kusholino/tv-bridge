"""
TV-Bridge Models (Pydantic-Free Version)

Verwendet Python Dataclasses statt Pydantic.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


# === WebSocket Message Models ===

@dataclass
class WSMessage:
    """Base WebSocket message."""
    type: str
    timestamp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HelloMessage:
    """Server hello message."""
    type: str = "hello"
    version: str = "1.0"
    server: str = "tv-bridge"
    timestamp: int = 0


@dataclass
class AuthMessage:
    """Client authentication message."""
    type: str = "auth"
    device_token: str = ""
    timestamp: int = 0


@dataclass
class AuthOkMessage:
    """Authentication success."""
    type: str = "auth_ok"
    device_id: str = ""
    session_id: str = ""
    timestamp: int = 0


@dataclass
class AuthFailedMessage:
    """Authentication failed."""
    type: str = "auth_failed"
    reason: str = ""
    timestamp: int = 0


@dataclass
class InputMoveMessage:
    """Mouse move input."""
    type: str = "input_move"
    dx: float = 0.0
    dy: float = 0.0
    timestamp: int = 0


@dataclass
class InputClickMessage:
    """Mouse click input."""
    type: str = "input_click"
    button: str = "left"  # left, right, middle
    action: str = "click"  # press, release, click
    timestamp: int = 0


@dataclass
class InputScrollMessage:
    """Scroll input."""
    type: str = "input_scroll"
    vertical: float = 0.0
    horizontal: float = 0.0
    timestamp: int = 0


@dataclass
class InputKeyMessage:
    """Keyboard input."""
    type: str = "input_key"
    key: str = ""
    action: str = "press"  # press, release
    timestamp: int = 0


@dataclass
class TextCommitMessage:
    """Text commit (bulk typing)."""
    type: str = "text_commit"
    text: str = ""
    timestamp: int = 0


@dataclass
class ProfileSettings:
    """Profile settings."""
    pointer_sensitivity: float = 1.0
    pointer_acceleration: bool = True
    scroll_sensitivity: float = 1.0
    natural_scroll: bool = False
    tap_to_click: bool = True


@dataclass
class ProfileSetMessage:
    """Set profile."""
    type: str = "profile_set"
    profile_name: str = "default"
    settings: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = 0


@dataclass
class ProfileGetMessage:
    """Get profile."""
    type: str = "profile_get"
    profile_name: str = "default"
    timestamp: int = 0


@dataclass
class ProfileDataMessage:
    """Profile data response."""
    type: str = "profile_data"
    profile_name: str = "default"
    settings: Dict[str, Any] = field(default_factory=dict)
    timestamp: int = 0


@dataclass
class ErrorMessage:
    """Error message."""
    type: str = "error"
    code: str = ""
    message: str = ""
    timestamp: int = 0


@dataclass
class DeviceRevokedMessage:
    """Device revoked notification."""
    type: str = "device_revoked"
    reason: str = ""
    timestamp: int = 0


# === Database Models ===

@dataclass
class Device:
    """Device model."""
    id: str
    name: str
    token_hash: str
    created_at: str
    last_seen_at: Optional[str] = None
    allowed: bool = True
    revoked_at: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class DeviceProfile:
    """Device profile model."""
    device_id: str
    profile_name: str
    settings_json: str
    created_at: str
    updated_at: str


@dataclass
class PairingSession:
    """Pairing session model."""
    code: str
    token: str
    expires_at: str
    used: bool = False


# === HID Models ===

@dataclass
class HIDMouseReport:
    """HID Mouse Report (Boot Protocol)."""
    buttons: int = 0  # Bit 0: Left, Bit 1: Right, Bit 2: Middle
    x: int = 0        # Relative X (-127 to 127)
    y: int = 0        # Relative Y (-127 to 127)
    
    def to_bytes(self) -> bytes:
        """Convert to 3-byte HID report."""
        # Clamp values
        x = max(-127, min(127, self.x))
        y = max(-127, min(127, self.y))
        
        # Convert to unsigned bytes
        x_byte = x & 0xFF
        y_byte = y & 0xFF
        
        return bytes([self.buttons, x_byte, y_byte])


@dataclass
class HIDKeyboardReport:
    """HID Keyboard Report (Boot Protocol)."""
    modifier: int = 0  # Modifier keys (Ctrl, Shift, Alt, etc.)
    reserved: int = 0
    key1: int = 0
    key2: int = 0
    key3: int = 0
    key4: int = 0
    key5: int = 0
    key6: int = 0
    
    def to_bytes(self) -> bytes:
        """Convert to 8-byte HID report."""
        return bytes([
            self.modifier,
            self.reserved,
            self.key1,
            self.key2,
            self.key3,
            self.key4,
            self.key5,
            self.key6
        ])


# === Helper Functions ===

def parse_message(data: Dict[str, Any]) -> Optional[Any]:
    """Parse WebSocket message from dict."""
    msg_type = data.get("type")
    
    if msg_type == "auth":
        return AuthMessage(**data)
    elif msg_type == "input_move":
        return InputMoveMessage(**data)
    elif msg_type == "input_click":
        return InputClickMessage(**data)
    elif msg_type == "input_scroll":
        return InputScrollMessage(**data)
    elif msg_type == "input_key":
        return InputKeyMessage(**data)
    elif msg_type == "text_commit":
        return TextCommitMessage(**data)
    elif msg_type == "profile_set":
        return ProfileSetMessage(**data)
    elif msg_type == "profile_get":
        return ProfileGetMessage(**data)
    else:
        return None
