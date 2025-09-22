@echo off
echo 🛑 Dừng PostgreSQL containers...
echo.

docker-compose down

echo.
echo ✅ Đã dừng tất cả containers!
echo.
pause
