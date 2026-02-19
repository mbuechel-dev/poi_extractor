"""Road safety analyzer for ultra-cycling routes."""

import re
import json
import gpxpy.gpx
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from shapely.geometry import box, Polygon, LineString

from .models import RoadSegment
from .osm_manager import OSMDataManager
from .criteria import SafetyCriteria
from ..core.utils import load_gpx_route


class RoadSafetyAnalyzer:
    """Analyze road safety along cycling routes."""
    
    def __init__(
        self, 
        criteria: SafetyCriteria,
        osm_cache_dir: str = "data/osm_cache",
        osm_data_path: Optional[str] = None
    ):
        """
        Initialize analyzer.
        
        Args:
            criteria: SafetyCriteria configuration object
            osm_cache_dir: Directory for caching downloaded OSM files
            osm_data_path: Optional: Use specific OSM file instead of auto-download
        """
        self.criteria = criteria
        self.osm_manager = OSMDataManager(cache_dir=osm_cache_dir)
        self.manual_osm_path = osm_data_path
        
    def analyze_route(
        self, 
        gpx_path: str, 
        buffer_km: float,
        min_risk_score: float = 7.0,
        auto_download: bool = True
    ) -> List[RoadSegment]:
        """
        Analyze roads within buffer distance of route.
        
        Args:
            gpx_path: Path to race route GPX file
            buffer_km: Buffer distance in kilometers
            min_risk_score: Minimum risk score to include (0-10)
            auto_download: Automatically download OSM data if True
            
        Returns:
            List of unsafe road segments
        """
        # 1. Get OSM data files
        if self.manual_osm_path:
            osm_files = [self.manual_osm_path]
            print(f"📁 Using manual OSM file: {self.manual_osm_path}")
        elif auto_download:
            print("🗺️  Detecting route location and downloading OSM data...")
            osm_files = self.osm_manager.get_osm_files_for_route(
                gpx_path, 
                buffer_km
            )
        else:
            raise ValueError("No OSM data provided and auto_download=False")
        
        # 2. Load and parse route
        print(f"\n📍 Loading route from {gpx_path}...")
        route_coords = load_gpx_route(gpx_path)
        print(f"✓ Loaded {len(route_coords)} points")
        
        # 3. Create buffer polygon
        buffer_polygon = self._create_buffer(route_coords, buffer_km)
        
        # 4. Extract roads from OSM file(s) within buffer
        all_roads = []
        for osm_file in osm_files:
            print(f"\n🔍 Processing {Path(osm_file).name}...")
            roads = self._extract_roads_from_osm(osm_file, buffer_polygon)
            all_roads.extend(roads)
            print(f"   Found {len(roads)} road segments")
        
        print(f"\n📊 Total road segments: {len(all_roads)}")
        
        # 5. Remove duplicates (if route crosses region boundaries)
        unique_roads = self._deduplicate_roads(all_roads)
        if len(unique_roads) < len(all_roads):
            print(f"   Unique road segments: {len(unique_roads)}")
        
        # 6. Score each road segment
        print(f"\n⚖️  Scoring road segments...")
        scored_roads = []
        for i, road in enumerate(unique_roads):
            if i % 1000 == 0 and i > 0:
                print(f"   Progress: {i}/{len(unique_roads)}")
            segment = self._score_road(road)
            scored_roads.append(segment)
        
        # 7. Filter by minimum risk score
        unsafe_roads = [
            road for road in scored_roads 
            if road.risk_score >= min_risk_score
        ]
        
        print(f"\n⚠️  Unsafe roads found: {len(unsafe_roads)}")
        return unsafe_roads
    
    def _create_buffer(
        self, 
        route_coords: List[Tuple[float, float]], 
        buffer_km: float
    ) -> Polygon:
        """Create buffer polygon around route."""
        # Get bounding box
        lats = [c[0] for c in route_coords]
        lons = [c[1] for c in route_coords]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Add buffer (approximate: 1 degree ≈ 111 km)
        buffer_deg = buffer_km / 111.0
        
        return box(
            min_lon - buffer_deg,
            min_lat - buffer_deg,
            max_lon + buffer_deg,
            max_lat + buffer_deg
        )
    
    def _extract_roads_from_osm(
        self, 
        osm_file: str, 
        buffer_polygon: Polygon
    ) -> List[Dict]:
        """Extract road data from OSM PBF file using osmium."""
        try:
            import osmium
            from ..core.osm_handlers import process_osm_roads
        except ImportError:
            raise ImportError(
                "osmium required for safety analysis. "
                "Install with: pip install poi-extractor[local]"
            )
        
        # Use osmium handler to extract roads
        print(f"  Extracting roads using osmium...")
        roads = process_osm_roads(osm_file, buffer_polygon)
        
        # Parse and normalize road data
        for road in roads:
            # Parse maxspeed if present
            if road['maxspeed']:
                road['maxspeed'] = self._parse_maxspeed(road['maxspeed'])
            else:
                road['maxspeed'] = 0
            
            # Parse lanes if present
            if road['lanes']:
                road['lanes'] = self._parse_int(road['lanes'], default=1)
            else:
                road['lanes'] = 1
        
        return roads
    
    def _deduplicate_roads(self, roads: List[Dict]) -> List[Dict]:
        """Remove duplicate road segments based on OSM ID."""
        seen_ids = set()
        unique = []
        
        for road in roads:
            if road['id'] not in seen_ids:
                unique.append(road)
                seen_ids.add(road['id'])
        
        return unique
    
    def _score_road(self, road: Dict) -> RoadSegment:
        """Calculate safety risk score for a road."""
        risk_score = 0.0
        risk_factors = []
        
        highway_type = road['highway']
        maxspeed = road['maxspeed']
        lanes = road['lanes']
        cycleway = road.get('cycleway')
        shoulder = road.get('shoulder')
        bicycle = road.get('bicycle')
        surface = road.get('surface')
        
        # Check if highway type is forbidden
        if self.criteria.is_forbidden_highway(highway_type):
            risk_score = 10.0  # Maximum risk
            risk_factors.append('forbidden_highway_type')
            # Still calculate other factors for information
        
        # 1. Speed penalty (0-4 points)
        if maxspeed > 0:
            speed_penalty = self.criteria.get_speed_penalty(maxspeed)
            if speed_penalty > 0:
                risk_score += speed_penalty
                if maxspeed >= 100:
                    risk_factors.append('very_high_speed')
                elif maxspeed >= 80:
                    risk_factors.append('high_speed')
                elif maxspeed >= 60:
                    risk_factors.append('moderate_speed')
        
        # 2. Highway type penalty (0-5 points)
        highway_penalty = self.criteria.get_highway_penalty(highway_type)
        if highway_penalty > 0:
            risk_score += highway_penalty
            risk_factors.append(f'highway_{highway_type}')
        
        # 3. Lack of bike infrastructure (0-2.5 points)
        has_cycleway = bool(cycleway)
        has_shoulder = bool(shoulder and shoulder != 'no')
        
        infra_penalty = self.criteria.get_infrastructure_penalty(
            has_cycleway, has_shoulder
        )
        if infra_penalty > 0:
            risk_score += infra_penalty
            if not has_cycleway and not has_shoulder:
                risk_factors.append('no_bike_infrastructure')
            elif not has_cycleway:
                risk_factors.append('no_cycleway')
        
        # 4. Multiple lanes (0-2 points)
        if lanes > 2:
            lane_penalty = self.criteria.get_lane_penalty(lanes)
            if lane_penalty > 0:
                risk_score += lane_penalty
                if lanes >= 4:
                    risk_factors.append('multi_lane')
                else:
                    risk_factors.append('three_lanes')
        
        # 5. Poor surface (0-1.5 points)
        if surface:
            surface_penalty = self.criteria.get_surface_penalty(surface)
            if surface_penalty > 0:
                risk_score += surface_penalty
                risk_factors.append('poor_surface')
        
        # 6. Infrastructure bonus (negative score)
        infra_bonus = self.criteria.get_infrastructure_bonus(cycleway, bicycle)
        if infra_bonus < 0:
            risk_score += infra_bonus
            risk_factors.append('good_bike_infrastructure')
        
        # Ensure score is in valid range
        risk_score = max(0.0, min(10.0, risk_score))
        
        return RoadSegment(
            osm_id=road['id'],
            name=road['name'],
            coordinates=road['coordinates'],
            highway_type=highway_type,
            maxspeed=maxspeed,
            has_cycleway=has_cycleway,
            has_shoulder=has_shoulder,
            lanes=lanes,
            surface=surface,
            bicycle_access=bicycle,
            risk_score=risk_score,
            risk_factors=risk_factors,
        )
    
    def _parse_maxspeed(self, maxspeed) -> int:
        """Parse maxspeed tag to integer km/h."""
        if not maxspeed or maxspeed == 'none':
            return 0
        
        # Handle "50 mph", "80 km/h", etc.
        match = re.search(r'(\d+)', str(maxspeed))
        if match:
            speed = int(match.group(1))
            # Convert mph to km/h if needed
            if 'mph' in str(maxspeed).lower():
                speed = int(speed * 1.60934)
            return speed
        
        return 0
    
    def _parse_int(self, value, default: int = 1) -> int:
        """Safely parse integer value."""
        try:
            # Handle ranges like "2-3" - take the lower value
            if isinstance(value, str) and '-' in value:
                return int(value.split('-')[0])
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def export_to_gpx(self, segments: List[RoadSegment], output_path: str):
        """
        Export unsafe road segments to GPX file.
        
        Args:
            segments: List of RoadSegment objects
            output_path: Path to output GPX file
        """
        gpx = gpxpy.gpx.GPX()
        gpx.name = "Unsafe Roads Analysis"
        gpx.description = (
            f"Safety analysis of {len(segments)} road segments. "
            f"Import to GPX Studio or similar tool for visualization."
        )
        
        for segment in segments:
            # Create a track for each road segment
            track = gpxpy.gpx.GPXTrack()
            track.name = f"{segment.name} (Risk: {segment.risk_score:.1f})"
            track.description = (
                f"Highway: {segment.highway_type} | "
                f"Risk: {segment.risk_level} ({segment.risk_score:.1f}/10) | "
                f"Factors: {', '.join(segment.risk_factors)}"
            )
            
            # Add track segment with coordinates
            track_segment = gpxpy.gpx.GPXTrackSegment()
            for lat, lon in segment.coordinates:
                track_segment.points.append(
                    gpxpy.gpx.GPXTrackPoint(lat, lon)
                )
            
            track.segments.append(track_segment)
            gpx.tracks.append(track)
        
        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(gpx.to_xml())
        
        print(f"\n✓ Exported {len(segments)} unsafe road segments to {output_path}")
    
    def export_to_geojson(self, segments: List[RoadSegment], output_path: str):
        """
        Export unsafe road segments to GeoJSON file.
        
        Args:
            segments: List of RoadSegment objects
            output_path: Path to output GeoJSON file
        """
        features = []
        
        for segment in segments:
            # Convert coordinates to GeoJSON format (lon, lat)
            coordinates = [[lon, lat] for lat, lon in segment.coordinates]
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "name": segment.name,
                    "osm_id": segment.osm_id,
                    "highway_type": segment.highway_type,
                    "risk_score": round(segment.risk_score, 2),
                    "risk_level": segment.risk_level,
                    "risk_factors": segment.risk_factors,
                    "maxspeed": segment.maxspeed,
                    "lanes": segment.lanes,
                    "has_cycleway": segment.has_cycleway,
                    "has_shoulder": segment.has_shoulder,
                    "color": segment.color,
                    "length_km": round(segment.length_km(), 2),
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Ensure output directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"✓ Exported {len(segments)} road segments to GeoJSON: {output_path}")
