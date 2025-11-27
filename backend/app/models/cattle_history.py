"""
Cattle History model for Sumbawa Digital Ranch MVP
Tracks historical GPS positions and movement patterns of individual cattle
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from app.database.db import Base


class CattleHistory(Base):
    """
    Cattle History model representing historical GPS tracking data
    Stores movement patterns and location history for analysis
    """
    __tablename__ = "cattle_history"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Foreign key to cattle
    cattle_id = Column(UUID(as_uuid=True), ForeignKey("cattle.id", ondelete="CASCADE"),
                       nullable=False, index=True, comment="Reference to cattle record")

    # Spatial data - historical GPS location
    location = Column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
        comment="Historical GPS location (WGS84 coordinate system)"
    )

    # Timestamp
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False,
                      comment="Time when location was recorded")

    # Relationships
    cattle = relationship("Cattle", back_populates="history")

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_cattle_history_cattle_timestamp', 'cattle_id', 'timestamp'),
        Index('idx_cattle_history_timestamp', 'timestamp'),
    )

    def __init__(self, cattle_id: uuid.UUID, latitude: float, longitude: float,
                 timestamp: Optional[datetime] = None):
        """
        Initialize a new cattle history record

        Args:
            cattle_id: UUID of the cattle
            latitude: GPS latitude coordinate (-90 to 90)
            longitude: GPS longitude coordinate (-180 to 180)
            timestamp: When the location was recorded (defaults to now)
        """
        self.cattle_id = cattle_id
        self.timestamp = timestamp or datetime.utcnow()
        self.set_location(latitude, longitude)

    def set_location(self, latitude: float, longitude: float):
        """
        Set GPS location for this history record

        Args:
            latitude: Latitude coordinate (-90 to 90)
            longitude: Longitude coordinate (-180 to 180)
        """
        if not (-90 <= latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")

        # Set location using PostGIS ST_MakePoint
        from sqlalchemy import func
        self.location = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

    def get_coordinates(self) -> Optional[Dict[str, float]]:
        """
        Get location as latitude/longitude dictionary

        Returns:
            Dictionary with 'lat' and 'lng' keys, or None if no location set
        """
        if not self.location:
            return None

        try:
            from sqlalchemy import func
            # Get coordinates from PostGIS point
            result = {
                'lng': float(func.ST_X(self.location)),
                'lat': float(func.ST_Y(self.location))
            }
            return result
        except Exception:
            return None

    def get_distance_from_point(self, latitude: float, longitude: float) -> Optional[float]:
        """
        Calculate distance from this history point to a given point in meters

        Args:
            latitude: Reference point latitude
            longitude: Reference point longitude

        Returns:
            Distance in meters, or None if location not available
        """
        if not self.location:
            return None

        try:
            from sqlalchemy import func
            # Calculate distance using PostGIS
            distance_degrees = func.ST_Distance(
                self.location,
                func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
            )
            # Convert degrees to meters (approximate)
            return float(distance_degrees * 111000)  # 1 degree ≈ 111 km
        except Exception:
            return None

    def to_dict(self, include_cattle_info: bool = False) -> Dict[str, Any]:
        """
        Convert history record to dictionary for JSON serialization

        Args:
            include_cattle_info: Whether to include related cattle information

        Returns:
            Dictionary representation of history data
        """
        result = {
            'id': str(self.id),
            'cattle_id': str(self.cattle_id),
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

        # Add location coordinates
        coords = self.get_coordinates()
        if coords:
            result['location'] = coords

        # Add cattle information if requested
        if include_cattle_info and self.cattle:
            result['cattle'] = {
                'identifier': self.cattle.identifier,
                'age': self.cattle.age,
                'health_status': self.cattle.health_status
            }

        return result

    def to_geojson(self) -> Dict[str, Any]:
        """
        Convert history record to GeoJSON format for mapping

        Returns:
            GeoJSON feature dictionary
        """
        properties = {
            'id': str(self.id),
            'cattle_id': str(self.cattle_id),
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

        # Add cattle information if available
        if self.cattle:
            properties['cattle_identifier'] = self.cattle.identifier
            properties['cattle_age'] = self.cattle.age
            properties['cattle_health'] = self.cattle.health_status

        geometry = None
        if self.location:
            coords = self.get_coordinates()
            if coords:
                geometry = {
                    'type': 'Point',
                    'coordinates': [coords['lng'], coords['lat']]
                }

        return {
            'type': 'Feature',
            'properties': properties,
            'geometry': geometry
        }

    @classmethod
    def create_history_batch(cls, session, cattle_locations: List[Dict[str, Any]]) -> List['CattleHistory']:
        """
        Create multiple history records in batch for performance

        Args:
            session: SQLAlchemy session
            cattle_locations: List of dictionaries with keys:
                - cattle_id: UUID of cattle
                - latitude: float
                - longitude: float
                - timestamp: datetime (optional)

        Returns:
            List of created CattleHistory objects
        """
        history_records = []
        for location_data in cattle_locations:
            history = cls(
                cattle_id=location_data['cattle_id'],
                latitude=location_data['latitude'],
                longitude=location_data['longitude'],
                timestamp=location_data.get('timestamp')
            )
            history_records.append(history)

        session.add_all(history_records)
        session.commit()
        return history_records

    @classmethod
    def get_movement_stats(cls, session, cattle_id: uuid.UUID,
                           start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """
        Calculate movement statistics for a cattle within time range

        Args:
            session: SQLAlchemy session
            cattle_id: UUID of the cattle
            start_time: Start of time period
            end_time: End of time period

        Returns:
            Dictionary with movement statistics
        """
        from sqlalchemy import func, and_
        from geoalchemy2.functions import ST_Distance, ST_SetSRID, ST_MakePoint

        # Get all history records for the time period
        records = session.query(cls).filter(
            and_(
                cls.cattle_id == cattle_id,
                cls.timestamp >= start_time,
                cls.timestamp <= end_time
            )
        ).order_by(cls.timestamp).all()

        if not records:
            return {
                'total_points': 0,
                'total_distance': 0,
                'average_speed': 0,
                'max_distance_from_start': 0
            }

        # Calculate total distance traveled (sum of distances between consecutive points)
        total_distance = 0
        max_distance_from_start = 0

        if len(records) > 1:
            start_location = records[0].location
            for i in range(1, len(records)):
                # Distance from previous point
                distance = session.query(func.ST_Distance(records[i-1].location, records[i].location)).scalar()
                if distance:
                    total_distance += float(distance * 111000)  # Convert to meters

                # Distance from start point
                distance_from_start = session.query(func.ST_Distance(start_location, records[i].location)).scalar()
                if distance_from_start:
                    max_distance_from_start = max(max_distance_from_start, float(distance_from_start * 111000))

        # Calculate average speed (meters per hour)
        time_diff = (records[-1].timestamp - records[0].timestamp).total_seconds() / 3600  # hours
        average_speed = total_distance / time_diff if time_diff > 0 else 0

        return {
            'total_points': len(records),
            'total_distance_meters': total_distance,
            'average_speed_meters_per_hour': average_speed,
            'max_distance_from_start_meters': max_distance_from_start,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'first_point': records[0].to_dict(),
            'last_point': records[-1].to_dict()
        }

    def __repr__(self) -> str:
        """String representation of cattle history object"""
        coords = self.get_coordinates()
        location_str = f"({coords['lat']:.4f}, {coords['lng']:.4f})" if coords else "(no location)"
        return f"<CattleHistory(cattle_id={self.cattle_id}, timestamp={self.timestamp}, location={location_str})>"

    def __str__(self) -> str:
        """Human-readable string representation"""
        coords = self.get_coordinates()
        location_str = f"{coords['lat']:.4f}, {coords['lng']:.4f}" if coords else "no location"
        return f"Cattle history at {self.timestamp} - {location_str}"


# Helper class for spatial queries related to cattle history
class CattleHistorySpatialQueries:
    """Helper class for spatial queries on cattle history data"""

    @staticmethod
    def get_history_heatmap_data(session, start_time: datetime, end_time: datetime,
                                grid_size_meters: float = 100) -> List[Dict[str, Any]]:
        """
        Generate heatmap data by aggregating history points into grid cells

        Args:
            session: SQLAlchemy session
            start_time: Start time for heatmap data
            end_time: End time for heatmap data
            grid_size_meters: Size of each grid cell in meters

        Returns:
            List of grid cells with intensity values
        """
        from sqlalchemy import func, and_
        from geoalchemy2.functions import ST_SnapToGrid, ST_X, ST_Y

        # Convert grid size from meters to degrees (approximate)
        grid_size_degrees = grid_size_meters / 111000

        # Aggregate points into grid cells
        heatmap_query = session.query(
            ST_X(func.ST_SnapToGrid(CattleHistory.location, grid_size_degrees)).label('grid_lng'),
            ST_Y(func.ST_SnapToGrid(CattleHistory.location, grid_size_degrees)).label('grid_lat'),
            func.count().label('intensity')
        ).filter(
            and_(
                CattleHistory.timestamp >= start_time,
                CattleHistory.timestamp <= end_time
            )
        ).group_by(
            func.ST_SnapToGrid(CattleHistory.location, grid_size_degrees)
        ).all()

        # Convert to dictionary format
        return [
            {
                'lat': float(row.grid_lat),
                'lng': float(row.grid_lng),
                'intensity': int(row.intensity),
                'weight': float(row.intensity)  # For Leaflet heat plugin
            }
            for row in heatmap_query
        ]

    @staticmethod
    def get_movement_corridors(session, start_time: datetime, end_time: datetime,
                              min_points: int = 10) -> List[Dict[str, Any]]:
        """
        Identify common movement corridors by analyzing history data patterns

        Args:
            session: SQLAlchemy session
            start_time: Start time for analysis
            end_time: End time for analysis
            min_points: Minimum number of points to consider a corridor

        Returns:
            List of movement corridors with metadata
        """
        # This is a simplified version - in production, you might use more sophisticated
        # clustering algorithms like DBSCAN on the history points
        from sqlalchemy import func, and_
        from geoalchemy2.functions import ST_ClusterDBSCAN, ST_MakeLine

        # Cluster points into movement paths
        clusters = session.query(
            CattleHistory.cattle_id,
            ST_ClusterDBSCAN(CattleHistory.location, 0.001, 3).label('cluster_id'),
            func.ST_ConvexHull(func.ST_Collect(CattleHistory.location)).label('corridor')
        ).filter(
            and_(
                CattleHistory.timestamp >= start_time,
                CattleHistory.timestamp <= end_time
            )
        ).group_by(
            CattleHistory.cattle_id,
            ST_ClusterDBSCAN(CattleHistory.location, 0.001, 3)
        ).having(
            func.count() >= min_points
        ).all()

        return [
            {
                'cattle_id': str(cluster.cattle_id),
                'cluster_id': cluster.cluster_id,
                'corridor_geometry': func.ST_AsGeoJSON(cluster.corridor)
            }
            for cluster in clusters
        ]