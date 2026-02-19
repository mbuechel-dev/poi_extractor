# POI Extractor

Extract Points of Interest (POIs) along GPX routes from OpenStreetMap data, optimized for Garmin devices.

Perfect for ultra-endurance races (like Atlas Mountain Race), bikepacking routes, and multi-day tours.

## 🎯 What This Does

1. **Extracts POIs** from OpenStreetMap (hotels, water, food, supermarkets, etc.)
2. **Filters POIs** within a configurable corridor along your GPX route
3. **Snaps POIs** to the nearest road using OSRM (optional, makes Garmin navigation smoother)
4. **Exports** Garmin-ready GPX files with waypoints

## 📋 Prerequisites

- **Python 3.8+** - For POI extraction
- **Docker** (optional) - For OSRM road snapping
- **Your GPX route file** - Place it in the `data/` folder

## 🚀 Quick Start

### 1. Install the Package

```powershell
# Activate your virtual environment
.\.venv\Scripts\Activate.ps1

# Install the package (basic version)
pip install -e .

# Or with optional local OSM file support (requires C++ build tools)
pip install -e .[local]
```

### 2. Extract POIs from Your Route

**Simple mode** (uses Overpass API - no setup needed):

```powershell
poi-extractor extract --gpx data/your_route.gpx --strategy simple
```

**For long routes** (splits into stages to avoid API timeouts):

```powershell
poi-extractor extract --gpx data/long_route.gpx --strategy stages --stage-km 150
```

**For offline/faster extraction** (requires local OSM file):

```powershell
# First, download OSM data (one-time setup)
.\scripts\setup_osrm.ps1

# Then extract using local file
poi-extractor extract --gpx data/route.gpx --strategy local --osm osrm/morocco-latest.osm.pbf
```

### 3. Export to Garmin GPX

```powershell
poi-extractor export --csv data/pois_along_route.csv --output data/pois.gpx
```

**Advanced options:**

```powershell
# Export separate files per category
poi-extractor export --split --output-dir data/gpx

# Export only specific categories
poi-extractor export --categories water food hotels
```

## 📖 Command Reference

### Extract Command

```powershell
poi-extractor extract [OPTIONS]
```

**Required:**
- `--gpx PATH` - Input GPX route file

**Strategy Options:**
- `--strategy {simple|stages|local}` - Extraction method (default: simple)
  - `simple` - Uses Overpass API, good for short routes
  - `stages` - Splits long routes into stages, avoids API timeouts
  - `local` - Uses local OSM file, fastest for repeated runs

