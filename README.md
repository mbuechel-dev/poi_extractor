# AMR POI Extraction Tool

Extract Points of Interest (POIs) along your Atlas Mountain Race (or any GPX route) from OpenStreetMap data, optimized for Garmin devices.

## 🎯 What This Does

1. **Sets up OSRM** (Open Source Routing Machine) locally with Morocco road data
2. **Extracts POIs** from OpenStreetMap (hotels, water, food, supermarkets, etc.)
3. **Filters POIs** within a configurable corridor along your GPX route
4. **Snaps POIs** to the nearest road using OSRM (so Garmin doesn't think they're off-road)
5. **Exports** Garmin-ready GPX files with waypoints

## 📋 Prerequisites

- **Docker** - For running OSRM
- **Python 3.8+** - For POI extraction scripts
- **~8GB disk space** - For Morocco OSM data and OSRM processing
- **Your GPX route file** - Place it in the `data/` folder

## 🚀 Quick Start

### 1. Check Docker Installation

```powershell
docker --version
```

If Docker is not installed, download from [docker.com](https://www.docker.com/products/docker-desktop/)

### 2. Set Up OSRM

This downloads Morocco OSM data (~500MB) and prepares it for routing:

```powershell
.\scripts\setup_osrm.ps1
```

⏱️ This takes **15-30 minutes** depending on your machine.

### 3. Start OSRM Server

```powershell
.\scripts\start_osrm.ps1
```

Leave this running in a terminal. The server runs at `http://localhost:5000`

Test it in another terminal:

```powershell
.\scripts\test_osrm.ps1
```

### 4. Install Python Dependencies

```powershell
# Activate your virtual environment (already set up)
.\.venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

⏱️ This takes **5-10 minutes**. GEOS and other geospatial libraries take time to compile.

### 5. Extract POIs from Your Route

Place your GPX file in `data/` folder (e.g., `data/amr_route.gpx`), then:

```powershell
python extract_pois.py --gpx data/amr_route.gpx
```

**Options:**
- `--buffer 2000` - Change corridor width (default: 1000m)
- `--osm osrm/morocco-latest.osm.pbf` - OSM file path
- `--output data/pois.csv` - Output CSV file
- `--no-snap` - Skip OSRM snapping (faster but less accurate)

⏱️ Takes **10-20 minutes** for full Morocco scan.

### 6. Export to Garmin GPX

```powershell
python export_to_garmin.py
```

**Options:**
- `--csv data/pois_along_route.csv` - Input CSV
- `--output data/amr-poi.gpx` - Output GPX file
- `--split` - Export separate files per category
- `--categories water food` - Only export specific categories
- `--no-snap` - Use original coordinates

This creates `data/amr-poi.gpx` ready for your Garmin!

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
hello_world/
├── data/               # Your GPX files and output
│   ├── amr_route.gpx  # (your route - add this)
│   ├── pois_along_route.csv
│   └── amr-poi.gpx
├── osrm/              # OSRM data (auto-created)
│   └── morocco-latest.osm.pbf
├── scripts/           # Utility scripts
│   ├── setup_osrm.ps1
│   ├── start_osrm.ps1
│   └── test_osrm.ps1
├── extract_pois.py    # Main POI extraction
├── export_to_garmin.py # GPX export
└── requirements.txt   # Python dependencies
```

## ⚙️ Configuration

Edit `extract_pois.py` to customize POI categories:

```python
POI_FILTERS = {
    "hotels": {"tourism": ["hotel", "guest_house", "hostel"]},
    "food": {"amenity": ["restaurant", "cafe", "fast_food"]},
    "water": {"amenity": ["drinking_water", "fountain"]},
    "supermarket": {"shop": ["supermarket", "convenience"]},
    # Add your own:
    "pharmacy": {"amenity": ["pharmacy"]},
    "fuel": {"amenity": ["fuel"]},
    "bike_shop": {"shop": ["bicycle"]},
}
```

## 🔥 Advanced Usage

### Different Buffer Distances per Category

Edit the code to filter each category with different buffers:

```python
# Water every 500m, hotels every 2km
water_pois = extractor.filter_pois_along_route(buffer=500, categories=["water"])
hotel_pois = extractor.filter_pois_along_route(buffer=2000, categories=["hotels"])
```

### Split by Race Stages

If you have stage GPX files:

```powershell
python extract_pois.py --gpx data/stage1.gpx --output data/stage1_pois.csv
python extract_pois.py --gpx data/stage2.gpx --output data/stage2_pois.csv
```

### Calculate Distance from Start

Add route distance calculations to know "km 412: supermarket":

```python
# In extract_pois.py, add:
from shapely.ops import nearest_points

for poi in pois_along_route:
    nearest = nearest_points(poi.geometry, route_line)[1]
    poi['distance_from_start'] = route_line.project(nearest)
```

## 🛠️ Troubleshooting

### Docker Issues

**Error: "docker: command not found"**
- Install Docker Desktop for Windows
- Restart terminal after installation

**Error: "Cannot connect to Docker daemon"**
- Make sure Docker Desktop is running
- Check Docker Desktop settings → Resources → WSL Integration (if using WSL)

### OSRM Issues

**Error: "Connection refused to localhost:5000"**
- Make sure OSRM server is running: `.\scripts\start_osrm.ps1`
- Check firewall settings

**Server crashes or slow**
- OSRM needs ~4GB RAM for Morocco data
- Close other applications

### Python Issues

**Error: "No module named 'geopandas'"**
- Make sure virtual environment is activated
- Run: `pip install -r requirements.txt`

**Error: "GEOS library not found"**
- Install via conda: `conda install -c conda-forge geopandas`

**Extraction very slow**
- Use `--no-snap` flag to skip OSRM snapping
- Reduce buffer distance with `--buffer 500`

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

- First run is slow (OSM parsing), subsequent runs with same area are faster
- Use SSD for OSRM data processing
- Limit buffer distance to reasonable corridor
- Split large routes into stages

---

**Happy racing! 🚴‍♂️🏔️**

Questions or issues? The scripts have detailed error messages and suggestions.
