# Test OSRM Server
# This script tests if the OSRM server is running correctly

Write-Host "Testing OSRM server..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/nearest/v1/car/-7.99,31.63" -UseBasicParsing
    $json = $response.Content | ConvertFrom-Json
    
    Write-Host "`n✓ OSRM is alive!" -ForegroundColor Green
    Write-Host "`nResponse:" -ForegroundColor Cyan
    $json | ConvertTo-Json -Depth 3
} catch {
    Write-Host "`n✗ OSRM server is not responding!" -ForegroundColor Red
    Write-Host "Make sure the server is running with: .\scripts\start_osrm.ps1" -ForegroundColor Yellow
}
