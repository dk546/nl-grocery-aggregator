"""
Modern chart system for consistent visualization across the application.

Provides reusable chart builders with a unified, minimal theme.
All charts share the same quiet, modern aesthetic with muted colors.
"""

from typing import Dict, List, Optional, Union, Tuple
import pandas as pd
import altair as alt
import streamlit as st


# Modern color palette (muted, accessible)
COLORS = {
    "healthy": "#22c55e",      # Muted green
    "neutral": "#94a3b8",      # Blue-gray
    "less_healthy": "#ef4444", # Amber/red
    "primary": "#3b82f6",      # Muted blue
    "secondary": "#64748b",    # Slate gray
    "text": "#1e293b",         # Dark slate
    "background": "#ffffff",   # White
    "grid": "#f1f5f9",         # Very light gray
}


def apply_modern_theme(chart: alt.Chart) -> alt.Chart:
    """
    Apply a unified modern theme to an Altair chart.
    
    Args:
        chart: Altair chart to theme
        
    Returns:
        Themed chart with consistent styling
    """
    return chart.configure_view(
        strokeWidth=0,           # No borders
        fill=COLORS["background"],
    ).configure_axis(
        grid=True,
        gridColor=COLORS["grid"],
        gridOpacity=0.3,
        gridWidth=0.5,
        domain=False,            # No axis lines
        domainWidth=0,
        labelColor=COLORS["text"],
        labelFontSize=11,
        titleColor=COLORS["text"],
        titleFontSize=12,
        titleFontWeight="normal",
        ticks=False,             # No tick marks
    ).configure_legend(
        titleFontSize=11,
        labelFontSize=10,
        labelColor=COLORS["text"],
        titleColor=COLORS["text"],
        strokeColor=COLORS["grid"],
        padding=8,
        cornerRadius=4,
    ).configure(
        padding={"left": 10, "top": 10, "right": 10, "bottom": 10},
        background=COLORS["background"],
    )


def build_radial_score(score: float, label: str, max_score: float = 100) -> alt.Chart:
    """
    Build a radial progress ring chart (hero score display).
    
    Args:
        score: Current score value (0-100)
        label: Label text to display in center
        max_score: Maximum possible score (default 100)
        
    Returns:
        Themed radial progress chart
    """
    # Normalize score to 0-1 range
    normalized_score = min(1.0, max(0.0, score / max_score))
    
    # Create data for the ring
    data = pd.DataFrame({
        "value": [normalized_score, 1.0 - normalized_score],
        "category": ["filled", "empty"],
        "start": [0, normalized_score],
        "end": [normalized_score, 1.0]
    })
    
    # Determine color based on score
    if score >= 80:
        color = COLORS["healthy"]
    elif score >= 60:
        color = "#fbbf24"  # Amber/yellow
    elif score >= 40:
        color = "#fb923c"  # Orange
    else:
        color = COLORS["less_healthy"]
    
    # Base chart (ring)
    base = alt.Chart(data).mark_arc(
        innerRadius=80,
        outerRadius=100,
        strokeWidth=0
    ).encode(
        theta=alt.Theta("value:Q", stack=True),
        color=alt.Color(
            "category:N",
            scale=alt.Scale(
                domain=["filled", "empty"],
                range=[color, "#e2e8f0"]  # Filled = score color, empty = light gray
            ),
            legend=None
        ),
        tooltip=alt.Tooltip("value:Q", format=".0%")
    ).properties(
        width=300,
        height=300
    )
    
    # Add text in center (overlay on the arc)
    text_data = pd.DataFrame({
        "x": [0],
        "y": [0],
        "label": [f"{int(score)}"],
        "subtitle": [label]
    })
    
    text_chart = alt.Chart(text_data).mark_text(
        align="center",
        baseline="middle",
        fontSize=36,
        fontWeight="bold",
        color=COLORS["text"],
        dx=0,
        dy=-10
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[-1, 1])),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[-1, 1])),
        text="label:N"
    ).properties(
        width=300,
        height=300
    )
    
    subtitle_chart = alt.Chart(text_data).mark_text(
        align="center",
        baseline="middle",
        fontSize=12,
        color=COLORS["secondary"],
        dx=0,
        dy=15
    ).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[-1, 1])),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[-1, 1])),
        text="subtitle:N"
    ).properties(
        width=300,
        height=300
    )
    
    chart = (base + text_chart + subtitle_chart).resolve_scale(color="independent")
    return apply_modern_theme(chart)


