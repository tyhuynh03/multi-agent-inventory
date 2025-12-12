# PowerShell script to run Docker services forever
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Chay he thong vinh vien (Forever Mode)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "[ERROR] File .env khong ton tai!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Vui long tao file .env tu example.env:" -ForegroundColor Yellow
    Write-Host "  copy example.env .env" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Nhan Enter de thoat"
    exit 1
}

Write-Host "[INFO] Khoi dong Docker services voi restart policy..." -ForegroundColor Green
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Khong the khoi dong services!" -ForegroundColor Red
    Read-Host "Nhan Enter de thoat"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Services da duoc khoi dong" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Docker containers se tu dong restart neu bi dung" -ForegroundColor Yellow
Write-Host "(restart: unless-stopped)" -ForegroundColor Yellow
Write-Host ""
Write-Host "App URL:      http://localhost:8501" -ForegroundColor Cyan
Write-Host "PostgreSQL:   localhost:5432" -ForegroundColor Cyan
Write-Host ""
Write-Host "De dung:      docker-compose down" -ForegroundColor Yellow
Write-Host "De xem logs:  docker-compose logs -f" -ForegroundColor Yellow
Write-Host ""
Write-Host "Script nay se theo doi va restart neu can..." -ForegroundColor Green
Write-Host "Nhan Ctrl+C de dung script (containers van chay)" -ForegroundColor Yellow
Write-Host ""

# Monitor loop
while ($true) {
    Start-Sleep -Seconds 30
    $containers = docker ps --format "{{.Names}}" | Select-String -Pattern "inventory_app|inventory_postgres"
    
    if (-not $containers) {
        Write-Host "[WARNING] Phat hien container bi dung, dang restart..." -ForegroundColor Yellow
        docker-compose up -d
    }
}


