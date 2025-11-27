"""
Resource API Routes for Sumbawa Digital Ranch MVP
Provides REST endpoints for resource management (water, feed, shelter)
"""
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.db import get_db
from app.services.resource_service import ResourceService
from app.models.resource import Resource, ResourceTypeEnum


# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/resources", tags=["resources"])

# Pydantic models for request/response validation


class ResourceCreate(BaseModel):
    """Model for creating a new resource"""
    resource_type: str = Field(..., description="Resource type (water_trough, feeding_station, shelter)")
    name: str = Field(..., min_length=1, max_length=200, description="Resource name")
    latitude: float = Field(..., ge=-90, le=90, description="GPS latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="GPS longitude coordinate")
    description: Optional[str] = Field(None, description="Resource description")
    capacity: Optional[int] = Field(None, ge=0, description="Resource capacity")


class ResourceUpdate(BaseModel):
    """Model for updating resource information"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Resource name")
    description: Optional[str] = Field(None, description="Resource description")
    capacity: Optional[int] = Field(None, ge=0, description="Resource capacity")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="GPS latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="GPS longitude coordinate")


class ResourceResponse(BaseModel):
    """Model for resource response"""
    id: str
    resource_type: str
    name: str
    display_name: str
    type_display_name: str
    color: str
    location: Optional[Dict[str, float]]
    description: Optional[str]
    capacity: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]


# API Endpoints


@router.get("/", response_model=List[ResourceResponse])
async def get_all_resources(
    include_location: bool = Query(True, description="Include GPS coordinates"),
    include_metrics: bool = Query(False, description="Include usage metrics"),
    db: Session = Depends(get_db)
):
    """
    Get all resources in the system

    Args:
        include_location: Whether to include GPS coordinates
        include_metrics: Whether to include usage metrics
        db: Database session

    Returns:
        List of resource objects
    """
    try:
        service = ResourceService(db)
        resources = service.get_all_resources(include_location, include_metrics)

        # Convert to response model
        response_data = []
        for resource in resources:
            response_data.append(ResourceResponse(**resource))

        return response_data

    except Exception as e:
        logger.error(f"Error getting all resources: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve resource data")


@router.get("/types")
async def get_resource_types(db: Session = Depends(get_db)):
    """
    Get available resource types with descriptions

    Args:
        db: Database session

    Returns:
        List of available resource types
    """
    return [
        {
            "type": ResourceTypeEnum.WATER_TROUGH,
            "display_name": "Water Trough",
            "description": "Water supply points for cattle",
            "icon": "💧",
            "color": "#2196F3"
        },
        {
            "type": ResourceTypeEnum.FEEDING_STATION,
            "display_name": "Feeding Station",
            "description": "Feeding areas for cattle",
            "icon": "🌾",
            "color": "#FF9800"
        },
        {
            "type": ResourceTypeEnum.SHELTER,
            "display_name": "Shelter",
            "description": "Shelter areas for cattle",
            "icon": "🏠",
            "color": "#607D8B"
        }
    ]


@router.get("/type/{resource_type}", response_model=List[ResourceResponse])
async def get_resources_by_type(
    resource_type: str,
    include_location: bool = Query(True, description="Include GPS coordinates"),
    db: Session = Depends(get_db)
):
    """
    Get resources filtered by type

    Args:
        resource_type: Type of resource (water_trough, feeding_station, shelter)
        include_location: Whether to include GPS coordinates
        db: Database session

    Returns:
        List of filtered resource objects
    """
    try:
        service = ResourceService(db)
        resources = service.get_resources_by_type(resource_type, include_location)

        # Convert to response model
        response_data = []
        for resource in resources:
            response_data.append(ResourceResponse(**resource))

        return response_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting resources by type {resource_type}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve resource data")


@router.get("/nearby", response_model=List[ResourceResponse])
async def get_nearby_resources(
    latitude: float = Query(..., ge=-90, le=90, description="Reference point latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Reference point longitude"),
    radius_meters: float = Query(500, ge=10, le=10000, description="Search radius in meters"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    db: Session = Depends(get_db)
):
    """
    Get resources within specified radius from a point

    Args:
        latitude: Reference point latitude
        longitude: Reference point longitude
        radius_meters: Search radius in meters
        resource_type: Optional filter by resource type
        db: Database session

    Returns:
        List of nearby resources with distance information
    """
    try:
        service = ResourceService(db)
        resources = service.get_resources_near_point(
            latitude, longitude, radius_meters, resource_type
        )

        # Convert to response model
        response_data = []
        for resource in resources:
            response_data.append(ResourceResponse(**resource))

        return response_data

    except Exception as e:
        logger.error(f"Error getting nearby resources: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve nearby resources")


@router.get("/nearest")
async def get_nearest_resource(
    latitude: float = Query(..., ge=-90, le=90, description="Reference point latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Reference point longitude"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    max_distance_meters: float = Query(1000, ge=10, le=10000, description="Maximum search distance"),
    db: Session = Depends(get_db)
):
    """
    Get the nearest resource to a point

    Args:
        latitude: Reference point latitude
        longitude: Reference point longitude
        resource_type: Optional filter by resource type
        max_distance_meters: Maximum search distance
        db: Database session

    Returns:
        Nearest resource with distance information
    """
    try:
        service = ResourceService(db)
        resource = service.get_nearest_resource(
            latitude, longitude, resource_type, max_distance_meters
        )

        if not resource:
            raise HTTPException(status_code=404, detail="No resources found within specified distance")

        return resource

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting nearest resource: {e}")
        raise HTTPException(status_code=500, detail="Failed to find nearest resource")


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource_by_id(
    resource_id: str,
    include_location: bool = Query(True, description="Include GPS coordinates"),
    db: Session = Depends(get_db)
):
    """
    Get a specific resource by ID

    Args:
        resource_id: UUID of the resource
        include_location: Whether to include GPS coordinates
        db: Database session

    Returns:
        Resource object
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(resource_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid resource ID format")

        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        resource_data = resource.to_dict(include_location=include_location)
        return ResourceResponse(**resource_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resource {resource_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve resource data")


@router.post("/", response_model=ResourceResponse)
async def create_resource(resource_create: ResourceCreate, db: Session = Depends(get_db)):
    """
    Create a new resource

    Args:
        resource_create: Resource creation data
        db: Database session

    Returns:
        Created resource object
    """
    try:
        service = ResourceService(db)
        resource = service.create_resource(
            resource_type=resource_create.resource_type,
            name=resource_create.name,
            latitude=resource_create.latitude,
            longitude=resource_create.longitude,
            description=resource_create.description,
            capacity=resource_create.capacity
        )

        resource_data = resource.to_dict(include_location=True)
        return ResourceResponse(**resource_data)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating resource: {e}")
        raise HTTPException(status_code=500, detail="Failed to create resource")


@router.put("/{resource_id}", response_model=ResourceResponse)
async def update_resource(
    resource_id: str,
    resource_update: ResourceUpdate,
    db: Session = Depends(get_db)
):
    """
    Update resource information

    Args:
        resource_id: UUID of the resource
        resource_update: Resource update data
        db: Database session

    Returns:
        Updated resource object
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(resource_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid resource ID format")

        service = ResourceService(db)
        success = service.update_resource(
            resource_id=uuid.UUID(resource_id),
            name=resource_update.name,
            description=resource_update.description,
            capacity=resource_update.capacity,
            latitude=resource_update.latitude,
            longitude=resource_update.longitude
        )

        if not success:
            raise HTTPException(status_code=404, detail="Resource not found")

        # Get updated resource
        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        resource_data = resource.to_dict(include_location=True)
        return ResourceResponse(**resource_data)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating resource {resource_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update resource")


@router.delete("/{resource_id}")
async def delete_resource(resource_id: str, db: Session = Depends(get_db)):
    """
    Delete a resource

    Args:
        resource_id: UUID of the resource
        db: Database session

    Returns:
        Success message
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(resource_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid resource ID format")

        service = ResourceService(db)
        success = service.delete_resource(uuid.UUID(resource_id))

        if not success:
            raise HTTPException(status_code=404, detail="Resource not found")

        return {"message": "Resource deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting resource {resource_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete resource")


@router.get("/water/all", response_model=List[ResourceResponse])
async def get_water_resources(
    include_location: bool = Query(True, description="Include GPS coordinates"),
    db: Session = Depends(get_db)
):
    """
    Get all water resources

    Args:
        include_location: Whether to include GPS coordinates
        db: Database session

    Returns:
        List of water resource objects
    """
    try:
        service = ResourceService(db)
        resources = service.get_water_resources(include_location)

        # Convert to response model
        response_data = []
        for resource in resources:
            response_data.append(ResourceResponse(**resource))

        return response_data

    except Exception as e:
        logger.error(f"Error getting water resources: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve water resources")


@router.get("/feeding/all", response_model=List[ResourceResponse])
async def get_feeding_resources(
    include_location: bool = Query(True, description="Include GPS coordinates"),
    db: Session = Depends(get_db)
):
    """
    Get all feeding station resources

    Args:
        include_location: Whether to include GPS coordinates
        db: Database session

    Returns:
        List of feeding station objects
    """
    try:
        service = ResourceService(db)
        resources = service.get_feeding_resources(include_location)

        # Convert to response model
        response_data = []
        for resource in resources:
            response_data.append(ResourceResponse(**resource))

        return response_data

    except Exception as e:
        logger.error(f"Error getting feeding resources: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve feeding resources")


@router.get("/shelter/all", response_model=List[ResourceResponse])
async def get_shelter_resources(
    include_location: bool = Query(True, description="Include GPS coordinates"),
    db: Session = Depends(get_db)
):
    """
    Get all shelter resources

    Args:
        include_location: Whether to include GPS coordinates
        db: Database session

    Returns:
        List of shelter objects
    """
    try:
        service = ResourceService(db)
        resources = service.get_shelter_resources(include_location)

        # Convert to response model
        response_data = []
        for resource in resources:
            response_data.append(ResourceResponse(**resource))

        return response_data

    except Exception as e:
        logger.error(f"Error getting shelter resources: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve shelter resources")


@router.post("/analyze-accessibility")
async def analyze_resource_accessibility(
    cattle_positions: List[Dict[str, float]],
    max_distance_meters: float = Query(500, ge=10, le=2000, description="Maximum distance for accessibility"),
    db: Session = Depends(get_db)
):
    """
    Analyze resource accessibility for given cattle positions

    Args:
        cattle_positions: List of cattle GPS positions [{'lat': x, 'lng': y}, ...]
        max_distance_meters: Maximum distance to consider resource accessible
        db: Database session

    Returns:
        Accessibility analysis results
    """
    try:
        if not cattle_positions:
            raise HTTPException(status_code=400, detail="No cattle positions provided")

        service = ResourceService(db)
        analysis = service.analyze_resource_accessibility(cattle_positions, max_distance_meters)

        return analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing resource accessibility: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze resource accessibility")


@router.get("/utilization-heatmap")
async def get_resource_utilization_heatmap(
    hours_back: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    grid_size_meters: float = Query(100, ge=10, le=500, description="Grid size in meters"),
    db: Session = Depends(get_db)
):
    """
    Generate resource utilization heatmap based on cattle activity

    Args:
        hours_back: Number of hours to analyze
        grid_size_meters: Size of grid cells for heatmap
        db: Database session

    Returns:
        Heatmap data with resource analysis
    """
    try:
        service = ResourceService(db)
        heatmap_data = service.get_resource_utilization_heatmap(hours_back, grid_size_meters)

        return heatmap_data

    except Exception as e:
        logger.error(f"Error generating resource utilization heatmap: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate utilization heatmap")


@router.get("/density-analysis")
async def get_resource_density_analysis(
    geofence_wkt: str = Query(..., description="Geofence polygon in WKT format"),
    db: Session = Depends(get_db)
):
    """
    Analyze resource density within a geofenced area

    Args:
        geofence_wkt: Geofence polygon in Well-Known Text format
        db: Database session

    Returns:
        Resource density analysis
    """
    try:
        service = ResourceService(db)
        analysis = service.get_resource_density_analysis(geofence_wkt)

        return analysis

    except Exception as e:
        logger.error(f"Error analyzing resource density: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze resource density")


@router.get("/summary-stats")
async def get_resource_summary_stats(db: Session = Depends(get_db)):
    """
    Get summary statistics for all resources

    Args:
        db: Database session

    Returns:
        Resource summary statistics
    """
    try:
        service = ResourceService(db)
        stats = service.get_resource_summary_stats()

        return stats

    except Exception as e:
        logger.error(f"Error getting resource summary stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve resource statistics")