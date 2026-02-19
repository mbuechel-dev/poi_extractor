"""Garmin GPX exporter for POIs."""

import pandas as pd
import gpxpy.gpx
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from ..core import Config


class GarminExporter:
    """Export POIs to Garmin-compatible GPX format."""
    
    def __init__(self, csv_file: str, config: Optional[Config] = None):
        """
        Initialize Garmin Exporter.
        
        Args:
            csv_file: Path to CSV file with POI data
            config: Configuration object for symbol mappings (uses defaults if None)
        """
        self.csv_file = Path(csv_file)
        self.config = config or Config()
        self.pois = None
    
    def load_pois(self) -> pd.DataFrame:
        """
        Load POIs from CSV file.
        
        Returns:
            DataFrame of POIs
        """
        print(f"Loading POIs from {self.csv_file}...")
        self.pois = pd.read_csv(self.csv_file)
        print(f"✓ Loaded {len(self.pois)} POIs")
        return self.pois
    
    def export_gpx(self, output_file: str, use_snapped: bool = True,
                   categories: Optional[List[str]] = None) -> str:
        """
        Export POIs to GPX format.
        
        Args:
            output_file: Output GPX file path
            use_snapped: Use snapped coordinates if available (default: True)
            categories: List of categories to include (default: all)
            
        Returns:
            Path to output file
        """
        print(f"\nExporting to GPX: {output_file}")
        
        # Filter by categories if specified
        df = self.pois.copy()
        if categories:
            df = df[df["category"].isin(categories)]
            print(f"Filtering to categories: {categories}")
        
        # Create GPX object
        gpx = gpxpy.gpx.GPX()
        gpx.name = "POI Waypoints"
        gpx.description = (
            f"Points of Interest along route - "
            f"Generated {datetime.now().strftime('%Y-%m-%d')}"
        )
        
        # Add waypoints
        for _, row in df.iterrows():
            # Choose coordinates
            if (use_snapped and "snapped_lat" in df.columns and 
                pd.notna(row.get("snapped_lat"))):
                lat = row["snapped_lat"]
                lon = row["snapped_lon"]
            else:
                lat = row["lat"]
                lon = row["lon"]
            
            # Create waypoint name
            category = row["category"]
            name = row.get("name", "")
            if pd.isna(name) or name == "":
                wpt_name = category.capitalize()
            else:
                # Truncate long names for Garmin
                wpt_name = f"{category[:3].upper()} - {name[:20]}"
            
            # Create waypoint
            wpt = gpxpy.gpx.GPXWaypoint(
                latitude=lat,
                longitude=lon,
                name=wpt_name
            )
            
            # Add symbol/type for Garmin using config
            symbol = self.config.get_garmin_symbol(category)
            wpt.symbol = symbol
            wpt.type = category
            
            # Add description with additional details
            desc_parts = [f"Category: {category}"]
            if pd.notna(name) and name != "":
                desc_parts.append(f"Name: {name}")
            for col in ["amenity", "shop", "tourism", "addr:street", "addr:city"]:
                if col in df.columns and pd.notna(row.get(col)):
                    desc_parts.append(f"{col}: {row[col]}")
            wpt.description = " | ".join(desc_parts)
            
            gpx.waypoints.append(wpt)
        
        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(gpx.to_xml())
        
        print(f"✓ Exported {len(gpx.waypoints)} waypoints to {output_file}")
        return str(output_file)
    
    def export_by_category(self, output_dir: str, 
                          use_snapped: bool = True) -> List[str]:
        """
        Export separate GPX files for each category.
        
        Args:
            output_dir: Output directory for GPX files
            use_snapped: Use snapped coordinates if available
            
        Returns:
            List of output file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nExporting separate files by category to {output_dir}")
        
        categories = self.pois["category"].unique()
        files = []
        
        for category in categories:
            output_file = output_dir / f"poi-{category}.gpx"
            self.export_gpx(
                str(output_file),
                use_snapped=use_snapped,
                categories=[category]
            )
            files.append(str(output_file))
        
        print(f"\n✓ Exported {len(files)} category files")
        return files
    
    def print_statistics(self):
        """Print statistics about POIs."""
        print("\n=== POI Statistics ===")
        print(f"Total POIs: {len(self.pois)}")
        print("\nBy Category:")
        for category, count in self.pois["category"].value_counts().items():
            print(f"  {category:15s}: {count:4d}")
        
        # Check for names
        if "name" in self.pois.columns:
            named = self.pois["name"].notna().sum()
            print(f"\nNamed POIs: {named} ({named/len(self.pois)*100:.1f}%)")
