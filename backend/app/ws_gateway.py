"""
TV-Bridge WebSocket Gateway

WebSocket-Server für Client-Verbindungen.
"""

import asyncio
import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect

from .models import (
    WSMessage, MessageType, ClientSession, SessionState,
    HelloPayload, AuthPayload, AuthOkPayload, AuthFailedPayload,
    InputMovePayload, InputClickPayload, InputScrollPayload,
    InputKeyPayload, TextCommitPayload,
    ProfileGetPayload, ProfileSetPayload, ProfileDataPayload,
    ErrorPayload
)
from .auth_service import auth_service
from .input_engine import input_engine
from .config_store import config_store
from .settings import settings

logger = logging.getLogger(__name__)


class WSGateway:
    """WebSocket-Gateway"""
    
    def __init__(self):
        self._sessions: Dict[str, ClientSession] = {}
        self._websockets: Dict[str, WebSocket] = {}
        self._ping_tasks: Dict[str, asyncio.Task] = {}
    
    def get_active_connections(self) -> int:
        """Anzahl aktiver Verbindungen"""
        return len([s for s in self._sessions.values() if s.state == SessionState.AUTHENTICATED])
    
    async def handle_connection(self, websocket: WebSocket, client_ip: str):
        """Handhabt WebSocket-Verbindung"""
        session_id = str(uuid.uuid4())
        
        # Accept Connection
        await websocket.accept()
        
        # Session erstellen
        session = ClientSession(
            session_id=session_id,
            state=SessionState.CONNECTED,
            connected_at=datetime.utcnow(),
            last_seen=datetime.utcnow()
        )
        
        self._sessions[session_id] = session
        self._websockets[session_id] = websocket
        
        logger.info(f"WebSocket connected: {session_id} from {client_ip}")
        
        try:
            # Hello senden
            await self._send_hello(session_id)
            
            # Message-Loop
            while True:
                # Message empfangen
                data = await websocket.receive_text()
                
                # Parsen
                try:
                    message_dict = json.loads(data)
                    message = WSMessage(**message_dict)
                except Exception as e:
                    logger.warning(f"Invalid message from {session_id}: {e}")
                    await self._send_error(session_id, "invalid_message", str(e))
                    continue
                
                # Timestamp validieren
                if not self._validate_timestamp(message.timestamp):
                    logger.warning(f"Invalid timestamp from {session_id}: {message.timestamp}")
                    await self._send_error(session_id, "invalid_timestamp", "Timestamp too old or in future")
                    continue
                
                # Last-Seen aktualisieren
                session.last_seen = datetime.utcnow()
                
                # Message handlen
                await self._handle_message(session_id, message, client_ip)
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        
        except Exception as e:
            logger.error(f"WebSocket error for {session_id}: {e}", exc_info=True)
        
        finally:
            # Cleanup
            await self._cleanup_session(session_id)
    
    async def _send_hello(self, session_id: str):
        """Sendet Hello-Message"""
        payload = HelloPayload(
            server_version=settings.server_version,
            capabilities=["mouse", "keyboard", "scroll"],
            requires_auth=True
        )
        
        await self._send_message(session_id, MessageType.HELLO, payload.model_dump())
    
    async def _send_message(self, session_id: str, msg_type: MessageType, payload: dict):
        """Sendet Message an Client"""
        if session_id not in self._websockets:
            return
        
        message = WSMessage(
            type=msg_type,
            protocol_version="1.0",
            timestamp=int(datetime.utcnow().timestamp() * 1000),
            payload=payload
        )
        
        websocket = self._websockets[session_id]
        
        try:
            await websocket.send_text(message.model_dump_json())
        except Exception as e:
            logger.error(f"Error sending message to {session_id}: {e}")
    
    async def _send_error(self, session_id: str, code: str, message: str, details: str = None):
        """Sendet Error-Message"""
        payload = ErrorPayload(
            code=code,
            message=message,
            details=details
        )
        
        await self._send_message(session_id, MessageType.ERROR, payload.model_dump())
    
    def _validate_timestamp(self, timestamp_ms: int) -> bool:
        """Validiert Message-Timestamp"""
        now = datetime.utcnow()
        message_time = datetime.fromtimestamp(timestamp_ms / 1000.0)
        
        # Max Age
        if message_time < now - timedelta(seconds=settings.timestamp_max_age_seconds):
            return False
        
        # Max Future
        if message_time > now + timedelta(seconds=settings.timestamp_max_future_seconds):
            return False
        
        return True
    
    async def _handle_message(self, session_id: str, message: WSMessage, client_ip: str):
        """Handhabt eingehende Message"""
        session = self._sessions.get(session_id)
        if not session:
            return
        
        msg_type = message.type
        
        # Auth-Message
        if msg_type == MessageType.AUTH:
            await self._handle_auth(session_id, message, client_ip)
        
        # Pong
        elif msg_type == MessageType.PONG:
            # Heartbeat-Antwort
            pass
        
        # Input-Events (nur wenn authenticated)
        elif session.state == SessionState.AUTHENTICATED:
            if msg_type == MessageType.INPUT_MOVE:
                await self._handle_input_move(session_id, message)
            
            elif msg_type == MessageType.INPUT_CLICK:
                await self._handle_input_click(session_id, message)
            
            elif msg_type == MessageType.INPUT_SCROLL:
                await self._handle_input_scroll(session_id, message)
            
            elif msg_type == MessageType.INPUT_KEY:
                await self._handle_input_key(session_id, message)
            
            elif msg_type == MessageType.TEXT_COMMIT:
                await self._handle_text_commit(session_id, message)
            
            elif msg_type == MessageType.PROFILE_GET:
                await self._handle_profile_get(session_id, message)
            
            elif msg_type == MessageType.PROFILE_SET:
                await self._handle_profile_set(session_id, message)
            
            else:
                logger.warning(f"Unknown message type from {session_id}: {msg_type}")
        
        else:
            # Nicht authentifiziert
            await self._send_error(session_id, "not_authenticated", "Authentication required")
    
    async def _handle_auth(self, session_id: str, message: WSMessage, client_ip: str):
        """Handhabt Auth-Message"""
        session = self._sessions[session_id]
        
        try:
            auth_payload = AuthPayload(**message.payload)
        except Exception as e:
            await self._send_error(session_id, "invalid_message", f"Invalid auth payload: {e}")
            return
        
        # Authentifizieren
        success, device, error_reason = await auth_service.authenticate(
            auth_payload.device_token,
            client_ip
        )
        
        if not success:
            # Auth fehlgeschlagen
            payload = AuthFailedPayload(
                reason=error_reason,
                message=f"Authentication failed: {error_reason}"
            )
            
            await self._send_message(session_id, MessageType.AUTH_FAILED, payload.model_dump())
            return
        
        # Auth erfolgreich
        session.device_id = device.id
        session.device_name = device.name
        session.state = SessionState.AUTHENTICATED
        session.debug = auth_payload.debug
        
        payload = AuthOkPayload(
            device_id=device.id,
            device_name=device.name,
            session_id=session_id
        )
        
        await self._send_message(session_id, MessageType.AUTH_OK, payload.model_dump())
        
        # Ping-Task starten
        self._ping_tasks[session_id] = asyncio.create_task(self._ping_loop(session_id))
        
        logger.info(f"Session authenticated: {session_id} as {device.name}")
    
    async def _handle_input_move(self, session_id: str, message: WSMessage):
        """Handhabt Input-Move"""
        session = self._sessions[session_id]
        
        try:
            payload = InputMovePayload(**message.payload)
        except Exception as e:
            await self._send_error(session_id, "invalid_message", str(e))
            return
        
        # Profil holen
        profile_data = await config_store.get_profile(session.device_id)
        if not profile_data:
            logger.warning(f"No profile for device {session.device_id}")
            return
        
        # Input Engine
        await input_engine.handle_move(session.device_id, payload, profile_data.settings)
    
    async def _handle_input_click(self, session_id: str, message: WSMessage):
        """Handhabt Input-Click"""
        session = self._sessions[session_id]
        
        try:
            payload = InputClickPayload(**message.payload)
        except Exception as e:
            await self._send_error(session_id, "invalid_message", str(e))
            return
        
        profile_data = await config_store.get_profile(session.device_id)
        if not profile_data:
            return
        
        await input_engine.handle_click(session.device_id, payload, profile_data.settings)
    
    async def _handle_input_scroll(self, session_id: str, message: WSMessage):
        """Handhabt Input-Scroll"""
        session = self._sessions[session_id]
        
        try:
            payload = InputScrollPayload(**message.payload)
        except Exception as e:
            await self._send_error(session_id, "invalid_message", str(e))
            return
        
        profile_data = await config_store.get_profile(session.device_id)
        if not profile_data:
            return
        
        await input_engine.handle_scroll(session.device_id, payload, profile_data.settings)
    
    async def _handle_input_key(self, session_id: str, message: WSMessage):
        """Handhabt Input-Key"""
        session = self._sessions[session_id]
        
        try:
            payload = InputKeyPayload(**message.payload)
        except Exception as e:
            await self._send_error(session_id, "invalid_message", str(e))
            return
        
        profile_data = await config_store.get_profile(session.device_id)
        if not profile_data:
            return
        
        await input_engine.handle_key(session.device_id, payload, profile_data.settings)
    
    async def _handle_text_commit(self, session_id: str, message: WSMessage):
        """Handhabt Text-Commit"""
        session = self._sessions[session_id]
        
        try:
            payload = TextCommitPayload(**message.payload)
        except Exception as e:
            await self._send_error(session_id, "invalid_message", str(e))
            return
        
        profile_data = await config_store.get_profile(session.device_id)
        if not profile_data:
            return
        
        await input_engine.handle_text_commit(session.device_id, payload, profile_data.settings)
    
    async def _handle_profile_get(self, session_id: str, message: WSMessage):
        """Handhabt Profile-Get"""
        session = self._sessions[session_id]
        
        try:
            payload = ProfileGetPayload(**message.payload)
        except Exception as e:
            await self._send_error(session_id, "invalid_message", str(e))
            return
        
        profile_data = await config_store.get_profile(session.device_id, payload.profile_name)
        
        if not profile_data:
            await self._send_error(session_id, "profile_not_found", f"Profile not found: {payload.profile_name}")
            return
        
        response_payload = ProfileDataPayload(
            profile_name=profile_data.profile_name,
            settings=profile_data.settings
        )
        
        await self._send_message(session_id, MessageType.PROFILE_DATA, response_payload.model_dump())
    
    async def _handle_profile_set(self, session_id: str, message: WSMessage):
        """Handhabt Profile-Set"""
        session = self._sessions[session_id]
        
        try:
            payload = ProfileSetPayload(**message.payload)
        except Exception as e:
            await self._send_error(session_id, "invalid_message", str(e))
            return
        
        # Profil speichern
        await config_store.update_profile(
            session.device_id,
            payload.profile_name,
            payload.settings
        )
        
        logger.info(f"Profile updated: {session.device_id}/{payload.profile_name}")
    
    async def _ping_loop(self, session_id: str):
        """Ping-Loop für Heartbeat"""
        try:
            while True:
                await asyncio.sleep(settings.ws_ping_interval)
                
                if session_id not in self._sessions:
                    break
                
                session = self._sessions[session_id]
                
                # Timeout prüfen
                if datetime.utcnow() - session.last_seen > timedelta(seconds=settings.ws_ping_timeout):
                    logger.warning(f"Session timeout: {session_id}")
                    await self._cleanup_session(session_id)
                    break
                
                # Ping senden
                await self._send_message(session_id, MessageType.PING, {})
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ping loop error for {session_id}: {e}")
    
    async def revoke_device_sessions(self, device_id: str, reason: str = "Device revoked"):
        """Schließt alle Sessions eines Geräts (nach Revocation)"""
        for session_id, session in list(self._sessions.items()):
            if session.device_id == device_id:
                # DeviceRevoked-Message senden
                from .models import DeviceRevokedPayload
                payload = DeviceRevokedPayload(
                    reason=reason,
                    disconnect_in_seconds=5
                )
                
                await self._send_message(session_id, MessageType.DEVICE_REVOKED, payload.model_dump())
                
                # Nach kurzer Delay disconnecten
                await asyncio.sleep(5)
                await self._cleanup_session(session_id)
    
    async def _cleanup_session(self, session_id: str):
        """Cleanup Session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        
        if session_id in self._websockets:
            websocket = self._websockets[session_id]
            try:
                await websocket.close()
            except:
                pass
            del self._websockets[session_id]
        
        if session_id in self._ping_tasks:
            self._ping_tasks[session_id].cancel()
            del self._ping_tasks[session_id]
        
        logger.info(f"Session cleaned up: {session_id}")


# Singleton-Instanz
ws_gateway = WSGateway()
