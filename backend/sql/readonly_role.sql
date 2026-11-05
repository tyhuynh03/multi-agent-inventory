-- Role chỉ đọc, chạy một lần:
--   docker exec -i inventory_postgres psql -U inventory_user -d inventory_db < backend/sql/readonly_role.sql
-- Sau đó đặt DB_USER=inventory_ro trong .env. Đây là lớp phòng thủ duy nhất có tác dụng
-- với cả đường SQL do LLM sinh ra (agents/ gọi run_sql_unified trực tiếp, không qua backend).

CREATE ROLE inventory_ro LOGIN PASSWORD 'change_me_ro_password';

-- Chặn từ gốc: mọi kết nối bằng role này mặc định read-only và chết sau 10 giây.
ALTER ROLE inventory_ro SET statement_timeout = '10s';
ALTER ROLE inventory_ro SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE inventory_ro SET default_transaction_read_only = on;

GRANT CONNECT ON DATABASE inventory_db TO inventory_ro;
GRANT USAGE ON SCHEMA public TO inventory_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO inventory_ro;

-- Bảng tạo sau này cũng chỉ đọc, không cần chạy lại script.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO inventory_ro;

-- Tuỳ chọn: bỏ quyền mọi người dùng truy cập schema public (Postgres 15 mặc định đã tắt CREATE).
-- REVOKE ALL ON SCHEMA public FROM PUBLIC;
