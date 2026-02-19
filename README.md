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

## 🔥 Advanced Usage

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
