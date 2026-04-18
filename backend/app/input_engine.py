"""
TV-Bridge Input Engine

Verarbeitet Input-Events vom Client, wendet Profil-Einstellungen an
und konvertiert sie in HID-Aktionen.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from collections import deque
from typing import Optional

from .models import (
    InputMovePayload, InputClickPayload, InputScrollPayload,
    InputKeyPayload, TextCommitPayload, ProfileSettings
)
from .hid_service import hid_service
from .config_store import config_store
from .settings import settings

logger = logging.getLogger(__name__)


class InputEngine:
    """Input-Event-Processing-Engine"""
    
    def __init__(self):
        self.event_queue = asyncio.Queue(maxsize=settings.input_queue_size)
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        
        # Event Coalescing
        self._pending_moves: dict[str, deque] = {}  # device_id -> deque of moves
        self._coalescing_window = timedelta(milliseconds=settings.event_coalescing_window_ms)
        
        # Rate Limiting
        self._rate_limit_buckets: dict[str, deque] = {}  # device_id -> deque of timestamps
    
    async def start(self):
        """Startet Input-Processor"""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Input engine started")
    
    async def stop(self):
        """Stoppt Input-Processor"""
        self._running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Input engine stopped")
    
    def _check_rate_limit(self, device_id: str) -> bool:
        """Prüft Rate Limit für Device"""
        now = datetime.utcnow()
        window = timedelta(seconds=1)
        
        if device_id not in self._rate_limit_buckets:
            self._rate_limit_buckets[device_id] = deque()
        
        bucket = self._rate_limit_buckets[device_id]
        
        # Alte Einträge entfernen
        while bucket and bucket[0] < now - window:
            bucket.popleft()
        
        # Limit prüfen
        if len(bucket) >= settings.input_rate_limit:
            logger.warning(f"Rate limit exceeded for device {device_id}")
            return False
        
        bucket.append(now)
        return True
    
    async def handle_move(self, device_id: str, payload: InputMovePayload, profile: ProfileSettings):
        """Verarbeitet Mouse-Move-Event"""
        if not self._check_rate_limit(device_id):
            return
        
        # Sensitivität anwenden
        dx = payload.dx * profile.pointer_sensitivity
        dy = payload.dy * profile.pointer_sensitivity
        
        # Pointer-Beschleunigung (optional)
        if profile.pointer_acceleration:
            speed = (dx**2 + dy**2)**0.5
            if speed > 10:
                acceleration_factor = 1.0 + (speed / 100.0)
                dx *= acceleration_factor
                dy *= acceleration_factor
        
        # Event Coalescing
        if device_id not in self._pending_moves:
            self._pending_moves[device_id] = deque()
        
        self._pending_moves[device_id].append((dx, dy, datetime.utcnow()))
        
        # Wenn Queue nicht zu voll, direkt verarbeiten
        if self.event_queue.qsize() < settings.input_queue_size // 2:
            await self._flush_pending_moves(device_id)
    
    async def _flush_pending_moves(self, device_id: str):
        """Flusht akkumulierte Move-Events"""
        if device_id not in self._pending_moves or not self._pending_moves[device_id]:
            return
        
        # Alle Moves summieren
        total_dx = 0.0
        total_dy = 0.0
        
        while self._pending_moves[device_id]:
            dx, dy, _ = self._pending_moves[device_id].popleft()
            total_dx += dx
            total_dy += dy
        
        # Clamp auf HID-Bereich (-127 bis 127)
        # Bei größeren Bewegungen: mehrere Reports
        while abs(total_dx) > 0 or abs(total_dy) > 0:
            step_dx = int(max(-127, min(127, total_dx)))
            step_dy = int(max(-127, min(127, total_dy)))
            
            await hid_service.move_mouse(step_dx, step_dy)
            
            total_dx -= step_dx
            total_dy -= step_dy
            
            # Delay zwischen Reports vermeiden (HID kann mehrere schnell aufnehmen)
    
    async def handle_click(self, device_id: str, payload: InputClickPayload, profile: ProfileSettings):
        """Verarbeitet Mouse-Click-Event"""
        # Tap-to-Click optional
        if not profile.tap_to_click and payload.action == "click":
            return
        
        if payload.action == "down":
            await hid_service.click_mouse(payload.button, press=True)
        elif payload.action == "up":
            await hid_service.click_mouse(payload.button, press=False)
        elif payload.action == "click":
            # Down + Up
            await hid_service.click_mouse(payload.button, press=True)
            await asyncio.sleep(0.01)  # 10ms
            await hid_service.click_mouse(payload.button, press=False)
    
    async def handle_scroll(self, device_id: str, payload: InputScrollPayload, profile: ProfileSettings):
        """Verarbeitet Scroll-Event"""
        # Sensitivität anwenden
        vertical = payload.vertical * profile.scroll_sensitivity
        horizontal = payload.horizontal * profile.scroll_sensitivity
        
        # Natural Scroll (invertieren)
        if profile.natural_scroll:
            vertical = -vertical
            horizontal = -horizontal
        
        # Scroll in HID
        # Note: Boot Protocol Mouse hat kein Wheel, wir nutzen Arrow-Keys als Fallback
        vertical_steps = int(vertical)
        horizontal_steps = int(horizontal)
        
        await hid_service.scroll(vertical_steps, horizontal_steps)
    
    async def handle_key(self, device_id: str, payload: InputKeyPayload, profile: ProfileSettings):
        """Verarbeitet Key-Press-Event"""
        if payload.action == "press":
            await hid_service.press_key(payload.key)
        elif payload.action == "release":
            await hid_service.release_key(payload.key)
    
    async def handle_text_commit(self, device_id: str, payload: TextCommitPayload, profile: ProfileSettings):
        """Verarbeitet Text-Commit-Event"""
        await hid_service.type_text(payload.text)
    
    async def _process_events(self):
        """Event-Processor-Loop"""
        while self._running:
            try:
                # Periodisch pending moves flushen
                for device_id in list(self._pending_moves.keys()):
                    if self._pending_moves[device_id]:
                        oldest_time = self._pending_moves[device_id][0][2]
                        if datetime.utcnow() - oldest_time > self._coalescing_window:
                            await self._flush_pending_moves(device_id)
                
                # Kurze Pause
                await asyncio.sleep(0.016)  # ~60 Hz
                
            except Exception as e:
                logger.error(f"Error in input processor: {e}", exc_info=True)


# Singleton-Instanz
input_engine = InputEngine()