def build_donut_composition(counts_or_pct: Union[Dict[str, int], pd.DataFrame]) -> alt.Chart:
    """
    Build a minimal donut chart for composition breakdown.
    
    Args:
        counts_or_pct: Dict with segment names as keys and counts as values,
                      or DataFrame with 'segment' and 'count' columns
                      
    Returns:
        Themed donut chart
    """
    if isinstance(counts_or_pct, dict):
        df = pd.DataFrame([
            {"segment": k, "count": v} for k, v in counts_or_pct.items() if v > 0
        ])
    else:
        df = counts_or_pct.copy()
        df = df[df["count"] > 0]
    
    if df.empty:
        # Return empty chart placeholder
        empty_data = pd.DataFrame({"value": [1], "segment": ["No data"]})
        chart = alt.Chart(empty_data).mark_arc(innerRadius=60, outerRadius=100).encode(
            theta="value:Q",
            color=alt.Color("segment:N", scale=alt.Scale(domain=["No data"], range=[COLORS["grid"]]), legend=None)
        )
        return apply_modern_theme(chart)
    
    # Calculate percentages
    total = df["count"].sum()
    df["percent"] = df["count"] / total
    
    # Map segment names to colors (flexible mapping)
    color_map = {
        "Healthy": COLORS["healthy"],
        "🥦 Healthy": COLORS["healthy"],
        "healthy": COLORS["healthy"],
        "Neutral": COLORS["neutral"],
        "⚪ Neutral": COLORS["neutral"],
        "neutral": COLORS["neutral"],
        "Less Healthy": COLORS["less_healthy"],
        "⚠️ Less Healthy": COLORS["less_healthy"],
        "unhealthy": COLORS["less_healthy"],
    }
    
    # Get unique segments and assign colors
    segments = df["segment"].unique()
    colors = [color_map.get(str(s), COLORS["secondary"]) for s in segments]
    
    # Base donut
    chart = alt.Chart(df).mark_arc(
        innerRadius=60,
        outerRadius=100,
        strokeWidth=2,
        stroke=COLORS["background"]
    ).encode(
        theta=alt.Theta("count:Q", stack=True),
        color=alt.Color(
            "segment:N",
            scale=alt.Scale(domain=segments.tolist(), range=colors),
            legend=alt.Legend(title=None, orient="right", labelFontSize=11)
        ),
        tooltip=[
            alt.Tooltip("segment:N", title="Category"),
            alt.Tooltip("count:Q", title="Count"),
            alt.Tooltip("percent:Q", format=".0%", title="Share")
        ]
    ).properties(
        width=350,
        height=350
    )
    
    # Add percentage labels inside segments
    text = alt.Chart(df).mark_text(
        radius=110,
        size=12,
        align="center",
        baseline="middle",
        color="white",
        fontWeight="medium"
    ).encode(
        theta=alt.Theta("count:Q", stack=True),
        text=alt.Text("percent:Q", format=".0%")
    )
    
    return apply_modern_theme(chart + text)


