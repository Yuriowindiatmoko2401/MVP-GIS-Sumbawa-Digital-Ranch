"""
Cattle API Routes for Sumbawa Digital Ranch MVP
Provides REST endpoints for cattle management and tracking
"""
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.db import get_db
from app.services.cattle_service import CattleSimulationService
from app.models.cattle import Cattle, HealthStatusEnum


# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/cattle", tags=["cattle"])

# Pydantic models for request/response validation


class CattleCreate(BaseModel):
    """Model for creating a new cattle"""
    identifier: str = Field(..., min_length=1, max_length=50, description="Unique cattle identifier")
    age: int = Field(..., ge=0, le=30, description="Age in years")
    health_status: str = Field(..., description="Health status (Sehat, Perlu Perhatian, Sakit)")
    latitude: float = Field(..., ge=-90, le=90, description="GPS latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="GPS longitude coordinate")


class CattleUpdate(BaseModel):
    """Model for updating cattle information"""
    age: Optional[int] = Field(None, ge=0, le=30, description="Age in years")
    health_status: Optional[str] = Field(None, description="Health status (Sehat, Perlu Perhatian, Sakit)")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="GPS latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="GPS longitude coordinate")


class CattlePositionUpdate(BaseModel):
    """Model for updating cattle position"""
    latitude: float = Field(..., ge=-90, le=90, description="GPS latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="GPS longitude coordinate")


class CattleResponse(BaseModel):
    """Model for cattle response"""
    id: str
    identifier: str
    age: int
    health_status: str
    location: Optional[Dict[str, float]]
    last_update: Optional[str]
    created_at: Optional[str]


# API Endpoints


@router.get("/", response_model=List[CattleResponse])
async def get_all_cattle(
    include_history: bool = Query(False, description="Include recent position history"),
    history_hours: int = Query(24, ge=1, le=168, description="Hours of history to include"),
    db: Session = Depends(get_db)
):
    """
    Get all cattle with their current positions and optional history

    Args:
        include_history: Whether to include recent position history
        history_hours: Number of hours of history to include
        db: Database session

    Returns:
        List of cattle objects with current positions
    """
    try:
        service = CattleSimulationService(db)
        cattle_data = service.get_all_cattle_with_location(include_history, history_hours)

        # Convert to response model
        response_data = []
        for cattle in cattle_data:
            response_data.append(CattleResponse(**cattle))

        return response_data

    except Exception as e:
        logger.error(f"Error getting all cattle: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cattle data")


@router.get("/{cattle_id}", response_model=CattleResponse)
async def get_cattle_by_id(
    cattle_id: str,
    include_history: bool = Query(False, description="Include recent position history"),
    history_hours: int = Query(24, ge=1, le=168, description="Hours of history to include"),
    db: Session = Depends(get_db)
):
    """
    Get a specific cattle by ID with optional history

    Args:
        cattle_id: UUID of the cattle
        include_history: Whether to include recent position history
        history_hours: Number of hours of history to include
        db: Database session

    Returns:
        Cattle object with current position
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(cattle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cattle ID format")

        service = CattleSimulationService(db)
        cattle_data = service.get_all_cattle_with_location(include_history, history_hours)

        # Find the specific cattle
        cattle = next((c for c in cattle_data if c['id'] == cattle_id), None)
        if not cattle:
            raise HTTPException(status_code=404, detail="Cattle not found")

        return CattleResponse(**cattle)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cattle {cattle_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cattle data")


@router.get("/identifier/{identifier}", response_model=CattleResponse)
async def get_cattle_by_identifier(
    identifier: str,
    include_history: bool = Query(False, description="Include recent position history"),
    history_hours: int = Query(24, ge=1, le=168, description="Hours of history to include"),
    db: Session = Depends(get_db)
):
    """
    Get a specific cattle by identifier with optional history

    Args:
        identifier: Cattle identifier (e.g., "SAPI-001")
        include_history: Whether to include recent position history
        history_hours: Number of hours of history to include
        db: Database session

    Returns:
        Cattle object with current position
    """
    try:
        service = CattleSimulationService(db)
        cattle = service.get_cattle_by_identifier(identifier)
        if not cattle:
            raise HTTPException(status_code=404, detail=f"Cattle with identifier '{identifier}' not found")

        # Get cattle data with optional history
        cattle_data_list = service.get_all_cattle_with_location(include_history, history_hours)
        cattle_data = next((c for c in cattle_data_list if c['id'] == str(cattle.id)), None)

        if not cattle_data:
            # Fallback to basic cattle data
            cattle_data = cattle.to_dict(include_location=True)

        return CattleResponse(**cattle_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cattle by identifier {identifier}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cattle data")


@router.post("/", response_model=CattleResponse)
async def create_cattle(cattle_create: CattleCreate, db: Session = Depends(get_db)):
    """
    Create a new cattle record

    Args:
        cattle_create: Cattle creation data
        db: Database session

    Returns:
        Created cattle object
    """
    try:
        # Validate health status
        valid_statuses = [HealthStatusEnum.SEHAT, HealthStatusEnum.PERLU_PERHATIAN,
                         HealthStatusEnum.SAKIT]
        if cattle_create.health_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid health status. Must be one of: {valid_statuses}"
            )

        service = CattleSimulationService(db)
        cattle = service.add_cattle(
            identifier=cattle_create.identifier,
            age=cattle_create.age,
            health_status=cattle_create.health_status,
            latitude=cattle_create.latitude,
            longitude=cattle_create.longitude
        )

        return CattleResponse(**cattle.to_dict(include_location=True))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating cattle: {e}")
        raise HTTPException(status_code=500, detail="Failed to create cattle")


@router.put("/{cattle_id}", response_model=CattleResponse)
async def update_cattle(
    cattle_id: str,
    cattle_update: CattleUpdate,
    db: Session = Depends(get_db)
):
    """
    Update cattle information

    Args:
        cattle_id: UUID of the cattle
        cattle_update: Cattle update data
        db: Database session

    Returns:
        Updated cattle object
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(cattle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cattle ID format")

        # Get cattle
        cattle = db.query(Cattle).filter(Cattle.id == cattle_id).first()
        if not cattle:
            raise HTTPException(status_code=404, detail="Cattle not found")

        # Validate health status if provided
        if cattle_update.health_status:
            valid_statuses = [HealthStatusEnum.SEHAT, HealthStatusEnum.PERLU_PERHATIAN,
                             HealthStatusEnum.SAKIT]
            if cattle_update.health_status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid health status. Must be one of: {valid_statuses}"
                )
            cattle.update_health_status(cattle_update.health_status)

        # Update age if provided
        if cattle_update.age is not None:
            cattle.age = cattle_update.age

        # Update location if provided
        if cattle_update.latitude is not None and cattle_update.longitude is not None:
            cattle.set_location(cattle_update.latitude, cattle_update.longitude)

        db.commit()
        db.refresh(cattle)

        return CattleResponse(**cattle.to_dict(include_location=True))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cattle {cattle_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update cattle")


@router.patch("/{cattle_id}/position")
async def update_cattle_position(
    cattle_id: str,
    position_update: CattlePositionUpdate,
    db: Session = Depends(get_db)
):
    """
    Update cattle position only

    Args:
        cattle_id: UUID of the cattle
        position_update: New position data
        db: Database session

    Returns:
        Success message
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(cattle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cattle ID format")

        # Get cattle
        cattle = db.query(Cattle).filter(Cattle.id == cattle_id).first()
        if not cattle:
            raise HTTPException(status_code=404, detail="Cattle not found")

        # Add current position to history
        from app.models.cattle_history import CattleHistory
        current_coords = cattle.get_coordinates()
        if current_coords:
            history = CattleHistory(
                cattle_id=cattle.id,
                latitude=current_coords['lat'],
                longitude=current_coords['lng'],
                timestamp=datetime.utcnow()
            )
            db.add(history)

        # Update position
        cattle.set_location(position_update.latitude, position_update.longitude)
        db.commit()

        return {"message": "Cattle position updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cattle position {cattle_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update cattle position")


@router.get("/{cattle_id}/history")
async def get_cattle_history(
    cattle_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours of history to retrieve"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    db: Session = Depends(get_db)
):
    """
    Get position history for a specific cattle

    Args:
        cattle_id: UUID of the cattle
        hours: Number of hours of history to retrieve
        limit: Maximum number of records to return
        db: Database session

    Returns:
        List of historical positions
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(cattle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cattle ID format")

        # Check if cattle exists
        cattle = db.query(Cattle).filter(Cattle.id == cattle_id).first()
        if not cattle:
            raise HTTPException(status_code=404, detail="Cattle not found")

        # Get history
        from app.models.cattle_history import CattleHistory
        from datetime import timedelta

        start_time = datetime.utcnow() - timedelta(hours=hours)
        history = db.query(CattleHistory).filter(
            CattleHistory.cattle_id == cattle_id,
            CattleHistory.timestamp >= start_time
        ).order_by(CattleHistory.timestamp.desc()).limit(limit).all()

        return [
            {
                'id': str(record.id),
                'location': record.get_coordinates(),
                'timestamp': record.timestamp.isoformat()
            }
            for record in history
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cattle history {cattle_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cattle history")


@router.get("/{cattle_id}/movement-summary")
async def get_cattle_movement_summary(
    cattle_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get movement summary for a specific cattle

    Args:
        cattle_id: UUID of the cattle
        hours: Number of hours to analyze
        db: Database session

    Returns:
        Movement summary statistics
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(cattle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cattle ID format")

        service = CattleSimulationService(db)
        summary = service.get_cattle_movement_summary(uuid.UUID(cattle_id), hours)

        if 'error' in summary:
            raise HTTPException(status_code=404, detail=summary['error'])

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting movement summary {cattle_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve movement summary")


@router.post("/simulate-movement")
async def simulate_cattle_movement(
    geofence_id: Optional[str] = Query(None, description="Optional geofence ID to constrain movement"),
    db: Session = Depends(get_db)
):
    """
    Simulate movement for all cattle

    Args:
        geofence_id: Optional geofence UUID to restrict movement within
        db: Database session

    Returns:
        Updated cattle positions
    """
    try:
        # Validate geofence ID if provided
        geofence_uuid = None
        if geofence_id:
            try:
                geofence_uuid = uuid.UUID(geofence_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid geofence ID format")

        service = CattleSimulationService(db)
        updated_cattle = service.update_all_cattle_positions(geofence_uuid)

        return {
            "message": f"Updated positions for {len(updated_cattle)} cattle",
            "updated_cattle": [
                cattle.to_dict(include_location=True) for cattle in updated_cattle
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error simulating cattle movement: {e}")
        raise HTTPException(status_code=500, detail="Failed to simulate cattle movement")


@router.delete("/{cattle_id}")
async def delete_cattle(cattle_id: str, db: Session = Depends(get_db)):
    """
    Delete a cattle and all its history

    Args:
        cattle_id: UUID of the cattle
        db: Database session

    Returns:
        Success message
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(cattle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cattle ID format")

        service = CattleSimulationService(db)
        success = service.remove_cattle(uuid.UUID(cattle_id))

        if not success:
            raise HTTPException(status_code=404, detail="Cattle not found")

        return {"message": "Cattle deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting cattle {cattle_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete cattle")


@router.get("/positions/at-time")
async def get_cattle_positions_at_time(
    timestamp: str = Query(..., description="ISO format timestamp (YYYY-MM-DDTHH:MM:SS)"),
    db: Session = Depends(get_db)
):
    """
    Get all cattle positions at a specific historical timestamp

    Args:
        timestamp: Historical timestamp in ISO format
        db: Database session

    Returns:
        List of cattle with positions at the specified time
    """
    try:
        # Parse timestamp
        try:
            target_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

        service = CattleSimulationService(db)
        positions = service.get_cattle_positions_at_time(target_time)

        return positions

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cattle positions at time {timestamp}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve historical positions")