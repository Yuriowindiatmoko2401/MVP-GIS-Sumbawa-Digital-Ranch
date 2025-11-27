"""
Geofence Service for Sumbawa Digital Ranch MVP
Handles geofence violation detection and spatial boundary management
"""
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from geoalchemy2.functions import ST_Within, ST_Distance, ST_Intersects

from app.models.cattle import Cattle, CattleSpatialQueries
from app.models.geofence import Geofence, GeofenceSpatialQueries


class GeofenceService:
    """
    Service for geofence management and violation detection
    Monitors cattle positions and detects boundary violations
    """

    def __init__(self, db_session: Session):
        """
        Initialize geofence service

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.logger = logging.getLogger(__name__)

    def check_cattle_within_geofence(self, cattle_location_wkt: str,
                                   geofence_polygon_wkt: str) -> bool:
        """
        Check if a cattle location is within a geofence polygon

        Args:
            cattle_location_wkt: Cattle location as WKT POINT
            geofence_polygon_wkt: Geofence boundary as WKT POLYGON

        Returns:
            True if cattle is within geofence, False otherwise
        """
        try:
            from geoalchemy2.functions import ST_GeomFromText

            cattle_point = ST_GeomFromText(cattle_location_wkt, 4326)
            geofence_polygon = ST_GeomFromText(geofence_polygon_wkt, 4326)

            is_within = self.db.query(ST_Within(cattle_point, geofence_polygon)).scalar()
            return bool(is_within)

        except Exception as e:
            self.logger.error(f"Error checking cattle within geofence: {e}")
            return False

    def detect_violations(self, geofence_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Detect geofence violations for a specific geofence

        Args:
            geofence_id: UUID of the geofence to check

        Returns:
            List of violation alerts for cattle outside the geofence
        """
        # Get geofence
        geofence = self.db.query(Geofence).filter(Geofence.id == geofence_id).first()
        if not geofence or not geofence.is_active:
            return []

        # Get all cattle that should be within this geofence
        # For now, we check all active cattle
        all_cattle = self.db.query(Cattle).all()

        violations = []

        for cattle in all_cattle:
            if not cattle.location:
                continue

            # Check if cattle is within geofence
            try:
                is_within = self.db.query(ST_Within(cattle.location, geofence.boundary)).scalar()

                if not is_within:  # Cattle is outside geofence
                    # Get distance from geofence
                    distance_degrees = self.db.query(ST_Distance(cattle.location, geofence.boundary)).scalar()
                    distance_meters = float(distance_degrees * 111000) if distance_degrees else 0

                    # Get cattle coordinates
                    coords = cattle.get_coordinates()
                    lat = coords['lat'] if coords else None
                    lng = coords['lng'] if coords else None

                    violation_data = {
                        'cattle_id': str(cattle.id),
                        'identifier': cattle.identifier,
                        'age': cattle.age,
                        'health_status': cattle.health_status,
                        'current_location': {
                            'lat': lat,
                            'lng': lng
                        },
                        'violation_type': 'LEFT_GEOFENCE',
                        'violation_distance_meters': distance_meters,
                        'geofence_id': str(geofence.id),
                        'geofence_name': geofence.name,
                        'detection_timestamp': datetime.utcnow().isoformat(),
                        'last_update': cattle.last_update.isoformat() if cattle.last_update else None,
                        'severity': self._calculate_violation_severity(distance_meters, cattle.health_status)
                    }

                    violations.append(violation_data)

            except Exception as e:
                self.logger.error(f"Error checking violation for cattle {cattle.identifier}: {e}")
                continue

        return violations

    def detect_all_violations(self) -> List[Dict[str, Any]]:
        """
        Detect violations across all active geofences

        Returns:
            List of all violation alerts
        """
        all_violations = []

        # Get all active geofences
        active_geofences = self.db.query(Geofence).filter(Geofence.is_active == True).all()

        for geofence in active_geofences:
            geofence_violations = self.detect_violations(geofence.id)
            all_violations.extend(geofence_violations)

        return all_violations

    def _calculate_violation_severity(self, distance_meters: float,
                                    health_status: str) -> str:
        """
        Calculate violation severity based on distance and cattle health

        Args:
            distance_meters: Distance outside geofence in meters
            health_status: Health status of the cattle

        Returns:
            Severity level: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        """
        # Base severity by distance
        if distance_meters < 100:
            base_severity = 'LOW'
        elif distance_meters < 500:
            base_severity = 'MEDIUM'
        elif distance_meters < 1000:
            base_severity = 'HIGH'
        else:
            base_severity = 'CRITICAL'

        # Adjust severity based on health status
        if health_status == 'Sakit':
            # Sick animals get higher severity
            if base_severity == 'LOW':
                return 'MEDIUM'
            elif base_severity == 'MEDIUM':
                return 'HIGH'
            else:
                return 'CRITICAL'
        elif health_status == 'Perlu Perhatian':
            # Animals needing attention get one level higher severity
            if base_severity == 'LOW':
                return 'LOW'  # Keep low for minor attention needed
            elif base_severity == 'MEDIUM':
                return 'HIGH'
            else:
                return 'CRITICAL'

        return base_severity

    def create_violation_alert(self, cattle_id: uuid.UUID, violation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a violation alert record and format for WebSocket broadcast

        Args:
            cattle_id: UUID of the cattle in violation
            violation_data: Detailed violation information

        Returns:
            Formatted alert data for broadcasting
        """
        # In a production system, you might save this to a database table
        # For MVP, we'll format it for immediate broadcasting

        alert = {
            'alert_id': str(uuid.uuid4()),
            'type': 'geofence_violation',
            'priority': 'high',
            'timestamp': datetime.utcnow().isoformat(),
            'cattle': violation_data,
            'actions_required': self._get_required_actions(violation_data),
            'estimated_return_time': self._estimate_return_time(violation_data),
            'contact_info': {
                'ranch_manager': 'Ranch Manager',
                'emergency_contact': 'Emergency Contact'
            }
        }

        return alert

    def _get_required_actions(self, violation_data: Dict[str, Any]) -> List[str]:
        """
        Get required actions based on violation severity and cattle health

        Args:
            violation_data: Violation information

        Returns:
            List of required actions
        """
        severity = violation_data.get('severity', 'LOW')
        health_status = violation_data.get('health_status', 'Sehat')
        distance = violation_data.get('violation_distance_meters', 0)

        actions = []

        # Basic actions for all violations
        actions.append("Locate and verify cattle position")
        actions.append("Check for physical injuries or distress")

        # Actions based on distance
        if distance > 1000:
            actions.append("Deploy search team immediately")
            actions.append("Notify ranch manager")
            actions.append("Check nearby roads or dangerous areas")
        elif distance > 500:
            actions.append("Send ranch hand to retrieve")
            actions.append("Monitor movement pattern")
        else:
            actions.append("Guide cattle back to geofenced area")

        # Actions based on health status
        if health_status == 'Sakit':
            actions.insert(0, "URGENT: Sick animal requires immediate attention")
            actions.append("Contact veterinarian if condition worsens")
        elif health_status == 'Perlu Perhatian':
            actions.append("Monitor health condition closely")
            actions.append("Provide additional care if needed")

        return actions

    def _estimate_return_time(self, violation_data: Dict[str, Any]) -> str:
        """
        Estimate time required to return cattle to geofence

        Args:
            violation_data: Violation information

        Returns:
            Estimated return time as string
        """
        distance_meters = violation_data.get('violation_distance_meters', 0)
        health_status = violation_data.get('health_status', 'Sehat')

        # Base estimate: 15 minutes per 100 meters on foot
        base_time_minutes = (distance_meters / 100) * 15

        # Adjust for health status
        if health_status == 'Sakit':
            base_time_minutes *= 2  # Double time for sick animals
        elif health_status == 'Perlu Perhatian':
            base_time_minutes *= 1.5  # 50% more time for animals needing attention

        # Minimum time of 10 minutes
        base_time_minutes = max(base_time_minutes, 10)

        # Maximum time of 4 hours
        base_time_minutes = min(base_time_minutes, 240)

        # Convert to human-readable format
        if base_time_minutes < 60:
            return f"{int(base_time_minutes)} minutes"
        else:
            hours = int(base_time_minutes // 60)
            minutes = int(base_time_minutes % 60)
            return f"{hours}h {minutes}m"

    def get_cattle_geofence_status(self, cattle_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get geofence status for a specific cattle

        Args:
            cattle_id: UUID of the cattle

        Returns:
            Dictionary with geofence status information
        """
        cattle = self.db.query(Cattle).filter(Cattle.id == cattle_id).first()
        if not cattle or not cattle.location:
            return {
                'cattle_id': str(cattle_id) if cattle_id else None,
                'status': 'unknown',
                'message': 'Cattle not found or no location data'
            }

        # Check all active geofences
        active_geofences = self.db.query(Geofence).filter(Geofence.is_active == True).all()

        geofence_statuses = []
        within_any_geofence = False

        for geofence in active_geofences:
            try:
                is_within = self.db.query(ST_Within(cattle.location, geofence.boundary)).scalar()

                geofence_status = {
                    'geofence_id': str(geofence.id),
                    'geofence_name': geofence.name,
                    'is_within': bool(is_within),
                    'description': geofence.description
                }

                if not is_within:
                    # Calculate distance from geofence
                    distance_degrees = self.db.query(ST_Distance(cattle.location, geofence.boundary)).scalar()
                    distance_meters = float(distance_degrees * 111000) if distance_degrees else 0
                    geofence_status['distance_meters'] = distance_meters

                    # Check if this is a violation (cattle should be within this geofence)
                    if self._should_cattle_be_in_geofence(cattle, geofence):
                        geofence_status['violation'] = True
                        geofence_status['severity'] = self._calculate_violation_severity(
                            distance_meters, cattle.health_status
                        )
                    else:
                        geofence_status['violation'] = False
                else:
                    geofence_status['distance_meters'] = 0
                    geofence_status['violation'] = False
                    within_any_geofence = True

                geofence_statuses.append(geofence_status)

            except Exception as e:
                self.logger.error(f"Error checking geofence status for {geofence.name}: {e}")
                continue

        # Determine overall status
        if within_any_geofence:
            overall_status = 'within_geofence'
        elif any(gs['violation'] for gs in geofence_statuses):
            overall_status = 'violation'
        else:
            overall_status = 'outside_safe_areas'

        return {
            'cattle_id': str(cattle_id),
            'cattle_identifier': cattle.identifier,
            'overall_status': overall_status,
            'location': cattle.get_coordinates(),
            'last_update': cattle.last_update.isoformat() if cattle.last_update else None,
            'geofence_statuses': geofence_statuses,
            'violations': [gs for gs in geofence_statuses if gs.get('violation', False)]
        }

    def _should_cattle_be_in_geofence(self, cattle: Cattle, geofence: Geofence) -> bool:
        """
        Determine if a cattle should be within a specific geofence
        This can be customized based on business rules

        Args:
            cattle: Cattle object
            geofence: Geofence object

        Returns:
            True if cattle should be within this geofence
        """
        # For MVP, assume all cattle should be within all geofences
        # In production, you might have different rules based on:
        # - Cattle age (young vs adult)
        # - Health status (sick cattle might be in special areas)
        # - Time of day (different areas for day vs night)
        # - Weather conditions
        # - Special events

        return True

    def create_geofence(self, name: str, coordinates: List[List[float]],
                       description: Optional[str] = None) -> Geofence:
        """
        Create a new geofence

        Args:
            name: Geofence name
            coordinates: List of coordinate pairs defining polygon boundary
            description: Optional description

        Returns:
            Created geofence object
        """
        geofence = Geofence(
            name=name,
            coordinates=coordinates,
            description=description
        )

        self.db.add(geofence)
        self.db.commit()
        self.db.refresh(geofence)

        return geofence

    def update_geofence(self, geofence_id: uuid.UUID,
                       name: Optional[str] = None,
                       description: Optional[str] = None,
                       coordinates: Optional[List[List[float]]] = None) -> bool:
        """
        Update geofence details

        Args:
            geofence_id: UUID of the geofence
            name: New name (optional)
            description: New description (optional)
            coordinates: New boundary coordinates (optional)

        Returns:
            True if updated successfully, False otherwise
        """
        geofence = self.db.query(Geofence).filter(Geofence.id == geofence_id).first()
        if not geofence:
            return False

        try:
            geofence.update_details(
                name=name,
                description=description,
                coordinates=coordinates
            )
            self.db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error updating geofence {geofence_id}: {e}")
            self.db.rollback()
            return False

    def activate_geofence(self, geofence_id: uuid.UUID) -> bool:
        """
        Activate a geofence

        Args:
            geofence_id: UUID of the geofence

        Returns:
            True if activated successfully, False otherwise
        """
        geofence = self.db.query(Geofence).filter(Geofence.id == geofence_id).first()
        if not geofence:
            return False

        geofence.activate()
        self.db.commit()
        return True

    def deactivate_geofence(self, geofence_id: uuid.UUID) -> bool:
        """
        Deactivate a geofence

        Args:
            geofence_id: UUID of the geofence

        Returns:
            True if deactivated successfully, False otherwise
        """
        geofence = self.db.query(Geofence).filter(Geofence.id == geofence_id).first()
        if not geofence:
            return False

        geofence.deactivate()
        self.db.commit()
        return True

    def get_geofence_statistics(self, geofence_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a specific geofence

        Args:
            geofence_id: UUID of the geofence

        Returns:
            Dictionary with geofence statistics
        """
        geofence = self.db.query(Geofence).filter(Geofence.id == geofence_id).first()
        if not geofence:
            return {'error': 'Geofence not found'}

        # Get geofence metrics
        area_km2 = geofence.get_area_kilometers_squared()
        perimeter_meters = geofence.get_perimeter_meters()
        centroid = geofence.get_centroid()

        # Count cattle within and outside
        within_count = 0
        outside_count = 0
        cattle_details = []

        try:
            all_cattle = self.db.query(Cattle).all()
            for cattle in all_cattle:
                if not cattle.location:
                    continue

                is_within = self.db.query(ST_Within(cattle.location, geofence.boundary)).scalar()
                cattle_data = cattle.to_dict(include_location=True)

                if is_within:
                    within_count += 1
                    cattle_data['geofence_status'] = 'within'
                else:
                    outside_count += 1
                    cattle_data['geofence_status'] = 'outside'
                    # Calculate distance from geofence
                    distance_degrees = self.db.query(ST_Distance(cattle.location, geofence.boundary)).scalar()
                    if distance_degrees:
                        cattle_data['distance_from_geofence_meters'] = float(distance_degrees * 111000)

                cattle_details.append(cattle_data)

        except Exception as e:
            self.logger.error(f"Error counting cattle in geofence: {e}")

        # Calculate cattle density
        density_per_km2 = within_count / area_km2 if area_km2 and area_km2 > 0 else 0

        return {
            'geofence_info': geofence.to_dict(include_metrics=True),
            'statistics': {
                'area_km2': area_km2,
                'perimeter_meters': perimeter_meters,
                'centroid': centroid,
                'cattle_within': within_count,
                'cattle_outside': outside_count,
                'total_cattle': within_count + outside_count,
                'cattle_density_per_km2': density_per_km2,
                'compliance_rate': (within_count / (within_count + outside_count) * 100) if (within_count + outside_count) > 0 else 0
            },
            'cattle_details': cattle_details,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    def get_all_geofences_with_status(self) -> List[Dict[str, Any]]:
        """
        Get all geofences with their current status and statistics

        Returns:
            List of geofence status information
        """
        active_geofences = self.db.query(Geofence).filter(Geofence.is_active == True).all()

        geofence_statuses = []

        for geofence in active_geofences:
            try:
                stats = self.get_geofence_statistics(geofence.id)
                geofence_statuses.append(stats)
            except Exception as e:
                self.logger.error(f"Error getting statistics for geofence {geofence.name}: {e}")
                continue

        return geofence_statuses

    def __del__(self):
        """Cleanup when service is destroyed"""
        if hasattr(self, 'db') and self.db:
            self.db.close()