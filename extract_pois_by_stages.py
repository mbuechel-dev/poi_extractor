"""
Split long route into stages and extract POIs for each stage.
Avoids Overpass API timeouts for long routes like AMR.
"""

import gpxpy
import requests
import time
from pathlib import Path
import argparse
from math import radians, sin, cos, sqrt, atan2
import csv


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth radius in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def calculate_route_length(points):
    """Calculate total route length in kilometers"""
    total = 0
    for i in range(len(points) - 1):
        total += haversine_distance(points[i][0], points[i][1], 
                                   points[i+1][0], points[i+1][1])
    return total / 1000  # Convert to km


def load_gpx(gpx_file):
    """Load GPX route and return list of (lat, lon) points"""
    with open(gpx_file) as f:
        gpx = gpxpy.parse(f)
    
    points = []
    for track in gpx.tracks:
        for seg in track.segments:
            for p in seg.points:
                points.append((p.latitude, p.longitude))
    
    if not points:
        for waypoint in gpx.waypoints:
            points.append((waypoint.latitude, waypoint.longitude))
    
    return points


def split_route_by_distance(points, stage_km=150):
    """Split route into stages by distance"""
    print(f"\n📏 Splitting route into ~{stage_km}km stages...")
    
    total_length = calculate_route_length(points)
    print(f"  Total route length: {total_length:.1f} km")
    
    num_stages = int(total_length / stage_km) + 1
    print(f"  Creating {num_stages} stages...")
    
    stages = []
    current_stage_points = []
    current_stage_dist = 0
    stage_num = 1
    stage_start_km = 0
    
    for i, point in enumerate(points):
        current_stage_points.append(point)
        
        if i < len(points) - 1:
            segment_dist = haversine_distance(point[0], point[1], 
                                             points[i+1][0], points[i+1][1]) / 1000
            current_stage_dist += segment_dist
            
            # If we've reached the stage distance and we're not at the last point
            if current_stage_dist >= stage_km and i < len(points) - 1:
                stages.append({
                    'stage_num': stage_num,
                    'start_km': stage_start_km,
                    'end_km': stage_start_km + current_stage_dist,
                    'stage_km': current_stage_dist,
                    'points': current_stage_points
                })
                
                print(f"    Stage {stage_num}: km {stage_start_km:.1f} - {stage_start_km + current_stage_dist:.1f} ({current_stage_dist:.1f} km, {len(current_stage_points)} points)")
                
                # Start new stage
                stage_start_km += current_stage_dist
                stage_num += 1
                current_stage_points = [point]  # Start with last point of previous stage
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
        print(f"    Stage {stage_num}: km {stage_start_km:.1f} - {stage_start_km + current_stage_dist:.1f} ({current_stage_dist:.1f} km, {len(current_stage_points)} points)")
    
    return stages


def get_bounding_box(points, buffer_deg=0.02):
    """Calculate bounding box around points with buffer"""
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    
    bbox = {
        'south': min(lats) - buffer_deg,
        'north': max(lats) + buffer_deg,
        'west': min(lons) - buffer_deg,
        'east': max(lons) + buffer_deg
    }
    
    return bbox


def query_overpass_for_stage(points, buffer_m=1000):
    """Query Overpass API for a single stage"""
    
    # Get bounding box (rough approximation: 1 degree ≈ 111 km)
    buffer_deg = buffer_m / 111000
    bbox = get_bounding_box(points, buffer_deg)
    bbox_str = f"({bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']})"
    
    # POI categories for Morocco
    categories = {
        "water": {"amenity": ["drinking_water", "fountain", "water_point"]},
        "food": {"amenity": ["restaurant", "cafe", "fast_food"]},
        "hotel": {"tourism": ["hotel", "guest_house", "hostel", "motel"]},
        "supermarket": {"shop": ["supermarket", "convenience"]},
        "pharmacy": {"amenity": ["pharmacy"]},
        "fuel": {"amenity": ["fuel"]},
        "hospital": {"amenity": ["hospital", "clinic", "doctors"]},
        "atm": {"amenity": ["atm", "bank"]}
    }
    
    all_pois = []
    
    # Try multiple servers in case of failure
    servers = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter",
    ]
    
    for category, tags in categories.items():
        print(f"  Querying {category}...", end=" ", flush=True)
        
        # Build query
        query = f"""
        [out:json][timeout:90];
        (
        """
        for key, values in tags.items():
            for value in values:
                query += f'  node["{key}"="{value}"]{bbox_str};\n'
                query += f'  way["{key}"="{value}"]{bbox_str};\n'
        query += ");\nout center;"
        
        success = False
        for server in servers:
            try:
                response = requests.post(server, data={'data': query}, timeout=90)
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
                
            except requests.Timeout:
                continue
            except requests.HTTPError as e:
                if e.response.status_code in [429, 504]:
                    continue
                else:
                    break
            except Exception:
                continue
        
        if not success:
            print(f"⚠ Failed (skipping)")
    
    return all_pois


