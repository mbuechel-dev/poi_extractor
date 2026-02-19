"""Osmium handlers for processing OSM PBF files."""

import osmium
from shapely.geometry import Point, LineString
from typing import Optional, Dict, List


class POIHandler(osmium.SimpleHandler):
    """
    Extract POI nodes from OSM data.
    
    Processes OSM nodes and filters them based on POI categories (amenity, shop, tourism tags).
    Uses streaming processing for memory efficiency.
    """
    
    def __init__(self, poi_categories: Dict[str, Dict[str, List[str]]], buffer_polygon: Optional[object] = None):
        """
        Initialize POI handler.
        
        Args:
            poi_categories: Dictionary of categories with tag filters
                Example: {'water': {'amenity': ['drinking_water', 'fountain']}}
            buffer_polygon: Optional shapely Polygon to filter POIs spatially
        """
        osmium.SimpleHandler.__init__(self)
        self.poi_categories = poi_categories
        self.buffer_polygon = buffer_polygon
        self.pois = []
    
    def node(self, n):
        """Process each OSM node and check if it matches POI categories."""
        # Skip nodes without location
        if not n.location.valid():
            return
        
        lat = n.location.lat
        lon = n.location.lon
        
        # Check buffer if provided
        if self.buffer_polygon:
            point = Point(lon, lat)
            if not self.buffer_polygon.intersects(point):
                return
        
        # Check if node matches any POI category
        for category, tag_filters in self.poi_categories.items():
            matched = False
            matched_tags = {}
            
            # Check each tag type (amenity, shop, tourism, man_made, etc.)
            for tag_type, tag_values in tag_filters.items():
                if tag_type in n.tags:
                    tag_value = n.tags[tag_type]
                    if tag_value in tag_values:
                        matched = True
                        matched_tags[tag_type] = tag_value
            
            if matched:
                # Extract POI data
                poi_data = {
                    'id': n.id,
                    'lat': lat,
                    'lon': lon,
                    'category': category,
                    'name': n.tags.get('name', f'Unnamed {category}'),
                    'tags': dict(n.tags),  # Store all tags for later use
                }
                
                # Add specific tag types to top level for easier access
                for tag_type in ['amenity', 'shop', 'tourism', 'man_made']:
                    if tag_type in n.tags:
                        poi_data[tag_type] = n.tags[tag_type]
                
                self.pois.append(poi_data)
                break  # Only assign to first matching category


class RoadHandler(osmium.SimpleHandler):
    """
    Extract road ways from OSM data.
    
    Processes OSM ways with highway tags and extracts road attributes for safety analysis.
    Filters roads based on buffer polygon and highway type.
    """
    
    # Highway types to exclude (not suitable for cycling analysis)
    EXCLUDED_HIGHWAYS = {
        'footway', 'path', 'cycleway', 'service', 'track', 
        'steps', 'pedestrian', 'bridleway', 'corridor'
    }
    
    def __init__(self, buffer_polygon: object):
        """
        Initialize road handler.
        
        Args:
            buffer_polygon: Shapely Polygon to filter roads spatially
        """
        osmium.SimpleHandler.__init__(self)
        self.buffer_polygon = buffer_polygon
        self.roads = []
        self._processed_count = 0
        self._filtered_count = 0
    
    def way(self, w):
        """Process each OSM way and check if it's a relevant road."""
        # Only process ways with highway tag
        if 'highway' not in w.tags:
            return
        
        highway_type = w.tags['highway']
        
        # Skip excluded highway types
        if highway_type in self.EXCLUDED_HIGHWAYS:
            return
        
        self._processed_count += 1
        
        # Extract node coordinates
        try:
            coords = []
            for n in w.nodes:
                if n.location.valid():
                    coords.append((n.location.lat, n.location.lon))
            
            # Need at least 2 points for a line
            if len(coords) < 2:
                return
            
        except Exception:
            # Skip ways with location errors
            return
        
        # Check if road intersects buffer
        try:
            # Create LineString with (lon, lat) for shapely
            line = LineString([(lon, lat) for lat, lon in coords])
            if not self.buffer_polygon.intersects(line):
                return
        except Exception:
            # Skip ways with geometry errors
            return
        
        self._filtered_count += 1
        
        # Extract road attributes
        road_data = {
            'id': w.id,
            'name': w.tags.get('name', 'Unnamed Road'),
            'highway': highway_type,
            'maxspeed': w.tags.get('maxspeed'),
            'lanes': w.tags.get('lanes'),
            'surface': w.tags.get('surface'),
            'cycleway': w.tags.get('cycleway'),
            'shoulder': w.tags.get('shoulder'),
            'bicycle': w.tags.get('bicycle'),
            'coordinates': coords,  # Store as (lat, lon) tuples
        }
        
        self.roads.append(road_data)
    
    def get_stats(self):
        """Return processing statistics."""
        return {
            'processed': self._processed_count,
            'filtered': self._filtered_count,
            'in_buffer': len(self.roads)
        }


def process_osm_pois(osm_file: str, poi_categories: Dict, buffer_polygon: Optional[object] = None) -> List[Dict]:
    """
    Extract POIs from OSM PBF file.
    
    Args:
        osm_file: Path to OSM PBF file
        poi_categories: Dictionary of POI categories with tag filters
        buffer_polygon: Optional shapely Polygon for spatial filtering
        
    Returns:
        List of POI dictionaries with id, lat, lon, category, name, tags
    """
    handler = POIHandler(poi_categories, buffer_polygon)
    handler.apply_file(osm_file, locations=True)
    return handler.pois


def process_osm_roads(osm_file: str, buffer_polygon: object) -> List[Dict]:
    """
    Extract roads from OSM PBF file.
    
    Args:
        osm_file: Path to OSM PBF file
        buffer_polygon: Shapely Polygon for spatial filtering
        
    Returns:
        List of road dictionaries with id, name, highway, coordinates, attributes
    """
    handler = RoadHandler(buffer_polygon)
    handler.apply_file(osm_file, locations=True)
    
    # Print statistics
    stats = handler.get_stats()
    print(f"   Processed {stats['processed']} highway ways")
    print(f"   Filtered to {stats['filtered']} in area")
    print(f"   Found {stats['in_buffer']} in buffer")
    
    return handler.roads
