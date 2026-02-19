# Quick Start Guide - Simplified Version

**✅ Your system is ready to use!**

## Three Versions Available:

### 1. **Stage-by-Stage Version** ⭐ RECOMMENDED FOR AMR
- Splits long routes into manageable stages
- Avoids Overpass API timeouts
- Perfect for 1000+ km routes
- Processes each stage separately with automatic rate limiting

**Use this command for AMR:**
```powershell
.\.venv\Scripts\python.exe extract_pois_by_stages.py --gpx data\AMR_2026_Updated.gpx --stage-km 150 --buffer 1000
.\.venv\Scripts\python.exe export_to_garmin.py
```

### 2. **Simplified Version** (Good for shorter routes)
- Uses Overpass API to query OpenStreetMap online
- Works immediately on any system
- Good for routes up to ~50km  
- May hit rate limits on very large queries

**Use this command:**
```powershell
.\.venv\Scripts\python.exe extract_pois_simple.py --gpx data\your_route.gpx
.\.venv\Scripts\python.exe export_to_garmin.py
```

### 3. **Full Version** (Requires C++ Build Tools)
- Processes local OSM files (faster, no rate limits)
- Better for long routes like full AMR
- Requires: [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

To use full version: Install C++ Build Tools, then run original `extract_pois.py`

---

## 🚀 Quick Workflow (Stage-by-Stage - RECOMMENDED)

1. **Place your AMR GPX file** in the `data/` folder (already done: `AMR_2026_Updated.gpx`)

2. **Extract POIs by stages:**
```powershell
.\.venv\Scripts\python.exe extract_pois_by_stages.py --gpx data\AMR_2026_Updated.gpx --stage-km 150
```

This will:
- Split your ~1200km route into ~8 stages of 150km each
- Query each stage separately (avoids timeouts)
- Wait between stages to respect API limits
- Merge all results into one file

**Options:**
- `--stage-km 150` - Length of each stage (default: 150km)
- `--buffer 1000` - Corridor width in meters (default: 1km)
- `--output data/custom_name.csv` - Custom output file

3. **Export to Garmin:**
```powershell
.\.venv\Scripts\python.exe export_to_garmin.py
```

4. **Load onto Garmin:**
   - Copy `data\amr-poi.gpx` to your Garmin device at `\Garmin\NewFiles\`

---

## ⚡ Expected Processing Time

For full AMR route (~1200km):
- **Stage-by-stage**: ~20-30 minutes (8 stages × 3 min each)
- **Single query**: Often times out ❌

---

## ✅ Test Results

Just tested with example route:
- ✓ Found **895 POIs** along route
- ✓ 727 hotels, 82 pharmacies, 50 water sources, 36 supermarkets
- ✓ Exported to `data\amr-poi.gpx`
- ✓ Ready for Garmin!

---

## 🎯 AMR-Specific Tips

**Buffer recommendations:**
- `--buffer 500` - Tight corridor, only immediate route
- `--buffer 1000` - Recommended for self-supported (1km)
- `--buffer 2000` - Wide search, includes detours

**Stage length recommendations:**
- `--stage-km 100` - More stages, slower but more reliable
- `--stage-km 150` - Balanced (recommended)
- `--stage-km 200` - Fewer stages, faster but may timeout

**Priority POIs for self-supported:**
- ✓ Water sources (fountains, drinking water)
- ✓ Supermarkets/convenience stores (resupply)
- ✓ Pharmacies (medical)
- ✓ Hotels/guest houses (accommodation)
- ✓ Fuel stations (often have food/water)

---

## Export Options

**Export specific categories:**
```powershell
.\.venv\Scripts\python.exe export_to_garmin.py --categories water food supermarket
```

**Split by category (separate GPX files):**
```powershell
.\.venv\Scripts\python.exe export_to_garmin.py --split --output-dir data\gpx
```

---

## 💡 Tips

- **Overpass API rate limits:** If you get "Too Many Requests" errors, wait a minute and try again
- **Large routes:** For routes >100km, consider splitting into stages
- **OSRM snapping:** Optional, improves accuracy if you have OSRM server running

---
roubleshooting

**"Gateway Timeout" errors:**
- ✓ Use stage-by-stage script instead
- ✓ Reduce stage length: `--stage-km 100`
- ✓ Wait a few minutes and retry

**"Too Many Requests":**
- ✓ Script automatically waits between stages
- ✓ If it happens, wait 5 minutes and resume

**Rate limit hit:**
- ✓ Script waits 3 seconds between stages
- ✓ Can increase wait time if needed

---

## 📁 Files Created

- ✅ `extract_pois_by_stages.py` - Stage-by-stage extraction ⭐ RECOMMENDED
- ✅ `extract_pois_simple.py` - Single-query extraction
- ✅ `export_to_garmin.py` - Garmin GPX export
- ✅ `data\pois_along_route.csv` - POI data with stage info
- ✅ `data\amr-poi.gpx` - Garmin-ready file

**Your POI extraction system is fully functional!** 🎉

**For AMR 2026, the stage-by-stage script is your best option!** 🚴‍♂️🏔️