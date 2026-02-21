# Quick Start Script for AMR POI Extraction
# This script runs the complete workflow

param(
    [string]$GpxFile = "",
    [int]$Buffer = 1000
)

Write-Host @"
╔═══════════════════════════════════════╗
║   AMR POI Extraction - Quick Start    ║
╔═══════════════════════════════════════╝
"@ -ForegroundColor Cyan

# Check if GPX file provided
if ($GpxFile -eq "") {
    Write-Host "`n❌ Error: Please provide a GPX file" -ForegroundColor Red
    Write-Host "`nUsage: .\quickstart.ps1 -GpxFile data\amr_route.gpx" -ForegroundColor Yellow
    Write-Host "       .\quickstart.ps1 -GpxFile data\amr_route.gpx -Buffer 2000" -ForegroundColor Yellow
    exit 1
}

if (!(Test-Path $GpxFile)) {
    Write-Host "`n❌ Error: GPX file not found: $GpxFile" -ForegroundColor Red
    exit 1
}

Write-Host "`n📍 Using GPX file: $GpxFile" -ForegroundColor Green
Write-Host "📏 Buffer distance: $Buffer meters`n" -ForegroundColor Green

# Step 1: Check Docker
Write-Host "Step 1/6: Checking Docker..." -ForegroundColor Yellow
docker --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker not found! Please install Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker is installed`n" -ForegroundColor Green

# Step 2: Check OSRM data
Write-Host "Step 2/6: Checking OSRM data..." -ForegroundColor Yellow
if (!(Test-Path "osrm\morocco-latest.osm.pbf")) {
    Write-Host "OSRM data not found. Running setup..." -ForegroundColor Yellow
    .\scripts\setup_osrm.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ OSRM setup failed!" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✓ OSRM data ready`n" -ForegroundColor Green

# Step 3: Check if OSRM server is running
Write-Host "Step 3/6: Checking OSRM server..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/nearest/v1/car/-7.99,31.63" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ OSRM server is running`n" -ForegroundColor Green
    $osrmRunning = $true
} catch {
    Write-Host "⚠ OSRM server not running" -ForegroundColor Yellow
    Write-Host "Starting OSRM server in background..." -ForegroundColor Yellow
    
    # Start OSRM in background
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '.\scripts\start_osrm.ps1'" -WindowStyle Minimized
    
    Write-Host "Waiting for OSRM to start (30 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/nearest/v1/car/-7.99,31.63" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        Write-Host "✓ OSRM server started`n" -ForegroundColor Green
        $osrmRunning = $true
    } catch {
        Write-Host "⚠ OSRM server may not be ready. Continuing without snapping...`n" -ForegroundColor Yellow
        $osrmRunning = $false
    }
}

# Step 4: Check Python environment
Write-Host "Step 4/6: Checking Python environment..." -ForegroundColor Yellow
if (!(Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "❌ Python virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Check if packages are installed
$pythonCmd = ".\.venv\Scripts\python.exe"
& $pythonCmd -c "import poi_extractor" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Python packages (this may take a few minutes)..." -ForegroundColor Yellow
    & $pythonCmd -m pip install -e .[all]
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Package installation failed!" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✓ Python environment ready`n" -ForegroundColor Green

# Step 5: Extract POIs
Write-Host "Step 5/6: Extracting POIs..." -ForegroundColor Yellow
$extractArgs = "--gpx", $GpxFile, "--buffer", $Buffer.ToString()
if (-not $osrmRunning) {
    $extractArgs += "--no-snap"
}

& $pythonCmd extract_pois.py @extractArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ POI extraction failed!" -ForegroundColor Red
    exit 1
}
Write-Host "`n✓ POI extraction complete`n" -ForegroundColor Green

# Step 6: Export to Garmin
Write-Host "Step 6/6: Exporting to Garmin GPX..." -ForegroundColor Yellow
$exportArgs = "--csv", "data\pois_along_route.csv"
if (-not $osrmRunning) {
    $exportArgs += "--no-snap"
}

& $pythonCmd export_to_garmin.py @exportArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Export failed!" -ForegroundColor Red
    exit 1
}

Write-Host @"

╔═══════════════════════════════════════╗
║          🎉 ALL DONE! 🎉              ║
╚═══════════════════════════════════════╝

Your Garmin POI file is ready:
📁 data\amr-poi.gpx

Next steps:
1. Connect your Garmin device
2. Copy data\amr-poi.gpx to \Garmin\NewFiles\
3. Safely eject device
4. POIs will appear as waypoints

For better results:
- Use Garmin POI Loader to convert to .gpi format
- Get custom icons and proximity alerts
- See README.md for details

Happy racing! 🚴‍♂️🏔️

"@ -ForegroundColor Green
