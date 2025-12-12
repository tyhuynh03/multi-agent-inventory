@echo off
echo ========================================
echo  Stopping Multi-Agent Inventory System
echo ========================================
echo.

docker-compose down

if errorlevel 1 (
    echo.
    echo [ERROR] Khong the dung services!
    pause
    exit /b 1
)

echo.
echo [OK] All services stopped successfully
echo.
pause

