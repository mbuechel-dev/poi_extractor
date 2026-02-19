"""Simple POI Extractor using Overpass API."""

import requests
import csv
from pathlib import Path
from typing import List, Dict, Optional

from ..core import (
    load_gpx_route,
    get_bounding_box,
    haversine_distance,
    snap_to_route_osrm,
    Config,
)


class SimpleExtractor:
    """Extract POIs using OpenStreetMap Overpass API."""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize SimpleExtractor.
        
        Args:
            config: Configuration object (uses defaults if None)
        """
        self.config = config or Config()
        self.pois = []
    
    def extract(self, gpx_file: str, buffer_meters: int = 1000, 
                use_osrm: bool = True, osrm_url: str = "http://localhost:5000"):
        """
        Extract POIs along a GPX route.
        
        Args:
            gpx_file: Path to GPX route file
            buffer_meters: Buffer distance in meters around route
            use_osrm: Whether to snap POIs to roads using OSRM
            osrm_url: OSRM server URL
            
        Returns:
            List of POI dictionaries
        """
        print(f"Loading GPX route from {gpx_file}...")
        route_points = load_gpx_route(gpx_file)
        print(f"✓ Loaded route with {len(route_points)} points")
        
        # Get bounding box
        bbox = get_bounding_box(route_points, buffer_km=buffer_meters/1000 + 0.5)
        print(f"Bounding box: {bbox['south']:.4f},{bbox['west']:.4f} to {bbox['north']:.4f},{bbox['east']:.4f}")
        
        # Query POIs for each category
        print("\nQuerying OpenStreetMap via Overpass API...")
        print("(This may take a few minutes...)")
        
        all_pois = []
        categories = self.config.get_categories()
        
        for category, filters in categories.items():
            result = self._query_overpass(bbox, category, filters)
            elements = result.get('elements', [])
            print(f"  Found {len(elements)} {category} in bounding box")
            
            # Convert to standard format
            for elem in elements:
                lat = elem.get('lat') or elem.get('center', {}).get('lat')
                lon = elem.get('lon') or elem.get('center', {}).get('lon')
                
                if lat and lon:
                    all_pois.append({
                        'category': category,
                        'name': elem.get('tags', {}).get('name', ''),
                        'lat': lat,
                        'lon': lon,
                        'amenity': elem.get('tags', {}).get('amenity', ''),
                        'shop': elem.get('tags', {}).get('shop', ''),
                        'tourism': elem.get('tags', {}).get('tourism', ''),
                    })
        
        print(f"\n✓ Found {len(all_pois)} total POIs in bounding box")
        
        # Filter POIs near route
        print(f"Filtering POIs within {buffer_meters}m of route...")
        self.pois = self._filter_pois_near_route(all_pois, route_points, buffer_meters)
        print(f"✓ {len(self.pois)} POIs along route")
        
        # Show breakdown by category
        self._print_category_breakdown()
        
        # Snap to route with OSRM if available
        if use_osrm:
            self._snap_pois_to_route(osrm_url)
        else:
            for poi in self.pois:
                poi['snapped_lat'] = poi['lat']
                poi['snapped_lon'] = poi['lon']
        
        return self.pois
    
    def _query_overpass(self, bbox: Dict, category: str, filters: Dict) -> Dict:
        """Query Overpass API for POIs."""
        overpass_url = "https://overpass-api.de/api/interpreter"
        
        # Build query for multiple tag types
        queries = []
        for key, values in filters.items():
            for value in values:
                queries.append(
                    f'node["{key}"="{value}"]({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});'
                )
                queries.append(
                    f'way["{key}"="{value}"]({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});'
                )
        
        query = f"""
        [out:json][timeout:180];
        (
          {chr(10).join('  ' + q for q in queries)}
        );
        out center;
        """
        
        try:
            response = requests.post(
                overpass_url,
                data={'data': query},
                timeout=180
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  Warning: Could not query {category}: {e}")
            return {'elements': []}
    
    def _filter_pois_near_route(self, pois: List[Dict], 
                                route_points: List[tuple], 
                                buffer_meters: int) -> List[Dict]:
        """Filter POIs within buffer distance of route."""
        filtered = []
        
        for poi in pois:
            poi_lat = poi['lat']
            poi_lon = poi['lon']
            
            # Check if POI is within buffer of any route point
            for route_lat, route_lon in route_points:
                dist = haversine_distance(route_lat, route_lon, poi_lat, poi_lon)
                if dist <= buffer_meters:
                    poi['distance_to_route'] = int(dist)
                    filtered.append(poi)
                    break
        
        return filtered
    
    def _snap_pois_to_route(self, osrm_url: str):
        """Snap POIs to roads using OSRM."""
        print("\nSnapping POIs to roads via OSRM...")
        try:
            # Test OSRM connection
            requests.get(f"{osrm_url}/nearest/v1/car/-7.99,31.63", timeout=2)
            
            for poi in self.pois:
                snapped_lat, snapped_lon = snap_to_route_osrm(
                    poi['lat'], poi['lon'], osrm_url
                )
                poi['snapped_lat'] = snapped_lat
                poi['snapped_lon'] = snapped_lon
            
            print(f"✓ Snapped {len(self.pois)} POIs")
        except Exception:
            print("  ⚠ OSRM not available, skipping snapping")
            for poi in self.pois:
                poi['snapped_lat'] = poi['lat']
                poi['snapped_lon'] = poi['lon']
    
    def _print_category_breakdown(self):
        """Print breakdown of POIs by category."""
        categories_count = {}
        for poi in self.pois:
            cat = poi['category']
            categories_count[cat] = categories_count.get(cat, 0) + 1
        
        for cat, count in sorted(categories_count.items()):
            print(f"  - {cat}: {count}")
    
    def save_to_csv(self, output_file: str):
        """
        Save POIs to CSV file.
        
        Args:
            output_file: Path to output CSV file
        """
        print(f"\nSaving to CSV: {output_file}")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['category', 'name', 'lat', 'lon', 'snapped_lat', 'snapped_lon',
                         'amenity', 'shop', 'tourism', 'distance_to_route']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for poi in self.pois:
                writer.writerow({
                    'category': poi.get('category', ''),
                    'name': poi.get('name', ''),
                    'lat': poi.get('lat', ''),
                    'lon': poi.get('lon', ''),
                    'snapped_lat': poi.get('snapped_lat', ''),
                    'snapped_lon': poi.get('snapped_lon', ''),
                    'amenity': poi.get('amenity', ''),
                    'shop': poi.get('shop', ''),
                    'tourism': poi.get('tourism', ''),
                    'distance_to_route': int(poi.get('distance_to_route', 0)),
                })
        
        print(f"✓ Saved {len(self.pois)} POIs to {output_file}")
