"""Local POI Extractor using osmium and local OSM PBF files."""

import csv
from pathlib import Path
from typing import Optional

import gpxpy
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
import requests

from ..core import Config, snap_to_route_osrm
from ..core.osm_handlers import process_osm_pois


class LocalExtractor:
    """Extract POIs from local OSM PBF files using osmium."""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize LocalExtractor.
        
        Args:
            config: Configuration object (uses defaults if None)
        """
        self.config = config or Config()
        self.route_line = None
        self.pois = None
        self.pois_along_route = None
    
    def extract(self, gpx_file: str, osm_file: str, buffer_meters: int = 1000,
                use_osrm: bool = True, osrm_url: str = "http://localhost:5000",
                **kwargs):
        """
        Extract POIs from local OSM file along a GPX route.
        
        Args:
            gpx_file: Path to GPX route file
            osm_file: Path to local OSM PBF file
            buffer_meters: Buffer distance in meters around route
            use_osrm: Whether to snap POIs to roads using OSRM
            osrm_url: OSRM server URL
            
        Returns:
            GeoDataFrame of POIs along route
        """
        self._load_gpx_route(gpx_file)
        self._load_pois(osm_file)
        self._filter_pois_along_route(buffer_meters)
        
        if use_osrm:
            try:
                self._snap_to_route(osrm_url)
            except Exception as e:
                print(f"\nWarning: OSRM snapping failed: {e}")
                print("Continuing without snapping...")
                self._add_default_snapped_coords()
        else:
            self._add_default_snapped_coords()
        
        return self.pois_along_route
    
    def _load_gpx_route(self, gpx_file: str):
        """Load and parse GPX route file."""
        print(f"Loading GPX route from {gpx_file}...")
        
        with open(gpx_file) as f:
            gpx = gpxpy.parse(f)
        
        points = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append((point.longitude, point.latitude))
        
        # Try waypoints if no tracks
        if not points:
            for waypoint in gpx.waypoints:
                points.append((waypoint.longitude, waypoint.latitude))
        
        if not points:
            raise ValueError("No points found in GPX file!")
        
        self.route_line = LineString(points)
        print(f"✓ Loaded route with {len(points)} points")
    
    def _load_pois(self, osm_file: str):
        """Load POIs from OSM PBF file using osmium."""
        print(f"\nLoading POIs from {osm_file}...")
        
        try:
            import osmium
        except ImportError:
            raise ImportError(
                "osmium required for local OSM processing. "
                "Install with: pip install poi-extractor[local]"
            )
        
        categories = self.config.get_categories()
        
        # Process OSM file with osmium
        print(f"  Processing OSM file (this may take a minute)...")
        pois_data = process_osm_pois(osm_file, categories, buffer_polygon=None)
        
        if not pois_data:
            raise ValueError("No POIs found in OSM file!")
        
        # Convert to GeoDataFrame
        print(f"  Converting {len(pois_data)} POIs to GeoDataFrame...")
        
        # Create geometries
        geometries = [Point(poi['lon'], poi['lat']) for poi in pois_data]
        
        # Create DataFrame
        df_data = {
            'category': [poi['category'] for poi in pois_data],
            'name': [poi['name'] for poi in pois_data],
            'geometry': geometries,
        }
        
        # Add tag columns if present
        for tag_type in ['amenity', 'shop', 'tourism']:
            df_data[tag_type] = [poi.get(tag_type) for poi in pois_data]
        
        self.pois = gpd.GeoDataFrame(df_data, crs="EPSG:4326")
        
        print(f"\n✓ Loaded {len(self.pois)} total POIs")
        
        # Show breakdown by category
        for category in self.pois['category'].unique():
            count = len(self.pois[self.pois['category'] == category])
            print(f"  - {category}: {count}")
    
    def _filter_pois_along_route(self, buffer_meters: int):
        """Filter POIs within buffer distance of route."""
        print(f"\nFiltering POIs within {buffer_meters}m of route...")
        
        # Convert to metric CRS for buffering
        route_gdf = gpd.GeoDataFrame(
            geometry=[self.route_line],
            crs="EPSG:4326"
        )
        route_m = route_gdf.to_crs(3857)
        pois_m = self.pois.to_crs(3857)
        
        # Buffer the route
        buffer_m = route_m.buffer(buffer_meters)
        
        # Filter POIs
        pois_along_route_m = pois_m[pois_m.intersects(buffer_m.iloc[0])]
        self.pois_along_route = pois_along_route_m.to_crs(4326)
        
        print(f"✓ Found {len(self.pois_along_route)} POIs along route")
        
        # Show breakdown by category
        for category in self.pois_along_route["category"].unique():
            count = len(self.pois_along_route[
                self.pois_along_route["category"] == category
            ])
            print(f"  - {category}: {count}")
    
    def _snap_to_route(self, osrm_url: str):
        """Snap POIs to nearest road using OSRM."""
        print(f"\nSnapping POIs to route via OSRM...")
        
        total = len(self.pois_along_route)
        snapped_coords = []
        
        for idx, row in self.pois_along_route.iterrows():
            if idx % 50 == 0:
                print(f"  Progress: {idx}/{total}")
            
            geom = row.geometry
            if geom.geom_type == 'Point':
                lat, lon = geom.y, geom.x
            else:
                # Use centroid for non-point geometries
                centroid = geom.centroid
                lat, lon = centroid.y, centroid.x
            
            snapped_lat, snapped_lon = snap_to_route_osrm(lat, lon, osrm_url)
            snapped_coords.append((snapped_lat, snapped_lon))
        
        self.pois_along_route["snapped_lat"] = [c[0] for c in snapped_coords]
        self.pois_along_route["snapped_lon"] = [c[1] for c in snapped_coords]
        
        print(f"✓ Snapped {len(snapped_coords)} POIs")
    
    def _add_default_snapped_coords(self):
        """Add original coordinates as snapped coordinates."""
        self.pois_along_route["snapped_lon"] = self.pois_along_route.geometry.x
        self.pois_along_route["snapped_lat"] = self.pois_along_route.geometry.y
    
    def save_to_csv(self, output_file: str):
        """
        Save POIs to CSV file.
        
        Args:
            output_file: Path to output CSV file
        """
        print(f"\nSaving to CSV: {output_file}")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df = self.pois_along_route.copy()
        df["lon"] = df.geometry.x
        df["lat"] = df.geometry.y
        
        columns = ["category", "name", "lon", "lat", "snapped_lon", "snapped_lat"]
        
        # Add any other useful columns that exist
        for col in ["amenity", "shop", "tourism", "addr:street", "addr:city"]:
            if col in df.columns:
                columns.append(col)
        
        # Rename lon/lat to match expected format
        df_export = df[columns].copy()
        df_export.columns = [
            'category', 'name', 'lon', 'lat', 'snapped_lon', 'snapped_lat'
        ] + columns[6:]
        
        # Reorder to match other extractors' format
        final_columns = ['category', 'name', 'lat', 'lon', 
                        'snapped_lat', 'snapped_lon'] + columns[6:]
        df_export = df_export[['category', 'name', 'lat', 'lon', 
                               'snapped_lat', 'snapped_lon']]
        
        df_export.to_csv(output_file, index=False)
        print(f"✓ Saved {len(df)} POIs to {output_file}")
