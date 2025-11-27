"""
Cattle Service for Sumbawa Digital Ranch MVP
Handles GPS simulation, cattle movement logic, and position updates
"""
import uuid
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.cattle import Cattle, CattleSpatialQueries
from app.models.cattle_history import CattleHistory
from app.models.geofence import Geofence


class CattleSimulationService:
    """
    Service for simulating cattle GPS movement and tracking
    Implements realistic movement patterns within geofenced areas
    """

    def __init__(self, db_session: Session):
        """
        Initialize cattle simulation service

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.random = random.Random()  # Separate random instance

    def simulate_movement(self, cattle: Cattle, boundary_polygon: Optional[str] = None,
                         max_drift_meters: float = 50) -> Optional[Tuple[float, float]]:
        """
        Simulate realistic cattle movement within geofence boundary

        Args:
            cattle: Cattle object to move
            boundary_polygon: Geofence boundary as WKT (optional)
            max_drift_meters: Maximum movement distance in meters

        Returns:
            Tuple of (longitude, latitude) or None if movement not possible
        """
        # Get current coordinates
        current_coords = cattle.get_coordinates()
        if not current_coords:
            return None

        current_lng, current_lat = current_coords['lng'], current_coords['lat']

        # Convert max_drift_meters to degrees (approximate)
        max_drift_degrees = max_drift_meters / 111000  # 1 degree ≈ 111 km

        # Generate random movement vector
        # Use Brownian motion with tendency to continue current direction
        angle = self.random.uniform(0, 2 * math.pi)

        # Random distance between 10% and 100% of max drift
        distance_degrees = self.random.uniform(0.1 * max_drift_degrees, max_drift_degrees)

        # Calculate new position
        new_lng = current_lng + distance_degrees * math.cos(angle)
        new_lat = current_lat + distance_degrees * math.sin(angle)

        # If boundary provided, constrain movement within polygon
        if boundary_polygon:
            new_lng, new_lat = self._constrain_to_polygon(
                new_lng, new_lat, boundary_polygon, max_drift_degrees * 2
            )

        return new_lng, new_lat

    def _constrain_to_polygon(self, lng: float, lat: float, polygon_wkt: str,
                             max_search_degrees: float) -> Tuple[float, float]:
        """
        Constrain point to be within polygon using iterative approach

        Args:
            lng: Longitude to constrain
            lat: Latitude to constrain
            polygon_wkt: Polygon boundary in WKT format
            max_search_degrees: Maximum search radius for valid point

        Returns:
            Tuple of constrained (longitude, latitude)
        """
        try:
            from geoalchemy2.functions import ST_Within, ST_GeomFromText, ST_SetSRID, ST_MakePoint

            # Create point
            point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)
            polygon = ST_GeomFromText(polygon_wkt, 4326)

            # Check if point is already within polygon
            is_within = self.db.query(ST_Within(point, polygon)).scalar()

            if is_within:
                return lng, lat

            # If outside, find nearest point within polygon using iterative approach
            best_lng, best_lat = lng, lat
            found = False

            # Search in expanding circles
            search_radius = 0.001  # Start with ~100m
            max_radius = max_search_degrees

            while search_radius <= max_radius and not found:
                # Test points around the circle
                num_points = 16
                for i in range(num_points):
                    angle = 2 * math.pi * i / num_points
                    test_lng = lng + search_radius * math.cos(angle)
                    test_lat = lat + search_radius * math.sin(angle)

                    test_point = ST_SetSRID(ST_MakePoint(test_lng, test_lat), 4326)
                    if self.db.query(ST_Within(test_point, polygon)).scalar():
                        best_lng, best_lat = test_lng, test_lat
                        found = True
                        break

                if not found:
                    search_radius *= 2  # Expand search area

            # If still not found, return original point (will be handled as violation)
            return best_lng, best_lat

        except Exception:
            # If any error occurs, return original position
            return lng, lat

    def update_all_cattle_positions(self, geofence_id: Optional[uuid.UUID] = None) -> List[Cattle]:
        """
        Update positions for all cattle within a geofence or all cattle

        Args:
            geofence_id: Optional geofence UUID to restrict movement within

        Returns:
            List of updated cattle objects
        """
        updated_cattle = []
        boundary_polygon = None

        # Get geofence boundary if specified
        if geofence_id:
            geofence = self.db.query(Geofence).filter(Geofence.id == geofence_id).first()
            if geofence and geofence.is_active:
                boundary_polygon = self.db.query(func.ST_AsText(geofence.boundary)).scalar()
            else:
                # Get all cattle if geofence not found
                cattle_list = self.db.query(Cattle).all()
        else:
            # Get all cattle
            cattle_list = self.db.query(Cattle).all()

        # Filter cattle by geofence if specified
        if geofence_id and boundary_polygon:
            cattle_list = CattleSpatialQueries.get_cattle_within_polygon(self.db, boundary_polygon)

        # Update each cattle position
        for cattle in cattle_list:
            new_coords = self.simulate_movement(cattle, boundary_polygon)
            if new_coords:
                new_lng, new_lat = new_coords

                # Save current position to history
                history = CattleHistory(
                    cattle_id=cattle.id,
                    latitude=new_lat,
                    longitude=new_lng,
                    timestamp=datetime.utcnow()
                )
                self.db.add(history)

                # Update cattle current position
                cattle.set_location(new_lat, new_lng)
                updated_cattle.append(cattle)

        # Commit all changes
        self.db.commit()

        return updated_cattle

    def get_all_cattle_with_location(self, include_history: bool = False,
                                     history_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get all cattle with their current locations and optionally history

        Args:
            include_history: Whether to include recent position history
            history_hours: Number of hours of history to include

        Returns:
            List of cattle data dictionaries
        """
        # Get all cattle
        cattle_list = self.db.query(Cattle).all()
        result = []

        for cattle in cattle_list:
            cattle_data = cattle.to_dict(include_location=True)

            # Add distance from last update time
            if cattle.last_update:
                time_diff = datetime.utcnow() - cattle.last_update
                cattle_data['last_update_minutes_ago'] = int(time_diff.total_seconds() / 60)

            # Include recent history if requested
            if include_history:
                history_cutoff = datetime.utcnow() - timedelta(hours=history_hours)
                recent_history = self.db.query(CattleHistory).filter(
                    and_(
                        CattleHistory.cattle_id == cattle.id,
                        CattleHistory.timestamp >= history_cutoff
                    )
                ).order_by(CattleHistory.timestamp.desc()).limit(50).all()

                cattle_data['recent_history'] = [
                    history.to_dict() for history in recent_history
                ]

            result.append(cattle_data)

        return result

    def get_cattle_movement_summary(self, cattle_id: uuid.UUID,
                                    hours: int = 24) -> Dict[str, Any]:
        """
        Get movement summary for a specific cattle

        Args:
            cattle_id: UUID of the cattle
            hours: Number of hours to analyze

        Returns:
            Movement summary dictionary
        """
        cattle = self.db.query(Cattle).filter(Cattle.id == cattle_id).first()
        if not cattle:
            return {'error': 'Cattle not found'}

        # Get movement statistics
        start_time = datetime.utcnow() - timedelta(hours=hours)
        stats = CattleHistory.get_movement_stats(self.db, cattle_id, start_time, datetime.utcnow())

        # Add current information
        current_coords = cattle.get_coordinates()
        if current_coords:
            stats['current_position'] = current_coords

        stats['cattle_info'] = {
            'id': str(cattle.id),
            'identifier': cattle.identifier,
            'age': cattle.age,
            'health_status': cattle.health_status
        }

        return stats

    def add_cattle(self, identifier: str, age: int, health_status: str,
                   latitude: float, longitude: float) -> Cattle:
        """
        Add a new cattle to the system

        Args:
            identifier: Unique cattle identifier
            age: Age in years
            health_status: Health status
            latitude: Initial GPS latitude
            longitude: Initial GPS longitude

        Returns:
            Created cattle object
        """
        # Check if identifier already exists
        existing = self.db.query(Cattle).filter(Cattle.identifier == identifier).first()
        if existing:
            raise ValueError(f"Cattle with identifier '{identifier}' already exists")

        # Create new cattle
        cattle = Cattle(
            identifier=identifier,
            age=age,
            health_status=health_status,
            latitude=latitude,
            longitude=longitude
        )

        self.db.add(cattle)
        self.db.commit()
        self.db.refresh(cattle)

        # Add initial history record
        history = CattleHistory(
            cattle_id=cattle.id,
            latitude=latitude,
            longitude=longitude,
            timestamp=datetime.utcnow()
        )
        self.db.add(history)
        self.db.commit()

        return cattle

    def update_cattle_health(self, cattle_id: uuid.UUID, new_health_status: str) -> bool:
        """
        Update cattle health status

        Args:
            cattle_id: UUID of the cattle
            new_health_status: New health status

        Returns:
            True if updated successfully, False otherwise
        """
        cattle = self.db.query(Cattle).filter(Cattle.id == cattle_id).first()
        if not cattle:
            return False

        try:
            cattle.update_health_status(new_health_status)
            self.db.commit()
            return True
        except ValueError:
            return False

    def get_cattle_by_identifier(self, identifier: str) -> Optional[Cattle]:
        """
        Get cattle by identifier

        Args:
            identifier: Cattle identifier

        Returns:
            Cattle object or None if not found
        """
        return self.db.query(Cattle).filter(Cattle.identifier == identifier).first()

    def remove_cattle(self, cattle_id: uuid.UUID) -> bool:
        """
        Remove a cattle from the system (including history)

        Args:
            cattle_id: UUID of the cattle

        Returns:
            True if removed successfully, False otherwise
        """
        cattle = self.db.query(Cattle).filter(Cattle.id == cattle_id).first()
        if not cattle:
            return False

        self.db.delete(cattle)  # This will cascade delete history records
        self.db.commit()
        return True

    def get_cattle_positions_at_time(self, timestamp: datetime) -> List[Dict[str, Any]]:
        """
        Get all cattle positions at a specific historical timestamp

        Args:
            timestamp: Historical timestamp to query

        Returns:
            List of cattle with their positions at the specified time
        """
        # For each cattle, find the closest history record to the timestamp
        result = []

        cattle_list = self.db.query(Cattle).all()

        for cattle in cattle_list:
            # Find closest history record
            closest_history = self.db.query(CattleHistory).filter(
                and_(
                    CattleHistory.cattle_id == cattle.id,
                    CattleHistory.timestamp <= timestamp
                )
            ).order_by(CattleHistory.timestamp.desc()).first()

            if closest_history:
                cattle_data = cattle.to_dict(include_location=False)
                coords = closest_history.get_coordinates()
                if coords:
                    cattle_data['location'] = coords
                    cattle_data['position_at'] = closest_history.timestamp.isoformat()
                    cattle_data['position_type'] = 'historical'
                else:
                    cattle_data['location'] = None
                    cattle_data['position_type'] = 'unknown'

                result.append(cattle_data)
            else:
                # No history record, use current position if timestamp is recent
                if cattle.last_update and cattle.last_update <= timestamp:
                    cattle_data = cattle.to_dict(include_location=True)
                    cattle_data['position_at'] = cattle.last_update.isoformat()
                    cattle_data['position_type'] = 'current'
                    result.append(cattle_data)

        return result

    def get_cattle_activity_patterns(self, hours: int = 24,
                                    grid_size_meters: float = 100) -> Dict[str, Any]:
        """
        Analyze cattle activity patterns over time

        Args:
            hours: Number of hours to analyze
            grid_size_meters: Size of grid cells for spatial analysis

        Returns:
            Dictionary with activity pattern analysis
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Get total history points in time range
        total_points = self.db.query(CattleHistory).filter(
            CattleHistory.timestamp >= start_time
        ).count()

        # Get activity heatmap data
        heatmap_data = CattleHistorySpatialQueries.get_history_heatmap_data(
            self.db, start_time, datetime.utcnow(), grid_size_meters
        )

        # Get activity by hour
        hourly_activity = []
        for hour in range(hours):
            hour_start = datetime.utcnow() - timedelta(hours=hour+1)
            hour_end = datetime.utcnow() - timedelta(hours=hour)

            points_in_hour = self.db.query(CattleHistory).filter(
                and_(
                    CattleHistory.timestamp >= hour_start,
                    CattleHistory.timestamp < hour_end
                )
            ).count()

            hourly_activity.append({
                'hour': hour,
                'timestamp': hour_start.isoformat(),
                'activity_count': points_in_hour
            })

        # Get most active areas
        most_active_areas = sorted(heatmap_data, key=lambda x: x['intensity'], reverse=True)[:10]

        return {
            'analysis_period_hours': hours,
            'total_activity_points': total_points,
            'average_points_per_hour': total_points / hours if hours > 0 else 0,
            'hourly_activity': list(reversed(hourly_activity)),
            'heatmap_data': heatmap_data,
            'most_active_areas': most_active_areas,
            'grid_size_meters': grid_size_meters,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    def cleanup_old_history(self, days_to_keep: int = 30) -> int:
        """
        Clean up old history records to maintain database performance

        Args:
            days_to_keep: Number of days of history to keep

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        old_records = self.db.query(CattleHistory).filter(
            CattleHistory.timestamp < cutoff_date
        )

        count = old_records.count()
        old_records.delete()
        self.db.commit()

        return count

    def __del__(self):
        """Cleanup when service is destroyed"""
        if hasattr(self, 'db') and self.db:
            self.db.close()