import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="Enterprise RFM Intelligence Dashboard", layout="wide")

st.title("📊 Enterprise Customer RFM & Product Intelligence Dashboard")

st.markdown("""
This dashboard provides:
• Percentile-based RFM segmentation  
• Product intelligence by category  
• Revenue projections  
• Timeframe clarity  
""")

# ---------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------

uploaded_file = st.file_uploader("Upload Order Dataset", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    required_cols = [
        "user_id",
        "order_id",
        "order_date",
        "category",
        "product_name",
        "quantity",
        "order_value",
        "discount_given"
    ]

    # Dataset Structure Validation
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Dataset must include columns: {required_cols}")
        st.stop()

    df["order_date"] = pd.to_datetime(df["order_date"])

    # ---------------------------------------------------
    # TIMEFRAME DISPLAY
    # ---------------------------------------------------

    data_start = df["order_date"].min()
    data_end = df["order_date"].max()

    st.subheader("📅 Data Timeframe")

    col1, col2 = st.columns(2)
    col1.metric("Data Start Date", data_start.date())
    col2.metric("Data End Date", data_end.date())

    # ---------------------------------------------------
    # ANALYSIS DATE SELECTION
    # ---------------------------------------------------

    analysis_date = st.date_input(
        "Select Analysis Date",
        value=datetime.today(),  # Allow today's date
        min_value=data_start,
        max_value=datetime.today()
    )

    snapshot_date = pd.to_datetime(analysis_date)

    st.info(f"Recency calculated using analysis date: {snapshot_date.date()}")

    # ---------------------------------------------------
    # RFM CALCULATION
    # ---------------------------------------------------

    rfm = df.groupby("user_id").agg({
        "order_date": lambda x: (snapshot_date - x.max()).days,
        "order_id": "count",
        "order_value": "sum"
    }).reset_index()

    rfm.columns = ["user_id", "Recency", "Frequency", "Monetary"]

    # Percentile Scoring
    rfm["R_Score"] = pd.qcut(rfm["Recency"], 5, labels=[5,4,3,2,1]).astype(int)
    rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
    rfm["M_Score"] = pd.qcut(rfm["Monetary"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)

    rfm["RFM_Score"] = (
        rfm["R_Score"].astype(str) +
        rfm["F_Score"].astype(str) +
        rfm["M_Score"].astype(str)
    )

    # Segmentation
    def segment(row):
        if row["R_Score"] >= 4 and row["F_Score"] >= 4 and row["M_Score"] >= 4:
            return "Champion Customer"
        elif row["F_Score"] >= 4 and row["R_Score"] >= 3:
            return "Loyal Customer"
        elif row["R_Score"] >= 3:
            return "Fence Sitter"
        elif row["R_Score"] == 2:
            return "At Risk Customer"
        else:
            return "Churned Customer"

    rfm["Segment"] = rfm.apply(segment, axis=1)

    # ---------------------------------------------------
    # KPI SECTION
    # ---------------------------------------------------

    st.subheader("📌 Key RFM KPIs")

    total_customers = len(rfm)
    avg_recency = round(rfm["Recency"].mean(), 1)
    avg_frequency = round(rfm["Frequency"].mean(), 1)
    avg_monetary = round(rfm["Monetary"].mean(), 0)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Customers", total_customers)
    col2.metric("Avg Recency (Days)", avg_recency)
    col3.metric("Avg Frequency", avg_frequency)
    col4.metric("Avg Monetary (₹)", avg_monetary)

    # ---------------------------------------------------
    # MOST SOLD PRODUCT PER CATEGORY
    # ---------------------------------------------------

    st.subheader("🛒 Most Sold Product by Category")

    category_sales = df.groupby(
        ["category", "product_name"]
    ).agg({
        "quantity": "sum",
        "order_value": "sum"
    }).reset_index()

    top_products = category_sales.loc[
        category_sales.groupby("category")["quantity"].idxmax()
    ]

    st.dataframe(top_products, use_container_width=True)

    # ---------------------------------------------------
    # REVENUE TREND
    # ---------------------------------------------------

    monthly = df.groupby(
        pd.Grouper(key="order_date", freq="M")
    )["order_value"].sum().reset_index()

    fig_line = px.line(
        monthly,
        x="order_date",
        y="order_value",
        title="Monthly Revenue Trend"
    )

    st.plotly_chart(fig_line, use_container_width=True)

    # ---------------------------------------------------
    # REVENUE PROJECTION
    # ---------------------------------------------------

    st.subheader("📈 Revenue Projection (Trend Continuation)")

    monthly["Month_Number"] = range(1, len(monthly) + 1)

    slope, intercept = np.polyfit(monthly["Month_Number"], monthly["order_value"], 1)

    next_month = len(monthly) + 1
    projected_revenue = slope * next_month + intercept

    st.metric("Projected Next Month Revenue (₹)", f"{projected_revenue:,.0f}")

    # ---------------------------------------------------
    # SEGMENT REVENUE CONTRIBUTION
    # ---------------------------------------------------

    st.subheader("💰 Revenue Contribution by Segment")

    seg_revenue = rfm.merge(
        df.groupby("user_id")["order_value"].sum().reset_index(),
        on="user_id"
    )

    seg_rev_summary = seg_revenue.groupby("Segment")["order_value"].sum().reset_index()

    fig_seg = px.bar(
        seg_rev_summary,
        x="Segment",
        y="order_value",
        title="Revenue by Customer Segment"
    )

    st.plotly_chart(fig_seg, use_container_width=True)

    # ---------------------------------------------------
    # RFM DISTRIBUTION
    # ---------------------------------------------------

    st.subheader("📊 RFM Score Distribution")

    colA, colB, colC = st.columns(3)

    colA.plotly_chart(px.histogram(rfm, x="R_Score", title="Recency Score"), use_container_width=True)
    colB.plotly_chart(px.histogram(rfm, x="F_Score", title="Frequency Score"), use_container_width=True)
    colC.plotly_chart(px.histogram(rfm, x="M_Score", title="Monetary Score"), use_container_width=True)

    st.caption(f"Dashboard generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")