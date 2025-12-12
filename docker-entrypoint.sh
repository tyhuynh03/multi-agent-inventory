#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Starting Multi-Agent Inventory System"
echo "=========================================="

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "⏳ Waiting for PostgreSQL to be ready..."
    
    max_tries=30
    count=0
    
    until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
        count=$((count + 1))
        if [ $count -ge $max_tries ]; then
            echo "❌ PostgreSQL did not become ready in time"
            exit 1
        fi
        echo "   Attempt $count/$max_tries - PostgreSQL is unavailable, sleeping..."
        sleep 2
    done
    
    echo "✅ PostgreSQL is ready!"
}

# Function to check if tables have data
check_data_exists() {
    local count=$(PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM warehouses;" 2>/dev/null | xargs)
    echo "$count"
}

# Function to run migration
run_migration() {
    echo ""
    echo "📊 Checking if data migration is needed..."
    
    data_count=$(check_data_exists)
    
    if [ "$data_count" = "0" ] || [ -z "$data_count" ]; then
        echo "📦 No data found. Running migration from CSV files..."
        python migrate_to_postgres.py
        
        if [ $? -eq 0 ]; then
            echo "✅ Data migration completed successfully!"
        else
            echo "❌ Data migration failed!"
            exit 1
        fi
    else
        echo "✅ Data already exists ($data_count warehouses found). Skipping migration."
    fi
}

# Function to initialize RAG
initialize_rag() {
    echo ""
    echo "🤖 Checking if RAG initialization is needed..."
    
    if [ ! -d "data/chroma_db" ] || [ -z "$(ls -A data/chroma_db 2>/dev/null)" ]; then
        echo "🔧 RAG database not found. Initializing RAG system..."
        python -m rag.initialize_rag
        
        if [ $? -eq 0 ]; then
            echo "✅ RAG initialization completed successfully!"
        else
            echo "⚠️ RAG initialization failed, but continuing..."
        fi
    else
        echo "✅ RAG database already exists. Skipping initialization."
    fi
}

# Main execution
echo ""
echo "Step 1: Wait for PostgreSQL"
wait_for_postgres

echo ""
echo "Step 2: Migrate data (if needed)"
run_migration

echo ""
echo "Step 3: Initialize RAG (if needed)"
initialize_rag

echo ""
echo "=========================================="
echo "✅ Initialization complete!"
echo "🌐 Starting Streamlit application..."
echo "=========================================="
echo ""

# Start Streamlit
exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0