def filter_pois_near_route(pois, route_points, buffer_m=1000):
    """Filter POIs to only those near the route"""
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


def remove_duplicates(pois):
    """Remove duplicate POIs based on coordinates"""
    seen = set()
    unique = []
    
    for poi in pois:
        coord = (round(poi['lat'], 6), round(poi['lon'], 6))
        if coord not in seen:
            seen.add(coord)
            unique.append(poi)
    
    return unique


def save_to_csv(pois, output_file):
    """Save POIs to CSV"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = ['category', 'name', 'lat', 'lon', 'snapped_lat', 'snapped_lon',
                  'stage', 'stage_start_km', 'distance_to_route', 'amenity', 'shop', 'tourism']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for poi in pois:
            writer.writerow({
                'category': poi.get('category', ''),
                'name': poi.get('name', ''),
                'lat': poi.get('lat', ''),
                'lon': poi.get('lon', ''),
                'snapped_lat': poi.get('lat', ''),  # Use original coords as "snapped"
                'snapped_lon': poi.get('lon', ''),  # Can add OSRM snapping later
                'stage': poi.get('stage', ''),
                'stage_start_km': f"{poi.get('stage_start_km', 0):.1f}",
                'distance_to_route': poi.get('distance_to_route', ''),
                'amenity': poi.get('amenity', ''),
                'shop': poi.get('shop', ''),
                'tourism': poi.get('tourism', ''),
            })


def main():
    parser = argparse.ArgumentParser(description='Extract POIs from long route by splitting into stages')
    parser.add_argument('--gpx', required=True, help='Input GPX file')
    parser.add_argument('--buffer', type=int, default=1000, help='Buffer distance in meters (default: 1000)')
    parser.add_argument('--stage-km', type=int, default=150, help='Stage length in km (default: 150)')
    parser.add_argument('--output', default='data/pois_along_route.csv', help='Output CSV file')
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚴 AMR POI Extractor - Stage-by-Stage Processing")
    print("="*60)
    
    # Load route
    print(f"\n📂 Loading route from: {args.gpx}")
    route_points = load_gpx(args.gpx)
    print(f"  ✓ Loaded {len(route_points)} points")
    
    # Split into stages
    stages = split_route_by_distance(route_points, stage_km=args.stage_km)
    
    # Process each stage
    all_pois = []
    
    for stage in stages:
        print(f"\n🔍 Stage {stage['stage_num']}/{len(stages)} (km {stage['start_km']:.0f}-{stage['end_km']:.0f})")
        
        stage_pois = query_overpass_for_stage(stage['points'], buffer_m=args.buffer)
        
        if stage_pois:
            # Filter to only POIs near the route
            filtered_pois = filter_pois_near_route(stage_pois, stage['points'], buffer_m=args.buffer)
            
            # Add stage information
            for poi in filtered_pois:
                poi['stage'] = stage['stage_num']
                poi['stage_start_km'] = stage['start_km']
            
            all_pois.extend(filtered_pois)
            print(f"  ✓ POIs near route: {len(filtered_pois)}")
        else:
            print(f"  ⚠ No POIs found")
        
        # Be nice to Overpass API - wait between stages
        if stage['stage_num'] < len(stages):
            print("  ⏳ Waiting 3 seconds before next stage...")
            time.sleep(3)
    
    # Remove duplicates
    if all_pois:
        print(f"\n🔄 Removing duplicates...")
        all_pois = remove_duplicates(all_pois)
        
        # Count by category
        category_counts = {}
        stage_counts = {}
        for poi in all_pois:
            cat = poi['category']
            stage = poi['stage']
            category_counts[cat] = category_counts.get(cat, 0) + 1
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        # Save to CSV
        save_to_csv(all_pois, args.output)
        
        print("\n" + "="*60)
        print("✅ POI EXTRACTION COMPLETE!")
        print("="*60)
        print(f"\n📊 Summary:")
        print(f"  Total POIs found: {len(all_pois)}")
        print(f"  Saved to: {args.output}")
        print(f"\n📈 POIs by category:")
        for cat in sorted(category_counts.keys(), key=lambda x: category_counts[x], reverse=True):
            print(f"  {cat:15s}: {category_counts[cat]:4d}")
        print(f"\n📍 POIs by stage:")
        for stage in sorted(stage_counts.keys()):
            print(f"  Stage {stage:2d}: {stage_counts[stage]:4d}")
        
        print(f"\n🎯 Next step: Run export script")
        print(f"  .\.venv\Scripts\python.exe export_to_garmin.py")
        
    else:
        print("\n⚠ No POIs found in any stage")


if __name__ == "__main__":
    main()
