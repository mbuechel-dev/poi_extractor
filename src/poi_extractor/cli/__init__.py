"""Command-line interface for POI Extractor."""

import sys
import argparse


def main():
    """Main CLI entry point with subcommands."""
    parser = argparse.ArgumentParser(
        prog="poi-extractor",
        description="Extract POIs along routes and export to Garmin"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Extract subcommand
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract POIs from route"
    )
    extract_parser.add_argument(
        "--gpx",
        required=True,
        help="Input GPX route file"
    )
    extract_parser.add_argument(
        "--strategy",
        choices=["simple", "stages", "local"],
        default="simple",
        help="Extraction strategy: simple (Overpass API), stages (long routes), "
             "local (requires local OSM file and optional dependencies)"
    )
    extract_parser.add_argument(
        "--buffer",
        type=int,
        default=1000,
        help="Buffer distance in meters around route (default: 1000)"
    )
    extract_parser.add_argument(
        "--output",
        default="data/pois_along_route.csv",
        help="Output CSV file (default: data/pois_along_route.csv)"
    )
    extract_parser.add_argument(
        "--config",
        help="Path to config.ini file (default: use built-in categories)"
    )
    extract_parser.add_argument(
        "--no-snap",
        action="store_true",
        help="Skip OSRM road snapping"
    )
    extract_parser.add_argument(
        "--osrm-url",
        default="http://localhost:5000",
        help="OSRM server URL (default: http://localhost:5000)"
    )
    # Stage-specific option
    extract_parser.add_argument(
        "--stage-km",
        type=int,
        default=150,
        help="Stage length in km for 'stages' strategy (default: 150)"
    )
    # Local-specific option
    extract_parser.add_argument(
        "--osm",
        default="osrm/morocco-latest.osm.pbf",
        help="Local OSM PBF file for 'local' strategy"
    )
    
    # Export subcommand
    export_parser = subparsers.add_parser(
        "export",
        help="Export POIs to Garmin GPX format"
    )
    export_parser.add_argument(
        "--csv",
        default="data/pois_along_route.csv",
        help="Input CSV file with POIs (default: data/pois_along_route.csv)"
    )
    export_parser.add_argument(
        "--output",
        default="data/pois.gpx",
        help="Output GPX file (default: data/pois.gpx)"
    )
    export_parser.add_argument(
        "--split",
        action="store_true",
        help="Export separate files per category"
    )
    export_parser.add_argument(
        "--output-dir",
        default="data/gpx",
        help="Output directory for split files (default: data/gpx)"
    )
    export_parser.add_argument(
        "--no-snap",
        action="store_true",
        help="Use original coordinates instead of snapped"
    )
    export_parser.add_argument(
        "--categories",
        nargs="+",
        help="Only export specific categories"
    )
    export_parser.add_argument(
        "--config",
        help="Path to config.ini file for symbol mappings"
    )
    
    # Analyze-safety subcommand
    safety_parser = subparsers.add_parser(
        "analyze-safety",
        help="Analyze road safety along route"
    )
    safety_parser.add_argument(
        "--gpx",
        dest="gpx_file",
        required=True,
        help="Input GPX route file"
    )
    safety_parser.add_argument(
        "--buffer-km",
        type=float,
        default=100.0,
        help="Buffer distance in kilometers around route (default: 100)"
    )
    safety_parser.add_argument(
        "--min-risk-score",
        type=float,
        default=7.0,
        help="Minimum risk score to include (0-10, default: 7.0)"
    )
    safety_parser.add_argument(
        "--output-gpx",
        help="Output GPX file with unsafe roads (default: output/unsafe_roads.gpx)"
    )
    safety_parser.add_argument(
        "--output-geojson",
        help="Output GeoJSON file with unsafe roads"
    )
    safety_parser.add_argument(
        "--criteria-config",
        default="config/safety_criteria.yaml",
        help="Path to safety criteria config (default: config/safety_criteria.yaml)"
    )
    safety_parser.add_argument(
        "--osm-cache-dir",
        default="data/osm_cache",
        help="Directory for OSM file cache (default: data/osm_cache)"
    )
    safety_parser.add_argument(
        "--no-auto-download",
        dest="auto_download",
        action="store_false",
        help="Disable automatic OSM data download"
    )
    safety_parser.add_argument(
        "--osm-file",
        help="Use specific OSM PBF file instead of auto-download"
    )
    safety_parser.add_argument(
        "--no-route",
        dest="include_route",
        action="store_false",
        help="Do not include original route in output GPX (only show dangerous roads)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route to appropriate subcommand
    if args.command == "extract":
        from .extract import run_extract
        run_extract(args)
    elif args.command == "export":
        from .export import run_export
        run_export(args)
    elif args.command == "analyze-safety":
        from .safety import run_safety_analysis
        sys.exit(run_safety_analysis(args))


if __name__ == "__main__":
    main()
