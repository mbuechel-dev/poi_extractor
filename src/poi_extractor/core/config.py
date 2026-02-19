"""Configuration management for POI Extractor."""

import configparser
from pathlib import Path
from typing import Dict, List, Optional


class Config:
    """Parse and manage POI Extractor configuration."""
    
    # Default POI categories (used if no config file provided)
    DEFAULT_CATEGORIES = {
        "water": {
            "amenity": ["drinking_water", "fountain", "water_point"],
            "man_made": ["water_well", "water_tap"],
        },
        "food": {
            "amenity": ["restaurant", "cafe", "fast_food", "bar", "pub", "food_court"],
            "shop": ["bakery"],
        },
        "hotels": {
            "tourism": ["hotel", "guest_house", "hostel", "motel", "apartment", 
                       "alpine_hut", "wilderness_hut", "camp_site"],
        },
        "supermarket": {
            "shop": ["supermarket", "convenience", "general", "grocery"],
        },
        "pharmacy": {
            "amenity": ["pharmacy"],
        },
        "fuel": {
            "amenity": ["fuel"],
        },
        "medical": {
            "amenity": ["clinic", "hospital", "doctors", "dentist"],
        },
        "bike_shop": {
            "shop": ["bicycle", "sports"],
        },
        "atm": {
            "amenity": ["atm", "bank"],
        },
    }
    
    # Default Garmin symbol mappings
    DEFAULT_SYMBOLS = {
        "water": "Water Source",
        "food": "Restaurant",
        "hotels": "Lodging",
        "supermarket": "Shopping",
        "pharmacy": "Pharmacy",
        "fuel": "Gas Station",
        "medical": "Medical Facility",
        "bike_shop": "Bike Trail",
        "atm": "Bank",
    }
    
    # Default buffer distances (in meters)
    DEFAULT_BUFFERS = {
        "water": 500,
        "food": 1000,
        "hotels": 2000,
        "supermarket": 1000,
        "pharmacy": 1500,
        "fuel": 1500,
        "medical": 2000,
        "bike_shop": 2000,
        "atm": 1000,
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_file: Path to config.ini file. If None, uses defaults.
        """
        self.categories = self.DEFAULT_CATEGORIES.copy()
        self.symbols = self.DEFAULT_SYMBOLS.copy()
        self.buffers = self.DEFAULT_BUFFERS.copy()
        
        if config_file:
            self._load_config(config_file)
    
    def _load_config(self, config_file: str):
        """Load configuration from INI file."""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        parser = configparser.ConfigParser()
        parser.read(config_path)
        
        # Parse POI categories
        self.categories = {}
        for section in parser.sections():
            if section in ['buffer_distances', 'garmin_symbols']:
                continue
            
            category_filters = {}
            for key in parser[section]:
                values = [v.strip() for v in parser[section][key].split(',')]
                category_filters[key] = values
            
            self.categories[section] = category_filters
        
        # Parse buffer distances
        if 'buffer_distances' in parser:
            for category, distance in parser['buffer_distances'].items():
                try:
                    self.buffers[category] = int(distance)
                except ValueError:
                    pass
        
        # Parse Garmin symbols
        if 'garmin_symbols' in parser:
            for category, symbol in parser['garmin_symbols'].items():
                self.symbols[category] = symbol
    
    def get_categories(self) -> Dict[str, Dict[str, List[str]]]:
        """Get all POI category definitions."""
        return self.categories
    
    def get_buffer_distance(self, category: str, default: int = 1000) -> int:
        """Get buffer distance for a category."""
        return self.buffers.get(category, default)
    
    def get_garmin_symbol(self, category: str) -> str:
        """Get Garmin symbol for a category."""
        return self.symbols.get(category, "Flag, Blue")
    
    def get_category_list(self) -> List[str]:
        """Get list of all category names."""
        return list(self.categories.keys())
