"""
TV-Bridge Main Application (Pydantic-Free Version)

FastAPI ohne Pydantic - nutzt Plain Dicts und Type Hints.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, HTTPException, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any

# Imports ohne Pydantic
from settings_light import settings
from config_store import config_store
from hid_service import hid_service
from input_engine import input_engine
from auth_service import auth_service
from pairing_service import pairing_service
from ws_gateway import ws_gateway


# Logging setup
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting TV-Bridge backend...")
    
    try:
        # Initialize services
        await config_store.initialize()
        await hid_service.initialize()
        await input_engine.start()
        await pairing_service.initialize(config_store)
        await auth_service.initialize(config_store)
        await ws_gateway.initialize(auth_service, input_engine, pairing_service, config_store)
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down TV-Bridge backend...")
    await input_engine.stop()
    await hid_service.close()
    logger.info("Shutdown complete")


# FastAPI App
app = FastAPI(
    title="TV-Bridge API",
    description="Raspberry Pi USB HID Bridge for Smart TVs",
    version="1.0.0",
    lifespan=lifespan
)


# === WebSocket Endpoint ===

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for client connections."""
    await ws_gateway.handle_connection(websocket)


# === Admin API ===

def verify_admin_token(authorization: Optional[str] = Header(None)) -> bool:
    """Verify admin token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    if not auth_service.validate_admin_token(token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    return True


@app.post("/admin/pairing/start")
async def start_pairing(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Start pairing mode."""
    verify_admin_token(authorization)
    
    code, token = await pairing_service.start_pairing()
    
    return {
        "success": True,
        "pairing_code": code,
        "device_token": token,
        "expires_in": pairing_service.pairing_timeout
    }


@app.post("/admin/pairing/stop")
async def stop_pairing(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Stop pairing mode."""
    verify_admin_token(authorization)
    
    await pairing_service.stop_pairing()
    
    return {"success": True, "message": "Pairing stopped"}


@app.get("/admin/pairing/status")
async def pairing_status() -> Dict[str, Any]:
    """Get pairing status (public endpoint)."""
    is_active = await pairing_service.is_pairing_active()
    
    if is_active:
        _, expires_in = await pairing_service.get_pairing_status()
        return {
            "pairing_enabled": True,
            "expires_in": expires_in
        }
    else:
        return {"pairing_enabled": False}


@app.get("/admin/devices")
async def list_devices(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """List all devices."""
    verify_admin_token(authorization)
    
    devices = await config_store.list_devices()
    
    return {
        "devices": [
            {
                "id": d.id,
                "name": d.name,
                "created_at": d.created_at,
                "last_seen_at": d.last_seen_at,
                "allowed": d.allowed,
                "revoked_at": d.revoked_at,
                "notes": d.notes
            }
            for d in devices
        ]
    }


@app.post("/admin/devices/{device_id}/revoke")
async def revoke_device(device_id: str, authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Revoke a device."""
    verify_admin_token(authorization)
    
    await config_store.revoke_device(device_id, reason="Revoked by admin")
    await ws_gateway.revoke_device_sessions(device_id, "Device revoked by administrator")
    
    return {"success": True, "message": "Device revoked"}


@app.post("/admin/devices/{device_id}/allow")
async def allow_device(device_id: str, authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Allow a previously revoked device."""
    verify_admin_token(authorization)
    
    await config_store.allow_device(device_id)
    
    return {"success": True, "message": "Device allowed"}


@app.get("/admin/health")
async def health_check(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Health check endpoint."""
    verify_admin_token(authorization)
    
    hid_status = "ok" if hid_service.mouse_device and hid_service.keyboard_device else "error"
    db_status = "ok" if config_store.db else "error"
    
    return {
        "status": "ok" if hid_status == "ok" and db_status == "ok" else "degraded",
        "hid": hid_status,
        "database": db_status,
        "version": "1.0.0"
    }


# === Public Pairing Endpoint ===

@app.post("/pair")
async def pair_device(request: Request) -> Dict[str, Any]:
    """Public pairing endpoint."""
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    pairing_code = data.get("pairing_code", "").strip()
    device_name = data.get("device_name", "").strip()
    
    if not pairing_code or not device_name:
        raise HTTPException(status_code=400, detail="Missing pairing_code or device_name")
    
    try:
        device = await pairing_service.pair_device(pairing_code, device_name)
        
        return {
            "success": True,
            "device_id": device.id,
            "device_name": device.name,
            "device_token": data.get("_token")  # Token from pairing session
        }
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": str(e)}
        )


# === Static Files (Web App) ===

webapp_dir = Path(__file__).parent.parent.parent / "webapp"
if webapp_dir.exists():
    app.mount("/", StaticFiles(directory=str(webapp_dir), html=True), name="static")
    logger.info(f"Serving web app from {webapp_dir}")
else:
    logger.warning(f"Web app directory not found: {webapp_dir}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
