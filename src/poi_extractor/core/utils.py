"""Shared utility functions for POI extraction."""

import gpxpy
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points in meters using Haversine formula.
    
    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point
        
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def load_gpx_route(gpx_file):
    """
    Load and parse GPX route file.
    
    Args:
        gpx_file: Path to GPX file
        
    Returns:
        List of (latitude, longitude) tuples
        
    Raises:
        ValueError: If no points found in GPX file
    """
    gpx_file = Path(gpx_file)
    
    with open(gpx_file) as f:
        gpx = gpxpy.parse(f)
    
    points = []
    
    # Try tracks first
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude))
    
    # Fall back to waypoints if no tracks
    if not points:
        for waypoint in gpx.waypoints:
            points.append((waypoint.latitude, waypoint.longitude))
    
    if not points:
        raise ValueError(f"No points found in GPX file: {gpx_file}")
    
    return points


def get_bounding_box(points, buffer_km=2):
    """
    Calculate bounding box around route with buffer.
    
    Args:
        points: List of (lat, lon) tuples
        buffer_km: Buffer distance in kilometers
        
    Returns:
        Dict with keys: south, north, west, east
    """
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
    
    return bbox


def calculate_route_length(points):
    """
    Calculate total route length in kilometers.
    
    Args:
        points: List of (lat, lon) tuples
        
    Returns:
        Total length in kilometers
    """
    total = 0
    for i in range(len(points) - 1):
        total += haversine_distance(
            points[i][0], points[i][1],
            points[i+1][0], points[i+1][1]
        )
    return total / 1000  # Convert to km
