@echo off
echo ========================================
echo  Starting Multi-Agent Inventory System
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] File .env khong ton tai!
    echo.
    echo Vui long tao file .env tu example.env:
    echo   copy example.env .env
    echo.
    echo Sau do dien GROQ_API_KEY vao file .env
    pause
    exit /b 1
)

echo [1/3] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker khong duoc cai dat hoac khong chay!
    echo Vui long cai dat Docker Desktop.
    pause
    exit /b 1
)
echo [OK] Docker is running

echo.
echo [2/3] Starting services...
docker-compose up -d

if errorlevel 1 (
    echo.
    echo [ERROR] Khong the khoi dong services!
    echo Xem log de biet chi tiet: docker-compose logs
    pause
    exit /b 1
)

echo.
echo [3/3] Waiting for services to be ready...
echo.
echo Note: Lan dau chay se mat 2-3 phut de:
echo   - Load du lieu tu CSV vao database
echo   - Khoi tao RAG system
echo.
timeout /t 10 /nobreak >nul

echo.
echo ========================================
echo  SUCCESS! Application is running
echo ========================================
echo.
echo App URL:      http://localhost:8501
echo PostgreSQL:   localhost:5432
echo.
echo Commands:
echo   - View logs:    docker-compose logs -f
echo   - Stop:         docker-compose down
echo   - Restart:      docker-compose restart
echo.
echo Press any key to view logs (Ctrl+C to exit)...
pause >nul
docker-compose logs -f

