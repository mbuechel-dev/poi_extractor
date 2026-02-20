"""Road safety analyzer for ultra-cycling routes."""

import re
import json
import gpxpy.gpx
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from xml.etree import ElementTree as ET
from shapely.geometry import box, Polygon, LineString

from .models import RoadSegment
from .osm_manager import OSMDataManager
from .criteria import SafetyCriteria
from ..core.utils import load_gpx_route, calculate_route_length


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
        self._route_coords = None  # Store original route coordinates
        
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
        
        # Store route coordinates for export
        self._route_coords = route_coords
        
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
    
    def export_to_gpx(
        self, 
        segments: List[RoadSegment], 
        output_path: str,
        include_route: bool = True,
        route_coords: Optional[List[Tuple[float, float]]] = None
    ):
        """
        Export unsafe road segments and optionally original route to GPX file.
        
        Args:
            segments: List of RoadSegment objects
            output_path: Path to output GPX file
            include_route: If True, include original route as first track (default: True)
            route_coords: List of (lat, lon) tuples for original route. If None, uses stored route.
        """
        gpx = gpxpy.gpx.GPX()
        gpx.name = "Road Safety Analysis"
        gpx.description = (
            f"Safety analysis with original route and {len(segments)} unsafe road segments. "
            f"Import to GPX Studio or similar tool for visualization."
        )
        
        # Add original route as first track (in blue)
        if include_route:
            coords = route_coords if route_coords is not None else self._route_coords
            if coords:
                route_track = gpxpy.gpx.GPXTrack()
                route_track.name = "Original Route"
                route_track.description = "Planned cycling route"
                route_track.type = "Cycling"  # GPX Studio hint
                
                # Add track segment with coordinates
                route_segment = gpxpy.gpx.GPXTrackSegment()
                for lat, lon in coords:
                    route_segment.points.append(
                        gpxpy.gpx.GPXTrackPoint(lat, lon)
                    )
                
                route_track.segments.append(route_segment)
                gpx.tracks.append(route_track)
        
        # Add dangerous road segments
        for segment in segments:
            track = gpxpy.gpx.GPXTrack()
            track.name = f"{segment.name} (Risk: {segment.risk_score:.1f})"
            track.description = (
                f"Highway: {segment.highway_type} | "
                f"Risk: {segment.risk_level} ({segment.risk_score:.1f}/10) | "
                f"Factors: {', '.join(segment.risk_factors)}"
            )
            
            # Set track type based on risk level
            if segment.risk_score >= 9.0:
                track.type = "Critical"
            elif segment.risk_score >= 7.0:
                track.type = "High Risk"
            elif segment.risk_score >= 5.0:
                track.type = "Moderate Risk"
            else:
                track.type = "Low Risk"
            
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
        
        # Generate GPX XML and inject color extensions
        gpx_xml = gpx.to_xml()
        gpx_xml = self._inject_gpx_studio_colors(gpx_xml, segments, include_route)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(gpx_xml)
        
        # Print summary with statistics
        coords = route_coords if route_coords is not None else self._route_coords
        if include_route and coords:
            route_length = calculate_route_length(coords)
            print(f"\n✓ Exported GPX file: {output_path}")
            print(f"  • Original route: {route_length:.1f} km (blue)")
        else:
            print(f"\n✓ Exported GPX file: {output_path}")
        
        # Count by risk level
        critical = [s for s in segments if s.risk_score >= 9.0]
        high = [s for s in segments if 7.0 <= s.risk_score < 9.0]
        moderate = [s for s in segments if 5.0 <= s.risk_score < 7.0]
        
        print(f"  • Dangerous segments: {len(segments)} tracks")
        if critical:
            total_km = sum(s.length_km() for s in critical)
            print(f"    🔴 Critical: {len(critical)} segments, {total_km:.1f} km (red)")
        if high:
            total_km = sum(s.length_km() for s in high)
            print(f"    🟠 High: {len(high)} segments, {total_km:.1f} km (orange)")
        if moderate:
            total_km = sum(s.length_km() for s in moderate)
            print(f"    🟡 Moderate: {len(moderate)} segments, {total_km:.1f} km (yellow)")
    
    def _inject_gpx_studio_colors(
        self, 
        gpx_xml: str, 
        segments: List[RoadSegment],
        include_route: bool
    ) -> str:
        """
        Inject GPX Studio compatible color extensions into GPX XML.
        
        GPX Studio uses the 'extensions' tag with custom color attributes.
        This method parses the GPX XML and adds color extensions to each track.
        
        Args:
            gpx_xml: GPX XML string from gpxpy
            segments: List of RoadSegment objects
            include_route: Whether the first track is the original route
            
        Returns:
            Modified GPX XML with color extensions
        """
        # Parse the GPX XML
        root = ET.fromstring(gpx_xml)
        
        # Define namespaces
        ns = {
            'gpx': 'http://www.topografix.com/GPX/1/1',
            'gpxx': 'http://www.garmin.com/xmlschemas/GpxExtensions/v3',
        }
        
        # Register namespaces to preserve them in output
        ET.register_namespace('', 'http://www.topografix.com/GPX/1/1')
        ET.register_namespace('gpxx', 'http://www.garmin.com/xmlschemas/GpxExtensions/v3')
        
        # Add gpxx namespace to root if not present
        if 'gpxx' not in root.attrib:
            root.set('{http://www.w3.org/2000/xmlns/}gpxx', 'http://www.garmin.com/xmlschemas/GpxExtensions/v3')
        
        track_idx = 0
        
        # Process all tracks
        for track in root.findall('{http://www.topografix.com/GPX/1/1}trk'):
            # Get or create extensions element
            extensions = track.find('{http://www.topografix.com/GPX/1/1}extensions')
            if extensions is None:
                extensions = ET.SubElement(track, '{http://www.topografix.com/GPX/1/1}extensions')
            
            # First track is the route (if included)
            if track_idx == 0 and include_route:
                # Blue color for original route
                # Use Garmin extension for compatibility
                garmin_ext = ET.SubElement(extensions, '{http://www.garmin.com/xmlschemas/GpxExtensions/v3}TrackExtension')
                display_color = ET.SubElement(garmin_ext, '{http://www.garmin.com/xmlschemas/GpxExtensions/v3}DisplayColor')
                display_color.text = 'Blue'
            else:
                # Dangerous road segment - get color based on risk
                segment_idx = track_idx - (1 if include_route else 0)
                if segment_idx < len(segments):
                    segment = segments[segment_idx]
                    
                    # Determine color based on risk score
                    if segment.risk_score >= 9.0:
                        garmin_color = 'Red'
                    elif segment.risk_score >= 7.0:
                        garmin_color = 'DarkYellow'  # Orange
                    elif segment.risk_score >= 5.0:
                        garmin_color = 'Yellow'
                    else:
                        garmin_color = 'Green'
                    
                    # Add Garmin extension
                    garmin_ext = ET.SubElement(extensions, '{http://www.garmin.com/xmlschemas/GpxExtensions/v3}TrackExtension')
                    display_color = ET.SubElement(garmin_ext, '{http://www.garmin.com/xmlschemas/GpxExtensions/v3}DisplayColor')
                    display_color.text = garmin_color
            
            track_idx += 1
        
        # Convert back to string with proper XML declaration
        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        
        # Add XML declaration
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    
    def export_to_geojson(
        self, 
        segments: List[RoadSegment], 
        output_path: str,
        include_route: bool = True,
        route_coords: Optional[List[Tuple[float, float]]] = None
    ):
        """
        Export unsafe road segments and optionally original route to GeoJSON file.
        
        Args:
            segments: List of RoadSegment objects
            output_path: Path to output GeoJSON file
            include_route: If True, include original route as first feature (default: True)
            route_coords: List of (lat, lon) tuples for original route. If None, uses stored route.
        """
        features = []
        
        # Add original route as first feature (blue)
        if include_route:
            coords = route_coords if route_coords is not None else self._route_coords
            if coords:
                # Convert coordinates to GeoJSON format (lon, lat)
                route_line = [[lon, lat] for lat, lon in coords]
                
                route_feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": route_line
                    },
                    "properties": {
                        "type": "route",
                        "name": "Original Route",
                        "description": "Planned cycling route",
                        "color": "#4285F4",  # Google Maps blue
                        "stroke": "#4285F4",
                        "stroke-width": 3,
                        "stroke-opacity": 0.8
                    }
                }
                features.append(route_feature)
        
        # Add unsafe road segments
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
                    "type": "dangerous_road",
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
                    "stroke": segment.color,
                    "stroke-width": 4,
                    "stroke-opacity": 1.0,
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
        
        # Print summary
        if include_route and (route_coords or self._route_coords):
            print(f"✓ Exported GeoJSON file: {output_path}")
            print(f"  • Original route (blue)")
            print(f"  • {len(segments)} unsafe road segments (colored by risk)")
        else:
            print(f"✓ Exported {len(segments)} road segments to GeoJSON: {output_path}")
