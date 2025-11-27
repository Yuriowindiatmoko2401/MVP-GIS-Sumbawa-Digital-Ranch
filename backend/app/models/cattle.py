"""
Cattle model for Sumbawa Digital Ranch MVP
Defines the database schema for livestock tracking with GPS locations
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from app.database.db import Base


class HealthStatusEnum:
    """Health status enum values for cattle"""
    SEHAT = "Sehat"
    PERLU_PERHATIAN = "Perlu Perhatian"
    SAKIT = "Sakit"


class Cattle(Base):
    """
    Cattle model representing individual livestock with GPS tracking
    """
    __tablename__ = "cattle"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Basic information
    identifier = Column(String(50), unique=True, nullable=False, index=True,
                       comment="Unique cattle identifier (e.g., SAPI-001)")
    age = Column(Integer, nullable=False, comment="Age in years")

    # Health status
    health_status = Column(
        SQLEnum("health_status_enum", name="health_status_enum"),
        nullable=False,
        default=HealthStatusEnum.SEHAT,
        comment="Current health status of the cattle"
    )

    # Spatial data - GPS location using PostGIS Point
    location = Column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
        comment="Current GPS location (WGS84 coordinate system)"
    )

    # Timestamps
    last_update = Column(DateTime(timezone=True), default=datetime.utcnow,
                        comment="Last time location was updated")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow,
                       comment="Record creation timestamp")

    # Relationships
    history = relationship("CattleHistory", back_populates="cattle",
                          cascade="all, delete-orphan")

    def __init__(self, identifier: str, age: int, health_status: str = HealthStatusEnum.SEHAT,
                 latitude: float = None, longitude: float = None):
        """
        Initialize a new cattle record

        Args:
            identifier: Unique identifier for the cattle
            age: Age in years
            health_status: Current health status
            latitude: GPS latitude coordinate
            longitude: GPS longitude coordinate
        """
        self.identifier = identifier
        self.age = age
        self.health_status = health_status
        self.last_update = datetime.utcnow()

        # Set location if coordinates provided
        if latitude is not None and longitude is not None:
            self.set_location(latitude, longitude)

    @validates('age')
    def validate_age(self, key, age):
        """Validate age is within reasonable range"""
        if age is not None and (age < 0 or age > 30):
            raise ValueError("Age must be between 0 and 30 years")
        return age

    @validates('identifier')
    def validate_identifier(self, key, identifier):
        """Validate identifier format"""
        if not identifier or not identifier.strip():
            raise ValueError("Identifier cannot be empty")
        if len(identifier) > 50:
            raise ValueError("Identifier cannot exceed 50 characters")
        return identifier.strip().upper()

    def set_location(self, latitude: float, longitude: float):
        """
        Set cattle GPS location

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
        self.last_update = datetime.utcnow()

    def get_coordinates(self) -> Optional[Dict[str, float]]:
        """
        Get cattle location as latitude/longitude dictionary

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

    def get_location_text(self) -> str:
        """
        Get location as WKT (Well-Known Text) format

        Returns:
            WKT representation of the point location
        """
        from sqlalchemy import func
        return func.ST_AsText(self.location)

    def get_distance_from_point(self, latitude: float, longitude: float) -> Optional[float]:
        """
        Calculate distance from cattle to a given point in meters

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
            # Calculate distance using Haversine formula via PostGIS
            distance_degrees = func.ST_Distance(
                self.location,
                func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
            )
            # Convert degrees to meters (approximate)
            return float(distance_degrees * 111000)  # 1 degree ≈ 111 km
        except Exception:
            return None

    def to_dict(self, include_location: bool = True) -> Dict[str, Any]:
        """
        Convert cattle to dictionary for JSON serialization

        Args:
            include_location: Whether to include location coordinates

        Returns:
            Dictionary representation of cattle data
        """
        result = {
            'id': str(self.id),
            'identifier': self.identifier,
            'age': self.age,
            'health_status': self.health_status,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

        if include_location and self.location:
            coords = self.get_coordinates()
            if coords:
                result['location'] = coords

        return result

    def to_geojson(self) -> Dict[str, Any]:
        """
        Convert cattle to GeoJSON format for mapping

        Returns:
            GeoJSON feature dictionary
        """
        properties = {
            'id': str(self.id),
            'identifier': self.identifier,
            'age': self.age,
            'health_status': self.health_status,
            'last_update': self.last_update.isoformat() if self.last_update else None
        }

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

    def update_health_status(self, new_status: str):
        """
        Update cattle health status

        Args:
            new_status: New health status value
        """
        valid_statuses = [HealthStatusEnum.SEHAT, HealthStatusEnum.PERLU_PERHATIAN,
                         HealthStatusEnum.SAKIT]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid health status. Must be one of: {valid_statuses}")

        self.health_status = new_status
        self.last_update = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation of cattle object"""
        coords = self.get_coordinates()
        location_str = f"({coords['lat']:.4f}, {coords['lng']:.4f})" if coords else "(no location)"
        return f"<Cattle(id={self.identifier}, age={self.age}, status={self.health_status}, location={location_str})>"

    def __str__(self) -> str:
        """Human-readable string representation"""
        return f"Cattle {self.identifier} - {self.age} years old, {self.health_status}"


# PostGIS helper functions for spatial queries
class CattleSpatialQueries:
    """Helper class for common spatial queries related to cattle"""

    @staticmethod
    def get_cattle_within_polygon(session, polygon_wkt: str) -> List[Cattle]:
        """
        Get all cattle within a specified polygon

        Args:
            session: SQLAlchemy session
            polygon_wkt: Polygon in Well-Known Text format

        Returns:
            List of cattle objects within the polygon
        """
        from sqlalchemy import func, text
        from geoalchemy2.functions import ST_Within, ST_GeomFromText

        return session.query(Cattle).filter(
            ST_Within(
                Cattle.location,
                ST_GeomFromText(polygon_wkt, 4326)
            )
        ).all()

    @staticmethod
    def get_cattle_near_point(session, latitude: float, longitude: float,
                            radius_meters: float = 500) -> List[Cattle]:
        """
        Get cattle within specified radius from a point

        Args:
            session: SQLAlchemy session
            latitude: Reference point latitude
            longitude: Reference point longitude
            radius_meters: Search radius in meters

        Returns:
            List of cattle objects within radius
        """
        from sqlalchemy import func
        from geoalchemy2.functions import ST_DWithin, ST_SetSRID, ST_MakePoint

        # Convert meters to degrees (approximate)
        radius_degrees = radius_meters / 111000

        return session.query(Cattle).filter(
            ST_DWithin(
                Cattle.location,
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
                radius_degrees
            )
        ).all()

    @staticmethod
    def get_cattle_outside_geofence(session, geofence_id: uuid.UUID) -> List[Cattle]:
        """
        Get cattle that are outside a specific geofence

        Args:
            session: SQLAlchemy session
            geofence_id: UUID of the geofence

        Returns:
            List of cattle objects outside the geofence
        """
        from sqlalchemy import func
        from geoalchemy2.functions import ST_Within
        from app.models.geofence import Geofence

        return session.query(Cattle).join(Geofence).filter(
            Geofence.id == geofence_id,
            ~ST_Within(Cattle.location, Geofence.boundary)
        ).all()