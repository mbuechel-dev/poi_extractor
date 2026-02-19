"""
Simplified POI Extractor for AMR Route
Extracts Points of Interest using Overpass API (no C++ compilation needed)
"""

import gpxpy
import requests
import json
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2


# POI Categories
POI_FILTERS = {
    "water": ["drinking_water", "fountain", "water_point"],
    "food": ["restaurant", "cafe", "fast_food", "bar"],
    "hotels": ["hotel", "guest_house", "hostel", "motel", "apartment"],
    "supermarket": ["supermarket", "convenience", "general"],
    "pharmacy": ["pharmacy"],
    "fuel": ["fuel"],
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth radius in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def load_gpx_route(gpx_file):
    """Load and parse GPX route file"""
    print(f"Loading GPX route from {gpx_file}...")
    
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
    
    if not points:
        raise ValueError("No points found in GPX file!")
    
    print(f"✓ Loaded route with {len(points)} points")
    return points


def get_bounding_box(points, buffer_km=2):
    """Calculate bounding box around route with buffer"""
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    
    # Add buffer (rough approximation: 1 degree ≈ 111 km)
    buffer_deg = buffer_km / 111.0
    
    bbox = {
        'south': min(lats) - buffer_deg,
        'north': max(lats) + buffer_deg,
        'west': min(lons) - buffer_deg,
        'east': max(lons) + buffer_deg
    }
    
    print(f"\nBounding box: {bbox['south']:.4f},{bbox['west']:.4f} to {bbox['north']:.4f},{bbox['east']:.4f}")
    return bbox


def query_overpass(bbox, category, amenities, timeout=180):
    """Query Overpass API for POIs"""
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Build query for multiple amenity types
    queries = []
    for amenity in amenities:
        queries.append(f'node["amenity"="{amenity}"]({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});')
        queries.append(f'way["amenity"="{amenity}"]({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});')
    
    # Also query shop and tourism tags
    if category == "supermarket":
        for shop in amenities:
            queries.append(f'node["shop"="{shop}"]({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});')
            queries.append(f'way["shop"="{shop}"]({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});')
    elif category == "hotels":
        for tourism in amenities:
            queries.append(f'node["tourism"="{tourism}"]({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});')
            queries.append(f'way["tourism"="{tourism}"]({bbox["south"]},{bbox["west"]},{bbox["north"]},{bbox["east"]});')
    
    query = f"""
    [out:json][timeout:{timeout}];
    (
      {''.join(queries)}
    );
    out center;
    """
    
    print(f"  Querying Overpass API for {category}...")
    
    try:
        response = requests.post(overpass_url, data={'data': query}, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        print(f"  ⚠ Timeout querying {category}, skipping...")
        return {'elements': []}
    except Exception as e:
        print(f"  ⚠ Error querying {category}: {e}")
        return {'elements': []}


def filter_pois_near_route(pois, route_points, buffer_meters=1000):
    """Filter POIs within buffer distance of route"""
    filtered = []
    
    for poi in pois:
        poi_lat = poi['lat']
        poi_lon = poi['lon']
        
        # Check if POI is within buffer of any route point
        for route_lat, route_lon in route_points:
            dist = haversine_distance(route_lat, route_lon, poi_lat, poi_lon)
            if dist <= buffer_meters:
                poi['distance_to_route'] = dist
                filtered.append(poi)
                break
    
    return filtered


def snap_to_route_osrm(lat, lon, osrm_url="http://localhost:5000"):
    """Snap POI to nearest road using OSRM"""
    try:
        url = f"{osrm_url}/nearest/v1/car/{lon},{lat}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            snapped = data["waypoints"][0]["location"]
            return snapped[1], snapped[0]  # lat, lon
    except:
        pass
    return lat, lon


def extract_pois(gpx_file, buffer_meters=1000, use_osrm=True):
    """Main POI extraction logic"""
    
    # Load route
    route_points = load_gpx_route(gpx_file)
    
    # Get bounding box
    bbox = get_bounding_box(route_points, buffer_km=buffer_meters/1000 + 0.5)
    
    # Query POIs for each category
    print("\nQuerying OpenStreetMap via Overpass API...")
    print("(This may take a few minutes...)")
    
    all_pois = []
    
    for category, amenities in POI_FILTERS.items():
        result = query_overpass(bbox, category, amenities)
        
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
    print(f"\nFiltering POIs within {buffer_meters}m of route...")
    filtered_pois = filter_pois_near_route(all_pois, route_points, buffer_meters)
    print(f"✓ {len(filtered_pois)} POIs along route")
    
    # Show breakdown
    categories_count = {}
    for poi in filtered_pois:
        cat = poi['category']
        categories_count[cat] = categories_count.get(cat, 0) + 1
    
    for cat, count in categories_count.items():
        print(f"  - {cat}: {count}")
    
    # Snap to route with OSRM if available
    if use_osrm:
        print("\nSnapping POIs to roads via OSRM...")
        try:
            # Test OSRM connection
            requests.get("http://localhost:5000/nearest/v1/car/-7.99,31.63", timeout=2)
            
            for poi in filtered_pois:
                snapped_lat, snapped_lon = snap_to_route_osrm(poi['lat'], poi['lon'])
                poi['snapped_lat'] = snapped_lat
                poi['snapped_lon'] = snapped_lon
            
            print(f"✓ Snapped {len(filtered_pois)} POIs")
        except:
            print("  ⚠ OSRM not available, skipping snapping")
            for poi in filtered_pois:
                poi['snapped_lat'] = poi['lat']
                poi['snapped_lon'] = poi['lon']
    else:
        for poi in filtered_pois:
            poi['snapped_lat'] = poi['lat']
            poi['snapped_lon'] = poi['lon']
    
    return filtered_pois


def save_to_csv(pois, output_file):
    """Save POIs to CSV"""
    import csv
    
    print(f"\nSaving to CSV: {output_file}")
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['category', 'name', 'lat', 'lon', 'snapped_lat', 'snapped_lon', 
                      'amenity', 'shop', 'tourism', 'distance_to_route']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for poi in pois:
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
    
    print(f"✓ Saved {len(pois)} POIs to {output_file}")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract POIs along a GPX route (Simplified version)")
    parser.add_argument("--gpx", required=True, help="Input GPX file")
    parser.add_argument("--buffer", type=int, default=1000, help="Buffer distance in meters (default: 1000)")
    parser.add_argument("--output", default="data/pois_along_route.csv", help="Output CSV file")
    parser.add_argument("--no-snap", action="store_true", help="Skip OSRM snapping")
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("AMR POI Extractor (Simplified)")
    print("=" * 50)
    
    # Extract POIs
    pois = extract_pois(args.gpx, args.buffer, use_osrm=not args.no_snap)
    
    # Save results
    save_to_csv(pois, args.output)
    
    print("\n=== POI Extraction Complete! ===")
    print(f"Results saved to: {args.output}")
    print("\nNext step: Run export_to_garmin.py to create GPX file")
    print("\nNote: This simplified version uses Overpass API.")
    print("For large areas, consider installing C++ Build Tools and using pyrosm.")


if __name__ == "__main__":
    main()
