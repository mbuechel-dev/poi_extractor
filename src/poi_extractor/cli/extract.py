"""Extract subcommand implementation."""

import sys
from pathlib import Path

from ..core import Config
from ..extractors import get_extractor


def run_extract(args):
    """
    Run the POI extraction.
    
    Args:
        args: Parsed command-line arguments
    """
    print("=" * 60)
    print("POI Extractor")
    print("=" * 60)
    print(f"\nStrategy: {args.strategy}")
    print(f"GPX file: {args.gpx}")
    print(f"Buffer: {args.buffer}m")
    print(f"Output: {args.output}")
    
    # Validate GPX file exists
    if not Path(args.gpx).exists():
        print(f"\n❌ Error: GPX file not found: {args.gpx}")
        sys.exit(1)
    
    # Load configuration
    config = None
    if args.config:
        print(f"Config: {args.config}")
        if not Path(args.config).exists():
            print(f"\n❌ Error: Config file not found: {args.config}")
            sys.exit(1)
        try:
            config = Config(args.config)
            print(f"✓ Loaded config with {len(config.get_category_list())} categories")
        except Exception as e:
            print(f"\n❌ Error loading config: {e}")
            sys.exit(1)
    else:
        config = Config()  # Use defaults
        print(f"Using default config with {len(config.get_category_list())} categories")
    
    # Get extractor class
    try:
        extractor_class = get_extractor(args.strategy)
    except ImportError as e:
        print(f"\n❌ Error: {e}")
        print("\nTo use the 'local' strategy, install optional dependencies:")
        print("  pip install poi-extractor[local]")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    
    # Create extractor instance
    extractor = extractor_class(config=config)
    
    # Prepare extraction arguments
    extract_kwargs = {
        "gpx_file": args.gpx,
        "buffer_meters": args.buffer,
        "use_osrm": not args.no_snap,
        "osrm_url": args.osrm_url,
    }
    
    # Add strategy-specific arguments
    if args.strategy == "stages":
        extract_kwargs["stage_km"] = args.stage_km
        print(f"Stage length: {args.stage_km}km")
    elif args.strategy == "local":
        extract_kwargs["osm_file"] = args.osm
        if not Path(args.osm).exists():
            print(f"\n❌ Error: OSM file not found: {args.osm}")
            print("\nFor the 'local' strategy, you need a local OSM PBF file.")
            print("Run setup script to download: .\\scripts\\setup_osrm.ps1")
            sys.exit(1)
        print(f"OSM file: {args.osm}")
    
    if args.no_snap:
        print("OSRM snapping: disabled")
    else:
        print(f"OSRM snapping: {args.osrm_url}")
    
    print("\n" + "-" * 60)
    
    # Run extraction
    try:
        pois = extractor.extract(**extract_kwargs)
        
        if not pois or (hasattr(pois, '__len__') and len(pois) == 0):
            print("\n⚠ Warning: No POIs found!")
        
        # Save to CSV
        extractor.save_to_csv(args.output)
        
        print("\n" + "=" * 60)
        print("✅ POI EXTRACTION COMPLETE!")
        print("=" * 60)
        print(f"\nResults saved to: {args.output}")
        print("\nNext step: Export to Garmin GPX format")
        print(f"  poi-extractor export --csv {args.output}")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Extraction interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