def build_diverging_category_bars(data: Union[List[Dict], pd.DataFrame]) -> alt.Chart:
    """
    Build horizontal diverging bars showing healthy vs less healthy by category.
    
    Args:
        data: List of dicts or DataFrame with columns:
              - category (str)
              - healthy_pct (float, 0-1 or 0-100)
              - less_healthy_pct (float, 0-1 or 0-100)
              Optional: neutral_pct
              
    Returns:
        Themed diverging bar chart
    """
    if isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()
    
    if df.empty or "category" not in df.columns:
        # Return empty placeholder
        empty_df = pd.DataFrame({"category": ["No data"], "value": [0], "type": ["healthy"]})
        chart = alt.Chart(empty_df).mark_bar().encode(
            x="value:Q",
            y="category:N"
        )
        return apply_modern_theme(chart)
    
    # Normalize percentages to 0-1 if they appear to be 0-100
    if "healthy_pct" in df.columns and df["healthy_pct"].max() > 1:
        df["healthy_pct"] = df["healthy_pct"] / 100
    if "less_healthy_pct" in df.columns and df["less_healthy_pct"].max() > 1:
        df["less_healthy_pct"] = df["less_healthy_pct"] / 100
    
    # Create long format for stacking
    chart_data = []
    for _, row in df.iterrows():
        category = row["category"]
        # Healthy goes to the right (positive)
        chart_data.append({
            "category": category,
            "value": row.get("healthy_pct", 0),
            "type": "Healthy",
            "order": 1
        })
        # Less healthy goes to the left (negative)
        chart_data.append({
            "category": category,
            "value": -row.get("less_healthy_pct", 0),
            "type": "Less Healthy",
            "order": 2
        })
    
    df_long = pd.DataFrame(chart_data)
    
    # Sort by total absolute value (descending)
    category_order = df_long.groupby("category")["value"].apply(lambda x: abs(x).sum()).sort_values(ascending=False).index.tolist()
    
    chart = alt.Chart(df_long).mark_bar(
        cornerRadiusTopRight=3,
        cornerRadiusBottomRight=3
    ).encode(
        x=alt.X(
            "value:Q",
            axis=alt.Axis(
                title="Proportion",
                format=".0%",
                labelExpr="abs(datum.value) > 0.05 ? datum.label : ''"  # Hide small labels
            ),
            scale=alt.Scale(domain=[-1, 1])
        ),
        y=alt.Y(
            "category:N",
            sort=category_order,
            axis=alt.Axis(title=None),
            spacing=8
        ),
        color=alt.Color(
            "type:N",
            scale=alt.Scale(
                domain=["Healthy", "Less Healthy"],
                range=[COLORS["healthy"], COLORS["less_healthy"]]
            ),
            legend=alt.Legend(title=None, orient="top-right")
        ),
        tooltip=[
            alt.Tooltip("category:N", title="Category"),
            alt.Tooltip("type:N", title="Type"),
            alt.Tooltip("value:Q", format=".0%", title="Proportion")
        ],
        order="order:O"
    ).properties(
        height=300
    )
    
    # Add center line
    rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(
        stroke=COLORS["grid"],
        strokeWidth=1,
        strokeDash=[3, 3]
    ).encode(x="x:Q")
    
    return apply_modern_theme(chart + rule)


def build_funnel(steps: List[Tuple[str, int]]) -> alt.Chart:
    """
    Build a horizontal funnel chart (stepped bars) showing conversion flow.
    
    Args:
        steps: List of tuples (step_name, count) in order from first to last
               Example: [("Search", 100), ("Add to cart", 50), ("Export", 20)]
               
    Returns:
        Themed funnel chart
    """
    if not steps:
        return apply_modern_theme(alt.Chart(pd.DataFrame()).mark_bar())
    
    df = pd.DataFrame(steps, columns=["step", "count"])
    
    # Calculate widths as percentages of first step
    max_count = df["count"].max()
    if max_count == 0:
        df["width_pct"] = 0
    else:
        df["width_pct"] = df["count"] / max_count
    
    # Create stepped appearance (each bar is narrower)
    chart = alt.Chart(df).mark_bar(
        cornerRadius=4
    ).encode(
        x=alt.X(
            "count:Q",
            axis=alt.Axis(title="Count", grid=False),
            scale=alt.Scale(domain=[0, max_count * 1.1])
        ),
        y=alt.Y(
            "step:N",
            sort=df["step"].tolist(),  # Maintain order
            axis=alt.Axis(title=None),
            spacing=12
        ),
        color=alt.Color(
            "step:N",
            scale=alt.Scale(
                domain=df["step"].tolist(),
                range=[COLORS["primary"]] * len(df)  # Use primary color with varying opacity
            ),
            legend=None
        ),
        tooltip=[
            alt.Tooltip("step:N", title="Step"),
            alt.Tooltip("count:Q", title="Count"),
            alt.Tooltip("width_pct:Q", format=".0%", title="Conversion")
        ]
    ).properties(
        height=200
    )
    
    return apply_modern_theme(chart)