**Common Options:**
- `--buffer METERS` - Buffer distance around route (default: 1000)
- `--output PATH` - Output CSV file (default: data/pois_along_route.csv)
- `--config PATH` - Custom config.ini file for POI categories
- `--no-snap` - Skip OSRM road snapping
- `--osrm-url URL` - OSRM server URL (default: http://localhost:5000)

**Strategy-Specific:**
- `--stage-km KM` - Stage length for 'stages' strategy (default: 150)
- `--osm PATH` - OSM PBF file for 'local' strategy

### Export Command

```powershell
poi-extractor export [OPTIONS]
```

**Options:**
- `--csv PATH` - Input CSV file (default: data/pois_along_route.csv)
- `--output PATH` - Output GPX file (default: data/pois.gpx)
- `--split` - Export separate files per category
- `--output-dir PATH` - Directory for split files (default: data/gpx)
- `--categories CAT [CAT ...]` - Only export specific categories
- `--no-snap` - Use original coordinates instead of snapped
- `--config PATH` - Custom config.ini for symbol mappings

## 🔧 Optional: OSRM Setup for Road Snapping

Road snapping improves Garmin navigation but is optional.

### 1. Check Docker Installation

```powershell
docker --version
```

If not installed, download from [docker.com](https://www.docker.com/products/docker-desktop/)

### 2. Set Up OSRM (one-time)

```powershell
.\scripts\setup_osrm.ps1
```

⏱️ Takes 15-30 minutes. Downloads Morocco OSM data (~500MB) and prepares routing.

### 3. Start OSRM Server

```powershell
.\scripts\start_osrm.ps1
```

Leave running while extracting POIs. Server runs at `http://localhost:5000`

## 📱 Loading onto Garmin

### Option A: Simple Waypoints

1. Connect your Garmin device to computer
2. Copy `data/amr-poi.gpx` to `/Garmin/NewFiles/`
3. Safely eject device
4. POIs appear as waypoints

### Option B: Proper POI Database (Recommended)

1. Download [Garmin POI Loader](https://www8.garmin.com/support/download_details.jsp?id=927)
2. Convert GPX files to `.gpi` format
3. Copy `.gpi` files to `/Garmin/POI/`
4. Get custom icons, proximity alerts, and better organization

## 🗂️ Project Structure

```
poi_extractor/
├── src/
│   └── poi_extractor/           # Main package
│       ├── core/                # Shared utilities
│       ├── extractors/          # Extraction strategies
│       ├── exporters/           # Output formatters
│       └── cli/                 # Command-line interface
├── data/                        # Your GPX files and output
│   ├── your_route.gpx          # (add your route here)
│   ├── pois_along_route.csv
│   └── pois.gpx
├── osrm/                        # OSRM data (optional, auto-created)
│   └── morocco-latest.osm.pbf
├── scripts/                     # PowerShell utility scripts
│   ├── setup_osrm.ps1
│   ├── start_osrm.ps1
│   └── test_osrm.ps1
├── config.ini                   # POI category configuration
├── pyproject.toml              # Package metadata
└── README.md
```

## ⚙️ Configuration

Customize POI categories by editing `config.ini`:

```ini
[water]
amenity = drinking_water, fountain, water_point
man_made = water_well, water_tap

[food]
amenity = restaurant, cafe, fast_food, bar, pub
shop = bakery

[hotels]
tourism = hotel, guest_house, hostel, motel, apartment

# Add your own categories!
[bike_shop]
shop = bicycle, sports

[buffer_distances]
water = 500
food = 1000
hotels = 2000

[garmin_symbols]
water = Water Source
food = Restaurant
hotels = Lodging
```

Use custom config with:

```powershell
poi-extractor extract --config my_config.ini --gpx route.gpx
poi-extractor export --config my_config.ini --csv pois.csv
```

## �️ Road Safety Analysis

**NEW FEATURE**: Analyze roads along your race route to identify potentially unsafe sections for cyclists.

Perfect for race organizers planning ultra-endurance events who need to:
- Identify high-speed roads without cycling infrastructure
- Find motorways and dangerous highway sections
- Detect roads with heavy traffic or poor surfaces
- Export results for route modification or safety briefings

### Quick Safety Analysis

```powershell
# Analyze roads within 100km of your route
poi-extractor analyze-safety --gpx data/race_route.gpx

# Output: output/unsafe_roads.gpx (import to GPX Studio for visualization)
```

### How It Works

1. **Auto-downloads** OSM data based on route location (via Geofabrik)
2. **Extracts** all roads within specified buffer (default: 100km)
3. **Scores** each road segment based on safety criteria (0-10 scale)
4. **Filters** roads above risk threshold (default: 7.0/10)
5. **Exports** unsafe segments as colored GPX tracks for visualization

### Safety Criteria

Roads are scored based on:

| Factor | Weight | Details |
|--------|--------|---------|
| **Speed Limit** | 0-4 points | ≥100 km/h = very high risk |
| **Highway Type** | 0-5 points | Motorways, trunk roads = dangerous |
| **No Bike Infrastructure** | 0-2.5 points | Missing cycleway & shoulder |
| **Multiple Lanes** | 0-2 points | 4+ lanes = heavy traffic |
| **Poor Surface** | 0-1.5 points | Unpaved, gravel, cobblestone |
| **Good Infrastructure** | -2 points | Protected cycleways = bonus |

**Risk Levels:**
- 🔴 **Critical** (9-10): Forbidden for cycling, extremely dangerous
- 🟠 **High** (7-9): Requires attention, plan alternatives
- 🟡 **Moderate** (5-7): Monitor, add safety warnings

### Advanced Options

```powershell
# Customize buffer distance and risk threshold
poi-extractor analyze-safety \
  --gpx race_route.gpx \
  --buffer-km 50 \
  --min-risk-score 6.0 \
  --output-gpx data/dangerous_roads.gpx

# Export as GeoJSON for web visualization
poi-extractor analyze-safety \
  --gpx race_route.gpx \
  --output-geojson data/unsafe_roads.geojson

# Use custom safety criteria
poi-extractor analyze-safety \
  --gpx race_route.gpx \
  --criteria-config my_safety_criteria.yaml

# Use manually downloaded OSM file (no auto-download)
poi-extractor analyze-safety \
  --gpx race_route.gpx \
  --osm-file morocco-latest.osm.pbf \
  --no-auto-download
```

### Safety Analysis Command Reference

```powershell
poi-extractor analyze-safety [OPTIONS]
```

**Required:**
- `--gpx PATH` - Input GPX route file

**Buffer & Filtering:**
- `--buffer-km KM` - Buffer distance around route (default: 100)
- `--min-risk-score SCORE` - Minimum risk score 0-10 (default: 7.0)

**Output:**
- `--output-gpx PATH` - GPX file with unsafe roads (default: output/unsafe_roads.gpx)
- `--output-geojson PATH` - GeoJSON file for web viewers

**Configuration:**
- `--criteria-config PATH` - Safety criteria YAML (default: config/safety_criteria.yaml)
- `--osm-cache-dir PATH` - OSM cache directory (default: data/osm_cache)

**Data Source:**
- `--no-auto-download` - Disable automatic OSM download
- `--osm-file PATH` - Use specific OSM PBF file

### Visualizing Results

**Option 1: GPX Studio** (Recommended)
1. Go to [gpxstudio.github.io](https://gpxstudio.github.io)
2. Import your race route GPX
3. Import the `unsafe_roads.gpx` file
4. Roads are color-coded by risk level
5. Click segments to see risk factors

**Option 2: GeoJSON Viewers**
1. Export with `--output-geojson`
2. View on [geojson.io](http://geojson.io)
3. Or use QGIS for detailed analysis
4. Properties include: risk score, factors, road metrics

### Customizing Safety Criteria

Edit `config/safety_criteria.yaml` to adjust scoring:

```yaml
risk_thresholds:
  critical: 9.0
  high: 7.0
  moderate: 5.0

speed_limits:  # km/h
  very_high: 100
  high: 80
  moderate: 60
  low: 50

scoring:
  speed_penalty:
    very_high: 4.0
    high: 3.0
    moderate: 2.0
    low: 1.0
  
  highway_types:
    motorway: 5.0
    trunk: 4.0
    primary: 2.0
    secondary: 1.0
    tertiary: 0.5
```

### Requirements

Safety analysis requires optional dependencies:

```powershell
pip install -e .[local]
```

This installs:
- `geopandas` - Geospatial operations
- `shapely` - Geometry processing
- `osmium` - Reliable OSM file parsing

**Note**: osmium compiles successfully on all platforms including Windows and WSL.

### Race Organizer Workflow

1. **Extract race route** from planning tool
2. **Run safety analysis** with default settings
3. **Review critical segments** (9-10 score) on map
4. **Plan alternatives** or add marshals to dangerous sections
5. **Generate rider briefing** with high-risk areas marked
6. **Export filtered results** for specific risk levels

Example for race briefing (critical roads only):

```powershell
poi-extractor analyze-safety \
  --gpx amr_2026.gpx \
  --min-risk-score 9.0 \
  --output-gpx amr_critical_roads.gpx
```

## �🔥 Advanced Usage

### Using as a Python Library

```python
from poi_extractor import SimpleExtractor, GarminExporter, Config

# Load custom config
config = Config("my_config.ini")

# Extract POIs
extractor = SimpleExtractor(config=config)
pois = extractor.extract(
    gpx_file="data/route.gpx",
    buffer_meters=1500,
    use_osrm=True
)
extractor.save_to_csv("data/pois.csv")

# Export to Garmin
exporter = GarminExporter("data/pois.csv", config=config)
exporter.load_pois()
exporter.export_gpx("data/pois.gpx")
```

### Different Buffer Distances per Category

Edit `config.ini` to set per-category buffer distances:

```ini
[buffer_distances]
water = 500      # Critical - check every 500m
food = 1000      # Important - 1km is fine
hotels = 2000    # Can plan ahead - 2km OK
```

### Programmatic Usage

```python
# Get extractor by strategy
from poi_extractor import get_extractor

ExtractorClass = get_extractor("stages")
extractor = ExtractorClass()
pois = extractor.extract(gpx_file="route.gpx", stage_km=100)
```

## 🔄 Migrating from Old Scripts

If you were using the old standalone scripts:

| Old Command | New Command |
|-------------|-------------|
| `python extract_pois_simple.py --gpx route.gpx` | `poi-extractor extract --strategy simple --gpx route.gpx` |
| `python extract_pois_by_stages.py --gpx route.gpx` | `poi-extractor extract --strategy stages --gpx route.gpx` |
| `python extract_pois.py --gpx route.gpx` | `poi-extractor extract --strategy local --gpx route.gpx` |
| `python export_to_garmin.py` | `poi-extractor export` |

The old scripts are still available but deprecated.

## 🛠️ Troubleshooting

### Installation Issues

**Error: "No module named 'poi_extractor'"**
- Make sure you installed the package: `pip install -e .`
- Activate your virtual environment

**Error: "geopandas not found" when using --strategy local**
- Install optional dependencies: `pip install -e .[local]`
- Alternatively, use `--strategy simple` or `--strategy stages` instead

**Error: "Microsoft Visual C++ required"**
- The `local` strategy requires C++ build tools
- Install from [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/)
- Or use `--strategy simple` which has no build requirements

### Docker/OSRM Issues

**Error: "docker: command not found"**
- Install Docker Desktop for Windows
- Restart terminal after installation
- OSRM is optional - use `--no-snap` to skip road snapping

**Error: "Connection refused to localhost:5000"**
- Make sure OSRM server is running: `.\scripts\start_osrm.ps1`
- Or use `--no-snap` flag to skip OSRM snapping
- Check firewall settings

### Extraction Issues

**Extraction very slow**
- Use `--no-snap` flag to skip OSRM snapping (faster)
- For long routes, use `--strategy stages`
- Reduce buffer distance: `--buffer 500`

**"Overpass API timeout"**
- Use `--strategy stages` for long routes
- Or use `--strategy local` with downloaded OSM file

**No POIs found**
- Check your GPX file has valid track or waypoints
- Increase buffer distance: `--buffer 2000`
- Verify POI categories exist in your area on openstreetmap.org

## 📊 Output Examples

### CSV Output (`pois_along_route.csv`)

```csv
category,name,lon,lat,snapped_lon,snapped_lat
water,Fountain,-7.589,31.623,-7.589,31.624
food,Cafe Argana,-7.992,31.631,-7.992,31.631
hotels,Riad Dar Sara,-7.628,31.635,-7.628,31.636
```

### GPX Output

Compatible with:
- Garmin Edge (830, 1030, 1040)
- Garmin Fenix (6, 7)
- Garmin GPSMAP
- Any device supporting GPX waypoints

## 🎯 Self-Supported Race Tips

### Priority POIs for AMR

1. **Water** 💧 - Most critical, 500m buffer
2. **Food/Shops** 🍽️ - Plan resupply points, 1km buffer
3. **Hotels/Guesthouses** 🏠 - Auberges in Morocco are gold
4. **Pharmacies** 💊 - For emergencies

### OSM Data Quality for Morocco

- ✅ Water fountains: Generally good
- ✅ Towns/villages: Excellent coverage
- ⚠️ Remote fountains: Double-check key ones
- ⚠️ Opening hours: Often missing, call ahead

### Recommended Workflow

1. Extract all POIs with 1km buffer
2. Export separate files per category
3. Load only critical categories on device (save memory)
4. Keep full CSV for planning/backup

## 📚 Resources

- [OSRM Documentation](http://project-osrm.org/)
- [Garmin POI Loader](https://www8.garmin.com/support/download_details.jsp?id=927)
- [Geofabrik Downloads](https://download.geofabrik.de/) - OSM data
- [OpenStreetMap Wiki](https://wiki.openstreetmap.org/) - Tag documentation

## 🤝 Contributing

This is a personal project for AMR, but feel free to adapt it for:
- Other ultra-endurance races
- Bikepacking routes
- Multi-day tours
- Any GPX-based navigation

## ⚡ Performance Tips

- **Simple strategy**: No setup, but slower for repeated runs. Good for one-off extractions.
- **Stages strategy**: Best for very long routes (>500km). Avoids API timeouts.
- **Local strategy**: Fastest for repeated runs with same geographic area. Requires setup.
- Use `--no-snap` to skip road snapping (faster, but less accurate for Garmin)
- Limit buffer distance to reasonable corridor (500-2000m)
- Use SSD for OSRM data processing
- First run with local strategy is slow (OSM parsing), subsequent runs are fast

## 📦 Package Installation Options

```powershell
# Lightweight installation (Overpass API only)
pip install -e .

# Full installation (includes local OSM file support)
pip install -e .[local]

# Development installation (includes testing tools)
pip install -e .[dev]

# Everything
pip install -e .[all]
```

---

**Happy racing! 🚴‍♂️🏔️**

Questions or issues? The scripts have detailed error messages and suggestions.
