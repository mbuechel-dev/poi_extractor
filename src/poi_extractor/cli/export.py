"""Export subcommand implementation."""

import sys
from pathlib import Path

from ..core import Config
from ..exporters import GarminExporter


def run_export(args):
    """
    Run the POI export to Garmin GPX format.
    
    Args:
        args: Parsed command-line arguments
    """
    print("=" * 60)
    print("Garmin GPX Exporter")
    print("=" * 60)
    print(f"\nInput CSV: {args.csv}")
    
    # Validate CSV file exists
    if not Path(args.csv).exists():
        print(f"\n❌ Error: CSV file not found: {args.csv}")
        print("\nRun extraction first:")
        print("  poi-extractor extract --gpx <route.gpx>")
        sys.exit(1)
    
    # Load configuration for symbol mappings
    config = None
    if args.config:
        print(f"Config: {args.config}")
        if not Path(args.config).exists():
            print(f"\n❌ Error: Config file not found: {args.config}")
            sys.exit(1)
        try:
            config = Config(args.config)
        except Exception as e:
            print(f"\n❌ Error loading config: {e}")
            sys.exit(1)
    else:
        config = Config()  # Use defaults
    
    # Create exporter
    exporter = GarminExporter(args.csv, config=config)
    
    try:
        # Load POIs
        exporter.load_pois()
        
        # Print statistics
        exporter.print_statistics()
        
        # Export
        use_snapped = not args.no_snap
        
        if args.split:
            print(f"\nOutput directory: {args.output_dir}")
            print(f"Mode: Split by category")
            exporter.export_by_category(args.output_dir, use_snapped=use_snapped)
        else:
            print(f"\nOutput file: {args.output}")
            if args.categories:
                print(f"Categories filter: {', '.join(args.categories)}")
            print(f"Mode: Single file")
            exporter.export_gpx(
                args.output,
                use_snapped=use_snapped,
                categories=args.categories
            )
        
        print("\n" + "=" * 60)
        print("✅ EXPORT COMPLETE!")
        print("=" * 60)
        
        print("\nTo load onto Garmin device:")
        print("  Method 1 (Simple):")
        print("    Copy GPX files to your device's /Garmin/NewFiles/ folder")
        print("  Method 2 (Advanced):")
        print("    Use Garmin POI Loader to convert to .gpi format")
        print("    and place in /Garmin/POI/ folder")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Export interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error during export: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
