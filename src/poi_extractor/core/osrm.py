"""OSRM (Open Source Routing Machine) integration for road snapping."""

import requests


def snap_to_route_osrm(lat, lon, osrm_url="http://localhost:5000", timeout=5):
    """
    Snap POI to nearest road using OSRM nearest service.
    
    Args:
        lat: Latitude of POI
        lon: Longitude of POI
        osrm_url: URL of OSRM server (default: http://localhost:5000)
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (snapped_lat, snapped_lon), or original (lat, lon) if snapping fails
    """
    try:
        url = f"{osrm_url}/nearest/v1/car/{lon},{lat}"
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "Ok" and data.get("waypoints"):
                snapped = data["waypoints"][0]["location"]
                return snapped[1], snapped[0]  # Return as (lat, lon)
    except Exception:
        pass
    
    # Return original coordinates if snapping fails
    return lat, lon


def test_osrm_connection(osrm_url="http://localhost:5000"):
    """
    Test if OSRM server is accessible.
    
    Args:
        osrm_url: URL of OSRM server
        
    Returns:
        True if server is accessible, False otherwise
    """
    try:
        # Test with a simple query (coordinates in Morocco)
        url = f"{osrm_url}/nearest/v1/car/-7.0,33.0"
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False