def build_time_series(df: pd.DataFrame, x_col: str, y_col: str, time_window: str = "hour") -> alt.Chart:
    """
    Build a smooth line/area chart for time series data.
    
    Args:
        df: DataFrame with time and value columns
        x_col: Column name for time/x axis
        y_col: Column name for values/y axis
        time_window: Time granularity ("hour", "day", etc.) for formatting
        
    Returns:
        Themed time series chart
    """
    if df.empty or x_col not in df.columns or y_col not in df.columns:
        return apply_modern_theme(alt.Chart(pd.DataFrame()).mark_line())
    
    # Ensure x_col is datetime if it's a string
    if df[x_col].dtype == "object":
        df[x_col] = pd.to_datetime(df[x_col], errors="coerce")
    
    chart = alt.Chart(df).mark_area(
        fill=COLORS["primary"],
        fillOpacity=0.3,
        stroke=COLORS["primary"],
        strokeWidth=2,
        interpolate="monotone"  # Smooth curve
    ).encode(
        x=alt.X(
            f"{x_col}:T",
            axis=alt.Axis(
                title=None,
                format="%H:%M" if time_window == "hour" else "%Y-%m-%d",
                labelAngle=-45
            )
        ),
        y=alt.Y(
            f"{y_col}:Q",
            axis=alt.Axis(title="Events", grid=True)
        ),
        tooltip=[
            alt.Tooltip(f"{x_col}:T", title="Time", format="%Y-%m-%d %H:%M"),
            alt.Tooltip(f"{y_col}:Q", title="Count")
        ]
    ).properties(
        height=300
    )
    
    return apply_modern_theme(chart)


def build_event_mix_stacked(data: Union[List[Dict], pd.DataFrame]) -> alt.Chart:
    """
    Build a horizontal stacked bar chart showing event type proportions.
    
    Args:
        data: List of dicts or DataFrame with columns:
              - event_type (str)
              - count (int)
              Or a Series/index with event_type and counts as values
              
    Returns:
        Themed stacked bar chart
    """
    if isinstance(data, dict):
        # Convert dict to DataFrame
        df = pd.DataFrame([
            {"event_type": k, "count": v} for k, v in data.items()
        ])
    elif isinstance(data, list):
        df = pd.DataFrame(data)
    else:
        df = data.copy()
    
    if df.empty or "event_type" not in df.columns:
        return apply_modern_theme(alt.Chart(pd.DataFrame()).mark_bar())
    
    # Sort by count descending
    df = df.sort_values("count", ascending=False)
    
    # Calculate total for normalization
    total = df["count"].sum()
    if total == 0:
        df["percent"] = 0
    else:
        df["percent"] = df["count"] / total
    
    chart = alt.Chart(df).mark_bar(
        cornerRadius=3
    ).encode(
        x=alt.X(
            "percent:Q",
            axis=alt.Axis(title="Proportion", format=".0%"),
            stack="normalize"
        ),
        y=alt.Y(
            "event_type:N",
            sort=df["event_type"].tolist(),
            axis=alt.Axis(title=None),
            spacing=8
        ),
        color=alt.Color(
            "event_type:N",
            scale=alt.Scale(
                domain=df["event_type"].tolist(),
                range=[COLORS["primary"], COLORS["secondary"], COLORS["healthy"], COLORS["less_healthy"]]
            ),
            legend=alt.Legend(title=None, orient="right")
        ),
        tooltip=[
            alt.Tooltip("event_type:N", title="Event Type"),
            alt.Tooltip("count:Q", title="Count"),
            alt.Tooltip("percent:Q", format=".0%", title="Proportion")
        ]
    ).properties(
        height=300
    )
    
    return apply_modern_theme(chart)

