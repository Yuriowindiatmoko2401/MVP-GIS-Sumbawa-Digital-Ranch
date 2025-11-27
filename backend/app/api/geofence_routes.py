"""
Geofence API Routes for Sumbawa Digital Ranch MVP
Provides REST endpoints for geofence management and violation detection
"""
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.db import get_db
from app.services.geofence_service import GeofenceService
from app.models.geofence import Geofence


# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/geofences", tags=["geofences"])

# Pydantic models for request/response validation


class GeofenceCreate(BaseModel):
    """Model for creating a new geofence"""
    name: str = Field(..., min_length=1, max_length=200, description="Geofence name")
    coordinates: List[List[float]] = Field(..., description="List of coordinate pairs [[lng1, lat1], [lng2, lat2], ...]")
    description: Optional[str] = Field(None, description="Geofence description")


class GeofenceUpdate(BaseModel):
    """Model for updating geofence information"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Geofence name")
    description: Optional[str] = Field(None, description="Geofence description")
    coordinates: Optional[List[List[float]]] = Field(None, description="List of coordinate pairs [[lng1, lat1], [lng2, lat2], ...]")


class GeofenceResponse(BaseModel):
    """Model for geofence response"""
    id: str
    name: str
    is_active: bool
    description: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


# API Endpoints


@router.get("/", response_model=List[GeofenceResponse])
async def get_all_geofences(
    only_active: bool = Query(True, description="Only return active geofences"),
    db: Session = Depends(get_db)
):
    """
    Get all geofences in the system

    Args:
        only_active: Whether to only return active geofences
        db: Database session

    Returns:
        List of geofence objects
    """
    try:
        service = GeofenceService(db)
        geofences_with_status = service.get_all_geofences_with_status()

        # Filter by active status if requested
        if only_active:
            geofences_with_status = [
                gf for gf in geofences_with_status
                if gf.get('geofence_info', {}).get('is_active', False)
            ]

        # Convert to response model
        response_data = []
        for geofence_data in geofences_with_status:
            geofence_info = geofence_data.get('geofence_info', {})
            response_data.append(GeofenceResponse(**geofence_info))

        return response_data

    except Exception as e:
        logger.error(f"Error getting all geofences: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve geofence data")


@router.get("/{geofence_id}")
async def get_geofence_by_id(
    geofence_id: str,
    include_statistics: bool = Query(False, description="Include detailed statistics"),
    include_geometry: bool = Query(True, description="Include boundary geometry"),
    db: Session = Depends(get_db)
):
    """
    Get a specific geofence by ID

    Args:
        geofence_id: UUID of the geofence
        include_statistics: Whether to include detailed statistics
        include_geometry: Whether to include boundary geometry
        db: Database session

    Returns:
        Geofence object with optional statistics
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(geofence_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid geofence ID format")

        service = GeofenceService(db)
        stats = service.get_geofence_statistics(uuid.UUID(geofence_id))

        if 'error' in stats:
            raise HTTPException(status_code=404, detail=stats['error'])

        # Return basic geofence info or full statistics
        if include_statistics:
            return stats
        else:
            geofence_info = stats.get('geofence_info', {})
            return geofence_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting geofence {geofence_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve geofence data")


@router.post("/", response_model=GeofenceResponse)
async def create_geofence(geofence_create: GeofenceCreate, db: Session = Depends(get_db)):
    """
    Create a new geofence

    Args:
        geofence_create: Geofence creation data
        db: Database session

    Returns:
        Created geofence object
    """
    try:
        # Validate coordinates
        if len(geofence_create.coordinates) < 3:
            raise HTTPException(status_code=400, detail="Geofence must have at least 3 coordinate points")

        service = GeofenceService(db)
        geofence = service.create_geofence(
            name=geofence_create.name,
            coordinates=geofence_create.coordinates,
            description=geofence_create.description
        )

        geofence_data = geofence.to_dict()
        return GeofenceResponse(**geofence_data)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating geofence: {e}")
        raise HTTPException(status_code=500, detail="Failed to create geofence")


@router.put("/{geofence_id}", response_model=GeofenceResponse)
async def update_geofence(
    geofence_id: str,
    geofence_update: GeofenceUpdate,
    db: Session = Depends(get_db)
):
    """
    Update geofence information

    Args:
        geofence_id: UUID of the geofence
        geofence_update: Geofence update data
        db: Database session

    Returns:
        Updated geofence object
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(geofence_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid geofence ID format")

        service = GeofenceService(db)
        success = service.update_geofence(
            geofence_id=uuid.UUID(geofence_id),
            name=geofence_update.name,
            description=geofence_update.description,
            coordinates=geofence_update.coordinates
        )

        if not success:
            raise HTTPException(status_code=404, detail="Geofence not found")

        # Get updated geofence
        geofence = db.query(Geofence).filter(Geofence.id == geofence_id).first()
        geofence_data = geofence.to_dict()
        return GeofenceResponse(**geofence_data)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating geofence {geofence_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update geofence")


@router.post("/{geofence_id}/activate")
async def activate_geofence(geofence_id: str, db: Session = Depends(get_db)):
    """
    Activate a geofence

    Args:
        geofence_id: UUID of the geofence
        db: Database session

    Returns:
        Success message
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(geofence_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid geofence ID format")

        service = GeofenceService(db)
        success = service.activate_geofence(uuid.UUID(geofence_id))

        if not success:
            raise HTTPException(status_code=404, detail="Geofence not found")

        return {"message": "Geofence activated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating geofence {geofence_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to activate geofence")


@router.post("/{geofence_id}/deactivate")
async def deactivate_geofence(geofence_id: str, db: Session = Depends(get_db)):
    """
    Deactivate a geofence

    Args:
        geofence_id: UUID of the geofence
        db: Database session

    Returns:
        Success message
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(geofence_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid geofence ID format")

        service = GeofenceService(db)
        success = service.deactivate_geofence(uuid.UUID(geofence_id))

        if not success:
            raise HTTPException(status_code=404, detail="Geofence not found")

        return {"message": "Geofence deactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating geofence {geofence_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate geofence")


@router.get("/{geofence_id}/violations")
async def get_geofence_violations(geofence_id: str, db: Session = Depends(get_db)):
    """
    Get current violations for a specific geofence

    Args:
        geofence_id: UUID of the geofence
        db: Database session

    Returns:
        List of current violations
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(geofence_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid geofence ID format")

        service = GeofenceService(db)
        violations = service.detect_violations(uuid.UUID(geofence_id))

        return {
            "geofence_id": geofence_id,
            "violations_count": len(violations),
            "violations": violations,
            "detection_timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting geofence violations {geofence_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve violations")


@router.get("/violations/all")
async def get_all_violations(db: Session = Depends(get_db)):
    """
    Get all violations across all active geofences

    Args:
        db: Database session

    Returns:
        List of all current violations
    """
    try:
        service = GeofenceService(db)
        all_violations = service.detect_all_violations()

        return {
            "total_violations": len(all_violations),
            "violations": all_violations,
            "detection_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting all violations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve violations")


@router.get("/{geofence_id}/statistics")
async def get_geofence_statistics(geofence_id: str, db: Session = Depends(get_db)):
    """
    Get comprehensive statistics for a specific geofence

    Args:
        geofence_id: UUID of the geofence
        db: Database session

    Returns:
        Detailed geofence statistics
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(geofence_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid geofence ID format")

        service = GeofenceService(db)
        stats = service.get_geofence_statistics(uuid.UUID(geofence_id))

        if 'error' in stats:
            raise HTTPException(status_code=404, detail=stats['error'])

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting geofence statistics {geofence_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/status/all")
async def get_all_geofences_with_status(db: Session = Depends(get_db)):
    """
    Get all active geofences with their current status and statistics

    Args:
        db: Database session

    Returns:
        List of geofence status information
    """
    try:
        service = GeofenceService(db)
        geofence_statuses = service.get_all_geofences_with_status()

        return geofence_statuses

    except Exception as e:
        logger.error(f"Error getting all geofences with status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve geofence status")


@router.get("/cattle/{cattle_id}/status")
async def get_cattle_geofence_status(cattle_id: str, db: Session = Depends(get_db)):
    """
    Get geofence status for a specific cattle

    Args:
        cattle_id: UUID of the cattle
        db: Database session

    Returns:
        Cattle geofence status information
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(cattle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cattle ID format")

        service = GeofenceService(db)
        status = service.get_cattle_geofence_status(uuid.UUID(cattle_id))

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cattle geofence status {cattle_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cattle geofence status")


@router.post("/check-point")
async def check_point_in_geofences(
    latitude: float = Query(..., ge=-90, le=90, description="Point latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Point longitude"),
    db: Session = Depends(get_db)
):
    """
    Check which geofences contain a specific point

    Args:
        latitude: Point latitude
        longitude: Point longitude
        db: Database session

    Returns:
        List of geofences that contain the point
    """
    try:
        service = GeofenceService(db)
        active_geofences = db.query(Geofence).filter(Geofence.is_active == True).all()

        point_geofences = []
        point_info = {
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': datetime.utcnow().isoformat()
        }

        for geofence in active_geofences:
            try:
                is_within = geofence.contains_point(latitude, longitude)
                geofence_data = {
                    'geofence_id': str(geofence.id),
                    'geofence_name': geofence.name,
                    'is_within': is_within,
                    'description': geofence.description
                }

                if not is_within:
                    # Calculate distance from geofence
                    distance = geofence.get_distance_to_point(latitude, longitude)
                    if distance is not None:
                        geofence_data['distance_meters'] = distance

                point_geofences.append(geofence_data)

            except Exception as e:
                logger.error(f"Error checking point in geofence {geofence.name}: {e}")
                continue

        return {
            'point_info': point_info,
            'geofences': point_geofences,
            'within_any_geofence': any(gf['is_within'] for gf in point_geofences),
            'violations': [gf for gf in point_geofences if not gf['is_within'] and gf.get('distance_meters', 0) > 0]
        }

    except Exception as e:
        logger.error(f"Error checking point in geofences: {e}")
        raise HTTPException(status_code=500, detail="Failed to check point in geofences")


@router.delete("/{geofence_id}")
async def delete_geofence(geofence_id: str, db: Session = Depends(get_db)):
    """
    Delete a geofence

    Args:
        geofence_id: UUID of the geofence
        db: Database session

    Returns:
        Success message
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(geofence_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid geofence ID format")

        # Check if geofence exists
        geofence = db.query(Geofence).filter(Geofence.id == geofence_id).first()
        if not geofence:
            raise HTTPException(status_code=404, detail="Geofence not found")

        # Delete geofence
        db.delete(geofence)
        db.commit()

        return {"message": "Geofence deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting geofence {geofence_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete geofence")