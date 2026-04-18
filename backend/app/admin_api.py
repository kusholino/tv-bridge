"""
TV-Bridge Admin API

REST-API für administrative Funktionen (Pairing, Geräte-Management, etc.).
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Request

from .models import (
    PairingStartRequest, PairingStartResponse, PairingStatusResponse,
    PairRequest, PairResponse,
    DeviceListResponse, DeviceRevokeRequest, DeviceUpdateRequest,
    HealthResponse
)
from .auth_service import auth_service
from .pairing_service import pairing_service
from .config_store import config_store
from .hid_service import hid_service
from .ws_gateway import ws_gateway
from .settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Auth Helper
# ============================================================================

async def verify_admin_token(authorization: Optional[str] = Header(None)):
    """Verifiziert Admin-Token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Bearer Token
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    if not await auth_service.validate_admin_token(token):
        raise HTTPException(status_code=403, detail="Invalid admin token")


# ============================================================================
# Pairing Endpoints
# ============================================================================

@router.post("/pairing/start", response_model=PairingStartResponse)
async def start_pairing(
    request: PairingStartRequest = PairingStartRequest(),
    authorization: str = Header(None)
):
    """Startet Pairing-Modus"""
    await verify_admin_token(authorization)
    
    pairing_code, _ = await pairing_service.start_pairing(request.timeout_seconds)
    
    return PairingStartResponse(
        success=True,
        pairing_code=pairing_code,
        expires_in_seconds=request.timeout_seconds,
        qr_data=None  # TODO: QR-Code-Generation (Post-MVP)
    )


@router.post("/pairing/stop")
async def stop_pairing(authorization: str = Header(None)):
    """Stoppt Pairing-Modus"""
    await verify_admin_token(authorization)
    
    await pairing_service.stop_pairing()
    
    return {"success": True}


@router.get("/pairing/status", response_model=PairingStatusResponse)
async def pairing_status():
    """Pairing-Status (kein Auth nötig)"""
    active, expires_in = pairing_service.get_pairing_status()
    
    return PairingStatusResponse(
        pairing_enabled=active,
        expires_in_seconds=expires_in
    )


# ============================================================================
# Device Management
# ============================================================================

@router.get("/devices", response_model=DeviceListResponse)
async def list_devices(authorization: str = Header(None)):
    """Listet alle Geräte"""
    await verify_admin_token(authorization)
    
    devices = await config_store.list_devices()
    
    return DeviceListResponse(devices=devices)


@router.post("/devices/{device_id}/revoke")
async def revoke_device(
    device_id: str,
    request: DeviceRevokeRequest = DeviceRevokeRequest(),
    authorization: str = Header(None)
):
    """Widerruft Gerät"""
    await verify_admin_token(authorization)
    
    # Gerät holen
    device = await config_store.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Revoke
    await config_store.revoke_device(device_id, request.reason)
    
    # Aktive Sessions schließen
    await ws_gateway.revoke_device_sessions(device_id, request.reason or "Device revoked by administrator")
    
    return {"success": True}


@router.post("/devices/{device_id}/allow")
async def allow_device(device_id: str, authorization: str = Header(None)):
    """Erlaubt Gerät wieder"""
    await verify_admin_token(authorization)
    
    device = await config_store.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await config_store.allow_device(device_id)
    
    return {"success": True}


@router.put("/devices/{device_id}")
async def update_device(
    device_id: str,
    request: DeviceUpdateRequest,
    authorization: str = Header(None)
):
    """Aktualisiert Gerät"""
    await verify_admin_token(authorization)
    
    device = await config_store.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await config_store.update_device(
        device_id,
        name=request.name,
        notes=request.notes
    )
    
    return {"success": True}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, authorization: str = Header(None)):
    """Löscht Gerät komplett"""
    await verify_admin_token(authorization)
    
    device = await config_store.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Sessions schließen
    await ws_gateway.revoke_device_sessions(device_id, "Device deleted")
    
    # Löschen
    await config_store.delete_device(device_id)
    
    return {"success": True}


# ============================================================================
# Health & Status
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check(authorization: str = Header(None)):
    """System-Health-Check"""
    await verify_admin_token(authorization)
    
    # HID-Status
    mouse_ok, keyboard_ok = hid_service.is_healthy()
    
    # DB-Status
    try:
        await config_store.list_devices()
        db_ok = True
    except:
        db_ok = False
    
    # Overall-Status
    if mouse_ok and keyboard_ok and db_ok:
        status = "healthy"
    elif mouse_ok or keyboard_ok:
        status = "degraded"
    else:
        status = "unhealthy"
    
    # Uptime (approximation)
    uptime_seconds = 0  # TODO: Track startup time
    
    return HealthResponse(
        status=status,
        hid_mouse="ok" if mouse_ok else "error",
        hid_keyboard="ok" if keyboard_ok else "error",
        database="ok" if db_ok else "error",
        active_connections=ws_gateway.get_active_connections(),
        uptime_seconds=uptime_seconds
    )


# ============================================================================
# Public Pairing Endpoint (kein Admin-Token)
# ============================================================================

pairing_router = APIRouter(tags=["pairing"])


@pairing_router.post("/pair", response_model=PairResponse)
async def pair_device(request: PairRequest, req: Request):
    """Pairing-Endpoint für Clients"""
    client_ip = req.client.host
    
    success, device_id, device_token, error_msg = await pairing_service.pair_device(
        request.pairing_code,
        request.device_name
    )
    
    if not success:
        return PairResponse(
            success=False,
            error="pairing_failed",
            message=error_msg
        )
    
    return PairResponse(
        success=True,
        device_id=device_id,
        device_token=device_token,
        device_name=request.device_name
    )
