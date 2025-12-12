@echo off
echo ========================================
echo  Chay he thong vinh vien (Forever Mode)
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] File .env khong ton tai!
    echo.
    echo Vui long tao file .env tu example.env:
    echo   copy example.env .env
    echo.
    pause
    exit /b 1
)

echo [INFO] Khoi dong Docker services voi restart policy...
docker-compose up -d

if errorlevel 1 (
    echo [ERROR] Khong the khoi dong services!
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Services da duoc khoi dong
echo ========================================
echo.
echo Docker containers se tu dong restart neu bi dung
echo (restart: unless-stopped)
echo.
echo App URL:      http://localhost:8501
echo PostgreSQL:   localhost:5432
echo.
echo De dung:      docker-compose down
echo De xem logs:  docker-compose logs -f
echo.
echo Script nay se theo doi va restart neu can...
echo.

:loop
timeout /t 30 /nobreak >nul
docker ps | findstr "inventory_app inventory_postgres" >nul
if errorlevel 1 (
    echo [WARNING] Phat hien container bi dung, dang restart...
    docker-compose up -d
)
goto loop


