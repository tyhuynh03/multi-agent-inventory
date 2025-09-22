@echo off
echo 🚀 Khởi động PostgreSQL với Docker...
echo.

echo 📦 Đang tải và khởi động PostgreSQL container...
docker-compose up -d postgres

echo.
echo ⏳ Đợi PostgreSQL khởi động hoàn tất...
timeout /t 10 /nobreak > nul

echo.
echo 🔍 Kiểm tra trạng thái container...
docker-compose ps

echo.
echo ✅ Hoàn tất! 
echo.
echo 🗄️ PostgreSQL đang chạy tại: localhost:5432
echo    - Database: inventory_db
echo    - User: inventory_user
echo    - Password: inventory_pass
echo.
echo 💡 Kết nối bằng DBeaver hoặc client khác với thông tin trên
echo 📝 Để migrate dữ liệu, chạy: python migrate_to_postgres.py
echo.
pause
