"""Automatic OSM data download and management."""

import os
import json
import time
import requests
import urllib.request
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from shapely.geometry import box, Polygon


class OSMDataManager:
    """Manage automatic download of OSM extracts based on route location."""
    
    # Geofabrik regions metadata
    GEOFABRIK_BASE = "https://download.geofabrik.de"
    GEOFABRIK_INDEX = "https://download.geofabrik.de/index-v1.json"
    
    def __init__(self, cache_dir: str = "data/osm_cache"):
        """
        Initialize OSM data manager.
        
        Args:
            cache_dir: Directory to cache downloaded OSM files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.regions_index = None
        
    def get_osm_files_for_route(
        self, 
        gpx_path: str, 
        buffer_km: float = 100
    ) -> List[str]:
        """
        Automatically download OSM files covering the route.
        
        Args:
            gpx_path: Path to GPX route file
            buffer_km: Buffer distance around route
            
        Returns:
            List of paths to downloaded OSM PBF files
        """
        # 1. Load Geofabrik regions index
        if not self.regions_index:
            self.regions_index = self._load_geofabrik_index()
        
        # 2. Get route bounding box with buffer
        route_bbox = self._get_route_bbox(gpx_path, buffer_km)
        
        # 3. Find intersecting regions
        regions = self._find_intersecting_regions(route_bbox)
        
        if not regions:
            print(f"\n⚠️  No Geofabrik regions found for this route.")
            print(f"   Route bbox: {route_bbox}")
            print(f"\n💡 Workaround: Download OSM data manually and use --osm-file option:")
            print(f"   1. Visit https://download.geofabrik.de/")
            print(f"   2. Download the .osm.pbf file for your region")
            print(f"   3. Run: poi-extractor analyze-safety --gpx {gpx_path} --osm-file <downloaded-file.osm.pbf> --no-auto-download")
            raise ValueError(
                "Could not find matching OSM regions for route. "
                "Use --osm-file option with manually downloaded data (see above)."
            )
        
        print(f"📍 Route passes through {len(regions)} region(s): "
              f"{', '.join([r['name'] for r in regions])}")
        
        # 4. Download OSM files for each region
        osm_files = []
        for region in regions:
            osm_file = self._download_region(region)
            osm_files.append(osm_file)
        
        return osm_files
    
    def _load_geofabrik_index(self) -> dict:
        """Download and parse Geofabrik regions index."""
        cache_file = self.cache_dir / "geofabrik_index.json"
        
        # Use cached index if less than 7 days old
        if cache_file.exists():
            age_days = (time.time() - cache_file.stat().st_mtime) / 86400
            if age_days < 7:
                with open(cache_file) as f:
                    return json.load(f)
        
        print("📥 Downloading Geofabrik regions index...")
        try:
            response = requests.get(self.GEOFABRIK_INDEX, timeout=30)
            response.raise_for_status()
            index = response.json()
        except Exception as e:
            raise RuntimeError(
                f"Failed to download Geofabrik index: {e}\n"
                "Check your internet connection."
            )
        
        # Cache the index
        with open(cache_file, 'w') as f:
            json.dump(index, f)
        
        return index
    
    def _get_route_bbox(
        self, 
        gpx_path: str, 
        buffer_km: float
    ) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box for route with buffer.
        
        Args:
            gpx_path: Path to GPX file
            buffer_km: Buffer distance in kilometers
            
        Returns:
            (min_lon, min_lat, max_lon, max_lat)
        """
        from ..core.utils import load_gpx_route
        
        coords = load_gpx_route(gpx_path)
        
        if not coords:
            raise ValueError("No coordinates found in GPX file")
        
        # Calculate bbox
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        # Add buffer (approximate: 1 degree ≈ 111 km)
        buffer_deg = buffer_km / 111.0
        
        bbox = (
            min_lon - buffer_deg,
            min_lat - buffer_deg,
            max_lon + buffer_deg,
            max_lat + buffer_deg
        )
        
        print(f"📍 Route bounding box: {bbox[1]:.4f}°N to {bbox[3]:.4f}°N, "
              f"{bbox[0]:.4f}°E to {bbox[2]:.4f}°E")
        
        return bbox
    
    def _find_intersecting_regions(
        self, 
        bbox: Tuple[float, float, float, float]
    ) -> List[Dict]:
        """
        Find Geofabrik regions that intersect with bounding box.
        
        Args:
            bbox: (min_lon, min_lat, max_lon, max_lat)
            
        Returns:
            List of region metadata dictionaries
        """
        route_box = box(bbox[0], bbox[1], bbox[2], bbox[3])
        intersecting = []
        
        # Debug info
        total_features = len(self.regions_index.get('features', []))
        print(f"   Checking {total_features} Geofabrik regions...")
        
        # Iterate through all features (flat structure in Geofabrik index)
        for feature in self.regions_index.get('features', []):
            if 'properties' not in feature or 'geometry' not in feature:
                continue
            
            props = feature['properties']
            geom = feature['geometry']
            
            # Skip regions without PBF download
            if 'urls' not in props or 'pbf' not in props.get('urls', {}):
                continue
            
            try:
                # Parse geometry
                geom_type = geom.get('type')
                coords = geom.get('coordinates', [])
                
                if not coords:
                    continue
                
                # Handle different geometry types
                if geom_type == 'Polygon':
                    if len(coords) > 0 and len(coords[0]) > 2:
                        region_poly = Polygon(coords[0])
                    else:
                        continue
                elif geom_type == 'MultiPolygon':
                    if len(coords) > 0 and len(coords[0]) > 0 and len(coords[0][0]) > 2:
                        region_poly = Polygon(coords[0][0])
                    else:
                        continue
                else:
                    continue
                
                # Check intersection
                if route_box.intersects(region_poly):
                    pbf_url = props['urls']['pbf']
                    # Fix URL if it's relative
                    if pbf_url.startswith('http'):
                        # Already a full URL
                        pass
                    elif pbf_url.startswith('/'):
                        # Relative URL starting with /
                        pbf_url = self.GEOFABRIK_BASE + pbf_url
                    else:
                        # Relative URL without leading /
                        pbf_url = self.GEOFABRIK_BASE + '/' + pbf_url
                    
                    intersecting.append({
                        'name': props.get('name', 'Unknown'),
                        'id': props.get('id', 'unknown'),
                        'pbf_url': pbf_url,
                        'parent': props.get('parent', ''),
                        'size': props.get('size', 0),  # File size for optimization
                    })
            except Exception as e:
                # Skip regions with invalid geometry
                pass
        
        print(f"   Found {len(intersecting)} matching region(s)")
        
        # Optimize: prefer smaller, more specific regions
        return self._optimize_regions(intersecting)
    
    def _optimize_regions(self, regions: List[Dict]) -> List[Dict]:
        """
        Optimize region selection - prefer smaller, more specific regions.
        
        Avoids downloading continent-level regions when country/state regions are available.
        """
        if len(regions) <= 1:
            return regions
        
        # Continent-level regions to avoid (too large)
        CONTINENTS = {'africa', 'antarctica', 'asia', 'australia-oceania', 
                     'central-america', 'europe', 'north-america', 'south-america'}
        
        # Large multi-country regions to avoid if smaller options exist
        LARGE_REGIONS = {'dach'}  # Germany+Austria+Switzerland
        
        # Filter out continents if we have more specific regions
        non_continent = [r for r in regions if r['id'] not in CONTINENTS]
        
        if non_continent:
            regions = non_continent
            print(f"   Filtered out {len([r for r in regions if r['id'] in CONTINENTS])} continent-level regions")
        
        # Filter out large multi-country regions if we have country-specific options
        if len(regions) > 1:
            non_large = [r for r in regions if r['id'] not in LARGE_REGIONS]
            if non_large:
                regions = non_large
        
        # If we still have multiple regions, prefer the smallest by file size
        if len(regions) > 1:
            # Sort by size (smallest first), use 0 as default if size not available
            regions_with_size = [(r, r.get('size', float('inf'))) for r in regions]
            regions_with_size.sort(key=lambda x: x[1])
            
            # Take the smallest one
            selected = regions_with_size[0][0]
            print(f"   Selected smallest region: {selected['name']}")
            return [selected]
        
        return regions
    
    def _download_region(self, region: Dict) -> str:
        """
        Download OSM PBF file for a region.
        
        Args:
            region: Region metadata dictionary
            
        Returns:
            Path to downloaded PBF file
        """
        filename = region['pbf_url'].split('/')[-1]
        output_path = self.cache_dir / filename
        
        # Check if already downloaded
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"✓ Using cached: {filename} ({size_mb:.1f} MB)")
            return str(output_path)
        
        print(f"⬇  Downloading {region['name']} ({filename})...")
        print(f"   URL: {region['pbf_url']}")
        
        # Download with progress bar
        downloaded_mb = [0]
        
        def progress_hook(block_count, block_size, total_size):
            if total_size > 0:
                downloaded = block_count * block_size
                downloaded_mb[0] = downloaded / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                percent = min(100, block_count * block_size * 100 / total_size)
                print(f"\r   Progress: {percent:.1f}% ({downloaded_mb[0]:.1f}/{total_mb:.1f} MB)", 
                      end='', flush=True)
        
        try:
            urllib.request.urlretrieve(
                region['pbf_url'],
                output_path,
                reporthook=progress_hook
            )
            print(f"\n✓ Downloaded: {filename} ({downloaded_mb[0]:.1f} MB)")
        except Exception as e:
            # Clean up partial download
            if output_path.exists():
                output_path.unlink()
            raise RuntimeError(
                f"Failed to download {filename}: {e}\n"
                "Check your internet connection and try again."
            )
        
        return str(output_path)
    
    def clear_cache(self, older_than_days: int = 30):
        """
        Clear cached OSM files older than specified days.
        
        Args:
            older_than_days: Remove files older than this many days
        """
        cutoff = time.time() - (older_than_days * 86400)
        removed = 0
        freed_mb = 0
        
        for file in self.cache_dir.glob("*.osm.pbf"):
            if file.stat().st_mtime < cutoff:
                size_mb = file.stat().st_size / (1024 * 1024)
                file.unlink()
                removed += 1
                freed_mb += size_mb
                print(f"🗑️  Removed old cache file: {file.name} ({size_mb:.1f} MB)")
        
        if removed > 0:
            print(f"\n✓ Cleared {removed} cached OSM file(s) "
                  f"(freed {freed_mb:.1f} MB)")
        else:
            print(f"✓ No cached files older than {older_than_days} days found")
