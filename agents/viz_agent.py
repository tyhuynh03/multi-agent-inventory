from typing import Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from utils.logger import traceable


@traceable(name="viz.render")
def render_auto_chart(df: pd.DataFrame) -> Optional[plt.Figure]:
    if df is None or df.empty:
        return None

    fig = None

    # Ưu tiên chuỗi thời gian nếu có cột ngày/giờ
    time_candidates = [c for c in df.columns if c.lower() in ("date", "d", "time", "timestamp")] \
        or [c for c in df.columns if "date" in c.lower()]

    x_col = None
    if time_candidates:
        x_col = time_candidates[0]
        try:
            df[x_col] = pd.to_datetime(df[x_col], errors="coerce")
        except Exception:
            x_col = None

    if x_col and df.select_dtypes(np.number).shape[1] >= 1:
        num_cols = df.select_dtypes(np.number).columns.tolist()[:2]
        fig, ax = plt.subplots(figsize=(10, 4))
        for col in num_cols:
            ax.plot(df[x_col], df[col], marker="o", linewidth=1.2, label=col)
        ax.set_title("Auto visualization (time series)")
        ax.set_xlabel(x_col)
        ax.set_ylabel("Value")
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig

    # Fallback: bar chart theo cột phân loại đầu + cột số đầu
    numeric_cols = df.select_dtypes(np.number).columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols]
    if numeric_cols and categorical_cols:
        y = numeric_cols[0]
        x = categorical_cols[0]
        top = df.groupby(x, as_index=False)[y].sum().nlargest(20, y)
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(top[x].astype(str), top[y])
        ax.set_title(f"Auto visualization: {y} by {x}")
        ax.set_xticklabels(top[x].astype(str), rotation=45, ha="right")
        ax.set_ylabel(y)
        return fig

    return None
