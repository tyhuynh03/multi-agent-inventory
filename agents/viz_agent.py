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
You are a data visualization planner. Given a user question and a pandas table (with columns and samples), output a JSON spec for the best chart.

Rules:
- chart_type: one of ["line", "bar"]
- x: string column name for x-axis
- y: array of 1-3 numeric column names
- group_by: optional string column for series separation (e.g., product, category)
- agg: aggregation for y if grouping is needed, one of ["sum", "avg", "mean"]
- title: short title

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
        except Exception:
            # Fallback spec
            spec = {"chart_type": "line", "x": "Date", "y": [df.select_dtypes(np.number).columns.tolist()[:1][0]] if df.select_dtypes(np.number).shape[1] else [], "title": "Auto Chart"}
        return spec

    @traceable(name="viz.render_from_spec")
    def render_from_spec(self, df: pd.DataFrame, spec: Dict[str, Any]) -> Optional[go.Figure]:
        if df is None or df.empty:
            return None
        chart_type = spec.get("chart_type", "line")
        x = spec.get("x")
        y_cols = spec.get("y", [])
        group_by = spec.get("group_by")
        agg = spec.get("agg", "sum").lower()
        title = spec.get("title", "Chart")

        if x in df.columns:
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

        if group_by and group_by in working.columns and x and x in working.columns:
            agg_func = {col: ("mean" if agg in ("avg", "mean") else "sum") for col in y_cols}
            working = (
                working.groupby([x, group_by], as_index=False)
                .agg(agg_func)
            )

        # Plotly rendering
        try:
            if chart_type == "bar" and x and y_cols:
                if len(y_cols) > 1:
                    df_long = working.melt(id_vars=[x], value_vars=y_cols, var_name="Series", value_name="Value")
                    fig = px.bar(df_long, x=x, y="Value", color="Series", barmode="group", title=title)
                else:
                    col = y_cols[0]
                    if group_by and group_by in working.columns:
                        fig = px.bar(working, x=x, y=col, color=group_by, barmode="group", title=title)
                    else:
                        fig = px.bar(working, x=x, y=col, title=title)
            else:
                # default line; if multiple y -> add each as a trace
                if x and y_cols:
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

            fig.update_layout(template="plotly_white")
            return fig
        except Exception:
            # Fallback to matplotlib if plotly fails
            fig, ax = plt.subplots(figsize=(10, 4))
            if chart_type == "bar" and x and y_cols:
                col = y_cols[0]
                ax.bar(working[x].astype(str), working[col])
            else:
                for col in y_cols:
                    ax.plot(working[x], working[col], marker="o", linewidth=1.2, label=col)
            ax.set_title(title)
            if x:
                ax.set_xlabel(x)
            ax.set_ylabel("Value")
            ax.grid(True, alpha=0.3)
            if len(ax.lines) + len(ax.patches) > 1:
                ax.legend()
            return fig

    @traceable(name="viz.plan_and_render")
    def plan_and_render(self, question: str, df: pd.DataFrame) -> Dict[str, Any]:
        spec = self.plan_chart(question, df)
        fig = self.render_from_spec(df, spec)
        return {"spec": spec, "figure": fig}
