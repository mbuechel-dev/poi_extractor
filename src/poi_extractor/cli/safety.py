"""CLI command for road safety analysis."""

import sys
from pathlib import Path

from ..safety.analyzer import RoadSafetyAnalyzer
from ..safety.criteria import SafetyCriteria


def run_safety_analysis(args):
    """Execute road safety analysis command."""
    try:
        # Load safety criteria
        criteria = SafetyCriteria.from_yaml(args.criteria_config)
        
        # Initialize analyzer
        analyzer = RoadSafetyAnalyzer(
            criteria=criteria,
            osm_cache_dir=args.osm_cache_dir,
            osm_data_path=args.osm_file if hasattr(args, 'osm_file') else None
        )
        
        print("=" * 70)
        print("🚴 ROAD SAFETY ANALYSIS")
        print("=" * 70)
        print(f"Route: {args.gpx_file}")
        print(f"Buffer: {args.buffer_km} km")
        print(f"Minimum risk score: {args.min_risk_score}/10")
        print(f"Auto-download OSM: {args.auto_download}")
        
        # Run analysis
        unsafe_roads = analyzer.analyze_route(
            gpx_path=args.gpx_file,
            buffer_km=args.buffer_km,
            min_risk_score=args.min_risk_score,
            auto_download=args.auto_download
        )
        
        if len(unsafe_roads) == 0:
            print("\n✓ No unsafe roads found! This route looks safe.")
            return 0
        
        # Calculate statistics
        total_length = sum(road.length_km() for road in unsafe_roads)
        avg_risk = sum(road.risk_score for road in unsafe_roads) / len(unsafe_roads)
        
        # Count by risk level
        critical = sum(1 for r in unsafe_roads if r.risk_level == 'critical')
        high = sum(1 for r in unsafe_roads if r.risk_level == 'high')
        moderate = sum(1 for r in unsafe_roads if r.risk_level == 'moderate')
        
        print("\n" + "=" * 70)
        print("📊 ANALYSIS RESULTS")
        print("=" * 70)
        print(f"Unsafe roads found: {len(unsafe_roads)}")
        print(f"Total length: {total_length:.1f} km")
        print(f"Average risk score: {avg_risk:.1f}/10")
        print(f"\nRisk level breakdown:")
        print(f"  🔴 Critical (9-10): {critical} segments")
        print(f"  🟠 High (7-9): {high} segments")
        print(f"  🟡 Moderate (5-7): {moderate} segments")
        
        # Determine if route should be included in export
        include_route = args.include_route if hasattr(args, 'include_route') else True
        
        # Export results
        if args.output_gpx:
            analyzer.export_to_gpx(
                unsafe_roads, 
                args.output_gpx,
                include_route=include_route
            )
        
        if args.output_geojson:
            analyzer.export_to_geojson(
                unsafe_roads, 
                args.output_geojson,
                include_route=include_route
            )
        
        if not args.output_gpx and not args.output_geojson:
            # Default output
            default_gpx = "output/unsafe_roads.gpx"
            analyzer.export_to_gpx(
                unsafe_roads, 
                default_gpx,
                include_route=include_route
            )
        
        print("\n" + "=" * 70)
        print("💡 NEXT STEPS")
        print("=" * 70)
        print("1. Import the GPX file to GPX Studio (gpxstudio.github.io)")
        print("2. Review each unsafe road segment on the map")
        print("3. Consider alternative routes or add safety warnings")
        print("4. For GeoJSON: Use geojson.io or QGIS for analysis")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: File not found: {e}", file=sys.stderr)
        return 1
    except ImportError as e:
        print(f"\n❌ Error: Missing dependencies: {e}", file=sys.stderr)
        print("\nTo use safety analysis, install optional dependencies:")
        print("  pip install poi-extractor[local]")
        return 1
    except Exception as e:
        print(f"\n❌ Error during safety analysis: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
