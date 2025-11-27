"""
Resource Service for Sumbawa Digital Ranch MVP
Manages water troughs, feeding stations, and shelter locations
"""
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.resource import Resource, ResourceTypeEnum, ResourceSpatialQueries


class ResourceService:
    """
    Service for managing ranch resources (water, feed, shelter)
    Handles CRUD operations and spatial queries for resources
    """

    def __init__(self, db_session: Session):
        """
        Initialize resource service

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.logger = logging.getLogger(__name__)

    def get_all_resources(self, include_location: bool = True,
                         include_metrics: bool = False) -> List[Dict[str, Any]]:
        """
        Get all resources in the system

        Args:
            include_location: Whether to include GPS coordinates
            include_metrics: Whether to include usage metrics

        Returns:
            List of resource dictionaries
        """
        resources = self.db.query(Resource).all()
        return [resource.to_dict(include_location=include_location,
                                 include_distance=False,
                                 reference_point=None)
                for resource in resources]

    def get_resources_by_type(self, resource_type: str,
                             include_location: bool = True) -> List[Dict[str, Any]]:
        """
        Get resources filtered by type

        Args:
            resource_type: Type of resource (water_trough, feeding_station, shelter)
            include_location: Whether to include GPS coordinates

        Returns:
            List of filtered resource dictionaries
        """
        # Validate resource type
        valid_types = [ResourceTypeEnum.WATER_TROUGH, ResourceTypeEnum.FEEDING_STATION,
                       ResourceTypeEnum.SHELTER]
        if resource_type not in valid_types:
            raise ValueError(f"Invalid resource type. Must be one of: {valid_types}")

        resources = self.db.query(Resource).filter(Resource.resource_type == resource_type).all()
        return [resource.to_dict(include_location=include_location) for resource in resources]

    def get_resources_near_point(self, latitude: float, longitude: float,
                                radius_meters: float = 500,
                                resource_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get resources within specified radius from a point

        Args:
            latitude: Reference point latitude
            longitude: Reference point longitude
            radius_meters: Search radius in meters
            resource_type: Optional filter by resource type

        Returns:
            List of nearby resources with distance information
        """
        resources = ResourceSpatialQueries.get_resources_near_point(
            self.db, latitude, longitude, radius_meters, resource_type
        )

        reference_point = {'lat': latitude, 'lng': longitude}
        return [resource.to_dict(include_location=True, include_distance=True,
                                 reference_point=reference_point)
                for resource in resources]

    def get_nearest_resource(self, latitude: float, longitude: float,
                            resource_type: Optional[str] = None,
                            max_distance_meters: float = 1000) -> Optional[Dict[str, Any]]:
        """
        Get the nearest resource to a point

        Args:
            latitude: Reference point latitude
            longitude: Reference point longitude
            resource_type: Optional filter by resource type
            max_distance_meters: Maximum search distance

        Returns:
            Nearest resource dictionary or None if not found
        """
        resource = ResourceSpatialQueries.get_nearest_resource(
            self.db, latitude, longitude, resource_type, max_distance_meters
        )

        if resource:
            reference_point = {'lat': latitude, 'lng': longitude}
            return resource.to_dict(include_location=True, include_distance=True,
                                   reference_point=reference_point)
        return None

    def create_resource(self, resource_type: str, name: str,
                       latitude: float, longitude: float,
                       description: Optional[str] = None,
                       capacity: Optional[int] = None) -> Resource:
        """
        Create a new resource

        Args:
            resource_type: Type of resource (water_trough, feeding_station, shelter)
            name: Resource name
            latitude: GPS latitude coordinate
            longitude: GPS longitude coordinate
            description: Optional description
            capacity: Optional capacity information

        Returns:
            Created resource object
        """
        # Validate resource type
        valid_types = [ResourceTypeEnum.WATER_TROUGH, ResourceTypeEnum.FEEDING_STATION,
                       ResourceTypeEnum.SHELTER]
        if resource_type not in valid_types:
            raise ValueError(f"Invalid resource type. Must be one of: {valid_types}")

        # Check for duplicate names within same type
        existing = self.db.query(Resource).filter(
            and_(Resource.name == name, Resource.resource_type == resource_type)
        ).first()
        if existing:
            raise ValueError(f"Resource with name '{name}' and type '{resource_type}' already exists")

        resource = Resource(
            resource_type=resource_type,
            name=name,
            latitude=latitude,
            longitude=longitude,
            description=description,
            capacity=capacity
        )

        self.db.add(resource)
        self.db.commit()
        self.db.refresh(resource)

        return resource

    def update_resource(self, resource_id: uuid.UUID,
                       name: Optional[str] = None,
                       description: Optional[str] = None,
                       capacity: Optional[int] = None,
                       latitude: Optional[float] = None,
                       longitude: Optional[float] = None) -> bool:
        """
        Update resource details

        Args:
            resource_id: UUID of the resource
            name: New name (optional)
            description: New description (optional)
            capacity: New capacity (optional)
            latitude: New GPS latitude (optional)
            longitude: New GPS longitude (optional)

        Returns:
            True if updated successfully, False otherwise
        """
        resource = self.db.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            return False

        try:
            # Update basic details
            if name is not None:
                # Check for duplicate names
                existing = self.db.query(Resource).filter(
                    and_(Resource.name == name,
                         Resource.resource_type == resource.resource_type,
                         Resource.id != resource_id)
                ).first()
                if existing:
                    raise ValueError(f"Resource with name '{name}' already exists")
                resource.name = name

            if description is not None:
                resource.description = description

            if capacity is not None:
                resource.capacity = capacity

            # Update location if coordinates provided
            if latitude is not None and longitude is not None:
                resource.set_location(latitude, longitude)

            self.db.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error updating resource {resource_id}: {e}")
            self.db.rollback()
            return False

    def delete_resource(self, resource_id: uuid.UUID) -> bool:
        """
        Delete a resource

        Args:
            resource_id: UUID of the resource to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        resource = self.db.query(Resource).filter(Resource.id == resource_id).first()
        if not resource:
            return False

        self.db.delete(resource)
        self.db.commit()
        return True

    def get_water_resources(self, include_location: bool = True) -> List[Dict[str, Any]]:
        """
        Get all water resources

        Args:
            include_location: Whether to include GPS coordinates

        Returns:
            List of water resource dictionaries
        """
        return self.get_resources_by_type(ResourceTypeEnum.WATER_TROUGH, include_location)

    def get_feeding_resources(self, include_location: bool = True) -> List[Dict[str, Any]]:
        """
        Get all feeding station resources

        Args:
            include_location: Whether to include GPS coordinates

        Returns:
            List of feeding station dictionaries
        """
        return self.get_resources_by_type(ResourceTypeEnum.FEEDING_STATION, include_location)

    def get_shelter_resources(self, include_location: bool = True) -> List[Dict[str, Any]]:
        """
        Get all shelter resources

        Args:
            include_location: Whether to include GPS coordinates

        Returns:
            List of shelter resource dictionaries
        """
        return self.get_resources_by_type(ResourceTypeEnum.SHELTER, include_location)

    def analyze_resource_accessibility(self, cattle_positions: List[Dict[str, float]],
                                     max_distance_meters: float = 500) -> Dict[str, Any]:
        """
        Analyze resource accessibility for cattle positions

        Args:
            cattle_positions: List of cattle GPS positions [{'lat': x, 'lng': y}, ...]
            max_distance_meters: Maximum distance to consider resource accessible

        Returns:
            Dictionary with accessibility analysis
        """
        if not cattle_positions:
            return {'error': 'No cattle positions provided'}

        total_cattle = len(cattle_positions)
        accessible_counts = {
            'water': 0,
            'feed': 0,
            'shelter': 0
        }

        resource_details = {
            'water': [],
            'feed': [],
            'shelter': []
        }

        for cattle_pos in cattle_positions:
            lat, lng = cattle_pos['lat'], cattle_pos['lng']

            # Check water resources
            water_resources = self.get_resources_near_point(
                lat, lng, max_distance_meters, ResourceTypeEnum.WATER_TROUGH
            )
            if water_resources:
                accessible_counts['water'] += 1
                resource_details['water'].extend(water_resources)

            # Check feeding resources
            feed_resources = self.get_resources_near_point(
                lat, lng, max_distance_meters, ResourceTypeEnum.FEEDING_STATION
            )
            if feed_resources:
                accessible_counts['feed'] += 1
                resource_details['feed'].extend(feed_resources)

            # Check shelter resources
            shelter_resources = self.get_resources_near_point(
                lat, lng, max_distance_meters, ResourceTypeEnum.SHELTER
            )
            if shelter_resources:
                accessible_counts['shelter'] += 1
                resource_details['shelter'].extend(shelter_resources)

        # Calculate percentages
        accessibility_percentages = {
            resource_type: (count / total_cattle * 100) if total_cattle > 0 else 0
            for resource_type, count in accessible_counts.items()
        }

        # Remove duplicates from resource details
        for resource_type in resource_details:
            seen_ids = set()
            resource_details[resource_type] = [
                resource for resource in resource_details[resource_type]
                if resource['id'] not in seen_ids and not seen_ids.add(resource['id'])
            ]

        return {
            'total_cattle': total_cattle,
            'max_distance_meters': max_distance_meters,
            'cattle_with_access': accessible_counts,
            'accessibility_percentages': accessibility_percentages,
            'available_resources': {
                resource_type: len(resources)
                for resource_type, resources in resource_details.items()
            },
            'resource_details': resource_details,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    def get_resource_utilization_heatmap(self, hours_back: int = 24,
                                       grid_size_meters: float = 100) -> Dict[str, Any]:
        """
        Generate resource utilization heatmap based on cattle activity

        Args:
            hours_back: Number of hours to analyze
            grid_size_meters: Size of grid cells for heatmap

        Returns:
            Dictionary with heatmap data
        """
        # Get cattle history data for the specified time period
        from app.models.cattle_history import CattleHistory, CattleHistorySpatialQueries
        from datetime import timedelta

        start_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Get heatmap data from cattle history
        heatmap_data = CattleHistorySpatialQueries.get_history_heatmap_data(
            self.db, start_time, datetime.utcnow(), grid_size_meters
        )

        # Get resource locations
        resources = self.db.query(Resource).all()
        resource_points = []

        for resource in resources:
            coords = resource.get_coordinates()
            if coords:
                resource_points.append({
                    'id': str(resource.id),
                    'name': resource.name,
                    'type': resource.resource_type,
                    'lat': coords['lat'],
                    'lng': coords['lng'],
                    'capacity': resource.capacity
                })

        # Calculate resource influence zones
        influence_zones = []
        for resource in resource_points:
            # Create influence zone around each resource
            zone_size_degrees = 300 / 111000  # 300 meters in degrees
            influence_zones.append({
                'resource': {
                    'id': resource['id'],
                    'name': resource['name'],
                    'type': resource['type']
                },
                'center': {'lat': resource['lat'], 'lng': resource['lng']},
                'radius_meters': 300,
                'influence_score': self._calculate_resource_influence(resource)
            })

        return {
            'analysis_period_hours': hours_back,
            'grid_size_meters': grid_size_meters,
            'heatmap_data': heatmap_data,
            'resource_points': resource_points,
            'resource_influence_zones': influence_zones,
            'total_activity_points': len(heatmap_data),
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    def _calculate_resource_influence(self, resource: Dict[str, Any]) -> float:
        """
        Calculate influence score for a resource based on type and capacity

        Args:
            resource: Resource dictionary

        Returns:
            Influence score (0.0 to 1.0)
        """
        base_scores = {
            'water_trough': 0.8,      # Water is most important
            'feeding_station': 0.7,   # Food is very important
            'shelter': 0.5            # Shelter is moderately important
        }

        base_score = base_scores.get(resource['type'], 0.5)

        # Adjust for capacity if available
        if resource.get('capacity'):
            # Normalize capacity (assuming typical ranges)
            if resource['type'] == 'water_trough':
                # Water capacity in liters, typical 50-200
                capacity_score = min(resource['capacity'] / 200, 1.0)
            elif resource['type'] == 'feeding_station':
                # Feeding capacity in cattle count, typical 10-50
                capacity_score = min(resource['capacity'] / 50, 1.0)
            elif resource['type'] == 'shelter':
                # Shelter capacity in cattle count, typical 20-40
                capacity_score = min(resource['capacity'] / 40, 1.0)
            else:
                capacity_score = 0.5

            # Weight capacity as 30% of total score
            return (base_score * 0.7) + (capacity_score * 0.3)
        else:
            return base_score

    def get_resource_density_analysis(self, geofence_wkt: str) -> Dict[str, Any]:
        """
        Analyze resource density within a geofenced area

        Args:
            geofence_wkt: Geofence polygon in Well-Known Text format

        Returns:
            Dictionary with density analysis
        """
        return ResourceSpatialQueries.get_resource_density_analysis(self.db, geofence_wkt)

    def optimize_resource_placement(self, area_wkt: str,
                                   current_resources: List[Dict[str, Any]],
                                   target_density: Dict[str, float]) -> Dict[str, Any]:
        """
        Suggest optimal resource placement for an area

        Args:
            area_wkt: Area polygon in WKT format
            current_resources: List of existing resources
            target_density: Target density per resource type per km²

        Returns:
            Dictionary with placement recommendations
        """
        # Get current density
        current_analysis = self.get_resource_density_analysis(area_wkt)

        # Calculate area in km²
        area_km2 = current_analysis.get('area_km2', 1.0)
        if not area_km2 or area_km2 <= 0:
            area_km2 = 1.0  # Default to 1 km²

        # Calculate required resources based on target density
        required_resources = {
            'water_trough': int(target_density.get('water_trough', 1.0) * area_km2),
            'feeding_station': int(target_density.get('feeding_station', 2.0) * area_km2),
            'shelter': int(target_density.get('shelter', 1.0) * area_km2)
        }

        # Calculate additional resources needed
        current_counts = current_analysis.get('resources_by_type', {
            'water_trough': 0,
            'feeding_station': 0,
            'shelter': 0
        })

        additional_needed = {
            resource_type: max(0, required - current_counts.get(resource_type, 0))
            for resource_type, required in required_resources.items()
        }

        # Generate placement recommendations
        recommendations = []
        if sum(additional_needed.values()) > 0:
            # Get area bounds for placement suggestions
            # For MVP, suggest central placement
            recommendations.append({
                'type': 'new_resources',
                'resources_needed': additional_needed,
                'total_additional': sum(additional_needed.values()),
                'placement_strategy': 'even_distribution',
                'recommended_spacing_meters': 200
            })

        return {
            'area_km2': area_km2,
            'current_density': current_analysis.get('resources_per_km2', 0),
            'target_density': target_density,
            'required_resources': required_resources,
            'current_resources': current_counts,
            'additional_resources_needed': additional_needed,
            'recommendations': recommendations,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    def get_resource_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for all resources

        Returns:
            Dictionary with resource statistics
        """
        total_resources = self.db.query(Resource).count()

        resource_counts = {
            'water_trough': self.db.query(Resource).filter(
                Resource.resource_type == ResourceTypeEnum.WATER_TROUGH
            ).count(),
            'feeding_station': self.db.query(Resource).filter(
                Resource.resource_type == ResourceTypeEnum.FEEDING_STATION
            ).count(),
            'shelter': self.db.query(Resource).filter(
                Resource.resource_type == ResourceTypeEnum.SHELTER
            ).count()
        }

        # Calculate total capacity by type
        capacity_totals = {}
        for resource_type in resource_counts.keys():
            total_capacity = self.db.query(func.coalesce(func.sum(Resource.capacity), 0)).filter(
                Resource.resource_type == resource_type
            ).scalar()
            capacity_totals[resource_type] = int(total_capacity) if total_capacity else 0

        # Get most recently created resource
        latest_resource = self.db.query(Resource).order_by(Resource.created_at.desc()).first()

        return {
            'total_resources': total_resources,
            'resource_counts': resource_counts,
            'resource_percentages': {
                resource_type: (count / total_resources * 100) if total_resources > 0 else 0
                for resource_type, count in resource_counts.items()
            },
            'total_capacity_by_type': capacity_totals,
            'latest_resource': {
                'id': str(latest_resource.id),
                'name': latest_resource.name,
                'type': latest_resource.resource_type,
                'created_at': latest_resource.created_at.isoformat()
            } if latest_resource else None,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    def __del__(self):
        """Cleanup when service is destroyed"""
        if hasattr(self, 'db') and self.db:
            self.db.close()