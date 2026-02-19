"""
Export POIs to Garmin-ready GPX format
Creates waypoint files that can be loaded onto Garmin devices
"""

import pandas as pd
import gpxpy.gpx
from pathlib import Path
from datetime import datetime


# Category icons/symbols for Garmin
CATEGORY_SYMBOLS = {
    "water": "Water Source",
    "food": "Restaurant",
    "hotels": "Lodging",
    "supermarket": "Shopping",
    "pharmacy": "Pharmacy",
    "fuel": "Gas Station",
}


class GarminExporter:
    def __init__(self, csv_file):
        """
        Initialize Garmin Exporter
        
        Args:
            csv_file: Path to CSV file with POI data
        """
        self.csv_file = Path(csv_file)
        self.pois = None
        
    def load_pois(self):
        """Load POIs from CSV"""
        print(f"Loading POIs from {self.csv_file}...")
        self.pois = pd.read_csv(self.csv_file)
        print(f"✓ Loaded {len(self.pois)} POIs")
        return self.pois
    
    def export_gpx(self, output_file, use_snapped=True, categories=None):
        """
        Export POIs to GPX format
        
        Args:
            output_file: Output GPX file path
            use_snapped: Use snapped coordinates if available (default: True)
            categories: List of categories to include (default: all)
        """
        print(f"\nExporting to GPX: {output_file}")
        
        # Filter by categories if specified
        df = self.pois.copy()
        if categories:
            df = df[df["category"].isin(categories)]
            print(f"Filtering to categories: {categories}")
        
        # Create GPX object
        gpx = gpxpy.gpx.GPX()
        gpx.name = "AMR POIs"
        gpx.description = f"Points of Interest along route - Generated {datetime.now().strftime('%Y-%m-%d')}"
        
        # Add waypoints
        for _, row in df.iterrows():
            # Choose coordinates
            if use_snapped and "snapped_lat" in df.columns and pd.notna(row.get("snapped_lat")):
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
            
            # Add symbol/type for Garmin
            if category in CATEGORY_SYMBOLS:
                wpt.symbol = CATEGORY_SYMBOLS[category]
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
        
        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(gpx.to_xml())
        
        print(f"✓ Exported {len(gpx.waypoints)} waypoints to {output_file}")
        return output_file
    
    def export_by_category(self, output_dir, use_snapped=True):
        """
        Export separate GPX files for each category
        
        Args:
            output_dir: Output directory for GPX files
            use_snapped: Use snapped coordinates if available
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        print(f"\nExporting separate files by category to {output_dir}")
        
        categories = self.pois["category"].unique()
        files = []
        
        for category in categories:
            output_file = output_dir / f"amr-poi-{category}.gpx"
            self.export_gpx(output_file, use_snapped=use_snapped, categories=[category])
            files.append(output_file)
        
        print(f"\n✓ Exported {len(files)} category files")
        return files
    
    def print_statistics(self):
        """Print statistics about POIs"""
        print("\n=== POI Statistics ===")
        print(f"Total POIs: {len(self.pois)}")
        print("\nBy Category:")
        for category, count in self.pois["category"].value_counts().items():
            print(f"  {category:15s}: {count:4d}")
        
        # Check for names
        named = self.pois["name"].notna().sum()
        print(f"\nNamed POIs: {named} ({named/len(self.pois)*100:.1f}%)")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export POIs to Garmin GPX format")
    parser.add_argument("--csv", default="data/pois_along_route.csv", help="Input CSV file")
    parser.add_argument("--output", default="data/amr-poi.gpx", help="Output GPX file")
    parser.add_argument("--split", action="store_true", help="Export separate files per category")
    parser.add_argument("--output-dir", default="data/gpx", help="Output directory for split files")
    parser.add_argument("--no-snap", action="store_true", help="Use original coordinates instead of snapped")
    parser.add_argument("--categories", nargs="+", help="Only export specific categories")
    
    args = parser.parse_args()
    
    # Create exporter
    exporter = GarminExporter(args.csv)
    exporter.load_pois()
    exporter.print_statistics()
    
    # Export
    use_snapped = not args.no_snap
    
    if args.split:
        exporter.export_by_category(args.output_dir, use_snapped=use_snapped)
    else:
        exporter.export_gpx(args.output, use_snapped=use_snapped, categories=args.categories)
    
    print("\n=== Export Complete! ===")
    print("\nTo load onto Garmin:")
    print("  Option 1 (Simple): Copy GPX files to /Garmin/NewFiles/")
    print("  Option 2 (Better): Use Garmin POI Loader to convert to .gpi")
    print("              and place in /Garmin/POI/")


if __name__ == "__main__":
    main()
