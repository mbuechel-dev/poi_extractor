"""Safety criteria configuration management."""

from pathlib import Path
from typing import Dict, List, Optional
import yaml


class SafetyCriteria:
    """Parse and manage road safety analysis criteria."""
    
    # Default criteria (used if no config file provided)
    DEFAULT_THRESHOLDS = {
        'critical': 9.0,
        'high': 7.0,
        'medium': 5.0,
        'low': 3.0,
    }
    
    DEFAULT_SPEED_LIMITS = {
        'very_dangerous': 100,
        'dangerous': 80,
        'moderate': 60,
        'safe': 50,
    }
    
    DEFAULT_HIGHWAY_TYPES = {
        'forbidden': ['motorway', 'motorway_link'],
        'high_risk': ['trunk', 'trunk_link'],
        'medium_risk': ['primary', 'primary_link'],
        'low_risk': ['secondary', 'tertiary'],
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize safety criteria.
        
        Args:
            config_file: Path to YAML config file. If None, uses defaults.
        """
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
        self.speed_limits = self.DEFAULT_SPEED_LIMITS.copy()
        self.highway_types = self.DEFAULT_HIGHWAY_TYPES.copy()
        self.scoring = {}
        self.visualization = {}
        
        if config_file:
            self._load_config(config_file)
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'SafetyCriteria':
        """
        Load criteria from YAML file (class method for CLI compatibility).
        
        Args:
            yaml_path: Path to YAML configuration file
            
        Returns:
            SafetyCriteria instance
        """
        yaml_file = Path(yaml_path)
        
        if not yaml_file.exists():
            print(f"⚠️  Criteria file not found: {yaml_path}")
            print(f"   Using default safety criteria")
            return cls()
        
        try:
            return cls(config_file=yaml_path)
        except Exception as e:
            print(f"⚠️  Error loading criteria file: {e}")
            print(f"   Using default safety criteria")
            return cls()
    
    def _load_config(self, config_file: str):
        """Load configuration from YAML file."""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")
        
        # Load sections
        if 'risk_thresholds' in config:
            self.thresholds.update(config['risk_thresholds'])
        
        if 'speed_limits' in config:
            self.speed_limits.update(config['speed_limits'])
        
        if 'highway_types' in config:
            self.highway_types.update(config['highway_types'])
        
        if 'scoring' in config:
            self.scoring = config['scoring']
        
        if 'visualization' in config:
            self.visualization = config['visualization']
    
    def get_threshold(self, level: str) -> float:
        """Get risk score threshold for a level."""
        return self.thresholds.get(level, 5.0)
    
    def get_speed_limit(self, level: str) -> int:
        """Get speed limit threshold for a level."""
        return self.speed_limits.get(level, 50)
    
    def is_forbidden_highway(self, highway_type: str) -> bool:
        """Check if highway type is forbidden for cyclists."""
        forbidden = self.highway_types.get('forbidden', [])
        return highway_type in forbidden
    
    def get_highway_risk_level(self, highway_type: str) -> str:
        """Get risk level for highway type."""
        for level, types in self.highway_types.items():
            if highway_type in types:
                return level
        return 'unknown'
    
    def get_speed_penalty(self, maxspeed: int) -> float:
        """Get risk score penalty for speed limit."""
        if not self.scoring or 'speed_penalties' not in self.scoring:
            # Fallback to simple calculation
            if maxspeed >= 100:
                return 4.0
            elif maxspeed >= 80:
                return 3.0
            elif maxspeed >= 60:
                return 2.0
            elif maxspeed >= 50:
                return 1.0
            return 0.0
        
        penalties = self.scoring['speed_penalties']
        if maxspeed >= self.speed_limits.get('very_dangerous', 100):
            return penalties.get('very_high', 4.0)
        elif maxspeed >= self.speed_limits.get('dangerous', 80):
            return penalties.get('high', 3.0)
        elif maxspeed >= self.speed_limits.get('moderate', 60):
            return penalties.get('moderate', 2.0)
        elif maxspeed >= self.speed_limits.get('safe', 50):
            return penalties.get('low', 1.0)
        return 0.0
    
    def get_highway_penalty(self, highway_type: str) -> float:
        """Get risk score penalty for highway type."""
        if not self.scoring or 'highway_penalties' not in self.scoring:
            # Fallback penalties
            penalties = {
                'motorway': 5.0,
                'trunk': 3.0,
                'primary': 2.0,
                'secondary': 1.0,
            }
            return penalties.get(highway_type, 0.0)
        
        return self.scoring['highway_penalties'].get(highway_type, 0.0)
    
    def get_infrastructure_penalty(
        self, 
        has_cycleway: bool, 
        has_shoulder: bool
    ) -> float:
        """Get risk score penalty for lack of cycling infrastructure."""
        if not self.scoring or 'infrastructure_penalties' not in self.scoring:
            # Fallback
            if not has_cycleway and not has_shoulder:
                return 2.5
            elif not has_cycleway:
                return 1.5
            elif not has_shoulder:
                return 1.0
            return 0.0
        
        penalties = self.scoring['infrastructure_penalties']
        if not has_cycleway and not has_shoulder:
            return penalties.get('no_cycleway_no_shoulder', 2.5)
        elif not has_cycleway:
            return penalties.get('no_cycleway', 1.5)
        elif not has_shoulder:
            return penalties.get('no_shoulder', 1.0)
        return 0.0
    
    def get_lane_penalty(self, lanes: int) -> float:
        """Get risk score penalty for number of lanes."""
        if not self.scoring or 'lane_penalties' not in self.scoring:
            # Fallback
            if lanes >= 4:
                return 2.0
            elif lanes >= 3:
                return 1.0
            return 0.0
        
        penalties = self.scoring['lane_penalties']
        if lanes >= 4:
            return penalties.get('four_or_more', 2.0)
        elif lanes >= 3:
            return penalties.get('three', 1.0)
        return 0.0
    
    def get_surface_penalty(self, surface: Optional[str]) -> float:
        """Get risk score penalty for poor surface."""
        if not surface:
            return 0.0
        
        if not self.scoring or 'surface_penalties' not in self.scoring:
            # Fallback
            bad_surfaces = {
                'gravel': 0.5,
                'unpaved': 0.5,
                'dirt': 1.0,
                'sand': 1.5,
            }
            return bad_surfaces.get(surface, 0.0)
        
        penalties = self.scoring['surface_penalties']
        surface_lower = surface.lower()
        
        if surface_lower in ['dirt', 'sand', 'mud']:
            return penalties.get('very_bad', 1.5)
        elif surface_lower in ['gravel', 'unpaved', 'compacted']:
            return penalties.get('bad', 1.0)
        elif surface_lower in ['fine_gravel', 'pebblestone']:
            return penalties.get('unpaved', 0.5)
        return 0.0
    
    def get_infrastructure_bonus(
        self, 
        cycleway_type: Optional[str],
        bicycle_access: Optional[str]
    ) -> float:
        """Get risk score bonus (negative) for good cycling infrastructure."""
        if not self.scoring or 'infrastructure_bonuses' not in self.scoring:
            return 0.0
        
        bonuses = self.scoring['infrastructure_bonuses']
        total_bonus = 0.0
        
        if cycleway_type:
            if cycleway_type in ['track', 'separate', 'lane']:
                total_bonus += bonuses.get('dedicated_bike_lane', -2.0)
            elif cycleway_type == 'shared_lane':
                total_bonus += bonuses.get('wide_shoulder', -1.5)
        
        if bicycle_access == 'designated':
            total_bonus += bonuses.get('designated_bike_route', -1.0)
        
        return total_bonus
    
    def get_color(self, risk_score: float) -> str:
        """Get visualization color for risk score."""
        if risk_score >= self.thresholds['critical']:
            level = 'critical'
        elif risk_score >= self.thresholds['high']:
            level = 'high'
        elif risk_score >= self.thresholds['medium']:
            level = 'medium'
        elif risk_score >= self.thresholds['low']:
            level = 'low'
        else:
            level = 'minimal'
        
        if self.visualization and 'color_coding' in self.visualization:
            return self.visualization['color_coding'].get(level, '#808080')
        
        # Fallback colors
        colors = {
            'critical': '#FF0000',
            'high': '#FF8800',
            'medium': '#FFFF00',
            'low': '#88FF00',
            'minimal': '#00FF00',
        }
        return colors.get(level, '#808080')
