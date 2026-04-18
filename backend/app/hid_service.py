"""
TV-Bridge HID Service

USB HID Gadget Interface für Mouse und Keyboard.
Sendet binäre HID Reports an /dev/hidgX Devices.
"""

import logging
from pathlib import Path
from typing import Optional
import asyncio

from .models import HIDMouseReport, HIDKeyboardReport
from .settings import settings

logger = logging.getLogger(__name__)


# HID Keyboard Scan Codes (USB HID Usage Tables)
# Mapping von Key-Namen zu HID Usage IDs
HID_KEY_CODES = {
    # Buchstaben
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08, 'f': 0x09,
    'g': 0x0A, 'h': 0x0B, 'i': 0x0C, 'j': 0x0D, 'k': 0x0E, 'l': 0x0F,
    'm': 0x10, 'n': 0x11, 'o': 0x12, 'p': 0x13, 'q': 0x14, 'r': 0x15,
    's': 0x16, 't': 0x17, 'u': 0x18, 'v': 0x19, 'w': 0x1A, 'x': 0x1B,
    'y': 0x1C, 'z': 0x1D,
    
    # Zahlen
    '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21, '5': 0x22,
    '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,
    
    # Spezielle Tasten
    'Enter': 0x28, 'Escape': 0x29, 'Backspace': 0x2A, 'Tab': 0x2B,
    'Space': 0x2C, ' ': 0x2C,
    
    # Sonderzeichen
    '-': 0x2D, '=': 0x2E, '[': 0x2F, ']': 0x30, '\\': 0x31,
    ';': 0x33, "'": 0x34, '`': 0x35, ',': 0x36, '.': 0x37, '/': 0x38,
    
    # Funktionstasten
    'F1': 0x3A, 'F2': 0x3B, 'F3': 0x3C, 'F4': 0x3D, 'F5': 0x3E, 'F6': 0x3F,
    'F7': 0x40, 'F8': 0x41, 'F9': 0x42, 'F10': 0x43, 'F11': 0x44, 'F12': 0x45,
    
    # Navigation
    'Insert': 0x49, 'Home': 0x4A, 'PageUp': 0x4B,
    'Delete': 0x4C, 'End': 0x4D, 'PageDown': 0x4E,
    'ArrowRight': 0x4F, 'ArrowLeft': 0x50, 'ArrowDown': 0x51, 'ArrowUp': 0x52,
}

# Modifier-Bits
HID_MODIFIER = {
    'Control': 0x01,  # Left Control
    'Shift': 0x02,    # Left Shift
    'Alt': 0x04,      # Left Alt
    'Meta': 0x08,     # Left GUI (Windows/Command)
    'RightControl': 0x10,
    'RightShift': 0x20,
    'RightAlt': 0x40,
    'RightMeta': 0x80,
}


