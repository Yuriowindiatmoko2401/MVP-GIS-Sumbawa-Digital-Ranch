"""
Heatmap Service for Sumbawa Digital Ranch MVP
Analyzes cattle movement patterns and generates heatmap data
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from geoalchemy2.functions import ST_SnapToGrid, ST_X, ST_Y, ST_AsGeoJSON

from app.models.cattle_history import CattleHistory, CattleHistorySpatialQueries


class HeatmapService:
    """
    Service for generating and analyzing cattle activity heatmaps
    Provides spatial analysis of cattle movement patterns and behavior
    """

    def __init__(self, db_session: Session):
        """
        Initialize heatmap service

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.logger = logging.getLogger(__name__)

    def get_heatmap_data(self, hours_back: int = 24,
                        grid_size_meters: float = 100,
                        time_buckets: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate comprehensive heatmap data for cattle activity

        Args:
            hours_back: Number of hours to analyze
            grid_size_meters: Size of grid cells in meters
            time_buckets: Number of time buckets to divide analysis (optional)

        Returns:
            Dictionary with heatmap data and analysis
        """
        start_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Get basic heatmap data
        heatmap_points = CattleHistorySpatialQueries.get_history_heatmap_data(
            self.db, start_time, datetime.utcnow(), grid_size_meters
        )

        # Calculate intensity statistics
        if heatmap_points:
            intensities = [point['intensity'] for point in heatmap_points]
            intensity_stats = {
                'min': min(intensities),
                'max': max(intensities),
                'avg': sum(intensities) / len(intensities),
                'total': len(intensities)
            }
        else:
            intensity_stats = {'min': 0, 'max': 0, 'avg': 0, 'total': 0}

        # Get time-based analysis if requested
        temporal_analysis = None
        if time_buckets:
            temporal_analysis = self._get_temporal_heatmap(
                start_time, hours_back, time_buckets, grid_size_meters
            )

        return {
            'metadata': {
                'analysis_period_hours': hours_back,
                'grid_size_meters': grid_size_meters,
                'time_buckets': time_buckets,
                'start_time': start_time.isoformat(),
                'end_time': datetime.utcnow().isoformat(),
                'analysis_timestamp': datetime.utcnow().isoformat()
            },
            'heatmap_points': heatmap_points,
            'intensity_statistics': intensity_stats,
            'temporal_analysis': temporal_analysis,
            'total_points_analyzed': intensity_stats['total']
        }

    def _get_temporal_heatmap(self, start_time: datetime, hours: int,
                            time_buckets: int, grid_size_meters: float) -> List[Dict[str, Any]]:
        """
        Generate temporal heatmap data divided into time buckets

        Args:
            start_time: Start of analysis period
            hours: Total hours to analyze
            time_buckets: Number of time buckets
            grid_size_meters: Size of grid cells in meters

        Returns:
            List of temporal heatmap data
        """
        bucket_duration = timedelta(hours=hours / time_buckets)
        temporal_data = []

        for i in range(time_buckets):
            bucket_start = start_time + (bucket_duration * i)
            bucket_end = start_time + (bucket_duration * (i + 1))

            # Get heatmap data for this time bucket
            bucket_points = CattleHistorySpatialQueries.get_history_heatmap_data(
                self.db, bucket_start, bucket_end, grid_size_meters
            )

            # Calculate bucket statistics
            if bucket_points:
                intensities = [point['intensity'] for point in bucket_points]
                total_intensity = sum(intensities)
                max_intensity = max(intensities)
                avg_intensity = total_intensity / len(intensities)
            else:
                total_intensity = max_intensity = avg_intensity = 0

            temporal_data.append({
                'bucket_index': i,
                'start_time': bucket_start.isoformat(),
                'end_time': bucket_end.isoformat(),
                'duration_minutes': int(bucket_duration.total_seconds() / 60),
                'heatmap_points': bucket_points,
                'statistics': {
                    'total_intensity': total_intensity,
                    'max_intensity': max_intensity,
                    'avg_intensity': avg_intensity,
                    'point_count': len(bucket_points)
                }
            })

        return temporal_data

    def get_activity_zones(self, hours_back: int = 24,
                          min_activity_threshold: int = 5,
                          cluster_radius_meters: float = 150) -> Dict[str, Any]:
        """
        Identify high-activity zones and clustering patterns

        Args:
            hours_back: Number of hours to analyze
            min_activity_threshold: Minimum activity points to consider a zone
            cluster_radius_meters: Radius for clustering points

        Returns:
            Dictionary with activity zone analysis
        """
        start_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Get raw history points
        history_points = self.db.query(CattleHistory).filter(
            CattleHistory.timestamp >= start_time
        ).all()

        if not history_points:
            return {
                'metadata': {
                    'analysis_period_hours': hours_back,
                    'min_activity_threshold': min_activity_threshold,
                    'cluster_radius_meters': cluster_radius_meters,
                    'total_points': 0
                },
                'activity_zones': [],
                'recommendations': []
            }

        # Convert to coordinate format for analysis
        coordinates = []
        for point in history_points:
            coords = point.get_coordinates()
            if coords:
                coordinates.append({
                    'lat': coords['lat'],
                    'lng': coords['lng'],
                    'timestamp': point.timestamp,
                    'cattle_id': str(point.cattle_id)
                })

        # Perform simple clustering (grid-based approach)
        grid_size_degrees = cluster_radius_meters / 111000  # Convert to degrees

        # Create activity grid
        activity_grid = {}
        for coord in coordinates:
            grid_x = int(coord['lng'] / grid_size_degrees)
            grid_y = int(coord['lat'] / grid_size_degrees)
            grid_key = f"{grid_x},{grid_y}"

            if grid_key not in activity_grid:
                activity_grid[grid_key] = []

            activity_grid[grid_key].append(coord)

        # Identify activity zones
        activity_zones = []
        for grid_key, points in activity_grid.items():
            if len(points) >= min_activity_threshold:
                # Calculate zone statistics
                lats = [p['lat'] for p in points]
                lngs = [p['lng'] for p in points]
                timestamps = [p['timestamp'] for p in points]
                cattle_ids = list(set(p['cattle_id'] for p in points))

                # Calculate center point
                center_lat = sum(lats) / len(lats)
                center_lng = sum(lngs) / len(lngs)

                # Calculate time span
                time_span = max(timestamps) - min(timestamps)

                activity_zones.append({
                    'zone_id': str(uuid.uuid4()),
                    'center': {'lat': center_lat, 'lng': center_lng},
                    'activity_count': len(points),
                    'unique_cattle': len(cattle_ids),
                    'time_span_hours': time_span.total_seconds() / 3600,
                    'first_activity': min(timestamps).isoformat(),
                    'last_activity': max(timestamps).isoformat(),
                    'activity_density': len(points) / (time_span.total_seconds() / 3600) if time_span.total_seconds() > 0 else 0,
                    'grid_size_meters': cluster_radius_meters
                })

        # Sort zones by activity count
        activity_zones.sort(key=lambda z: z['activity_count'], reverse=True)

        # Generate recommendations
        recommendations = self._generate_activity_zone_recommendations(activity_zones, hours_back)

        return {
            'metadata': {
                'analysis_period_hours': hours_back,
                'min_activity_threshold': min_activity_threshold,
                'cluster_radius_meters': cluster_radius_meters,
                'total_points': len(coordinates),
                'zones_found': len(activity_zones)
            },
            'activity_zones': activity_zones,
            'top_zones': activity_zones[:5],  # Top 5 zones
            'recommendations': recommendations,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    def _generate_activity_zone_recommendations(self, activity_zones: List[Dict[str, Any]],
                                             analysis_hours: int) -> List[str]:
        """
        Generate recommendations based on activity zone analysis

        Args:
            activity_zones: List of activity zone data
            analysis_hours: Analysis period in hours

        Returns:
            List of recommendations
        """
        recommendations = []

        if not activity_zones:
            recommendations.append("No significant activity zones detected. Monitor cattle movement patterns.")
            return recommendations

        # High activity areas
        top_zone = activity_zones[0]
        if top_zone['activity_density'] > 20:  # High activity threshold
            recommendations.append(
                f"High activity zone detected at ({top_zone['center']['lat']:.4f}, {top_zone['center']['lng']:.4f}) "
                f"with {top_zone['activity_count']} activity points. Consider adding resources nearby."
            )

        # Zones with many different cattle
        if top_zone['unique_cattle'] > 5:
            recommendations.append(
                f"Popular gathering area with {top_zone['unique_cattle']} different cattle. "
                "This could be a good location for water or feeding resources."
            )

        # Long-duration activity zones
        if top_zone['time_span_hours'] > analysis_hours * 0.7:
            recommendations.append(
                "Sustained activity zone detected. Cattle may prefer this area for resting or grazing."
            )

        # Multiple zones suggestions
        if len(activity_zones) > 3:
            recommendations.append(
                f"Multiple activity zones ({len(activity_zones)}) detected. "
                "Consider placing resources to serve multiple zones efficiently."
            )

        # Resource placement suggestions
        if activity_zones:
            avg_lat = sum(zone['center']['lat'] for zone in activity_zones) / len(activity_zones)
            avg_lng = sum(zone['center']['lng'] for zone in activity_zones) / len(activity_zones)
            recommendations.append(
                f"Consider central resource placement around ({avg_lat:.4f}, {avg_lng:.4f}) "
                "to serve multiple activity zones."
            )

        return recommendations

    def get_movement_patterns(self, hours_back: int = 24,
                            cattle_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze movement patterns and behaviors

        Args:
            hours_back: Number of hours to analyze
            cattle_filter: Optional list of cattle IDs to filter analysis

        Returns:
            Dictionary with movement pattern analysis
        """
        start_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Get history data with optional cattle filter
        query = self.db.query(CattleHistory).filter(CattleHistory.timestamp >= start_time)
        if cattle_filter:
            query = query.filter(CattleHistory.cattle_id.in_(cattle_filter))

        history_points = query.order_by(CattleHistory.timestamp).all()

        if not history_points:
            return {
                'metadata': {
                    'analysis_period_hours': hours_back,
                    'cattle_count': 0 if not cattle_filter else len(cattle_filter),
                    'total_points': 0
                },
                'patterns': {},
                'recommendations': []
            }

        # Analyze by hour of day
        hourly_activity = {}
        daily_patterns = {}

        # Group cattle by ID for individual analysis
        cattle_data = {}
        for point in history_points:
            hour = point.timestamp.hour
            day_of_week = point.timestamp.strftime('%A')

            # Hourly activity
            if hour not in hourly_activity:
                hourly_activity[hour] = 0
            hourly_activity[hour] += 1

            # Daily patterns
            if day_of_week not in daily_patterns:
                daily_patterns[day_of_week] = 0
            daily_patterns[day_of_week] += 1

            # Individual cattle data
            cattle_id = str(point.cattle_id)
            if cattle_id not in cattle_data:
                cattle_data[cattle_id] = {
                    'point_count': 0,
                    'first_seen': point.timestamp,
                    'last_seen': point.timestamp,
                    'hours_active': set()
                }

            cattle_data[cattle_id]['point_count'] += 1
            cattle_data[cattle_id]['hours_active'].add(hour)
            cattle_data[cattle_id]['last_seen'] = max(
                cattle_data[cattle_id]['last_seen'], point.timestamp
            )

        # Calculate movement efficiency
        movement_stats = self._calculate_movement_statistics(history_points)

        # Generate patterns
        patterns = {
            'hourly_activity': hourly_activity,
            'daily_patterns': daily_patterns,
            'peak_activity_hours': sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:3],
            'most_active_days': sorted(daily_patterns.items(), key=lambda x: x[1], reverse=True)[:3],
            'cattle_participation': {
                'total_cattle': len(cattle_data),
                'avg_points_per_cattle': sum(data['point_count'] for data in cattle_data.values()) / len(cattle_data) if cattle_data else 0,
                'most_active_cattle': sorted(cattle_data.items(), key=lambda x: x[1]['point_count'], reverse=True)[:5]
            },
            'movement_statistics': movement_stats
        }

        # Generate recommendations
        recommendations = self._generate_movement_recommendations(patterns)

        return {
            'metadata': {
                'analysis_period_hours': hours_back,
                'cattle_count': len(cattle_data),
                'total_points': len(history_points),
                'unique_hours_analyzed': len(hourly_activity)
            },
            'patterns': patterns,
            'recommendations': recommendations,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }

    def _calculate_movement_statistics(self, history_points: List[CattleHistory]) -> Dict[str, Any]:
        """
        Calculate movement statistics from history points

        Args:
            history_points: List of cattle history points

        Returns:
            Dictionary with movement statistics
        """
        # Group by cattle for individual analysis
        cattle_groups = {}
        for point in history_points:
            cattle_id = str(point.cattle_id)
            if cattle_id not in cattle_groups:
                cattle_groups[cattle_id] = []
            cattle_groups[cattle_id].append(point)

        total_distance = 0
        total_cattle = len(cattle_groups)
        active_cattle = 0

        for cattle_id, points in cattle_groups.items():
            if len(points) < 2:
                continue

            # Sort by timestamp
            points.sort(key=lambda p: p.timestamp)

            # Calculate distance for this cattle
            cattle_distance = 0
            for i in range(1, len(points)):
                try:
                    distance_degrees = self.db.query(
                        func.ST_Distance(points[i-1].location, points[i].location)
                    ).scalar()
                    if distance_degrees:
                        cattle_distance += float(distance_degrees * 111000)  # Convert to meters
                except Exception:
                    continue

            total_distance += cattle_distance
            active_cattle += 1

        avg_distance_per_cattle = total_distance / active_cattle if active_cattle > 0 else 0

        return {
            'total_cattle_analyzed': total_cattle,
            'active_cattle_with_movement': active_cattle,
            'total_distance_meters': total_distance,
            'average_distance_per_cattle_meters': avg_distance_per_cattle,
            'analysis_period_hours': (history_points[-1].timestamp - history_points[0].timestamp).total_seconds() / 3600 if history_points else 0
        }

    def _generate_movement_recommendations(self, patterns: Dict[str, Any]) -> List[str]:
        """
        Generate recommendations based on movement pattern analysis

        Args:
            patterns: Movement pattern data

        Returns:
            List of recommendations
        """
        recommendations = []

        # Peak activity hours
        peak_hours = patterns.get('peak_activity_hours', [])
        if peak_hours:
            top_hour, count = peak_hours[0]
            recommendations.append(
                f"Peak activity detected at {top_hour}:00 with {count} data points. "
                "Schedule resource checks during this time."
            )

        # Movement levels
        movement_stats = patterns.get('movement_statistics', {})
        avg_distance = movement_stats.get('average_distance_per_cattle_meters', 0)

        if avg_distance < 100:
            recommendations.append("Low movement activity detected. Check if cattle have adequate space and resources.")
        elif avg_distance > 1000:
            recommendations.append("High movement activity detected. Ensure geofence boundaries are adequate.")

        # Cattle participation
        total_cattle = patterns.get('cattle_participation', {}).get('total_cattle', 0)
        if total_cattle > 0:
            avg_points = patterns.get('cattle_participation', {}).get('avg_points_per_cattle', 0)
            if avg_points < 10:
                recommendations.append("Low data points per cattle. Check GPS tracking frequency.")

        return recommendations

    def get_heatmap_geojson(self, hours_back: int = 24,
                           grid_size_meters: float = 100,
                           intensity_scale: str = 'linear') -> Dict[str, Any]:
        """
        Generate heatmap data in GeoJSON format for mapping

        Args:
            hours_back: Number of hours to analyze
            grid_size_meters: Size of grid cells in meters
            intensity_scale: Type of intensity scaling ('linear', 'log', 'sqrt')

        Returns:
            GeoJSON FeatureCollection with heatmap data
        """
        start_time = datetime.utcnow() - timedelta(hours=hours_back)

        # Get heatmap data
        heatmap_points = CattleHistorySpatialQueries.get_history_heatmap_data(
            self.db, start_time, datetime.utcnow(), grid_size_meters
        )

        if not heatmap_points:
            return {
                'type': 'FeatureCollection',
                'features': [],
                'metadata': {
                    'points_count': 0,
                    'grid_size_meters': grid_size_meters,
                    'hours_back': hours_back,
                    'intensity_scale': intensity_scale
                }
            }

        # Calculate intensity range for scaling
        intensities = [point['intensity'] for point in heatmap_points]
        min_intensity = min(intensities)
        max_intensity = max(intensities)

        # Apply intensity scaling
        def scale_intensity(value):
            if max_intensity == min_intensity:
                return 0.5

            normalized = (value - min_intensity) / (max_intensity - min_intensity)

            if intensity_scale == 'log':
                return math.log1p(normalized * 9) / math.log1p(9)
            elif intensity_scale == 'sqrt':
                return math.sqrt(normalized)
            else:  # linear
                return normalized

        import math

        # Create GeoJSON features
        features = []
        for point in heatmap_points:
            scaled_intensity = scale_intensity(point['intensity'])

            # Create a small circle around the grid point
            radius_degrees = grid_size_meters / 222000  # Half grid size in degrees

            feature = {
                'type': 'Feature',
                'properties': {
                    'intensity': point['intensity'],
                    'scaled_intensity': scaled_intensity,
                    'weight': point.get('weight', point['intensity']),
                    'lat': point['lat'],
                    'lng': point['lng']
                },
                'geometry': {
                    'type': 'Point',
                    'coordinates': [point['lng'], point['lat']]
                }
            }
            features.append(feature)

        return {
            'type': 'FeatureCollection',
            'features': features,
            'metadata': {
                'points_count': len(features),
                'grid_size_meters': grid_size_meters,
                'hours_back': hours_back,
                'intensity_scale': intensity_scale,
                'min_intensity': min_intensity,
                'max_intensity': max_intensity,
                'intensity_range': max_intensity - min_intensity,
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
        }

    def compare_periods(self, current_hours: int = 24,
                        previous_hours: int = 24) -> Dict[str, Any]:
        """
        Compare activity between two time periods

        Args:
            current_hours: Hours for current period (ending now)
            previous_hours: Hours for previous period (ending current_hours ago)

        Returns:
            Dictionary with comparative analysis
        """
        now = datetime.utcnow()
        current_start = now - timedelta(hours=current_hours)
        previous_end = current_start
        previous_start = previous_end - timedelta(hours=previous_hours)

        # Get data for both periods
        current_points = CattleHistorySpatialQueries.get_history_heatmap_data(
            self.db, current_start, now, 100  # 100m grid
        )
        previous_points = CattleHistorySpatialQueries.get_history_heatmap_data(
            self.db, previous_start, previous_end, 100
        )

        # Calculate statistics
        current_intensity = sum(point['intensity'] for point in current_points)
        previous_intensity = sum(point['intensity'] for point in previous_points)

        current_activity_zones = len(current_points)
        previous_activity_zones = len(previous_points)

        # Calculate change percentages
        intensity_change = ((current_intensity - previous_intensity) / previous_intensity * 100) if previous_intensity > 0 else 0
        zones_change = ((current_activity_zones - previous_activity_zones) / previous_activity_zones * 100) if previous_activity_zones > 0 else 0

        # Generate insights
        insights = []
        if intensity_change > 20:
            insights.append("Significant increase in cattle activity detected")
        elif intensity_change < -20:
            insights.append("Significant decrease in cattle activity detected")
        else:
            insights.append("Cattle activity levels are relatively stable")

        return {
            'metadata': {
                'current_period': {
                    'start': current_start.isoformat(),
                    'end': now.isoformat(),
                    'hours': current_hours
                },
                'previous_period': {
                    'start': previous_start.isoformat(),
                    'end': previous_end.isoformat(),
                    'hours': previous_hours
                }
            },
            'comparison': {
                'current_intensity': current_intensity,
                'previous_intensity': previous_intensity,
                'intensity_change_percent': intensity_change,
                'current_activity_zones': current_activity_zones,
                'previous_activity_zones': previous_activity_zones,
                'zones_change_percent': zones_change
            },
            'insights': insights,
            'current_heatmap_data': current_points,
            'previous_heatmap_data': previous_points,
            'analysis_timestamp': now.isoformat()
        }

    def __del__(self):
        """Cleanup when service is destroyed"""
        if hasattr(self, 'db') and self.db:
            self.db.close()