"""
Background Tasks for Sumbawa Digital Ranch MVP
Handles real-time cattle simulation and periodic updates
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session
from fastapi import FastAPI

from app.database.db import SessionLocal
from app.services.cattle_service import CattleSimulationService
from app.services.geofence_service import GeofenceService
from app.services.heatmap_service import HeatmapService
from app.websocket.ws_manager import manager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages background tasks for real-time cattle simulation and updates
    """

    def __init__(self):
        self.simulation_task = None
        self.violation_check_task = None
        self.heatmap_task = None
        self.is_running = False
        self.last_cattle_update = None
        self.last_violation_check = None
        self.last_heatmap_update = None

    async def start_simulation(self, app: FastAPI):
        """
        Start all background tasks

        Args:
            app: FastAPI application instance
        """
        if self.is_running:
            logger.warning("Background tasks already running")
            return

        self.is_running = True
        logger.info("Starting background tasks...")

        # Start cattle simulation task
        self.simulation_task = asyncio.create_task(
            self.simulate_cattle_movement_task(app)
        )

        # Start violation detection task
        self.violation_check_task = asyncio.create_task(
            self.violation_detection_task(app)
        )

        # Start heatmap update task
        self.heatmap_task = asyncio.create_task(
            self.heatmap_update_task(app)
        )

        logger.info("All background tasks started")

    async def stop_simulation(self):
        """
        Stop all background tasks
        """
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Stopping background tasks...")

        # Cancel all tasks
        if self.simulation_task:
            self.simulation_task.cancel()
        if self.violation_check_task:
            self.violation_check_task.cancel()
        if self.heatmap_task:
            self.heatmap_task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(
            self.simulation_task,
            self.violation_check_task,
            self.heatmap_task,
            return_exceptions=True
        )

        logger.info("All background tasks stopped")

    async def simulate_cattle_movement_task(self, app: FastAPI):
        """
        Background task to simulate cattle movement and broadcast updates

        Args:
            app: FastAPI application instance
        """
        logger.info("Starting cattle movement simulation task...")

        try:
            while self.is_running:
                # Get database session
                db = SessionLocal()
                try:
                    # Get main geofence (first active one)
                    from app.models.geofence import Geofence
                    main_geofence = db.query(Geofence).filter(Geofence.is_active == True).first()
                    geofence_id = main_geofence.id if main_geofence else None

                    # Simulate cattle movement
                    service = CattleSimulationService(db)
                    updated_cattle = service.update_all_cattle_positions(geofence_id)

                    if updated_cattle:
                        logger.info(f"Updated positions for {len(updated_cattle)} cattle")

                        # Broadcast cattle updates
                        await self._broadcast_cattle_updates(updated_cattle)
                        self.last_cattle_update = datetime.utcnow()

                except Exception as e:
                    logger.error(f"Error in cattle movement simulation: {e}")
                finally:
                    db.close()

                # Wait before next update (2-5 seconds random)
                import random
                await asyncio.sleep(random.uniform(2, 5))

        except asyncio.CancelledError:
            logger.info("Cattle movement simulation task cancelled")
        except Exception as e:
            logger.error(f"Fatal error in cattle movement simulation: {e}")

    async def violation_detection_task(self, app: FastAPI):
        """
        Background task to detect and broadcast geofence violations

        Args:
            app: FastAPI application instance
        """
        logger.info("Starting violation detection task...")

        try:
            while self.is_running:
                # Get database session
                db = SessionLocal()
                try:
                    # Check for violations
                    service = GeofenceService(db)
                    violations = service.detect_all_violations()

                    if violations:
                        logger.warning(f"Detected {len(violations)} geofence violations")

                        # Broadcast violation alerts
                        await self._broadcast_violation_alerts(violations)
                        self.last_violation_check = datetime.utcnow()

                    # Also check for new violations (compare with previous state)
                    await self._check_new_violations(db)

                except Exception as e:
                    logger.error(f"Error in violation detection: {e}")
                finally:
                    db.close()

                # Wait before next check (10 seconds)
                await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info("Violation detection task cancelled")
        except Exception as e:
            logger.error(f"Fatal error in violation detection: {e}")

    async def heatmap_update_task(self, app: FastAPI):
        """
        Background task to periodically update heatmap data

        Args:
            app: FastAPI application instance
        """
        logger.info("Starting heatmap update task...")

        try:
            while self.is_running:
                # Wait before next update (5 minutes)
                await asyncio.sleep(300)

                if not self.is_running:
                    break

                # Get database session
                db = SessionLocal()
                try:
                    # Generate latest heatmap data
                    service = HeatmapService(db)
                    heatmap_data = service.get_heatmap_data(hours_back=1, grid_size_meters=100)

                    # Broadcast heatmap refresh
                    await self._broadcast_heatmap_refresh(heatmap_data)
                    self.last_heatmap_update = datetime.utcnow()

                    logger.info("Broadcasted heatmap update")

                except Exception as e:
                    logger.error(f"Error in heatmap update: {e}")
                finally:
                    db.close()

        except asyncio.CancelledError:
            logger.info("Heatmap update task cancelled")
        except Exception as e:
            logger.error(f"Fatal error in heatmap update: {e}")

    async def _broadcast_cattle_updates(self, updated_cattle: List):
        """
        Broadcast cattle position updates to connected WebSocket clients

        Args:
            updated_cattle: List of updated cattle objects
        """
        try:
            cattle_list = [cattle.to_dict(include_location=True) for cattle in updated_cattle]

            await manager.broadcast_cattle_update(cattle_list)
            logger.debug(f"Broadcasted cattle update for {len(cattle_list)} cattle")

        except Exception as e:
            logger.error(f"Error broadcasting cattle updates: {e}")

    async def _broadcast_violation_alerts(self, violations: List[Dict[str, Any]]):
        """
        Broadcast violation alerts to connected WebSocket clients

        Args:
            violations: List of violation dictionaries
        """
        try:
            for violation in violations:
                # Create detailed alert
                from app.services.geofence_service import GeofenceService
                db = SessionLocal()
                try:
                    service = GeofenceService(db)
                    alert = service.create_violation_alert(
                        uuid.UUID(violation['cattle_id']),
                        violation
                    )
                    await manager.broadcast_violation_alert(alert)
                    logger.warning(f"Broadcasted violation alert for {violation['identifier']}")
                finally:
                    db.close()

        except Exception as e:
            logger.error(f"Error broadcasting violation alerts: {e}")

    async def _check_new_violations(self, db: Session):
        """
        Check for new violations by comparing current state with previous state

        Args:
            db: Database session
        """
        try:
            # This is a simplified version - in production you would store previous states
            # and compare to detect actual new violations
            pass  # Placeholder for more sophisticated violation tracking

        except Exception as e:
            logger.error(f"Error checking new violations: {e}")

    async def _broadcast_heatmap_refresh(self, heatmap_data: Dict[str, Any]):
        """
        Broadcast heatmap refresh to connected WebSocket clients

        Args:
            heatmap_data: Heatmap data dictionary
        """
        try:
            # Extract relevant heatmap points for broadcasting
            heatmap_points = heatmap_data.get('heatmap_points', [])

            await manager.broadcast_heatmap_refresh(heatmap_points)
            logger.debug(f"Broadcasted heatmap refresh with {len(heatmap_points)} points")

        except Exception as e:
            logger.error(f"Error broadcasting heatmap refresh: {e}")

    def get_task_status(self) -> Dict[str, Any]:
        """
        Get current status of all background tasks

        Returns:
            Dictionary with task status information
        """
        return {
            'is_running': self.is_running,
            'tasks': {
                'cattle_simulation': {
                    'running': self.simulation_task is not None and not self.simulation_task.done(),
                    'last_update': self.last_cattle_update.isoformat() if self.last_cattle_update else None
                },
                'violation_detection': {
                    'running': self.violation_check_task is not None and not self.violation_check_task.done(),
                    'last_update': self.last_violation_check.isoformat() if self.last_violation_check else None
                },
                'heatmap_update': {
                    'running': self.heatmap_task is not None and not self.heatmap_task.done(),
                    'last_update': self.last_heatmap_update.isoformat() if self.last_heatmap_update else None
                }
            },
            'websocket_connections': len(manager.active_connections),
            'timestamp': datetime.utcnow().isoformat()
        }

    async def manual_cattle_update(self, geofence_id: Optional[uuid.UUID] = None):
        """
        Manually trigger a cattle position update

        Args:
            geofence_id: Optional geofence ID to constrain movement
        """
        db = SessionLocal()
        try:
            service = CattleSimulationService(db)
            updated_cattle = service.update_all_cattle_positions(geofence_id)

            if updated_cattle:
                await self._broadcast_cattle_updates(updated_cattle)
                self.last_cattle_update = datetime.utcnow()

            return f"Updated positions for {len(updated_cattle)} cattle"

        except Exception as e:
            logger.error(f"Error in manual cattle update: {e}")
            return f"Error: {str(e)}"
        finally:
            db.close()

    async def manual_violation_check(self):
        """
        Manually trigger a violation check
        """
        db = SessionLocal()
        try:
            service = GeofenceService(db)
            violations = service.detect_all_violations()

            if violations:
                await self._broadcast_violation_alerts(violations)
                self.last_violation_check = datetime.utcnow()

            return f"Detected {len(violations)} violations"

        except Exception as e:
            logger.error(f"Error in manual violation check: {e}")
            return f"Error: {str(e)}"
        finally:
            db.close()


