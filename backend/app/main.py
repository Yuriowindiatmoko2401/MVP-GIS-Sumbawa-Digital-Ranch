"""
Main FastAPI application for Sumbawa Digital Ranch MVP
Provides REST API endpoints and WebSocket for real-time cattle tracking
"""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Import database and services
from app.database.db import test_connection, get_db, engine, Base
from app.websocket.ws_manager import ConnectionManager

# Import API routes
from app.api.cattle_routes import router as cattle_router
from app.api.resource_routes import router as resource_router
from app.api.geofence_routes import router as geofence_router
from app.api.heatmap_routes import router as heatmap_router

# Import background tasks
from app.tasks.background_tasks import startup_event, shutdown_event, register_task_management_routes

# Load environment variables
load_dotenv()

# Get CORS origins from environment
CORS_ORIGINS = os.getenv("CORS_ORIGINS", '["http://localhost:5173","http://localhost:3000"]')
if isinstance(CORS_ORIGINS, str):
    import json
    try:
        CORS_ORIGINS = json.loads(CORS_ORIGINS)
    except:
        CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]

# Initialize WebSocket manager
manager = ConnectionManager()


# Create FastAPI app
app = FastAPI(
    title="Sumbawa Digital Ranch API",
    description="Real-time GPS cattle tracking and management system for Sumbawa Digital Ranch MVP",
    version="1.0.0",
    lifespan=None  # We'll handle events manually
)


# Register lifespan events
app.add_event_handler("startup", lambda: startup_event(app))
app.add_event_handler("shutdown", lambda: shutdown_event(app))

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(cattle_router)
app.include_router(resource_router)
app.include_router(geofence_router)
app.include_router(heatmap_router)

# Register background task management routes
register_task_management_routes(app)


@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "message": "Sumbawa Digital Ranch API",
        "version": "1.0.0",
        "description": "Real-time GPS cattle tracking and management system",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "docs_url": "/docs",
        "websocket_url": "/ws"
    }


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    Returns system status and database connectivity
    """
    db_status = test_connection()

    return {
        "status": "healthy" if db_status else "unhealthy",
        "database_connected": db_status,
        "websocket_connections": len(manager.active_connections),
        "timestamp": "2025-11-27T10:29:00Z"  # Will be dynamic
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    Handles cattle position updates, geofence violations, and notifications
    """
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            # Echo back or process command
            await manager.broadcast(f"Server echo: {data}")

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unexpected errors
    """
    print(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "detail": str(exc) if os.getenv("ENVIRONMENT") == "development" else None}
    )


if __name__ == "__main__":
    import uvicorn

    # Run server with uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )