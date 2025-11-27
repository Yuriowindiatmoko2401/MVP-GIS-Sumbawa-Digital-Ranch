"""
Heatmap API Routes for Sumbawa Digital Ranch MVP
Provides REST endpoints for cattle activity heatmap analysis
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database.db import get_db
from app.services.heatmap_service import HeatmapService


# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/heatmap", tags=["heatmap"])

# Pydantic models for request/response validation


class HeatmapRequest(BaseModel):
    """Model for heatmap request parameters"""
    hours_back: int = Field(24, ge=1, le=168, description="Number of hours to analyze")
    grid_size_meters: float = Field(100, ge=10, le=500, description="Grid size in meters")
    time_buckets: Optional[int] = Field(None, ge=2, le=24, description="Number of time buckets")


class ActivityZonesRequest(BaseModel):
    """Model for activity zones analysis"""
    hours_back: int = Field(24, ge=1, le=168, description="Number of hours to analyze")
    min_activity_threshold: int = Field(5, ge=1, le=100, description="Minimum activity threshold")
    cluster_radius_meters: float = Field(150, ge=50, le=500, description="Clustering radius in meters")


class MovementPatternsRequest(BaseModel):
    """Model for movement patterns analysis"""
    hours_back: int = Field(24, ge=1, le=168, description="Number of hours to analyze")
    cattle_filter: Optional[List[str]] = Field(None, description="Optional list of cattle IDs")


# API Endpoints


@router.get("/")
async def get_heatmap_data(
    hours_back: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    grid_size_meters: float = Query(100, ge=10, le=500, description="Grid size in meters"),
    time_buckets: Optional[int] = Query(None, ge=2, le=24, description="Number of time buckets"),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive heatmap data for cattle activity

    Args:
        hours_back: Number of hours to analyze
        grid_size_meters: Size of grid cells in meters
        time_buckets: Number of time buckets to divide analysis (optional)
        db: Database session

    Returns:
        Comprehensive heatmap data and analysis
    """
    try:
        service = HeatmapService(db)
        heatmap_data = service.get_heatmap_data(hours_back, grid_size_meters, time_buckets)

        return heatmap_data

    except Exception as e:
        logger.error(f"Error generating heatmap data: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate heatmap data")


@router.get("/geojson")
async def get_heatmap_geojson(
    hours_back: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    grid_size_meters: float = Query(100, ge=10, le=500, description="Grid size in meters"),
    intensity_scale: str = Query("linear", regex="^(linear|log|sqrt)$", description="Intensity scaling method"),
    db: Session = Depends(get_db)
):
    """
    Generate heatmap data in GeoJSON format for mapping

    Args:
        hours_back: Number of hours to analyze
        grid_size_meters: Size of grid cells in meters
        intensity_scale: Type of intensity scaling ('linear', 'log', 'sqrt')
        db: Database session

    Returns:
        GeoJSON FeatureCollection with heatmap data
    """
    try:
        service = HeatmapService(db)
        geojson_data = service.get_heatmap_geojson(hours_back, grid_size_meters, intensity_scale)

        return geojson_data

    except Exception as e:
        logger.error(f"Error generating heatmap GeoJSON: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate heatmap GeoJSON")


@router.get("/activity-zones")
async def get_activity_zones(
    hours_back: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    min_activity_threshold: int = Query(5, ge=1, le=100, description="Minimum activity threshold"),
    cluster_radius_meters: float = Query(150, ge=50, le=500, description="Clustering radius in meters"),
    db: Session = Depends(get_db)
):
    """
    Identify high-activity zones and clustering patterns

    Args:
        hours_back: Number of hours to analyze
        min_activity_threshold: Minimum activity points to consider a zone
        cluster_radius_meters: Radius for clustering points
        db: Database session

    Returns:
        Dictionary with activity zone analysis
    """
    try:
        service = HeatmapService(db)
        zones_data = service.get_activity_zones(
            hours_back, min_activity_threshold, cluster_radius_meters
        )

        return zones_data

    except Exception as e:
        logger.error(f"Error analyzing activity zones: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze activity zones")


@router.get("/movement-patterns")
async def get_movement_patterns(
    hours_back: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    cattle_filter: Optional[str] = Query(None, description="Comma-separated list of cattle IDs"),
    db: Session = Depends(get_db)
):
    """
    Analyze movement patterns and behaviors

    Args:
        hours_back: Number of hours to analyze
        cattle_filter: Optional comma-separated list of cattle IDs
        db: Database session

    Returns:
        Dictionary with movement pattern analysis
    """
    try:
        # Parse cattle filter if provided
        cattle_ids = None
        if cattle_filter:
            cattle_ids = [cattle_id.strip() for cattle_id in cattle_filter.split(',') if cattle_id.strip()]

        service = HeatmapService(db)
        patterns_data = service.get_movement_patterns(hours_back, cattle_ids)

        return patterns_data

    except Exception as e:
        logger.error(f"Error analyzing movement patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze movement patterns")


@router.get("/compare-periods")
async def compare_periods(
    current_hours: int = Query(24, ge=1, le=168, description="Hours for current period"),
    previous_hours: int = Query(24, ge=1, le=168, description="Hours for previous period"),
    db: Session = Depends(get_db)
):
    """
    Compare activity between two time periods

    Args:
        current_hours: Hours for current period (ending now)
        previous_hours: Hours for previous period (ending current_hours ago)
        db: Database session

    Returns:
        Dictionary with comparative analysis
    """
    try:
        service = HeatmapService(db)
        comparison_data = service.compare_periods(current_hours, previous_hours)

        return comparison_data

    except Exception as e:
        logger.error(f"Error comparing periods: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare periods")


