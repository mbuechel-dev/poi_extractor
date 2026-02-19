"""Data models for road safety analysis."""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class RoadSegment:
    """Represents a road segment with safety attributes and risk assessment."""
    
    osm_id: str
    name: str
    coordinates: List[Tuple[float, float]]  # [(lat, lon), ...]
    highway_type: str
    maxspeed: int  # km/h
    has_cycleway: bool
    has_shoulder: bool
    lanes: int
    surface: Optional[str]
    bicycle_access: Optional[str]
    risk_score: float
    risk_factors: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return (
            f"RoadSegment(id={self.osm_id}, name='{self.name}', "
            f"type={self.highway_type}, risk={self.risk_score:.1f})"
        )
    
    @property
    def risk_level(self) -> str:
        """Get human-readable risk level."""
        if self.risk_score >= 9.0:
            return "critical"
        elif self.risk_score >= 7.0:
            return "high"
        elif self.risk_score >= 5.0:
            return "medium"
        elif self.risk_score >= 3.0:
            return "low"
        else:
            return "minimal"
    
    @property
    def color(self) -> str:
        """Get color code for visualization."""
        colors = {
            "critical": "#FF0000",  # Red
            "high": "#FF8800",      # Orange
            "medium": "#FFFF00",    # Yellow
            "low": "#88FF00",       # Light green
            "minimal": "#00FF00",   # Green
        }
        return colors.get(self.risk_level, "#808080")
    
    def length_km(self) -> float:
        """Calculate approximate length of road segment in kilometers."""
        from ..core.utils import haversine_distance
        
        if len(self.coordinates) < 2:
            return 0.0
        
        total = 0.0
        for i in range(len(self.coordinates) - 1):
            lat1, lon1 = self.coordinates[i]
            lat2, lon2 = self.coordinates[i + 1]
            total += haversine_distance(lat1, lon1, lat2, lon2)
        
        return total / 1000.0  # Convert meters to km
