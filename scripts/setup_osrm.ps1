# OSRM Setup Script for Windows
# This script downloads Morocco OSM data and prepares it for OSRM

Write-Host "=== OSRM Setup Script ===" -ForegroundColor Green

# Check Docker
Write-Host "`nChecking Docker installation..." -ForegroundColor Yellow
docker --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not installed or not running!" -ForegroundColor Red
    exit 1
}

# Create osrm directory if it doesn't exist
if (!(Test-Path "osrm")) {
    New-Item -ItemType Directory -Path "osrm"
}

Set-Location osrm

# Download Morocco OSM extract
Write-Host "`nDownloading Morocco OSM extract..." -ForegroundColor Yellow
$osm_file = "morocco-latest.osm.pbf"

if (Test-Path $osm_file) {
    Write-Host "File already exists. Skipping download." -ForegroundColor Cyan
} else {
    # Using Invoke-WebRequest for Windows
    $url = "https://download.geofabrik.de/africa/morocco-latest.osm.pbf"
    Invoke-WebRequest -Uri $url -OutFile $osm_file
    Write-Host "Download complete!" -ForegroundColor Green
}

# Prepare OSRM data
Write-Host "`nStep 1/3: Extracting OSM data..." -ForegroundColor Yellow
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/morocco-latest.osm.pbf

Write-Host "`nStep 2/3: Partitioning..." -ForegroundColor Yellow
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-partition /data/morocco-latest.osrm

Write-Host "`nStep 3/3: Customizing..." -ForegroundColor Yellow
docker run -t -v "${PWD}:/data" osrm/osrm-backend osrm-customize /data/morocco-latest.osrm

Write-Host "`n=== OSRM Setup Complete! ===" -ForegroundColor Green
Write-Host "To start the OSRM server, run: .\scripts\start_osrm.ps1" -ForegroundColor Cyan

Set-Location ..
