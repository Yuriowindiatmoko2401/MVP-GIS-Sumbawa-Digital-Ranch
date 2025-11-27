"""
Geofence model for Sumbawa Digital Ranch MVP
Defines polygon boundaries for ranch areas and restricted zones
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.orm import validates
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

from app.database.db import Base


class Geofence(Base):
    """
    Geofence model representing polygon boundaries for cattle management
    Used for defining ranch areas, restricted zones, and monitoring cattle movement
    """
    __tablename__ = "geofences"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Basic information
    name = Column(String(200), nullable=False, index=True,
                   comment="Human-readable name for geofence")

    # Spatial data - geofence boundary using PostGIS Polygon
    boundary = Column(
        Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True),
        nullable=False,
        comment="Geofence boundary polygon (WGS84 coordinate system)"
    )

    # Status and configuration
    is_active = Column(Boolean, default=True, nullable=False, index=True,
                        comment="Whether this geofence is currently active")

    # Additional details
    description = Column(Text, nullable=True,
                         comment="Detailed description of geofence purpose")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow,
                       comment="Geofence creation timestamp")
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow,
                       comment="Last update timestamp")

    def __init__(self, name: str, coordinates: List[List[float]], description: Optional[str] = None,
                 is_active: bool = True):
        """
        Initialize a new geofence record

        Args:
            name: Human-readable name for geofence
            coordinates: List of coordinate pairs defining polygon boundary
                         [[lng1, lat1], [lng2, lat2], ..., [lngN, latN]]
            description: Optional detailed description
            is_active: Whether geofence is initially active
        """
        self.name = name
        self.description = description
        self.is_active = is_active
        self.set_boundary_from_coordinates(coordinates)

    @validates('name')
    def validate_name(self, key, name):
        """Validate geofence name"""
        if not name or not name.strip():
            raise ValueError("Geofence name cannot be empty")
        if len(name) > 200:
            raise ValueError("Geofence name cannot exceed 200 characters")
        return name.strip()

    def set_boundary_from_coordinates(self, coordinates: List[List[float]]):
        """
        Set geofence boundary from coordinate list

        Args:
            coordinates: List of coordinate pairs [[lng1, lat1], [lng2, lat2], ...]
                         Must have at least 3 points and form a closed polygon
        """
        if len(coordinates) < 3:
            raise ValueError("Geofence must have at least 3 coordinate points")

        # Validate coordinate ranges
        for point in coordinates:
            if len(point) != 2:
                raise ValueError("Each coordinate must have exactly 2 values (longitude, latitude)")
            lng, lat = point
            if not (-180 <= lng <= 180):
                raise ValueError(f"Longitude {lng} must be between -180 and 180 degrees")
            if not (-90 <= lat <= 90):
                raise ValueError(f"Latitude {lat} must be between -90 and 90 degrees")

        # Ensure polygon is closed (first point equals last point)
        if coordinates[0] != coordinates[-1]:
            coordinates = coordinates + [coordinates[0]]

        # Create WKT representation
        coord_str = ", ".join([f"{lng} {lat}" for lng, lat in coordinates])
        wkt_polygon = f"POLYGON(({coord_str}))"

        # Set boundary using PostGIS
        from sqlalchemy import func
        self.boundary = func.ST_GeomFromText(wkt_polygon, 4326)
        self.updated_at = datetime.utcnow()

    def set_boundary_from_wkt(self, wkt_polygon: str):
        """
        Set geofence boundary from Well-Known Text (WKT) format

        Args:
            wkt_polygon: Polygon in WKT format, e.g., "POLYGON((lng1 lat1, lng2 lat2, ...))"
        """
        if not wkt_polygon or not wkt_polygon.strip():
            raise ValueError("WKT polygon cannot be empty")

        # Validate WKT format
        if not wkt_polygon.strip().upper().startswith('POLYGON'):
            raise ValueError("WKT must be a POLYGON geometry")

        # Set boundary using PostGIS
        from sqlalchemy import func
        self.boundary = func.ST_GeomFromText(wkt_polygon, 4326)
        self.updated_at = datetime.utcnow()

    def get_boundary_coordinates(self) -> Optional[List[List[float]]]:
        """
        Get geofence boundary as list of coordinate pairs

        Returns:
            List of coordinate pairs [[lng1, lat1], [lng2, lat2], ...] or None
        """
        if not self.boundary:
            return None

        try:
            from sqlalchemy import func
            from geoalchemy2.functions import ST_AsText, ST_ExteriorRing, ST_NumPoints, ST_PointN

            # Get exterior ring as WKT
            wkt_ring = session.query(ST_AsText(ST_ExteriorRing(self.boundary))).scalar()

            if wkt_ring.startswith('LINESTRING(') and wkt_ring.endswith(')'):
                # Extract coordinates from LINESTRING
                coord_str = wkt_ring[11:-1]  # Remove 'LINESTRING(' and ')'
                points = coord_str.split(',')

                coordinates = []
                for point in points:
                    parts = point.strip().split()
                    if len(parts) == 2:
                        lng, lat = float(parts[0]), float(parts[1])
                        coordinates.append([lng, lat])

                return coordinates
        except Exception:
            return None

    def get_area_meters_squared(self) -> Optional[float]:
        """
        Calculate geofence area in square meters

        Returns:
            Area in square meters, or None if boundary not available
        """
        if not self.boundary:
            return None

        try:
            from sqlalchemy import func
            # Calculate area using PostGIS and convert to square meters
            area_degrees_squared = session.query(func.ST_Area(self.boundary)).scalar()
            # Approximate conversion: 1 degree² ≈ (111 km)² = 12321 km² = 12321000000 m²
            return float(area_degrees_squared * 12321000000)
        except Exception:
            return None

    def get_area_kilometers_squared(self) -> Optional[float]:
        """
        Calculate geofence area in square kilometers

        Returns:
            Area in square kilometers, or None if boundary not available
        """
        area_m2 = self.get_area_meters_squared()
        return float(area_m2 / 1000000) if area_m2 is not None else None

    def get_perimeter_meters(self) -> Optional[float]:
        """
        Calculate geofence perimeter in meters

        Returns:
            Perimeter in meters, or None if boundary not available
        """
        if not self.boundary:
            return None

        try:
            from sqlalchemy import func
            # Calculate perimeter using PostGIS and convert to meters
            perimeter_degrees = session.query(func.ST_Perimeter(self.boundary)).scalar()
            # Approximate conversion: 1 degree ≈ 111 km
            return float(perimeter_degrees * 111000)
        except Exception:
            return None

    def get_centroid(self) -> Optional[Dict[str, float]]:
        """
        Get geofence centroid coordinates

        Returns:
            Dictionary with 'lat' and 'lng' keys, or None if boundary not available
        """
        if not self.boundary:
            return None

        try:
            from sqlalchemy import func
            # Get centroid using PostGIS
            centroid = session.query(func.ST_Centroid(self.boundary)).scalar()
            return {
                'lng': float(func.ST_X(centroid)),
                'lat': float(func.ST_Y(centroid))
            }
        except Exception:
            return None

    def get_bounds(self) -> Optional[Dict[str, float]]:
        """
        Get geofence bounding box

        Returns:
            Dictionary with min/max lat/lng, or None if boundary not available
        """
        if not self.boundary:
            return None

        try:
            from sqlalchemy import func
            # Get bounding box using PostGIS
            bounds = session.query(func.ST_Extent(self.boundary)).scalar()

            if bounds:
                # Parse bounds format: "BOX(lng_min lat_min, lng_max lat_max)"
                bounds_str = str(bounds)[4:-1]  # Remove 'BOX(' and ')'
                min_part, max_part = bounds_str.split(',')
                lng_min, lat_min = map(float, min_part.strip().split())
                lng_max, lat_max = map(float, max_part.strip().split())

                return {
                    'min_lat': lat_min,
                    'max_lat': lat_max,
                    'min_lng': lng_min,
                    'max_lng': lng_max,
                    'center_lat': (lat_min + lat_max) / 2,
                    'center_lng': (lng_min + lng_max) / 2
                }
        except Exception:
            return None

    def contains_point(self, latitude: float, longitude: float) -> bool:
        """
        Check if a point is within the geofence

        Args:
            latitude: Point latitude
            longitude: Point longitude

        Returns:
            True if point is within geofence, False otherwise
        """
        if not self.boundary or not self.is_active:
            return False

        try:
            from sqlalchemy import func
            from geoalchemy2.functions import ST_Within, ST_SetSRID, ST_MakePoint

            # Create point and check if within polygon
            point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
            return session.query(ST_Within(point, self.boundary)).scalar()
        except Exception:
            return False

    def get_distance_to_point(self, latitude: float, longitude: float) -> Optional[float]:
        """
        Calculate minimum distance from point to geofence boundary

        Args:
            latitude: Point latitude
            longitude: Point longitude

        Returns:
            Distance in meters, or None if boundary not available
        """
        if not self.boundary:
            return None

        try:
            from sqlalchemy import func
            # Calculate distance using PostGIS
            point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
            distance_degrees = session.query(func.ST_Distance(point, self.boundary)).scalar()

            # Convert degrees to meters (approximate)
            return float(distance_degrees * 111000) if distance_degrees is not None else None
        except Exception:
            return None

    def activate(self):
        """Activate this geofence"""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def deactivate(self):
        """Deactivate this geofence"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def to_dict(self, include_geometry: bool = True, include_metrics: bool = False) -> Dict[str, Any]:
        """
        Convert geofence to dictionary for JSON serialization

        Args:
            include_geometry: Whether to include boundary geometry
            include_metrics: Whether to include area and perimeter calculations

        Returns:
            Dictionary representation of geofence data
        """
        result = {
            'id': str(self.id),
            'name': self.name,
            'is_active': self.is_active,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if include_geometry:
            coords = self.get_boundary_coordinates()
            if coords:
                result['coordinates'] = coords

            centroid = self.get_centroid()
            if centroid:
                result['centroid'] = centroid

            bounds = self.get_bounds()
            if bounds:
                result['bounds'] = bounds

        if include_metrics:
            area_m2 = self.get_area_meters_squared()
            area_km2 = self.get_area_kilometers_squared()
            perimeter = self.get_perimeter_meters()

            if area_m2 is not None:
                result['area_meters_squared'] = area_m2
            if area_km2 is not None:
                result['area_kilometers_squared'] = area_km2
            if perimeter is not None:
                result['perimeter_meters'] = perimeter

        return result

    def to_geojson(self) -> Dict[str, Any]:
        """
        Convert geofence to GeoJSON format for mapping

        Returns:
            GeoJSON feature dictionary
        """
        properties = {
            'id': str(self.id),
            'name': self.name,
            'is_active': self.is_active,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        # Include metrics if available
        area_km2 = self.get_area_kilometers_squared()
        if area_km2 is not None:
            properties['area_km2'] = round(area_km2, 3)

        geometry = None
        if self.boundary:
            try:
                from sqlalchemy import func
                geometry_json = session.query(func.ST_AsGeoJSON(self.boundary)).scalar()
                if geometry_json:
                    geometry = geometry_json
            except Exception:
                pass

        return {
            'type': 'Feature',
            'properties': properties,
            'geometry': geometry
        }

    def update_details(self, name: Optional[str] = None, description: Optional[str] = None,
                      coordinates: Optional[List[List[float]]] = None):
        """
        Update geofence details

        Args:
            name: New name (optional)
            description: New description (optional)
            coordinates: New boundary coordinates (optional)
        """
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if coordinates is not None:
            self.set_boundary_from_coordinates(coordinates)

        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        """String representation of geofence object"""
        status = "Active" if self.is_active else "Inactive"
        area_km2 = self.get_area_kilometers_squared()
        area_str = f"{area_km2:.1f} km²" if area_km2 is not None else "unknown area"
        return f"<Geofence({self.name}, {status}, {area_str})>"

    def __str__(self) -> str:
        """Human-readable string representation"""
        status = "Active" if self.is_active else "Inactive"
        return f"Geofence '{self.name}' ({status})"


# Helper class for geofence spatial queries
class GeofenceSpatialQueries:
    """Helper class for spatial queries related to geofences"""

    @staticmethod
    def get_geofences_containing_point(session, latitude: float, longitude: float,
                                       only_active: bool = True) -> List[Geofence]:
        """
        Get all geofences that contain a specific point

        Args:
            session: SQLAlchemy session
            latitude: Point latitude
            longitude: Point longitude
            only_active: Whether to only return active geofences

        Returns:
            List of geofence objects containing the point
        """
        from sqlalchemy import func
        from geoalchemy2.functions import ST_Within, ST_SetSRID, ST_MakePoint

        point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        query = session.query(Geofence).filter(ST_Within(point, Geofence.boundary))

        if only_active:
            query = query.filter(Geofence.is_active == True)

        return query.all()

    @staticmethod
    def get_geofences_overlapping(session, geofence_wkt: str,
                                  only_active: bool = True) -> List[Geofence]:
        """
        Get geofences that overlap with a given polygon

        Args:
            session: SQLAlchemy session
            geofence_wkt: Polygon in Well-Known Text format
            only_active: Whether to only return active geofences

        Returns:
            List of overlapping geofence objects
        """
        from sqlalchemy import func
        from geoalchemy2.functions import ST_Intersects, ST_GeomFromText

        polygon = ST_GeomFromText(geofence_wkt, 4326)
        query = session.query(Geofence).filter(ST_Intersects(Geofence.boundary, polygon))

        if only_active:
            query = query.filter(Geofence.is_active == True)

        return query.all()

    @staticmethod
    def get_nearest_geofence(session, latitude: float, longitude: float,
                            max_distance_meters: float = 5000,
                            only_active: bool = True) -> Optional[Geofence]:
        """
        Get the nearest geofence to a point

        Args:
            session: SQLAlchemy session
            latitude: Point latitude
            longitude: Point longitude
            max_distance_meters: Maximum search distance
            only_active: Whether to only return active geofences

        Returns:
            Nearest geofence object or None if not found
        """
        from sqlalchemy import func
        from geoalchemy2.functions import ST_Distance, ST_SetSRID, ST_MakePoint

        # Convert meters to degrees (approximate)
        max_degrees = max_distance_meters / 111000

        point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        query = session.query(Geofence).filter(
            ST_Distance(point, Geofence.boundary) <= max_degrees
        )

        if only_active:
            query = query.filter(Geofence.is_active == True)

        # Order by distance and get the nearest
        query = query.order_by(ST_Distance(point, Geofence.boundary))
        return query.first()