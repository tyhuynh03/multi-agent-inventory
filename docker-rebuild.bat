@echo off
echo ========================================
echo  Rebuilding Multi-Agent Inventory System
echo ========================================
echo.

echo [1/2] Stopping services...
docker-compose down

echo.
echo [2/2] Building and starting services...
docker-compose up -d --build

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo Xem log de biet chi tiet: docker-compose logs
    pause
    exit /b 1
)

echo.
echo ========================================
echo  SUCCESS! Application rebuilt and running
echo ========================================
echo.
echo App URL: http://localhost:8501
echo.
pause

