@echo off
echo ========================================
echo  Chay Streamlit App vinh vien
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

REM Activate virtual environment if exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

echo [INFO] Dang khoi dong Streamlit app...
echo [INFO] App se chay tai: http://localhost:8501
echo.
echo [INFO] De dung, nhan Ctrl+C hoac dong cua so nay
echo.

:restart
echo [INFO] Dang khoi dong Streamlit...
streamlit run app.py
if errorlevel 1 (
    echo.
    echo [ERROR] Streamlit bi dung! Dang restart sau 5 giay...
    timeout /t 5 /nobreak >nul
    goto restart
) else (
    echo.
    echo [INFO] Streamlit da dung. Dang restart sau 5 giay...
    timeout /t 5 /nobreak >nul
    goto restart
)


