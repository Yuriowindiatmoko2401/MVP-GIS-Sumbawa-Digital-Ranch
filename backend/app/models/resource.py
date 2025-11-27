"""
Resource model for Sumbawa Digital Ranch MVP
Defines resources like water troughs, feeding stations, and shelters
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.orm import validates
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from sqlalchemy import Enum as SQLEnum

from app.database.db import Base


class ResourceTypeEnum:
    """Resource type enum values"""
    WATER_TROUGH = "water_trough"
    FEEDING_STATION = "feeding_station"
    SHELTER = "shelter"


class Resource(Base):
    """
    Resource model representing facilities and infrastructure for cattle
    Includes water sources, feeding areas, and shelter locations
    """
    __tablename__ = "resources"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Basic information
    resource_type = Column(
        SQLEnum("resource_type_enum", name="resource_type_enum"),
        nullable=False,
        index=True,
        comment="Type of resource (water, feed, shelter)"
    )

    name = Column(String(200), nullable=False, index=True,
                   comment="Human-readable name for the resource")

    # Spatial data - resource location using PostGIS Point
    location = Column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
        comment="Resource GPS location (WGS84 coordinate system)"
    )

    # Additional details
    description = Column(Text, nullable=True,
                         comment="Detailed description of the resource")
    capacity = Column(Integer, nullable=True,
                       comment="Maximum capacity of the resource (e.g., liters for water, cattle count for shelter)")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow,
                       comment="Resource creation timestamp")
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
                       comment="Last update timestamp")

    def __init__(self, resource_type: str, name: str, latitude: float, longitude: float,
                 description: Optional[str] = None, capacity: Optional[int] = None):
        """
        Initialize a new resource record

        Args:
            resource_type: Type of resource (water_trough, feeding_station, shelter)
            name: Human-readable name
            latitude: GPS latitude coordinate
            longitude: GPS longitude coordinate
            description: Optional detailed description
            capacity: Optional capacity information
        """
        self.resource_type = resource_type
        self.name = name
        self.description = description
        self.capacity = capacity
        self.set_location(latitude, longitude)

    @validates('resource_type')
    def validate_resource_type(self, key, resource_type):
        """Validate resource type"""
        valid_types = [ResourceTypeEnum.WATER_TROUGH, ResourceTypeEnum.FEEDING_STATION,
                       ResourceTypeEnum.SHELTER]
        if resource_type not in valid_types:
            raise ValueError(f"Invalid resource type. Must be one of: {valid_types}")
        return resource_type

    @validates('name')
    def validate_name(self, key, name):
        """Validate resource name"""
        if not name or not name.strip():
            raise ValueError("Resource name cannot be empty")
        if len(name) > 200:
            raise ValueError("Resource name cannot exceed 200 characters")
        return name.strip()

    @validates('capacity')
    def validate_capacity(self, key, capacity):
        """Validate capacity is positive"""
        if capacity is not None and capacity < 0:
            raise ValueError("Capacity cannot be negative")
        return capacity

    def set_location(self, latitude: float, longitude: float):
        """
        Set resource GPS location

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
        self.updated_at = datetime.utcnow()

    def get_coordinates(self) -> Optional[Dict[str, float]]:
        """
        Get resource location as latitude/longitude dictionary

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
        Calculate distance from resource to a given point in meters

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

    def is_water_resource(self) -> bool:
        """Check if this is a water resource"""
        return self.resource_type == ResourceTypeEnum.WATER_TROUGH

    def is_feed_resource(self) -> bool:
        """Check if this is a feeding station"""
        return self.resource_type == ResourceTypeEnum.FEEDING_STATION

    def is_shelter_resource(self) -> bool:
        """Check if this is a shelter"""
        return self.resource_type == ResourceTypeEnum.SHELTER

    def get_display_name(self) -> str:
        """Get formatted display name with type prefix"""
        type_prefix = {
            ResourceTypeEnum.WATER_TROUGH: "💧",
            ResourceTypeEnum.FEEDING_STATION: "🌾",
            ResourceTypeEnum.SHELTER: "🏠"
        }
        prefix = type_prefix.get(self.resource_type, "📍")
        return f"{prefix} {self.name}"

    def get_type_display_name(self) -> str:
        """Get human-readable type name"""
        type_names = {
            ResourceTypeEnum.WATER_TROUGH: "Water Trough",
            ResourceTypeEnum.FEEDING_STATION: "Feeding Station",
            ResourceTypeEnum.SHELTER: "Shelter"
        }
        return type_names.get(self.resource_type, "Unknown")

    def get_color_code(self) -> str:
        """Get color code for mapping visualization"""
        color_map = {
            ResourceTypeEnum.WATER_TROUGH: "#2196F3",  # Blue
            ResourceTypeEnum.FEEDING_STATION: "#FF9800",  # Orange
            ResourceTypeEnum.SHELTER: "#607D8B"  # Gray
        }
        return color_map.get(self.resource_type, "#757575")

    def to_dict(self, include_location: bool = True, include_distance: bool = False,
                reference_point: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Convert resource to dictionary for JSON serialization

        Args:
            include_location: Whether to include location coordinates
            include_distance: Whether to include distance from reference point
            reference_point: Reference point for distance calculation

        Returns:
            Dictionary representation of resource data
        """
        result = {
            'id': str(self.id),
            'resource_type': self.resource_type,
            'name': self.name,
            'display_name': self.get_display_name(),
            'type_display_name': self.get_type_display_name(),
            'color': self.get_color_code(),
            'description': self.description,
            'capacity': self.capacity,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if include_location:
            coords = self.get_coordinates()
            if coords:
                result['location'] = coords

        if include_distance and reference_point and self.location:
            distance = self.get_distance_from_point(reference_point['lat'], reference_point['lng'])
            if distance is not None:
                result['distance_meters'] = distance
                result['distance_text'] = f"{distance:.0f}m"

        return result

    def to_geojson(self) -> Dict[str, Any]:
        """
        Convert resource to GeoJSON format for mapping

        Returns:
            GeoJSON feature dictionary
        """
        properties = {
            'id': str(self.id),
            'resource_type': self.resource_type,
            'name': self.name,
            'display_name': self.get_display_name(),
            'type_display_name': self.get_type_display_name(),
            'color': self.get_color_code(),
            'description': self.description,
            'capacity': self.capacity,
            'created_at': self.created_at.isoformat() if self.created_at else None
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

    def update_details(self, name: Optional[str] = None, description: Optional[str] = None,
                      capacity: Optional[int] = None):
        """
        Update resource details

        Args:
            name: New name (optional)
            description: New description (optional)
            capacity: New capacity (optional)
        """
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if capacity is not None:
            self.capacity = capacity

        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation of resource object"""
        coords = self.get_coordinates()
        location_str = f"({coords['lat']:.4f}, {coords['lng']:.4f})" if coords else "(no location)"
        return f"<Resource({self.resource_type}, {self.name}, location={location_str})>"

    def __str__(self) -> str:
        """Human-readable string representation"""
        return f"{self.get_type_display_name()}: {self.name}"


# Helper class for resource spatial queries
class ResourceSpatialQueries:
    """Helper class for spatial queries related to resources"""

    @staticmethod
    def get_resources_near_point(session, latitude: float, longitude: float,
                                radius_meters: float = 500,
                                resource_type: Optional[str] = None) -> List[Resource]:
        """
        Get resources within specified radius from a point

        Args:
            session: SQLAlchemy session
            latitude: Reference point latitude
            longitude: Reference point longitude
            radius_meters: Search radius in meters
            resource_type: Optional filter by resource type

        Returns:
            List of resource objects within radius
        """
        from sqlalchemy import func
        from geoalchemy2.functions import ST_DWithin, ST_SetSRID, ST_MakePoint

        # Convert meters to degrees (approximate)
        radius_degrees = radius_meters / 111000

        query = session.query(Resource).filter(
            ST_DWithin(
                Resource.location,
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
                radius_degrees
            )
        )

        if resource_type:
            query = query.filter(Resource.resource_type == resource_type)

        return query.all()

    @staticmethod
    def get_nearest_resource(session, latitude: float, longitude: float,
                            resource_type: Optional[str] = None,
                            max_distance_meters: float = 1000) -> Optional[Resource]:
        """
        Get the nearest resource to a point

        Args:
            session: SQLAlchemy session
            latitude: Reference point latitude
            longitude: Reference point longitude
            resource_type: Optional filter by resource type
            max_distance_meters: Maximum search distance

        Returns:
            Nearest resource object or None if not found
        """
        from sqlalchemy import func
        from geoalchemy2.functions import ST_Distance, ST_SetSRID, ST_MakePoint

        # Convert meters to degrees (approximate)
        max_degrees = max_distance_meters / 111000

        query = session.query(Resource).filter(
            ST_DWithin(
                Resource.location,
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326),
                max_degrees
            )
        )

        if resource_type:
            query = query.filter(Resource.resource_type == resource_type)

        # Order by distance and get the nearest
        query = query.order_by(
            ST_Distance(
                Resource.location,
                ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
            )
        )

        return query.first()

    @staticmethod
    def get_resource_density_analysis(session, geofence_wkt: str) -> Dict[str, Any]:
        """
        Analyze resource density within a geofenced area

        Args:
            session: SQLAlchemy session
            geofence_wkt: Geofence polygon in Well-Known Text format

        Returns:
            Dictionary with density analysis results
        """
        from sqlalchemy import func
        from geoalchemy2.functions import ST_Within, ST_GeomFromText

        # Get all resources within the geofence
        resources_in_area = session.query(Resource).filter(
            ST_Within(
                Resource.location,
                ST_GeomFromText(geofence_wkt, 4326)
            )
        ).all()

        # Count by type
        type_counts = {
            ResourceTypeEnum.WATER_TROUGH: 0,
            ResourceTypeEnum.FEEDING_STATION: 0,
            ResourceTypeEnum.SHELTER: 0
        }

        total_capacity = {
            ResourceTypeEnum.WATER_TROUGH: 0,
            ResourceTypeEnum.FEEDING_STATION: 0,
            ResourceTypeEnum.SHELTER: 0
        }

        for resource in resources_in_area:
            type_counts[resource.resource_type] += 1
            if resource.capacity:
                total_capacity[resource.resource_type] += resource.capacity

        # Calculate area (approximate - in production you'd use actual polygon area)
        # This is a simplified calculation
        from geoalchemy2.functions import ST_Area
        area_km2 = session.query(func.ST_Area(ST_GeomFromText(geofence_wkt, 4326))).scalar()

        return {
            'total_resources': len(resources_in_area),
            'resources_by_type': type_counts,
            'total_capacity_by_type': total_capacity,
            'area_km2': float(area_km2) if area_km2 else None,
            'resources_per_km2': len(resources_in_area) / float(area_km2) if area_km2 and area_km2 > 0 else 0,
            'resources': [resource.to_dict() for resource in resources_in_area]
        }