# Global background task manager instance
background_manager = BackgroundTaskManager()


async def simulate_cattle_movement_task(app: FastAPI, db_session: Session):
    """
    Legacy function for backward compatibility

    Args:
        app: FastAPI application instance
        db_session: Database session (ignored, uses own session management)
    """
    logger.warning("Using legacy simulate_cattle_movement_task - consider using BackgroundTaskManager")
    await background_manager.start_simulation(app)


# Lifecycle event handlers
async def startup_event(app: FastAPI):
    """
    Handle application startup - start background tasks

    Args:
        app: FastAPI application instance
    """
    logger.info("🚀 Starting Sumbawa Digital Ranch background tasks...")
    await background_manager.start_simulation(app)


async def shutdown_event(app: FastAPI):
    """
    Handle application shutdown - stop background tasks

    Args:
        app: FastAPI application instance
    """
    logger.info("🛑 Stopping Sumbawa Digital Ranch background tasks...")
    await background_manager.stop_simulation()


# Global app reference for task management
_app_global = None

# API endpoints for task management
def register_task_management_routes(app: FastAPI):
    """
    Register API endpoints for background task management

    Args:
        app: FastAPI application instance
    """
    from fastapi import APIRouter, HTTPException

    global _app_global
    _app_global = app

    router = APIRouter(prefix="/api/tasks", tags=["background-tasks"])

    @router.get("/status")
    async def get_task_status():
        """
        Get current status of background tasks

        Returns:
            Task status information
        """
        return background_manager.get_task_status()

    @router.post("/cattle-update")
    async def trigger_cattle_update(
        geofence_id: Optional[str] = None
    ):
        """
        Manually trigger a cattle position update

        Args:
            geofence_id: Optional geofence ID to constrain movement

        Returns:
            Update result message
        """
        geofence_uuid = None
        if geofence_id:
            try:
                geofence_uuid = uuid.UUID(geofence_id)
            except ValueError:
                raise ValueError("Invalid geofence ID format")

        result = await background_manager.manual_cattle_update(geofence_uuid)
        return {"message": result, "timestamp": datetime.utcnow().isoformat()}

    @router.post("/violation-check")
    async def trigger_violation_check():
        """
        Manually trigger a violation check

        Returns:
            Violation check result message
        """
        result = await background_manager.manual_violation_check()
        return {"message": result, "timestamp": datetime.utcnow().isoformat()}

    @router.post("/restart")
    async def restart_tasks():
        """
        Restart all background tasks

        Returns:
            Restart result message
        """
        if _app_global is None:
            raise HTTPException(status_code=500, detail="Application not initialized")

        await background_manager.stop_simulation()
        await asyncio.sleep(1)  # Brief pause
        await background_manager.start_simulation(_app_global)

        return {
            "message": "Background tasks restarted successfully",
            "status": background_manager.get_task_status(),
            "timestamp": datetime.utcnow().isoformat()
        }

    app.include_router(router)