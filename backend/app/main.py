"""
TV-Bridge Main Application

FastAPI App Entry Point.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .settings import settings
from .config_store import config_store
from .hid_service import hid_service
from .input_engine import input_engine
from .ws_gateway import ws_gateway
from .admin_api import router as admin_router, pairing_router

# Logging konfigurieren
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(settings.log_dir) / "app.log") if Path(settings.log_dir).exists() else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# Lifecycle
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App-Lifecycle (Startup/Shutdown)"""
    logger.info("=== TV-Bridge starting up ===")
    logger.info(f"Version: {settings.server_version}")
    logger.info(f"Host: {settings.host}:{settings.port}")
    
    # Startup
    try:
        # Database
        logger.info("Initializing database...")
        await config_store.initialize()
        
        # HID Service
        logger.info("Initializing HID service...")
        try:
            await hid_service.initialize()
        except FileNotFoundError as e:
            logger.error(f"HID initialization failed: {e}")
            logger.error("Make sure USB gadget is configured (run setup_gadget.sh)")
            logger.error("System will start but input will not work!")
        
        # Input Engine
        logger.info("Starting input engine...")
        await input_engine.start()
        
        logger.info("=== TV-Bridge startup complete ===")
        
        yield
    
    finally:
        # Shutdown
        logger.info("=== TV-Bridge shutting down ===")
        
        await input_engine.stop()
        await hid_service.close()
        
        logger.info("=== TV-Bridge shutdown complete ===")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="TV-Bridge",
    description="Raspberry Pi USB HID Remote Control for Smart TVs",
    version=settings.server_version,
    lifespan=lifespan
)

# CORS (nur für Development)
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.warning("CORS enabled - only use in development!")


# ============================================================================
# Routes
# ============================================================================

# Admin API
app.include_router(admin_router)

# Public Pairing API
app.include_router(pairing_router)


# WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket-Endpoint für Clients"""
    client_ip = websocket.client.host
    await ws_gateway.handle_connection(websocket, client_ip)


# Static Files (Web-App)
webapp_path = Path(settings.webapp_dir)
if webapp_path.exists():
    app.mount("/assets", StaticFiles(directory=webapp_path / "assets"), name="assets")
    app.mount("/styles", StaticFiles(directory=webapp_path / "styles"), name="styles")
    app.mount("/scripts", StaticFiles(directory=webapp_path / "scripts"), name="scripts")
    
    @app.get("/")
    async def serve_webapp():
        """Serviert Web-App"""
        index_file = webapp_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Web-App not found"}
else:
    logger.warning(f"Web-App directory not found: {webapp_path}")
    
    @app.get("/")
    async def root():
        """Root-Endpoint (Fallback)"""
        return {
            "name": "TV-Bridge",
            "version": settings.server_version,
            "status": "running",
            "websocket": "/ws",
            "admin_api": "/admin",
            "pairing": "/pair"
        }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Globaler Exception-Handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "error": "internal_server_error",
        "message": "An internal error occurred"
    }


# ============================================================================
# Main (für direktes Ausführen)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