@router.get("/summary")
async def get_heatmap_summary(
    hours_back: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for heatmap analysis

    Args:
        hours_back: Number of hours to analyze
        db: Database session

    Returns:
        Summary statistics
    """
    try:
        service = HeatmapService(db)

        # Get basic heatmap data
        start_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Get activity zones for summary
        zones_data = service.get_activity_zones(hours_back)

        # Get movement patterns for summary
        patterns_data = service.get_movement_patterns(hours_back)

        # Get heatmap data for statistics
        heatmap_data = service.get_heatmap_data(hours_back)

        # Extract key metrics
        summary = {
            'analysis_period_hours': hours_back,
            'start_time': start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'heatmap_statistics': heatmap_data.get('intensity_statistics', {}),
            'activity_zones': {
                'total_zones': len(zones_data.get('activity_zones', [])),
                'top_zone': zones_data.get('activity_zones', [{}])[0] if zones_data.get('activity_zones') else None,
                'recommendations': zones_data.get('recommendations', [])
            },
            'movement_patterns': {
                'total_cattle_analyzed': patterns_data.get('patterns', {}).get('cattle_participation', {}).get('total_cattle', 0),
                'peak_activity_hours': patterns_data.get('patterns', {}).get('peak_activity_hours', []),
                'most_active_days': patterns_data.get('patterns', {}).get('most_active_days', [])
            },
            'recommendations': []
        }

        # Generate overall recommendations
        if summary['activity_zones']['top_zone']:
            top_zone = summary['activity_zones']['top_zone']
            if top_zone.get('activity_count', 0) > 20:
                summary['recommendations'].append(
                    f"High activity zone detected with {top_zone.get('activity_count')} activity points"
                )

        if summary['heatmap_statistics'].get('max', 0) > 50:
            summary['recommendations'].append("High activity intensity detected in some areas")

        if summary['movement_patterns']['total_cattle_analyzed'] == 0:
            summary['recommendations'].append("No cattle activity detected in the specified time period")

        return summary

    except Exception as e:
        logger.error(f"Error generating heatmap summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate heatmap summary")


@router.get("/cattle/{cattle_id}/contribution")
async def get_cattle_heatmap_contribution(
    cattle_id: str,
    hours_back: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get specific cattle's contribution to heatmap data

    Args:
        cattle_id: UUID of the cattle
        hours_back: Number of hours to analyze
        db: Database session

    Returns:
        Cattle-specific heatmap contribution data
    """
    try:
        import uuid
        from app.models.cattle_history import CattleHistory
        from datetime import timedelta

        # Validate UUID format
        try:
            uuid.UUID(cattle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cattle ID format")

        # Get cattle history for the specified time period
        start_time = datetime.utcnow() - timedelta(hours=hours_back)
        history = db.query(CattleHistory).filter(
            CattleHistory.cattle_id == cattle_id,
            CattleHistory.timestamp >= start_time
        ).order_by(CattleHistory.timestamp.desc()).all()

        if not history:
            return {
                'cattle_id': cattle_id,
                'message': 'No activity data found for this cattle in the specified period',
                'contribution_data': [],
                'analysis_timestamp': datetime.utcnow().isoformat()
            }

        # Convert to contribution format
        contribution_data = []
        for point in history:
            coords = point.get_coordinates()
            if coords:
                contribution_data.append({
                    'timestamp': point.timestamp.isoformat(),
                    'location': coords,
                    'intensity': 1  # Each point contributes intensity of 1
                })

        # Get cattle basic info
        from app.models.cattle import Cattle
        cattle = db.query(Cattle).filter(Cattle.id == cattle_id).first()

        return {
            'cattle_id': cattle_id,
            'cattle_info': {
                'identifier': cattle.identifier if cattle else 'Unknown',
                'age': cattle.age if cattle else 0,
                'health_status': cattle.health_status if cattle else 'Unknown'
            },
            'total_points': len(contribution_data),
            'activity_span_hours': (history[0].timestamp - history[-1].timestamp).total_seconds() / 3600 if len(history) > 1 else 0,
            'contribution_data': contribution_data,
            'analysis_period_hours': hours_back,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cattle heatmap contribution {cattle_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cattle heatmap contribution")


@router.post("/analyze")
async def analyze_heatmap(
    request: HeatmapRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze heatmap data with custom parameters

    Args:
        request: Heatmap analysis request
        db: Database session

    Returns:
        Analysis results
    """
    try:
        service = HeatmapService(db)
        analysis_data = service.get_heatmap_data(
            request.hours_back,
            request.grid_size_meters,
            request.time_buckets
        )

        return analysis_data

    except Exception as e:
        logger.error(f"Error analyzing heatmap: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze heatmap")


@router.post("/analyze-activity-zones")
async def analyze_activity_zones(
    request: ActivityZonesRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze activity zones with custom parameters

    Args:
        request: Activity zones analysis request
        db: Database session

    Returns:
        Activity zones analysis results
    """
    try:
        service = HeatmapService(db)
        zones_data = service.get_activity_zones(
            request.hours_back,
            request.min_activity_threshold,
            request.cluster_radius_meters
        )

        return zones_data

    except Exception as e:
        logger.error(f"Error analyzing activity zones: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze activity zones")


@router.post("/analyze-movement-patterns")
async def analyze_movement_patterns(
    request: MovementPatternsRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze movement patterns with custom parameters

    Args:
        request: Movement patterns analysis request
        db: Database session

    Returns:
        Movement patterns analysis results
    """
    try:
        service = HeatmapService(db)
        patterns_data = service.get_movement_patterns(
            request.hours_back,
            request.cattle_filter
        )

        return patterns_data

    except Exception as e:
        logger.error(f"Error analyzing movement patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze movement patterns")