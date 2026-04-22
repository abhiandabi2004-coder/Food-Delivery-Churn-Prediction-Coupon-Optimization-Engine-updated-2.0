import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="AI-Powered RFM Dashboard", layout="wide")

st.title("📊 AI-Powered Customer RFM Intelligence Dashboard")

uploaded_file = st.file_uploader("Upload Order Data CSV", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    required_cols = [
        "user_id",
        "order_id",
        "order_date",
        "product_name",
        "order_value",
        "discount_given"
    ]

    if not all(col in df.columns for col in required_cols):
        st.error("CSV must contain required columns.")
        st.stop()

    # -----------------------------
    # Clean Date
    # -----------------------------
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date"])

    # -----------------------------
    # Analysis Date (FIXED)
    # -----------------------------
    analysis_date = st.date_input(
        "📅 Select Analysis Date",
        value=df["order_date"].max()
    )

    snapshot_date = pd.to_datetime(analysis_date)

    st.write(f"Recency calculated as: {snapshot_date.date()} - Last Order Date")

    # -----------------------------
    # RFM Calculation (RECALCULATED EVERY TIME)
    # -----------------------------
    rfm = df.groupby("user_id").agg({
        "order_date": lambda x: (snapshot_date - x.max()).days,
        "order_id": "count",
        "order_value": "sum"
    }).reset_index()

    rfm.columns = ["user_id", "Recency", "Frequency", "Monetary"]

    # -----------------------------
    # RFM Scoring
    # -----------------------------
    rfm["R_Score"] = pd.qcut(rfm["Recency"], 5, labels=[5,4,3,2,1]).astype(int)
    rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)
    rfm["M_Score"] = pd.qcut(rfm["Monetary"].rank(method="first"), 5, labels=[1,2,3,4,5]).astype(int)

    rfm["RFM_Score"] = (
        rfm["R_Score"].astype(str) +
        rfm["F_Score"].astype(str) +
        rfm["M_Score"].astype(str)
    )

    # -----------------------------
    # Segmentation
    # -----------------------------
    def segment(row):
        if row["R_Score"] >= 4 and row["F_Score"] >= 4:
            return "Champion"
        elif row["F_Score"] >= 4:
            return "Loyal"
        elif row["R_Score"] >= 3:
            return "Fence Sitter"
        elif row["R_Score"] == 2:
            return "At Risk"
        else:
            return "Churned"

    rfm["Segment"] = rfm.apply(segment, axis=1)

    # -----------------------------
    # 🔥 FILTER (RESTORED)
    # -----------------------------
    st.sidebar.header("Filters")

    selected_segments = st.sidebar.multiselect(
        "Select Customer Segment",
        options=rfm["Segment"].unique(),
        default=rfm["Segment"].unique()
    )

    rfm_filtered = rfm[rfm["Segment"].isin(selected_segments)]

    # -----------------------------
    # KPIs
    # -----------------------------
    total_customers = len(rfm_filtered)
    total_revenue = rfm_filtered["Monetary"].sum()

    st.subheader("📌 Key Metrics")

    col1, col2 = st.columns(2)

    col1.metric("Total Customers", total_customers)
    col2.metric("Total Revenue", f"₹ {total_revenue:,.0f}")

    st.markdown("---")

    # -----------------------------
    # Revenue by Segment
    # -----------------------------
    seg_rev = rfm_filtered.groupby("Segment")["Monetary"].sum().reset_index()

    fig = px.bar(seg_rev, x="Segment", y="Monetary",
                 title="Revenue Contribution by Segment")

    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # Monthly Trend (FIXED)
    # -----------------------------
    df["year_month"] = df["order_date"].dt.to_period("M").astype(str)

    monthly = df.groupby("year_month")["order_value"].sum().reset_index()
    monthly = monthly.sort_values("year_month")

    fig_line = px.line(monthly, x="year_month", y="order_value",
                       title="Monthly Revenue Trend")

    st.plotly_chart(fig_line, use_container_width=True)

    # -----------------------------
    # 🔥 MOST PREFERRED PRODUCT PER SEGMENT (FIXED)
    # -----------------------------
    product_pref = (
        df.groupby(["user_id", "product_name"])
        .size()
        .reset_index(name="count")
    )

    product_pref = product_pref.loc[
        product_pref.groupby("user_id")["count"].idxmax()
    ]

    rfm_pref = rfm.merge(product_pref, on="user_id", how="left")

    segment_product = (
        rfm_pref.groupby(["Segment", "product_name"])
        .size()
        .reset_index(name="count")
    )

    segment_product = segment_product.loc[
        segment_product.groupby("Segment")["count"].idxmax()
    ]

    st.subheader("🍽️ Most Preferred Product by Segment")
    st.dataframe(segment_product)

    # -----------------------------
    # AI Recommendation
    # -----------------------------
    st.subheader("🤖 AI Managerial Insights")

    at_risk_count = len(rfm_filtered[rfm_filtered["Segment"].isin(["At Risk", "Churned"])])

    if at_risk_count > total_customers * 0.3:
        st.error("High number of at-risk customers. Immediate retention campaign required.")
    else:
        st.success("Customer base is stable.")

    st.markdown("""
    **Recommended Actions:**
    - Offer discounts to At Risk & Churned customers  
    - Promote top products within each segment  
    - Increase engagement for Fence Sitters  
    """)

    # -----------------------------
    # Final Table
    # -----------------------------
    st.subheader("Customer Data")
    st.dataframe(rfm_filtered)

    st.caption(f"Last Updated: {datetime.now()}")
