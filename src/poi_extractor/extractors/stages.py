"""Stage-based POI Extractor using Overpass API for long routes."""

import requests
import time
import csv
from pathlib import Path
from typing import List, Dict, Optional

from ..core import (
    load_gpx_route,
    get_bounding_box,
    haversine_distance,
    calculate_route_length,
    Config,
)


class StagesExtractor:
    """Extract POIs by splitting long routes into stages to avoid API timeouts."""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize StagesExtractor.
        
        Args:
            config: Configuration object (uses defaults if None)
        """
        self.config = config or Config()
        self.pois = []
    
    def extract(self, gpx_file: str, buffer_meters: int = 1000,
                stage_km: int = 150, **kwargs):
        """
        Extract POIs along a GPX route split into stages.
        
        Args:
            gpx_file: Path to GPX route file
            buffer_meters: Buffer distance in meters around route
            stage_km: Length of each stage in kilometers
            
        Returns:
            List of POI dictionaries with stage information
        """
        print(f"📂 Loading route from: {gpx_file}")
        route_points = load_gpx_route(gpx_file)
        print(f"✓ Loaded {len(route_points)} points")
        
        # Split route into stages
        stages = self._split_route_by_distance(route_points, stage_km)
        
        # Process each stage
        all_pois = []
        
        for stage in stages:
            print(f"\n🔍 Stage {stage['stage_num']}/{len(stages)} "
                  f"(km {stage['start_km']:.0f}-{stage['end_km']:.0f})")
            
            stage_pois = self._query_overpass_for_stage(
                stage['points'], buffer_meters
            )
            
            if stage_pois:
                # Filter to only POIs near the route
                filtered_pois = self._filter_pois_near_route(
                    stage_pois, stage['points'], buffer_meters
                )
                
                # Add stage information and original coords as "snapped"
                for poi in filtered_pois:
                    poi['stage'] = stage['stage_num']
                    poi['stage_start_km'] = stage['start_km']
                    poi['snapped_lat'] = poi['lat']
                    poi['snapped_lon'] = poi['lon']
                
                all_pois.extend(filtered_pois)
                print(f"✓ POIs near route: {len(filtered_pois)}")
            else:
                print(f"⚠ No POIs found")
            
            # Rate limiting - be nice to Overpass API
            if stage['stage_num'] < len(stages):
                print("⏳ Waiting 3 seconds before next stage...")
                time.sleep(3)
        
        # Remove duplicates
        if all_pois:
            print(f"\n🔄 Removing duplicates...")
            self.pois = self._remove_duplicates(all_pois)
            self._print_summary(len(stages))
        else:
            print("\n⚠ No POIs found in any stage")
            self.pois = []
        
        return self.pois
    
    def _split_route_by_distance(self, points: List[tuple], 
                                  stage_km: int) -> List[Dict]:
        """Split route into stages by distance."""
        print(f"\n📏 Splitting route into ~{stage_km}km stages...")
        
        total_length = calculate_route_length(points)
        print(f"Total route length: {total_length:.1f} km")
        
        num_stages = int(total_length / stage_km) + 1
        print(f"Creating {num_stages} stages...")
        
        stages = []
        current_stage_points = []
        current_stage_dist = 0
        stage_num = 1
        stage_start_km = 0
        
        for i, point in enumerate(points):
            current_stage_points.append(point)
            
            if i < len(points) - 1:
                segment_dist = haversine_distance(
                    point[0], point[1],
                    points[i+1][0], points[i+1][1]
                ) / 1000
                current_stage_dist += segment_dist
                
                # If we've reached the stage distance
                if current_stage_dist >= stage_km and i < len(points) - 1:
                    stages.append({
                        'stage_num': stage_num,
                        'start_km': stage_start_km,
                        'end_km': stage_start_km + current_stage_dist,
                        'stage_km': current_stage_dist,
                        'points': current_stage_points
                    })
                    
                    print(f"  Stage {stage_num}: km {stage_start_km:.1f} - "
                          f"{stage_start_km + current_stage_dist:.1f} "
                          f"({current_stage_dist:.1f} km, {len(current_stage_points)} points)")
                    
                    # Start new stage
                    stage_start_km += current_stage_dist
                    stage_num += 1
                    current_stage_points = [point]
                    current_stage_dist = 0
        
        # Add final stage
        if current_stage_points:
            stages.append({
                'stage_num': stage_num,
                'start_km': stage_start_km,
                'end_km': stage_start_km + current_stage_dist,
                'stage_km': current_stage_dist,
                'points': current_stage_points
            })
            print(f"  Stage {stage_num}: km {stage_start_km:.1f} - "
                  f"{stage_start_km + current_stage_dist:.1f} "
                  f"({current_stage_dist:.1f} km, {len(current_stage_points)} points)")
        
        return stages
    
    def _query_overpass_for_stage(self, points: List[tuple], 
                                   buffer_m: int) -> List[Dict]:
        """Query Overpass API for a single stage."""
        # Get bounding box
        buffer_deg = buffer_m / 111000  # rough approximation
        bbox = get_bounding_box(points, buffer_km=buffer_deg * 111)
        bbox_str = f"({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']})"
        
        all_pois = []
        categories = self.config.get_categories()
        
        # Try multiple servers in case of failure
        servers = [
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass-api.de/api/interpreter",
        ]
        
        for category, filters in categories.items():
            print(f"  Querying {category}...", end=" ", flush=True)
            
            # Build query
            query = "[out:json][timeout:90];\n(\n"
            for key, values in filters.items():
                for value in values:
                    query += f'  node["{key}"="{value}"]{bbox_str};\n'
                    query += f'  way["{key}"="{value}"]{bbox_str};\n'
            query += ");\nout center;"
            
            success = False
            for server in servers:
                try:
                    response = requests.post(
                        server,
                        data={'data': query},
                        timeout=90
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    # Parse results
                    category_count = 0
                    for element in data.get("elements", []):
                        if "lat" in element and "lon" in element:
                            lat, lon = element["lat"], element["lon"]
                        elif "center" in element:
                            lat, lon = element["center"]["lat"], element["center"]["lon"]
                        else:
                            continue
                        
                        all_pois.append({
                            "name": element.get("tags", {}).get("name", ""),
                            "category": category,
                            "lat": lat,
                            "lon": lon,
                            "amenity": element.get("tags", {}).get("amenity", ""),
                            "shop": element.get("tags", {}).get("shop", ""),
                            "tourism": element.get("tags", {}).get("tourism", ""),
                        })
                        category_count += 1
                    
                    print(f"✓ {category_count} found")
                    success = True
                    time.sleep(1)  # Rate limiting
                    break
                    
                except (requests.Timeout, requests.HTTPError):
                    continue
                except Exception:
                    continue
            
            if not success:
                print(f"⚠ Failed (skipping)")
        
        return all_pois
    
    def _filter_pois_near_route(self, pois: List[Dict],
                                route_points: List[tuple],
                                buffer_m: int) -> List[Dict]:
        """Filter POIs to only those near the route."""
        if not pois:
            return []
        
        filtered = []
        for poi in pois:
            poi_lat = poi['lat']
            poi_lon = poi['lon']
            
            # Check if POI is within buffer of any route point
            for route_lat, route_lon in route_points:
                dist = haversine_distance(route_lat, route_lon, poi_lat, poi_lon)
                if dist <= buffer_m:
                    poi['distance_to_route'] = int(dist)
                    filtered.append(poi)
                    break
        
        return filtered
    
    def _remove_duplicates(self, pois: List[Dict]) -> List[Dict]:
        """Remove duplicate POIs based on coordinates."""
        seen = set()
        unique = []
        
        for poi in pois:
            coord = (round(poi['lat'], 6), round(poi['lon'], 6))
            if coord not in seen:
                seen.add(coord)
                unique.append(poi)
        
        return unique
    
    def _print_summary(self, num_stages: int):
        """Print extraction summary."""
        category_counts = {}
        stage_counts = {}
        
        for poi in self.pois:
            cat = poi['category']
            stage = poi.get('stage', 1)
            category_counts[cat] = category_counts.get(cat, 0) + 1
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        print(f"\n📊 Summary:")
        print(f"  Total POIs found: {len(self.pois)}")
        print(f"\n📈 POIs by category:")
        for cat in sorted(category_counts.keys(), 
                         key=lambda x: category_counts[x], reverse=True):
            print(f"  {cat:15s}: {category_counts[cat]:4d}")
        print(f"\n📍 POIs by stage:")
        for stage in sorted(stage_counts.keys()):
            print(f"  Stage {stage:2d}: {stage_counts[stage]:4d}")
    
    def save_to_csv(self, output_file: str):
        """
        Save POIs to CSV file with stage information.
        
        Args:
            output_file: Path to output CSV file
        """
        print(f"\nSaving to CSV: {output_file}")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = ['category', 'name', 'lat', 'lon', 'snapped_lat', 'snapped_lon',
                     'stage', 'stage_start_km', 'distance_to_route', 
                     'amenity', 'shop', 'tourism']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
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
                    'stage': poi.get('stage', ''),
                    'stage_start_km': f"{poi.get('stage_start_km', 0):.1f}",
                    'distance_to_route': poi.get('distance_to_route', ''),
                    'amenity': poi.get('amenity', ''),
                    'shop': poi.get('shop', ''),
                    'tourism': poi.get('tourism', ''),
                })
        
        print(f"✓ Saved {len(self.pois)} POIs to {output_file}")
