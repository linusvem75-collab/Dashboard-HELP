"""
Retail Sales Intelligence Dashboard
=======================================
Streamlit app version of the BI analysis: temporal trends, category
profitability, customer segments, pricing sensitivity, and regional spread.

Run locally:  streamlit run app.py

NOTE: This is a deliberately single-file app. Everything data_prep.py used
to hold now lives inline below — Streamlit Cloud (and most simple deploy
targets) only ever see whatever files actually got committed to the repo,
and a second local file is the #1 cause of "ModuleNotFoundError" on deploy
even when the app runs fine locally. One file, nothing to leave behind.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------------
# DATA LOADING & CLEANING (formerly data_prep.py — inlined so the app
# has zero cross-file dependencies)
# ------------------------------------------------------------------

@st.cache_data(show_spinner="Loading and cleaning data...")
def load_and_clean(file_or_path) -> pd.DataFrame:
    # --- load with encoding fallback ---
    try:
        df = pd.read_csv(file_or_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(file_or_path, encoding="latin1")

    # --- standardize column names ---
    df.columns = [c.strip() for c in df.columns]

    # --- trim whitespace on text columns (fixes the 1,612 -> 17 sub-category issue) ---
    text_cols = df.select_dtypes(include="object").columns
    for c in text_cols:
        df[c] = df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

    # --- Order ID as text (identifier, not a quantity) ---
    if "Order ID" in df.columns:
        df["Order ID"] = df["Order ID"].astype(str)

    # --- dates ---
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], errors="coerce")
    df["Year"] = df["Order Date"].dt.year
    df["Quarter"] = df["Order Date"].dt.quarter
    df["Month"] = df["Order Date"].dt.month
    df["YearMonth"] = df["Order Date"].dt.to_period("M").astype(str)
    df["YearQuarter"] = df["Year"].astype(str) + "-Q" + df["Quarter"].astype(str)
    df["Lead Time (days)"] = (df["Ship Date"] - df["Order Date"]).dt.days

    # --- region split ---
    if "Region & District" in df.columns:
        split = df["Region & District"].str.split(",", n=1, expand=True)
        df["Region"] = split[0].str.strip().str.title()
        df["District"] = split[1].str.strip().str.title() if split.shape[1] > 1 else np.nan

    # --- impute the only numeric column with missingness (median, per earlier normality test) ---
    if "Product Base Margin" in df.columns:
        df["Product Base Margin"] = df["Product Base Margin"].fillna(df["Product Base Margin"].median())

    # --- derived financial fields ---
    df["Margin %"] = np.where(df["Sales"] != 0, df["Profit"] / df["Sales"] * 100, np.nan)

    # --- proper-case a few categorical columns for display ---
    for c in ["Customer First Name", "Customer Last Name", "Order Priority",
              "Customer Segment", "Product Category", "Product Sub-Category",
              "Product Container"]:
        if c in df.columns:
            df[c] = df[c].str.title()

    return df


def kpi_summary(df: pd.DataFrame) -> dict:
    total_sales = df["Sales"].sum()
    total_profit = df["Profit"].sum()
    margin = total_profit / total_sales * 100 if total_sales else 0
    orders = df["Order ID"].nunique()
    aov = total_sales / orders if orders else 0
    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "margin": margin,
        "orders": orders,
        "aov": aov,
    }

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Retail Sales Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY = "#2a78d6"
GREEN = "#1baf7a"
AMBER = "#eda100"
RED = "#e34948"
CATEGORY_COLORS = {"Technology": PRIMARY, "Furniture": GREEN, "Office Supplies": AMBER}

# ------------------------------------------------------------------
# SIDEBAR — DATA SOURCE + FILTERS
# ------------------------------------------------------------------
st.sidebar.title("📊 Retail Sales Dashboard")

uploaded = st.sidebar.file_uploader("Upload a CSV to replace the sample dataset", type=["csv"])
data_source = uploaded if uploaded is not None else "data/mock_dataset.csv"

df = load_and_clean(data_source)

st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

year_range = st.sidebar.slider(
    "Order year range",
    int(df["Year"].min()), int(df["Year"].max()),
    (int(df["Year"].min()), int(df["Year"].max())),
)

categories = st.sidebar.multiselect(
    "Product category", options=sorted(df["Product Category"].dropna().unique()),
    default=sorted(df["Product Category"].dropna().unique()),
)

segments = st.sidebar.multiselect(
    "Customer segment", options=sorted(df["Customer Segment"].dropna().unique()),
    default=sorted(df["Customer Segment"].dropna().unique()),
)

regions = st.sidebar.multiselect(
    "Region", options=sorted(df["Region"].dropna().unique()),
    default=sorted(df["Region"].dropna().unique()),
)

mask = (
    df["Year"].between(*year_range)
    & df["Product Category"].isin(categories)
    & df["Customer Segment"].isin(segments)
    & df["Region"].isin(regions)
)
fdf = df[mask].copy()

st.sidebar.markdown("---")
st.sidebar.caption(f"{len(fdf):,} of {len(df):,} line items match current filters.")

if fdf.empty:
    st.warning("No data matches the current filter selection — widen your filters in the sidebar.")
    st.stop()

# ------------------------------------------------------------------
# HEADER + KPIs
# ------------------------------------------------------------------
st.title("Retail Sales Intelligence Dashboard")
st.caption("Interactive version of the sales performance report — filter with the sidebar, explore each tab below.")

k = kpi_summary(fdf)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Sales", f"${k['total_sales']:,.0f}")
c2.metric("Total Profit", f"${k['total_profit']:,.0f}")
c3.metric("Profit Margin", f"{k['margin']:.1f}%")
c4.metric("Orders", f"{k['orders']:,}")
c5.metric("Avg Order Value", f"${k['aov']:,.0f}")

st.markdown("---")

# ------------------------------------------------------------------
# TABS
# ------------------------------------------------------------------
tab_trends, tab_category, tab_segment, tab_pricing, tab_regional, tab_data = st.tabs(
    ["📈 Temporal Trends", "📦 Category & Profitability", "👥 Customer Segments",
     "🏷️ Pricing & Discounts", "🗺️ Regional Spread", "🔍 Data Explorer"]
)

# ============================================================
# TAB 1 — TEMPORAL TRENDS
# ============================================================
with tab_trends:
    st.subheader("Monthly Sales")
    monthly = fdf.groupby("YearMonth", as_index=False)["Sales"].sum().sort_values("YearMonth")
    fig = px.area(monthly, x="YearMonth", y="Sales", color_discrete_sequence=[PRIMARY])
    fig.update_layout(yaxis_tickprefix="$", xaxis_title=None, yaxis_title="Sales", height=380)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Sales by Product Category")
    monthly_cat = fdf.groupby(["YearMonth", "Product Category"], as_index=False)["Sales"].sum()
    fig = px.line(monthly_cat, x="YearMonth", y="Sales", color="Product Category",
                   color_discrete_map=CATEGORY_COLORS)
    fig.update_layout(yaxis_tickprefix="$", xaxis_title=None, height=400)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Quarterly Sales")
        q = fdf.groupby("YearQuarter", as_index=False).agg(Sales=("Sales", "sum"))
        fig = px.bar(q, x="YearQuarter", y="Sales", color_discrete_sequence=[PRIMARY])
        fig.update_layout(yaxis_tickprefix="$", xaxis_title=None, height=350)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Quarterly Profit Margin")
        q2 = fdf.groupby("YearQuarter", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
        q2["Margin %"] = q2["Profit"] / q2["Sales"] * 100
        fig = px.line(q2, x="YearQuarter", y="Margin %", markers=True, color_discrete_sequence=[GREEN])
        fig.add_hline(y=0, line_dash="dash", line_color=RED)
        fig.update_layout(xaxis_title=None, height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.info("💡 Every year follows the same seasonal shape: a soft Q1, gradual build, and a sharp Q4 spike in both "
            "sales and margin. Q1 is where the profitability baseline is most fragile.")

# ============================================================
# TAB 2 — CATEGORY & PROFITABILITY
# ============================================================
with tab_category:
    st.subheader("Sales & Profit by Category")
    cat = fdf.groupby("Product Category", as_index=False).agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
    cat["Margin %"] = (cat["Profit"] / cat["Sales"] * 100).round(2)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(cat.sort_values("Sales", ascending=False).style.format(
            {"Sales": "${:,.0f}", "Profit": "${:,.0f}", "Margin %": "{:.1f}%"}), use_container_width=True, hide_index=True)
    with col2:
        fig = px.bar(cat, x="Product Category", y=["Sales", "Profit"], barmode="group",
                      color_discrete_sequence=[PRIMARY, GREEN])
        fig.update_layout(yaxis_tickprefix="$", height=320)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Profit Distribution by Category")
    fig = px.box(fdf, x="Product Category", y="Profit", color="Product Category",
                  color_discrete_map=CATEGORY_COLORS, points=False)
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Box shows the interquartile range; extreme outliers are compressed by Plotly's default zoom — "
               "use the toolbar to zoom out and inspect full range.")

    st.subheader("Sub-Category Drill-Down")
    sub = fdf.groupby(["Product Category", "Product Sub-Category"], as_index=False).agg(
        Sales=("Sales", "sum"), Profit=("Profit", "sum"))
    sub["Margin %"] = (sub["Profit"] / sub["Sales"] * 100).round(2)
    sub = sub.sort_values("Sales", ascending=False)
    st.dataframe(sub.style.format({"Sales": "${:,.0f}", "Profit": "${:,.0f}", "Margin %": "{:.1f}%"})
                 .background_gradient(subset=["Margin %"], cmap="RdYlGn", vmin=-20, vmax=40),
                 use_container_width=True, hide_index=True, height=400)

    loss_leaders = sub[sub["Profit"] < 0]
    if not loss_leaders.empty:
        st.warning(f"⚠️ {len(loss_leaders)} sub-categor{'y' if len(loss_leaders)==1 else 'ies'} showing negative "
                   f"total profit despite real sales volume — potential loss leaders: "
                   f"{', '.join(loss_leaders['Product Sub-Category'].tolist())}.")

# ============================================================
# TAB 3 — CUSTOMER SEGMENTS
# ============================================================
with tab_segment:
    st.subheader("Order Size & Consistency by Segment")
    order_level = fdf.groupby(["Order ID", "Customer Segment"], as_index=False).agg(
        OrderSales=("Sales", "sum"), OrderProfit=("Profit", "sum"))
    seg = order_level.groupby("Customer Segment", as_index=False).agg(
        AvgOrderSales=("OrderSales", "mean"), StdOrderSales=("OrderSales", "std"),
        Orders=("Order ID", "nunique"), TotalSales=("OrderSales", "sum"), TotalProfit=("OrderProfit", "sum"))
    seg["CV"] = (seg["StdOrderSales"] / seg["AvgOrderSales"]).round(2)
    seg["Margin %"] = (seg["TotalProfit"] / seg["TotalSales"] * 100).round(2)
    seg = seg.sort_values("AvgOrderSales", ascending=False)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(seg[["Customer Segment", "AvgOrderSales", "CV", "TotalSales", "Margin %"]]
                     .rename(columns={"AvgOrderSales": "Avg Order Size", "CV": "Consistency (CV)",
                                       "TotalSales": "Total Sales"})
                     .style.format({"Avg Order Size": "${:,.0f}", "Total Sales": "${:,.0f}", "Margin %": "{:.1f}%"}),
                     use_container_width=True, hide_index=True)
        st.caption("Consistency (CV) = std dev ÷ mean order size. Lower = more consistent order-to-order.")
    with col2:
        fig = px.bar(seg, x="Customer Segment", y="AvgOrderSales", color="Customer Segment", height=340)
        fig.update_layout(yaxis_tickprefix="$", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Order Value Distribution by Segment")
    fig = px.violin(order_level, x="Customer Segment", y="OrderSales", box=True, points=False)
    fig.update_layout(yaxis_tickprefix="$", height=380, yaxis_range=[0, order_level["OrderSales"].quantile(0.95)])
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 4 — PRICING & DISCOUNTS
# ============================================================
with tab_pricing:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Unit Price vs Sales")
        sample = fdf.sample(min(2000, len(fdf)), random_state=42)
        fig = px.scatter(sample, x="UnitPrice", y="Sales", color="Product Category",
                          color_discrete_map=CATEGORY_COLORS, opacity=0.5)
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)
        corr = fdf["UnitPrice"].corr(fdf["Sales"])
        st.caption(f"Correlation (Unit Price vs Sales): **{corr:.2f}**")
    with col2:
        st.subheader("Discount vs Margin")
        sample2 = fdf.sample(min(2000, len(fdf)), random_state=42)
        fig = px.scatter(sample2, x="Discount", y="Margin %", color="Product Category",
                          color_discrete_map=CATEGORY_COLORS, opacity=0.5)
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.update_layout(height=380, yaxis_range=[-200, 200])
        st.plotly_chart(fig, use_container_width=True)
        corr2 = fdf["Discount"].corr(fdf["Margin %"])
        st.caption(f"Correlation (Discount vs Margin %): **{corr2:.2f}**")

    st.subheader("Median Margin by Discount Band")
    fdf["Discount Band"] = pd.cut(fdf["Discount"], bins=[-0.01, 0.02, 0.05, 0.08, 0.12, 0.30],
                                    labels=["0-2%", "2-5%", "5-8%", "8-12%", "12%+"])
    band = fdf.groupby("Discount Band", observed=True).agg(
        MedianMargin=("Margin %", "median"), Items=("Discount", "size")).reset_index()
    fig = px.bar(band, x="Discount Band", y="MedianMargin", color="MedianMargin",
                  color_continuous_scale=["#e34948", "#eda100", "#1baf7a"], text="Items")
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(yaxis_ticksuffix="%", height=350, coloraxis_showscale=False)
    fig.update_traces(texttemplate="n=%{text}", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 Discount level shows almost no correlation with sales volume, but median margin turns negative "
            "once discounts exceed ~8% — deeper discounting is giving away margin without a matching demand lift.")

# ============================================================
# TAB 5 — REGIONAL SPREAD
# ============================================================
with tab_regional:
    st.subheader("Regional Market Share Over Time")
    reg_year = fdf.groupby(["Year", "Region"], as_index=False)["Sales"].sum()
    reg_year["Share %"] = reg_year.groupby("Year")["Sales"].transform(lambda s: s / s.sum() * 100)
    fig = px.line(reg_year, x="Year", y="Share %", color="Region", markers=True)
    fig.update_layout(yaxis_ticksuffix="%", height=400)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sales by Region")
        reg_totals = fdf.groupby("Region", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False)
        fig = px.bar(reg_totals, x="Region", y="Sales", color="Region", height=340)
        fig.update_layout(yaxis_tickprefix="$", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Sales by District (Top 10)")
        dist_totals = fdf.groupby("District", as_index=False)["Sales"].sum().sort_values(
            "Sales", ascending=False).head(10)
        fig = px.bar(dist_totals, x="District", y="Sales", color_discrete_sequence=[PRIMARY], height=340)
        fig.update_layout(yaxis_tickprefix="$")
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 6 — DATA EXPLORER
# ============================================================
with tab_data:
    st.subheader("Filtered Data Explorer")
    st.caption("This reflects your current sidebar filters. Use the column headers to sort.")
    display_cols = ["Order ID", "Order Date", "Customer Segment", "Product Category",
                     "Product Sub-Category", "Region", "District", "Sales", "Profit", "Margin %"]
    display_cols = [c for c in display_cols if c in fdf.columns]
    st.dataframe(fdf[display_cols].sort_values("Order Date", ascending=False),
                 use_container_width=True, hide_index=True, height=450)

    csv = fdf.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download filtered data as CSV", csv, "filtered_sales_data.csv", "text/csv")

st.markdown("---")
st.caption("Built with Streamlit · Data: retail sales line items, 2010–2013")
