from typing import Optional, Dict, Any
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

from utils.logger import traceable
from langchain_groq import ChatGroq
from configs.settings import GROQ_MODEL_NAME


 


class VisualizationAgent:
    """
    Agent lập kế hoạch biểu đồ bằng LLM và thực thi spec để vẽ.
    """

    def __init__(self):
        self.llm = ChatGroq(
            model=GROQ_MODEL_NAME,
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )

    @traceable(name="viz.plan")
    def plan_chart(self, question: str, df: pd.DataFrame) -> Dict[str, Any]:
        columns = ", ".join([str(c) for c in df.columns])
        sample = df.head(5).to_dict(orient="records")
        prompt = f"""
You are a data visualization planner for an inventory management system. Given a user question and a pandas table (with columns and samples), output a JSON spec for the best chart.

**Available Tables:**
- warehouses: warehouse_code, city, province, country, latitude, longitude
- skus: sku_id, sku_name  
- inventory: sku_id, warehouse_id, vendor_name, current_inventory_quantity, total_value, unit_price, average_lead_time_days
- sales: order_number, order_date, sku_id, warehouse_id, customer_type, order_quantity, revenue

**Rules:**
- chart_type: one of ["line", "bar", "pie", "donut", "scatter", "heatmap"]
- x: string column name for x-axis (for bar/line) or labels (for pie)
- y: array of 1-3 numeric column names (for bar/line) or single value column (for pie)
- group_by: optional string column for series separation (e.g., warehouse_id, sku_id, customer_type)
- agg: aggregation for y if grouping is needed, one of ["sum", "avg", "mean"]
- title: short descriptive title

Return ONLY valid JSON.

Question: {question}
Columns: {columns}
Sample rows: {sample}
"""
        try:
            res = self.llm.invoke(prompt)
            import json, re
            content = getattr(res, "content", "")
            match = re.search(r"\{[\s\S]*\}", content)
            spec = json.loads(match.group(0) if match else content)
            
            # Validate spec
            if not isinstance(spec, dict):
                raise ValueError("Invalid spec format")
            if "chart_type" not in spec:
                spec["chart_type"] = "bar"
            if "title" not in spec:
                spec["title"] = "Data Visualization"
                
        except Exception as e:
            print(f"⚠️ LLM planning failed: {e}, using fallback")
            # Better fallback spec
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
            
            if len(numeric_cols) >= 1 and len(categorical_cols) >= 1:
                spec = {
                    "chart_type": "bar",
                    "x": categorical_cols[0],
                    "y": [numeric_cols[0]],
                    "title": f"{numeric_cols[0]} by {categorical_cols[0]}"
                }
            elif len(numeric_cols) >= 2:
                spec = {
                    "chart_type": "scatter", 
                    "x": numeric_cols[0],
                    "y": [numeric_cols[1]],
                    "title": f"{numeric_cols[1]} vs {numeric_cols[0]}"
                }
            else:
                spec = {
                    "chart_type": "bar",
                    "x": df.columns[0] if len(df.columns) > 0 else "index",
                    "y": [df.columns[1]] if len(df.columns) > 1 else [df.columns[0]],
                    "title": "Data Overview"
                }
        return spec

    @traceable(name="viz.render_from_spec")
    def render_from_spec(self, df: pd.DataFrame, spec: Dict[str, Any]) -> Optional[go.Figure]:
        if df is None or df.empty:
            return None
        chart_type = spec.get("chart_type", "line")
        x = spec.get("x")
        y_cols = spec.get("y", [])
        group_by = spec.get("group_by")
        agg = (spec.get("agg") or "sum").lower()
        title = spec.get("title", "Chart")

        if x and x in df.columns:
            # cố gắng parse thời gian nếu có chữ 'date' trong tên cột
            if isinstance(x, str) and "date" in x.lower():
                try:
                    df[x] = pd.to_datetime(df[x], errors="coerce")
                except Exception:
                    pass

        # Chuẩn bị dữ liệu theo group/agg nếu cần
        working = df.copy()
        numeric = working.select_dtypes(np.number).columns.tolist()
        y_cols = [c for c in y_cols if c in numeric]
        if not y_cols and numeric:
            y_cols = numeric[:1]

        if group_by and group_by in working.columns and x and x in working.columns and y_cols:
            agg_func = {col: ("mean" if agg in ("avg", "mean") else "sum") for col in y_cols}
            working = (
                working.groupby([x, group_by], as_index=False)
                .agg(agg_func)
            )

        # Plotly rendering với better error handling
        try:
            if chart_type == "pie" and x and y_cols and len(y_cols) > 0:
                # Aggregate data if needed
                if len(working) > 10:  # Too many slices
                    top_9 = working.nlargest(9, y_cols[0])
                    others_sum = working.nsmallest(len(working)-9, y_cols[0])[y_cols[0]].sum()
                    if others_sum > 0:
                        others_row = {x: 'Others', y_cols[0]: others_sum}
                        top_9 = pd.concat([top_9, pd.DataFrame([others_row])], ignore_index=True)
                    working = top_9
                
                fig = px.pie(
                    working, 
                    names=x, 
                    values=y_cols[0],
                    title=title,
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                
                fig.update_traces(
                    textposition='inside', 
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>Value: %{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
                )
                
            elif chart_type == "donut" and x and y_cols and len(y_cols) > 0:
                # Donut chart: x as labels, y as values
                labels_col = x
                values_col = y_cols[0]
                
                fig = px.pie(
                    working, 
                    names=labels_col, 
                    values=values_col,
                    title=title,
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.4  # Create donut hole
                )
                
                # Custom colors and display both percentage and actual values
                fig.update_traces(
                    textposition='inside', 
                    textinfo='percent+label+value',
                    hovertemplate='<b>%{label}</b><br>Value: %{value:,.0f}<br>Percentage: %{percent}<extra></extra>',
                    marker=dict(
                        colors=px.colors.qualitative.Set3,
                        line=dict(color='white', width=2)
                    )
                )
                
                # Add legend
                fig.update_layout(
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.01
                    )
                )
                
            elif chart_type == "bar" and x and y_cols and len(y_cols) > 0:
                # Limit data points for better readability
                if len(working) > 20:
                    working = working.nlargest(20, y_cols[0])
                    title += " (Top 20)"
                
                if len(y_cols) > 1:
                    df_long = working.melt(id_vars=[x], value_vars=y_cols, var_name="Metric", value_name="Value")
                    fig = px.bar(df_long, x=x, y="Value", color="Metric", 
                               barmode="group", title=title,
                               color_discrete_sequence=px.colors.qualitative.Set1)
                else:
                    col = y_cols[0]
                    if group_by and group_by in working.columns:
                        fig = px.bar(working, x=x, y=col, color=group_by, 
                                   title=title, barmode="group",
                                   color_discrete_sequence=px.colors.qualitative.Set1)
                    else:
                        fig = px.bar(working, x=x, y=col, title=title,
                                   color_discrete_sequence=px.colors.qualitative.Set1)
                        
                # Improve bar chart appearance
                fig.update_layout(
                    xaxis_tickangle=-45 if len(working) > 5 else 0,
                    showlegend=True if (len(y_cols) > 1 or group_by) else False
                )
            else:
                # default line; if multiple y -> add each as a trace
                if x and y_cols and len(y_cols) > 0:
                    fig = go.Figure()
                    if group_by and group_by in working.columns:
                        for name, part in working.groupby(group_by):
                            for col in y_cols:
                                fig.add_trace(go.Scatter(x=part[x], y=part[col], mode="lines+markers", name=f"{name}-{col}"))
                    else:
                        for col in y_cols:
                            fig.add_trace(go.Scatter(x=working[x], y=working[col], mode="lines+markers", name=col))
                    fig.update_layout(title=title, xaxis_title=str(x), yaxis_title="Value")
                else:
                    return None

            # Add better layout and styling
            fig.update_layout(
                template="plotly_white",
                font=dict(size=12),
                title=dict(font=dict(size=16, color='#2E86AB')),
                margin=dict(t=60, b=60, l=60, r=60)
            )
            return fig
            
        except Exception as plot_error:
            print(f"⚠️ Plotly rendering failed: {plot_error}, falling back to matplotlib")
            # Enhanced matplotlib fallback
            # Matplotlib fallback với better styling
            plt.style.use('seaborn-v0_8' if hasattr(plt.style, 'seaborn-v0_8') else 'default')
            fig, ax = plt.subplots(figsize=(12, 6))
            
            if chart_type == "pie" and x and y_cols and len(y_cols) > 0:
                # Limit pie slices
                if len(working) > 8:
                    top_7 = working.nlargest(7, y_cols[0])
                    others_sum = working.nsmallest(len(working)-7, y_cols[0])[y_cols[0]].sum()
                    if others_sum > 0:
                        others_row = {x: 'Others', y_cols[0]: others_sum}
                        top_7 = pd.concat([top_7, pd.DataFrame([others_row])], ignore_index=True)
                    working = top_7
                
                labels = working[x].astype(str)
                values = working[y_cols[0]]
                colors = plt.cm.Set2(np.linspace(0, 1, len(working)))
                
                wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%', 
                                                colors=colors, startangle=90)
                
                # Improve text appearance
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')
                    
                ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
                
            elif chart_type == "donut" and x and y_cols and len(y_cols) > 0:
                # Matplotlib donut chart
                labels = working[x].astype(str)
                values = working[y_cols[0]]
                
                # Create donut chart by using pie with white center
                wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%', 
                                                colors=plt.cm.Set3.colors, startangle=90)
                
                # Add white circle in center to create donut effect
                centre_circle = plt.Circle((0,0), 0.4, fc='white')
                ax.add_artist(centre_circle)
                ax.set_title(title)
            elif chart_type == "bar" and x and y_cols and len(y_cols) > 0:
                # Limit bars for readability
                if len(working) > 15:
                    working = working.nlargest(15, y_cols[0])
                    title += " (Top 15)"
                
                col = y_cols[0]
                bars = ax.bar(working[x].astype(str), working[col], 
                            color=plt.cm.Set1(np.linspace(0, 1, len(working))))
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.annotate(f'{height:,.0f}',
                              xy=(bar.get_x() + bar.get_width() / 2, height),
                              xytext=(0, 3),  # 3 points vertical offset
                              textcoords="offset points",
                              ha='center', va='bottom', fontsize=9)
                
                ax.set_xlabel(x, fontweight='bold')
                ax.set_ylabel(col, fontweight='bold')
                
                # Rotate x-axis labels if too many
                if len(working) > 5:
                    plt.xticks(rotation=45, ha='right')
            else:
                # Line chart fallback
                if y_cols and len(y_cols) > 0:
                    colors = plt.cm.Set1(np.linspace(0, 1, len(y_cols)))
                    for i, col in enumerate(y_cols):
                        ax.plot(working[x] if x in working.columns else range(len(working)), 
                               working[col], marker="o", linewidth=2.5, 
                               label=col, color=colors[i], markersize=6)
                    
                    if len(y_cols) > 1:
                        ax.legend(frameon=True, fancybox=True, shadow=True)
            
            # Enhanced styling
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
            if x and chart_type not in ["pie", "donut"]:
                ax.set_xlabel(x, fontweight='bold')
            if chart_type not in ["pie", "donut"]:
                if not ax.get_ylabel():
                    ax.set_ylabel("Value", fontweight='bold')
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            return fig

    @traceable(name="viz.plan_and_render")
    def plan_and_render(self, question: str, df: pd.DataFrame) -> Dict[str, Any]:
        spec = self.plan_chart(question, df)
        fig = self.render_from_spec(df, spec)
        return {"spec": spec, "figure": fig}
