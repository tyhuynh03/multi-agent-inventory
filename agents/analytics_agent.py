"""
Analytics Agent - Phân tích kho hàng nâng cao
Tính toán: Stock Cover Days, Inventory Turnover, Stock Health, Restock Recommendations
"""

from typing import Optional, Dict, List, Any
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from langchain_groq import ChatGroq
from utils.logger import traceable
from configs.settings import GROQ_MODEL_NAME
from db.connection import get_db, run_sql_unified


class AnalyticsAgent:
    """
    Agent chuyên phân tích inventory metrics và stock cover days
    """
    
    def __init__(self, db_type: str = "postgresql"):
        self.llm = ChatGroq(
            model=GROQ_MODEL_NAME,
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )
        self.db_type = db_type
        
        # Stock cover thresholds
        self.CRITICAL_DAYS = 15
        self.WARNING_DAYS = 30
        self.HEALTHY_DAYS = 60
        self.OVERSTOCK_DAYS = 90
    
    @traceable(name="inventory_analytics.calculate_stock_cover")
    def calculate_stock_cover_days(
        self, 
        sku_id: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        period_days: int = 30
    ) -> pd.DataFrame:
        """
        Tính Stock Cover Days = Current Inventory / Average Daily Sales
        
        Args:
            sku_id: Filter by specific SKU (optional)
            warehouse_id: Filter by specific warehouse (optional)
            period_days: Number of days to calculate average sales (default: 30)
            
        Returns:
            DataFrame with stock cover days analysis
        """
        
        # Build SQL query to calculate stock cover
        # NOTE: Using last available date in sales table instead of CURRENT_DATE
        # to handle historical data (2021-2023)
        # Improved: Calculate avg_daily_sales using actual days with sales or period days
        sql = f"""
        WITH date_range AS (
            SELECT MAX(order_date) AS latest_date
            FROM sales
        ),
        daily_sales AS (
            SELECT 
                s.sku_id,
                s.warehouse_id,
                SUM(s.order_quantity)::numeric / {period_days}.0 AS avg_daily_sales,
                COUNT(DISTINCT s.order_date) AS active_days,
                SUM(s.order_quantity) AS total_quantity_sold
            FROM sales s
            CROSS JOIN date_range dr
            WHERE s.order_date >= dr.latest_date - INTERVAL '{period_days} days'
            GROUP BY s.sku_id, s.warehouse_id
            HAVING SUM(s.order_quantity) > 0
        ),
        inventory_current AS (
            SELECT 
                i.sku_id,
                i.warehouse_id,
                i.current_inventory_quantity,
                i.total_value,
                i.average_lead_time_days,
                i.vendor_name
            FROM inventory i
        )
        SELECT 
            ic.sku_id,
            sk.sku_name,
            ic.warehouse_id,
            ic.vendor_name,
            ic.current_inventory_quantity,
            COALESCE(ds.avg_daily_sales, 0) AS avg_daily_sales,
            COALESCE(ds.active_days, 0) AS active_days,
            COALESCE(ds.total_quantity_sold, 0) AS total_quantity_sold,
            CASE 
                WHEN COALESCE(ds.avg_daily_sales, 0) > 0 
                THEN ROUND(ic.current_inventory_quantity / ds.avg_daily_sales, 2)
                ELSE NULL 
            END AS stock_cover_days,
            ic.average_lead_time_days,
            ic.total_value,
            CASE 
                WHEN COALESCE(ds.avg_daily_sales, 0) = 0 THEN 'No Sales'
                WHEN ic.current_inventory_quantity / NULLIF(ds.avg_daily_sales, 0) < {self.CRITICAL_DAYS} THEN 'Critical'
                WHEN ic.current_inventory_quantity / NULLIF(ds.avg_daily_sales, 0) < {self.WARNING_DAYS} THEN 'Warning'
                WHEN ic.current_inventory_quantity / NULLIF(ds.avg_daily_sales, 0) < {self.HEALTHY_DAYS} THEN 'Healthy'
                WHEN ic.current_inventory_quantity / NULLIF(ds.avg_daily_sales, 0) >= {self.OVERSTOCK_DAYS} THEN 'Overstock'
                ELSE 'Good'
            END AS stock_status,
            CASE 
                WHEN COALESCE(ds.avg_daily_sales, 0) > 0 AND ic.average_lead_time_days IS NOT NULL
                THEN CASE 
                    WHEN ic.current_inventory_quantity / NULLIF(ds.avg_daily_sales, 0) < ic.average_lead_time_days THEN 'At Risk'
                    WHEN ic.current_inventory_quantity / NULLIF(ds.avg_daily_sales, 0) < ic.average_lead_time_days * 1.5 THEN 'Warning'
                    ELSE 'Safe'
                END
                ELSE NULL
            END AS stockout_risk
        FROM inventory_current ic
        LEFT JOIN daily_sales ds 
            ON ic.sku_id = ds.sku_id 
            AND ic.warehouse_id = ds.warehouse_id
        LEFT JOIN skus sk ON ic.sku_id = sk.sku_id
        WHERE 1=1
        """
        
        if sku_id:
            sql += f" AND ic.sku_id = '{sku_id}'"
        if warehouse_id:
            sql += f" AND ic.warehouse_id = '{warehouse_id}'"
        
        sql += " ORDER BY stock_cover_days ASC NULLS LAST"
        
        df, error = run_sql_unified(sql, self.db_type)
        
        if error:
            print(f"❌ Error calculating stock cover: {error}")
            return pd.DataFrame()
        
        return df
    
    @traceable(name="inventory_analytics.get_stock_health_summary")
    def get_stock_health_summary(self) -> Dict[str, Any]:
        """
        Tạo tóm tắt tình trạng stock health toàn hệ thống
        
        Returns:
            Dictionary with health statistics
        """
        df = self.calculate_stock_cover_days()
        
        if df.empty:
            return {"error": "No data available"}
        
        # Count by status
        status_counts = df['stock_status'].value_counts().to_dict()
        
        # Calculate statistics
        total_items = len(df)
        total_value = df['total_value'].sum()
        
        # Critical items detail
        critical_items = df[df['stock_status'] == 'Critical'].sort_values('stock_cover_days')
        
        # Overstock items detail
        overstock_items = df[df['stock_status'] == 'Overstock'].sort_values('stock_cover_days', ascending=False)
        
        summary = {
            "total_sku_warehouse_combinations": total_items,
            "total_inventory_value": round(total_value, 2),
            "status_breakdown": status_counts,
            "percentage_critical": round((status_counts.get('Critical', 0) / total_items * 100), 2),
            "percentage_warning": round((status_counts.get('Warning', 0) / total_items * 100), 2),
            "percentage_healthy": round((status_counts.get('Healthy', 0) + status_counts.get('Good', 0)) / total_items * 100, 2),
            "percentage_overstock": round((status_counts.get('Overstock', 0) / total_items * 100), 2),
            "critical_items_count": len(critical_items),
            "critical_items_value": round(critical_items['total_value'].sum(), 2),
            "overstock_items_count": len(overstock_items),
            "overstock_items_value": round(overstock_items['total_value'].sum(), 2),
            "avg_stock_cover_days": round(df['stock_cover_days'].mean(), 2),
            "median_stock_cover_days": round(df['stock_cover_days'].median(), 2)
        }
        
        return summary
    
    @traceable(name="inventory_analytics.get_restock_recommendations")
    def get_restock_recommendations(self, urgency: str = "all") -> pd.DataFrame:
        """
        Đề xuất restock dựa trên stock cover days và lead time
        
        Args:
            urgency: 'critical', 'warning', or 'all' (default)
            
        Returns:
            DataFrame with restock recommendations
        """
        df = self.calculate_stock_cover_days()
        
        if df.empty:
            return pd.DataFrame()
        
        # Filter based on urgency
        if urgency.lower() == "critical":
            df = df[df['stock_status'] == 'Critical']
        elif urgency.lower() == "warning":
            df = df[df['stock_status'].isin(['Critical', 'Warning'])]
        else:
            # Exclude healthy, good, and overstock
            df = df[df['stock_status'].isin(['Critical', 'Warning'])]
        
        if df.empty:
            return df
        
        # Calculate recommended reorder quantity
        # Formula: (Target Days - Current Cover Days) * Daily Sales
        target_cover_days = 45  # Target 45 days coverage
        
        df['recommended_reorder_qty'] = np.maximum(
            0,
            (target_cover_days - df['stock_cover_days'].fillna(0)) * df['avg_daily_sales']
        ).round(2)
        
        # Calculate when to reorder (considering lead time)
        df['days_until_stockout'] = df['stock_cover_days'].fillna(0)
        df['reorder_urgency'] = df.apply(
            lambda row: 'URGENT - Order Now!' if row['days_until_stockout'] <= row['average_lead_time_days']
            else f'Order in {int(row["days_until_stockout"] - row["average_lead_time_days"])} days',
            axis=1
        )
        
        # Sort by urgency
        df = df.sort_values('stock_cover_days')
        
        # Select relevant columns
        result = df[[
            'sku_id', 'sku_name', 'warehouse_id', 'vendor_name',
            'current_inventory_quantity', 'avg_daily_sales', 
            'stock_cover_days', 'average_lead_time_days',
            'recommended_reorder_qty', 'reorder_urgency', 'stock_status'
        ]]
        
        return result
    
    @traceable(name="inventory_analytics.get_overstock_items")
    def get_overstock_items(self) -> pd.DataFrame:
        """
        Tìm các SKU overstock (>90 days coverage)
        
        Returns:
            DataFrame with overstock items
        """
        df = self.calculate_stock_cover_days()
        
        if df.empty:
            return pd.DataFrame()
        
        # Filter overstock items
        overstock = df[df['stock_status'] == 'Overstock'].copy()
        
        if overstock.empty:
            return overstock
        
        # Calculate potential savings if reducing stock to 60 days
        target_days = 60
        overstock['excess_inventory_qty'] = (
            overstock['stock_cover_days'] - target_days
        ) * overstock['avg_daily_sales']
        
        # Calculate excess value (assuming cost = total_value / current_qty)
        overstock['cost_per_unit'] = overstock['total_value'] / overstock['current_inventory_quantity']
        overstock['excess_inventory_value'] = (
            overstock['excess_inventory_qty'] * overstock['cost_per_unit']
        ).round(2)
        
        # Sort by excess value
        overstock = overstock.sort_values('excess_inventory_value', ascending=False)
        
        result = overstock[[
            'sku_id', 'sku_name', 'warehouse_id', 'vendor_name',
            'current_inventory_quantity', 'stock_cover_days',
            'excess_inventory_qty', 'excess_inventory_value', 'total_value'
        ]]
        
        return result
    
    @traceable(name="inventory_analytics.predict_stockout_dates")
    def predict_stockout_dates(self, days_threshold: int = 60) -> pd.DataFrame:
        """
        Dự đoán ngày hết hàng cho các SKU
        
        Args:
            days_threshold: Only predict for items with cover < threshold days
            
        Returns:
            DataFrame with stockout predictions
        """
        df = self.calculate_stock_cover_days()
        
        if df.empty:
            return pd.DataFrame()
        
        # Filter items with stock cover below threshold
        df = df[
            (df['stock_cover_days'].notna()) & 
            (df['stock_cover_days'] < days_threshold) &
            (df['stock_cover_days'] > 0)
        ].copy()
        
        if df.empty:
            return df
        
        # Calculate predicted stockout date
        today = datetime.now()
        df['predicted_stockout_date'] = df['stock_cover_days'].apply(
            lambda days: (today + timedelta(days=days)).strftime('%Y-%m-%d')
        )
        
        # Calculate if stockout happens before restock arrives
        df['stockout_before_restock'] = df['stock_cover_days'] < df['average_lead_time_days']
        
        df['action_required'] = df['stockout_before_restock'].apply(
            lambda x: '🚨 CRITICAL - Emergency order needed' if x else '⚠️ Monitor and plan reorder'
        )
        
        # Sort by soonest stockout
        df = df.sort_values('stock_cover_days')
        
        result = df[[
            'sku_id', 'sku_name', 'warehouse_id', 'vendor_name',
            'current_inventory_quantity', 'avg_daily_sales',
            'stock_cover_days', 'predicted_stockout_date',
            'average_lead_time_days', 'stockout_before_restock', 'action_required'
        ]]
        
        return result
    
    @traceable(name="inventory_analytics.calculate_inventory_turnover")
    def calculate_inventory_turnover(self, period_days: int = 90) -> pd.DataFrame:
        """
        Tính Inventory Turnover Ratio
        Turnover = Total Sales Quantity / Average Inventory
        
        Args:
            period_days: Analysis period (default: 90 days)
            
        Returns:
            DataFrame with turnover metrics
        """
        sql = f"""
        WITH date_range AS (
            SELECT MAX(order_date) AS latest_date
            FROM sales
        ),
        sales_period AS (
            SELECT 
                s.sku_id,
                s.warehouse_id,
                SUM(s.order_quantity) AS total_sales_qty,
                SUM(s.revenue) AS total_revenue
            FROM sales s
            CROSS JOIN date_range dr
            WHERE s.order_date >= dr.latest_date - INTERVAL '{period_days} days'
            GROUP BY s.sku_id, s.warehouse_id
        )
        SELECT 
            i.sku_id,
            sk.sku_name,
            i.warehouse_id,
            i.current_inventory_quantity AS avg_inventory,
            COALESCE(sp.total_sales_qty, 0) AS total_sales_qty,
            COALESCE(sp.total_revenue, 0) AS total_revenue,
            CASE 
                WHEN i.current_inventory_quantity > 0 
                THEN ROUND(COALESCE(sp.total_sales_qty, 0) / i.current_inventory_quantity, 2)
                ELSE 0 
            END AS turnover_ratio,

            CASE 
                WHEN COALESCE(sp.total_sales_qty, 0) > 0 AND i.current_inventory_quantity > 0
                THEN ROUND({period_days} / (COALESCE(sp.total_sales_qty, 0) / i.current_inventory_quantity), 2)
                ELSE NULL
            END AS days_to_sell_inventory,
            i.total_value AS inventory_value
        FROM inventory i
        LEFT JOIN sales_period sp 
            ON i.sku_id = sp.sku_id 
            AND i.warehouse_id = sp.warehouse_id
        LEFT JOIN skus sk ON i.sku_id = sk.sku_id
        ORDER BY turnover_ratio DESC
        """
        
        df, error = run_sql_unified(sql, self.db_type)
        
        if error:
            print(f"❌ Error calculating turnover: {error}")
            return pd.DataFrame()
        
        return df
    
    @traceable(name="inventory_analytics.generate_analytics_report")
    def generate_analytics_report(self, user_question: str, df: pd.DataFrame) -> str:
        """
        Tạo natural language report từ inventory analytics data
        
        Args:
            user_question: User's original question
            df: Analytics DataFrame
            
        Returns:
            Natural language summary
        """
        if df.empty:
            return "No data available for analysis."
        
        # Prepare data summary for LLM
        summary_stats = {
            "total_records": len(df),
            "columns": list(df.columns),
            "sample_data": df.head(5).to_dict('records')
        }
        
        prompt = f"""
You are an inventory analytics expert. Generate a concise, actionable summary based on the data.

**User Question:** {user_question}

**Data Summary:**
- Total Records: {summary_stats['total_records']}
- Columns: {', '.join(summary_stats['columns'])}

**Sample Data (first 5 rows):**
{summary_stats['sample_data']}

**Instructions:**
**Instructions:**
1. Provide a 2-3 sentence executive summary
2. Focus on the most critical findings
3. Keep it concise and business-focused
4. Use emojis for visual clarity (🚨 critical, ⚠️ warning, ✅ good, 📊 stats)

**Format:**
Executive Summary:
[Your summary here]
"""
        
        try:
            response = self.llm.invoke(prompt)
            content = getattr(response, "content", "").strip()
            return content
        except Exception as e:
            print(f"⚠️ LLM summary failed: {e}")
            return f"Data retrieved successfully with {len(df)} records. See table below for details."
    
    @traceable(name="inventory_analytics.analyze_by_warehouse")
    def analyze_by_warehouse(self) -> pd.DataFrame:
        """
        Phân tích stock cover performance theo warehouse
        
        Returns:
            DataFrame with warehouse-level analysis
        """
        df = self.calculate_stock_cover_days()
        
        if df.empty:
            return pd.DataFrame()
        
        # Group by warehouse
        warehouse_stats = df.groupby('warehouse_id').agg({
            'sku_id': 'count',
            'stock_cover_days': ['mean', 'median', 'min', 'max'],
            'total_value': 'sum',
            'current_inventory_quantity': 'sum'
        }).round(2)
        
        warehouse_stats.columns = [
            'total_skus', 
            'avg_stock_cover_days', 
            'median_stock_cover_days',
            'min_stock_cover_days',
            'max_stock_cover_days',
            'total_inventory_value',
            'total_inventory_quantity'
        ]
        
        # Count critical items per warehouse
        critical_counts = df[df['stock_status'] == 'Critical'].groupby('warehouse_id').size()
        warehouse_stats['critical_items'] = critical_counts
        warehouse_stats['critical_items'] = warehouse_stats['critical_items'].fillna(0).astype(int)
        
        # Count overstock items per warehouse
        overstock_counts = df[df['stock_status'] == 'Overstock'].groupby('warehouse_id').size()
        warehouse_stats['overstock_items'] = overstock_counts
        warehouse_stats['overstock_items'] = warehouse_stats['overstock_items'].fillna(0).astype(int)
        
        warehouse_stats = warehouse_stats.reset_index()
        warehouse_stats = warehouse_stats.sort_values('avg_stock_cover_days')
        
        return warehouse_stats