class HIDService:
    """USB HID Gadget Service"""
    
    def __init__(
        self,
        mouse_device: str = None,
        keyboard_device: str = None
    ):
        self.mouse_device = mouse_device or settings.hid_mouse_device
        self.keyboard_device = keyboard_device or settings.hid_keyboard_device
        
        self._mouse_fd: Optional[int] = None
        self._keyboard_fd: Optional[int] = None
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialisiert HID-Devices"""
        logger.info("Initializing HID service...")
        
        # Mouse
        if not Path(self.mouse_device).exists():
            logger.error(f"Mouse device not found: {self.mouse_device}")
            logger.error("Make sure USB gadget is configured (run setup_gadget.sh)")
            raise FileNotFoundError(f"HID Mouse device not found: {self.mouse_device}")
        
        # Keyboard
        if not Path(self.keyboard_device).exists():
            logger.error(f"Keyboard device not found: {self.keyboard_device}")
            raise FileNotFoundError(f"HID Keyboard device not found: {self.keyboard_device}")
        
        # Devices öffnen (synchron, da File I/O)
        try:
            self._mouse_fd = open(self.mouse_device, 'wb', buffering=0)
            logger.info(f"Opened mouse device: {self.mouse_device}")
        except PermissionError:
            logger.error(f"Permission denied opening {self.mouse_device}")
            logger.error("Run as root or add user to appropriate group")
            raise
        
        try:
            self._keyboard_fd = open(self.keyboard_device, 'wb', buffering=0)
            logger.info(f"Opened keyboard device: {self.keyboard_device}")
        except PermissionError:
            logger.error(f"Permission denied opening {self.keyboard_device}")
            raise
        
        self._initialized = True
        logger.info("HID service initialized successfully")
    
    async def close(self):
        """Schließt HID-Devices"""
        if self._mouse_fd:
            self._mouse_fd.close()
            self._mouse_fd = None
        
        if self._keyboard_fd:
            self._keyboard_fd.close()
            self._keyboard_fd = None
        
        self._initialized = False
        logger.info("HID service closed")
    
    def is_healthy(self) -> tuple[bool, bool]:
        """Prüft Health-Status (mouse, keyboard)"""
        mouse_ok = self._mouse_fd is not None and not self._mouse_fd.closed
        keyboard_ok = self._keyboard_fd is not None and not self._keyboard_fd.closed
        return mouse_ok, keyboard_ok
    
    # ========================================================================
    # Mouse Functions
    # ========================================================================
    
    async def send_mouse_report(self, report: HIDMouseReport):
        """Sendet Mouse-Report"""
        if not self._initialized or not self._mouse_fd:
            logger.warning("Mouse device not initialized")
            return
        
        async with self._lock:
            try:
                report_bytes = report.to_bytes()
                await asyncio.to_thread(self._mouse_fd.write, report_bytes)
                await asyncio.to_thread(self._mouse_fd.flush)
            except Exception as e:
                logger.error(f"Error sending mouse report: {e}")
                raise
    
    async def move_mouse(self, dx: int, dy: int):
        """Bewegt Maus relativ"""
        report = HIDMouseReport(buttons=0, dx=dx, dy=dy)
        await self.send_mouse_report(report)
    
    async def click_mouse(self, button: str = "left", press: bool = True):
        """Klickt Maus-Button"""
        button_map = {
            "left": 0x01,
            "right": 0x02,
            "middle": 0x04
        }
        
        button_bits = button_map.get(button, 0x01)
        
        if press:
            # Button down
            report = HIDMouseReport(buttons=button_bits, dx=0, dy=0)
        else:
            # Button up
            report = HIDMouseReport(buttons=0, dx=0, dy=0)
        
        await self.send_mouse_report(report)
    
    async def scroll(self, vertical: int = 0, horizontal: int = 0):
        """
        Scroll-Emulation via Mouse Wheel
        
        Note: Boot Protocol Mouse unterstützt kein Wheel.
        Für MVP nutzen wir Arrow-Keys als Fallback.
        
        TODO: Erweiterte HID-Descriptor mit Wheel-Support (Post-MVP)
        """
        # Fallback: Konvertiere Scroll zu Arrow-Keys
        if vertical > 0:
            await self.press_key("ArrowDown")
            await self.release_key("ArrowDown")
        elif vertical < 0:
            await self.press_key("ArrowUp")
            await self.release_key("ArrowUp")
        
        if horizontal > 0:
            await self.press_key("ArrowRight")
            await self.release_key("ArrowRight")
        elif horizontal < 0:
            await self.press_key("ArrowLeft")
            await self.release_key("ArrowLeft")
    
    # ========================================================================
    # Keyboard Functions
    # ========================================================================
    
    async def send_keyboard_report(self, report: HIDKeyboardReport):
        """Sendet Keyboard-Report"""
        if not self._initialized or not self._keyboard_fd:
            logger.warning("Keyboard device not initialized")
            return
        
        async with self._lock:
            try:
                report_bytes = report.to_bytes()
                await asyncio.to_thread(self._keyboard_fd.write, report_bytes)
                await asyncio.to_thread(self._keyboard_fd.flush)
            except Exception as e:
                logger.error(f"Error sending keyboard report: {e}")
                raise
    
    async def press_key(self, key: str, modifiers: list[str] = None):
        """Drückt Taste"""
        key_code = HID_KEY_CODES.get(key, 0)
        
        if key_code == 0:
            logger.warning(f"Unknown key: {key}")
            return
        
        # Modifier-Bits berechnen
        modifier_bits = 0
        if modifiers:
            for mod in modifiers:
                modifier_bits |= HID_MODIFIER.get(mod, 0)
        
        report = HIDKeyboardReport(
            modifier=modifier_bits,
            reserved=0,
            keys=[key_code, 0, 0, 0, 0, 0]
        )
        
        await self.send_keyboard_report(report)
    
    async def release_key(self, key: str = None):
        """Lässt Taste los (oder alle Tasten)"""
        # Leeres Report = alle Tasten losgelassen
        report = HIDKeyboardReport(
            modifier=0,
            reserved=0,
            keys=[0, 0, 0, 0, 0, 0]
        )
        await self.send_keyboard_report(report)
    
    async def type_key(self, key: str, modifiers: list[str] = None, delay_ms: int = 10):
        """Tippt Taste (press + release)"""
        await self.press_key(key, modifiers)
        await asyncio.sleep(delay_ms / 1000.0)
        await self.release_key()
    
    async def type_text(self, text: str, delay_ms: int = 10):
        """
        Tippt Text (konvertiert zu Tastenkombinationen)
        
        Note: Einfache Implementierung für MVP.
        Unterstützt nur ASCII-Zeichen ohne Umlaute.
        """
        for char in text:
            # Uppercase = Shift
            if char.isupper():
                await self.type_key(char.lower(), modifiers=["Shift"], delay_ms=delay_ms)
            # Sonderzeichen mit Shift
            elif char in '!@#$%^&*()_+{}|:"<>?':
                shift_map = {
                    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
                    '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
                    '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
                    ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'
                }
                base_key = shift_map.get(char, char)
                await self.type_key(base_key, modifiers=["Shift"], delay_ms=delay_ms)
            # Normales Zeichen
            else:
                await self.type_key(char, delay_ms=delay_ms)


# Singleton-Instanz
hid_service = HIDService()
