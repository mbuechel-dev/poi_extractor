"""
POI Extractor for AMR Route
Extracts Points of Interest along a GPX route from OSM data

⚠️  DEPRECATED: This script is deprecated in favor of the package-based CLI.
Please use: poi-extractor extract --strategy local --gpx <file> --osm <osm_file>

To install the package with local support: pip install -e .[local]
"""

import warnings
warnings.warn(
    "This script is deprecated. Use 'poi-extractor extract --strategy local' instead. "
    "Install the package with: pip install -e .[local]",
    DeprecationWarning,
    stacklevel=2
)

import gpxpy
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
from pyrosm import OSM
import requests
from pathlib import Path


# POI Categories - customize these as needed
POI_FILTERS = {
    "hotels": {"tourism": ["hotel", "guest_house", "hostel", "motel", "apartment"]},
    "food": {"amenity": ["restaurant", "cafe", "fast_food", "bar"]},
    "water": {"amenity": ["drinking_water", "fountain", "water_point"]},
    "supermarket": {"shop": ["supermarket", "convenience", "general"]},
    "pharmacy": {"amenity": ["pharmacy"]},
    "fuel": {"amenity": ["fuel"]},
}


class POIExtractor:
    def __init__(self, gpx_file, osm_file, buffer_distance=1000):
        """
        Initialize POI Extractor
        
        Args:
            gpx_file: Path to GPX route file
            osm_file: Path to OSM PBF file
            buffer_distance: Buffer distance in meters around route (default 1000m)
        """
        self.gpx_file = Path(gpx_file)
        self.osm_file = Path(osm_file)
        self.buffer_distance = buffer_distance
        self.route_line = None
        self.pois = None
        self.pois_along_route = None
        
    def load_gpx_route(self):
        """Load and parse GPX route file"""
        print(f"Loading GPX route from {self.gpx_file}...")
        
        with open(self.gpx_file) as f:
            gpx = gpxpy.parse(f)
        
        points = []
        for track in gpx.tracks:
            for seg in track.segments:
                for p in seg.points:
                    points.append((p.longitude, p.latitude))
        
        if not points:
            # Try waypoints if no tracks
            for waypoint in gpx.waypoints:
                points.append((waypoint.longitude, waypoint.latitude))
        
        if not points:
            raise ValueError("No points found in GPX file!")
        
        self.route_line = LineString(points)
        print(f"✓ Loaded route with {len(points)} points")
        return self.route_line
    
    def load_pois(self):
        """Load POIs from OSM file"""
        print(f"\nLoading POIs from {self.osm_file}...")
        
        osm = OSM(str(self.osm_file))
        pois_list = []
        
        for category, tags in POI_FILTERS.items():
            print(f"  Loading {category}...")
            try:
                gdf = osm.get_pois(custom_filter=tags)
                if gdf is not None and len(gdf) > 0:
                    gdf["category"] = category
                    pois_list.append(gdf)
                    print(f"    Found {len(gdf)} {category} POIs")
            except Exception as e:
                print(f"    Warning: Could not load {category}: {e}")
        
        if not pois_list:
            raise ValueError("No POIs found!")
        
        self.pois = gpd.GeoDataFrame(pd.concat(pois_list, ignore_index=True), crs="EPSG:4326")
        print(f"\n✓ Loaded {len(self.pois)} total POIs")
        return self.pois
    
    def filter_pois_along_route(self):
        """Filter POIs within buffer distance of route"""
        print(f"\nFiltering POIs within {self.buffer_distance}m of route...")
        
        # Convert to metric CRS for buffering
        route_gdf = gpd.GeoDataFrame(geometry=[self.route_line], crs="EPSG:4326")
        route_m = route_gdf.to_crs(3857)
        pois_m = self.pois.to_crs(3857)
        
        # Buffer the route
        buffer_m = route_m.buffer(self.buffer_distance)
        
        # Filter POIs
        pois_along_route_m = pois_m[pois_m.intersects(buffer_m.iloc[0])]
        self.pois_along_route = pois_along_route_m.to_crs(4326)
        
        print(f"✓ Found {len(self.pois_along_route)} POIs along route")
        
        # Show breakdown by category
        for category in self.pois_along_route["category"].unique():
            count = len(self.pois_along_route[self.pois_along_route["category"] == category])
            print(f"  - {category}: {count}")
        
        return self.pois_along_route
    
    def snap_to_route(self, osrm_url="http://localhost:5000"):
        """Snap POIs to nearest road using OSRM"""
        print(f"\nSnapping POIs to route via OSRM...")
        
        def snap(lon, lat):
            try:
                url = f"{osrm_url}/nearest/v1/car/{lon},{lat}"
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    return data["waypoints"][0]["location"]
                return [lon, lat]
            except Exception as e:
                print(f"  Warning: Could not snap ({lon}, {lat}): {e}")
                return [lon, lat]
        
        total = len(self.pois_along_route)
        snapped_coords = []
        
        for idx, row in self.pois_along_route.iterrows():
            if idx % 50 == 0:
                print(f"  Progress: {idx}/{total}")
            
            geom = row.geometry
            if geom.geom_type == 'Point':
                snapped = snap(geom.x, geom.y)
                snapped_coords.append(snapped)
            else:
                # Use centroid for non-point geometries
                centroid = geom.centroid
                snapped = snap(centroid.x, centroid.y)
                snapped_coords.append(snapped)
        
        self.pois_along_route["snapped_lon"] = [c[0] for c in snapped_coords]
        self.pois_along_route["snapped_lat"] = [c[1] for c in snapped_coords]
        
        print(f"✓ Snapped {len(snapped_coords)} POIs")
        return self.pois_along_route
    
    def save_to_csv(self, output_file):
        """Save POIs to CSV for inspection"""
        print(f"\nSaving to CSV: {output_file}")
        
        df = self.pois_along_route.copy()
        df["lon"] = df.geometry.x
        df["lat"] = df.geometry.y
        
        columns = ["category", "name", "lon", "lat", "snapped_lon", "snapped_lat"]
        # Add any other useful columns that exist
        for col in ["amenity", "shop", "tourism", "addr:street", "addr:city"]:
            if col in df.columns:
                columns.append(col)
        
        df[columns].to_csv(output_file, index=False)
        print(f"✓ Saved {len(df)} POIs to {output_file}")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract POIs along a GPX route")
    parser.add_argument("--gpx", required=True, help="Input GPX file")
    parser.add_argument("--osm", default="osrm/morocco-latest.osm.pbf", help="OSM PBF file")
    parser.add_argument("--buffer", type=int, default=1000, help="Buffer distance in meters (default: 1000)")
    parser.add_argument("--output", default="data/pois_along_route.csv", help="Output CSV file")
    parser.add_argument("--no-snap", action="store_true", help="Skip OSRM snapping")
    parser.add_argument("--osrm-url", default="http://localhost:5000", help="OSRM server URL")
    
    args = parser.parse_args()
    
    # Create extractor
    extractor = POIExtractor(args.gpx, args.osm, args.buffer)
    
    # Process
    extractor.load_gpx_route()
    extractor.load_pois()
    extractor.filter_pois_along_route()
    
    if not args.no_snap:
        try:
            extractor.snap_to_route(args.osrm_url)
        except Exception as e:
            print(f"\nWarning: OSRM snapping failed: {e}")
            print("Continuing without snapping...")
    
    # Save results
    extractor.save_to_csv(args.output)
    
    print("\n=== POI Extraction Complete! ===")
    print(f"Results saved to: {args.output}")
    print("\nNext step: Run export_to_garmin.py to create GPX file")


if __name__ == "__main__":
    main()
