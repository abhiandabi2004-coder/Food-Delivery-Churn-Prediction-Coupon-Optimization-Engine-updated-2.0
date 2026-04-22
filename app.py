import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="AI-Powered RFM Dashboard", layout="wide")

st.title("📊 AI-Powered Customer RFM Intelligence Dashboard")

# -----------------------------
# Upload File
# -----------------------------
uploaded_file = st.file_uploader("Upload Order Data CSV", type=["csv"])

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file)

    # -----------------------------
    # Validate Columns
    # -----------------------------
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
    # Clean Date Column (FIXED)
    # -----------------------------
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date"])

    # -----------------------------
    # Analysis Date Selector
    # -----------------------------
    st.subheader("📅 Select Analysis Date")

    analysis_date = st.date_input(
        "Choose Analysis Date",
        value=df["order_date"].max()
    )

    snapshot_date = pd.to_datetime(analysis_date)

    st.info(f"Recency calculated based on {snapshot_date.date()}")

    # -----------------------------
    # RFM Calculation
    # -----------------------------
    rfm = df.groupby("user_id").agg({
        "order_date": lambda x: (snapshot_date - x.max()).days,
        "order_id": "count",
        "order_value": "sum"
    }).reset_index()

    rfm.columns = ["user_id", "Recency", "Frequency", "Monetary"]

    # -----------------------------
    # Percentile Scoring
    # -----------------------------
    rfm["R_Score"] = pd.qcut(rfm["Recency"], 5, labels=[5,4,3,2,1]).astype(int)
    rfm["F_Score"] = pd.qcut(
        rfm["Frequency"].rank(method="first"),
        5,
        labels=[1,2,3,4,5]
    ).astype(int)
    rfm["M_Score"] = pd.qcut(
        rfm["Monetary"].rank(method="first"),
        5,
        labels=[1,2,3,4,5]
    ).astype(int)

    rfm["RFM_Score"] = (
        rfm["R_Score"].astype(str) +
        rfm["F_Score"].astype(str) +
        rfm["M_Score"].astype(str)
    )

    # -----------------------------
    # Segmentation
    # -----------------------------
    def segment(row):
        if row["R_Score"] >= 4 and row["F_Score"] >= 4 and row["M_Score"] >= 4:
            return "Champion"
        elif row["F_Score"] >= 4 and row["R_Score"] >= 3:
            return "Loyal"
        elif row["R_Score"] >= 3:
            return "Fence Sitter"
        elif row["R_Score"] == 2:
            return "At Risk"
        else:
            return "Churned"

    rfm["Segment"] = rfm.apply(segment, axis=1)

    # -----------------------------
    # KPIs
    # -----------------------------
    total_customers = len(rfm)
    total_revenue = rfm["Monetary"].sum()
    champion_revenue = rfm[rfm["Segment"]=="Champion"]["Monetary"].sum()
    at_risk_revenue = rfm[rfm["Segment"].isin(["At Risk","Churned"])]["Monetary"].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Customers", total_customers)
    col2.metric("Total Revenue", f"₹ {total_revenue:,.0f}")
    col3.metric("Champion Revenue", f"₹ {champion_revenue:,.0f}")
    col4.metric("Revenue At Risk", f"₹ {at_risk_revenue:,.0f}")

    st.markdown("---")

    # -----------------------------
    # Revenue by Segment
    # -----------------------------
    seg_rev = rfm.groupby("Segment")["Monetary"].sum().reset_index()

    fig_pie = px.pie(
        seg_rev,
        names="Segment",
        values="Monetary",
        title="Revenue Contribution by Segment"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # -----------------------------
    # FIXED Monthly Trend (NO Grouper)
    # -----------------------------
    df["year_month"] = df["order_date"].dt.to_period("M").astype(str)

    monthly = df.groupby("year_month")["order_value"].sum().reset_index()
    monthly = monthly.sort_values("year_month")

    fig_line = px.line(
        monthly,
        x="year_month",
        y="order_value",
        title="Monthly Revenue Trend"
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # -----------------------------
    # Preferred Product
    # -----------------------------
    preferred = (
        df.groupby(["user_id", "product_name"])
        .size()
        .reset_index(name="count")
    )

    preferred = preferred.loc[
        preferred.groupby("user_id")["count"].idxmax()
    ]

    rfm = rfm.merge(preferred[["user_id", "product_name"]],
                    on="user_id", how="left")

    # -----------------------------
    # AI Managerial Recommendation
    # -----------------------------
    st.subheader("🤖 AI-Based Managerial Recommendations")

    revenue_dependency = champion_revenue / total_revenue if total_revenue > 0 else 0

    if revenue_dependency > 0.5:
        st.warning("High dependency on Champion customers. Revenue risk concentration exists.")
    else:
        st.success("Balanced revenue distribution across customer segments.")

    if at_risk_revenue > champion_revenue * 0.5:
        st.error("Significant revenue at risk. Immediate retention action required.")
    else:
        st.info("Revenue risk is under control.")

    st.markdown("""
    **Recommended Actions:**
    - Retain Champion customers with loyalty programs  
    - Re-engage At Risk & Churned customers  
    - Upsell Fence Sitters  
    - Monitor Recency trends regularly  
    """)

    # -----------------------------
    # Final Table
    # -----------------------------
    st.subheader("Customer RFM Table")
    st.dataframe(rfm.sort_values("RFM_Score", ascending=False), use_container_width=True)

    st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
