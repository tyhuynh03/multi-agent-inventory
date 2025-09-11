"""
Report Agent - Generate various inventory reports
Template-based approach for consistent, reliable reports
"""

import pandas as pd
from typing import Dict, List, Optional
from langsmith.run_helpers import traceable
from db.connection import get_db, run_sql


class ReportAgent:
    def __init__(self):
        # Pre-defined report templates
        self.report_templates = {
            "low_stock": {
                "sql": 'SELECT "Product ID", "Product Name", "Category", "Inventory Level", "Price" FROM inventory WHERE "Inventory Level" < {threshold} ORDER BY "Inventory Level" ASC',
                "title": "Low Stock Alert Report",
                "description": "Products with inventory below specified threshold",
                "default_params": {"threshold": 10}
            },
            "top_products": {
                "sql": 'SELECT "Product ID", "Product Name", "Category", "Units Sold", "Price", ("Units Sold" * "Price") as Revenue FROM inventory WHERE "Units Sold" > 0 ORDER BY "Units Sold" DESC LIMIT {limit}',
                "title": "Top Selling Products Report",
                "description": "Best performing products by units sold",
                "default_params": {"limit": 10}
            },
            "category_summary": {
                "sql": 'SELECT "Category", COUNT(*) as Product_Count, SUM("Inventory Level") as Total_Inventory, AVG("Price") as Avg_Price, SUM("Units Sold") as Total_Sold FROM inventory GROUP BY "Category" ORDER BY Total_Sold DESC',
                "title": "Category Performance Summary",
                "description": "Performance breakdown by product category",
                "default_params": {}
            },
            "inventory_valuation": {
                "sql": 'SELECT "Category", SUM("Inventory Level" * "Price") as Total_Value, COUNT(*) as Product_Count FROM inventory WHERE "Inventory Level" > 0 GROUP BY "Category" ORDER BY Total_Value DESC',
                "title": "Inventory Valuation Report",
                "description": "Total inventory value by category",
                "default_params": {}
            },
            "overstock": {
                "sql": 'SELECT "Product ID", "Product Name", "Category", "Inventory Level", "Price" FROM inventory WHERE "Inventory Level" > {threshold} ORDER BY "Inventory Level" DESC',
                "title": "Overstock Alert Report",
                "description": "Products with excess inventory",
                "default_params": {"threshold": 100}
            }
        }
    
    @traceable(name="report.generate")
    def generate_report(self, report_type: str, db_path: str, params: Optional[Dict] = None) -> Dict:
        """
        Generate a report based on template and parameters
        
        Args:
            report_type: Type of report to generate
            db_path: Path to SQLite database
            params: Optional parameters for the report
            
        Returns:
            Dict with report data and metadata
        """
        try:
            # Validate report type
            if report_type not in self.report_templates:
                available_types = list(self.report_templates.keys())
                return {
                    "success": False,
                    "error": f"Unknown report type: {report_type}. Available types: {available_types}",
                    "report_type": report_type
                }
            
            # Get template and merge parameters
            template = self.report_templates[report_type]
            merged_params = {**template["default_params"], **(params or {})}
            
            # Format SQL with parameters
            sql = template["sql"].format(**merged_params)
            
            # Execute query
            db = get_db(db_path)
            df, error = run_sql(db, sql)
            
            if error:
                return {
                    "success": False,
                    "error": f"SQL execution error: {error}",
                    "report_type": report_type
                }
            
            # Generate report summary
            summary = self._generate_summary(df, report_type, merged_params)
            
            return {
                "success": True,
                "report_type": report_type,
                "title": template["title"],
                "description": template["description"],
                "sql": sql,
                "data": df,
                "summary": summary,
                "parameters": merged_params,
                "message": f"📊 {template['title']} generated successfully! Found {len(df)} records."
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Report generation error: {str(e)}",
                "report_type": report_type
            }
    
    def _generate_summary(self, df: pd.DataFrame, report_type: str, params: Dict) -> Dict:
        """Generate summary statistics for the report"""
        if df.empty:
            return {"total_records": 0, "message": "No data found"}
        
        summary = {"total_records": len(df)}
        
        if report_type == "low_stock":
            summary.update({
                "total_products": len(df),
                "avg_inventory": df["Inventory Level"].mean(),
                "min_inventory": df["Inventory Level"].min(),
                "categories_affected": df["Category"].nunique()
            })
        elif report_type == "top_products":
            summary.update({
                "total_products": len(df),
                "total_revenue": df["Revenue"].sum() if "Revenue" in df.columns else 0,
                "avg_units_sold": df["Units Sold"].mean(),
                "top_category": df["Category"].mode().iloc[0] if not df.empty else "N/A"
            })
        elif report_type == "category_summary":
            summary.update({
                "total_categories": len(df),
                "total_products": df["Product_Count"].sum(),
                "total_inventory": df["Total_Inventory"].sum(),
                "total_sold": df["Total_Sold"].sum()
            })
        elif report_type == "inventory_valuation":
            summary.update({
                "total_categories": len(df),
                "total_value": df["Total_Value"].sum(),
                "avg_value_per_category": df["Total_Value"].mean(),
                "highest_value_category": df.loc[df["Total_Value"].idxmax(), "Category"] if not df.empty else "N/A"
            })
        elif report_type == "overstock":
            summary.update({
                "total_products": len(df),
                "avg_inventory": df["Inventory Level"].mean(),
                "max_inventory": df["Inventory Level"].max(),
                "categories_affected": df["Category"].nunique()
            })
        
        return summary
    
    def get_available_reports(self) -> List[Dict]:
        """Get list of available report types with descriptions"""
        return [
            {
                "type": report_type,
                "title": template["title"],
                "description": template["description"],
                "default_params": template["default_params"]
            }
            for report_type, template in self.report_templates.items()
        ]
    
    def format_report_html(self, report_data: Dict) -> str:
        """Format report data as HTML for display"""
        if not report_data["success"]:
            return f"<div class='error'>Error: {report_data['error']}</div>"
        
        df = report_data["data"]
        summary = report_data["summary"]
        
        html = f"""
        <div class='report'>
            <h2>{report_data['title']}</h2>
            <p><strong>Description:</strong> {report_data['description']}</p>
            <p><strong>Generated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <h3>Summary</h3>
            <ul>
        """
        
        for key, value in summary.items():
            if isinstance(value, float):
                value = f"{value:,.2f}"
            html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
        
        html += """
            </ul>
            
            <h3>Data</h3>
            <div class='table-container'>
        """
        
        # Convert DataFrame to HTML table
        html += df.to_html(classes='report-table', escape=False, index=False)
        
        html += """
            </div>
        </div>
        """
        
        return html
