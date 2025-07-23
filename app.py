import pandas as pd
import streamlit as st
import plotly.express as px
import mysql.connector
from datetime import datetime

# Database connection function
def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='S@Zwu3wCgBrxa9',  # change if needed
            database='marketing_tool'
        )
        return connection
    except mysql.connector.Error as e:
        st.error(f"Error connecting to database: {e}")
        return None

# Function to execute SQL queries
def execute_query(query, params=None):
    conn = connect_to_database()
    if not conn:
        return pd.DataFrame()
    
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            result = cursor.fetchall()
            return pd.DataFrame(result)
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# Sidebar filters
def apply_filters(df):
    st.sidebar.subheader("🔍 Filters")
    
    if 'brand' in df.columns:
        brands = df['brand'].dropna().unique().tolist()
        df = df[df['brand'].isin(st.sidebar.multiselect("🏷 Brand", brands, brands))]

    if 'category' in df.columns:
        categories = df['category'].dropna().unique().tolist()
        df = df[df['category'].isin(st.sidebar.multiselect("📂 Category", categories, categories))]

    if 'platform' in df.columns:
        platforms = df['platform'].dropna().unique().tolist()
        df = df[df['platform'].isin(st.sidebar.multiselect("📱 Platform", platforms, platforms))]

    if 'product' in df.columns:
        products = df['product'].dropna().unique().tolist()
        df = df[df['product'].isin(st.sidebar.multiselect("🧴 Product", products, products))]

    if 'campaign' in df.columns:
        campaigns = df['campaign'].dropna().unique().tolist()
        df = df[df['campaign'].isin(st.sidebar.multiselect("🚀 Campaign", campaigns, campaigns))]

    if df.empty:
        st.warning("No data available for selected filters.")
        st.stop()

    return df

# Function to calculate ROAS
def calculate_roas(revenue, cost):
    try:
        if cost == 0 or pd.isna(cost) or pd.isna(revenue):
            return 0
        return float(revenue) / float(cost)
    except (ZeroDivisionError, ValueError, TypeError):
        return 0

# Function to calculate ROI
def calculate_roi(revenue, cost):
    try:
        if cost == 0 or pd.isna(cost) or pd.isna(revenue):
            return 0
        return ((revenue - cost) / cost) * 100  # ROI formula
    except (ZeroDivisionError, ValueError, TypeError):
        return 0

# Handle file upload
def handle_file_upload():
    st.sidebar.subheader("📤 Upload Influencer Campaign Data (Optional)")
    uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        try:
            # Read the uploaded CSV file
            uploaded_data = pd.read_csv(uploaded_file)

            # Show a success message and the uploaded data
            st.sidebar.success("File uploaded successfully!")
            st.write("Uploaded Campaign Data:")
            st.write(uploaded_data)

            # Process or store the uploaded data as per your needs here
            return uploaded_data
        except Exception as e:
            st.error(f"Error processing file: {e}")
            return None
    else:
        return None

# Main dashboard layout
def render_dashboard():
    # Add header
    st.markdown(""" 
        <div style='text-align:center; color:white; padding:20px; background:#FF6B35; border-radius:10px; margin-bottom:10px'>
            <h1>📈 Influencer Marketing Dashboard</h1>
            <p>Campaign Performance, Engagement, and ROAS Metrics</p>
        </div>
    """, unsafe_allow_html=True)

    # Handle optional file upload
    uploaded_data = handle_file_upload()

    # Load and filter data from the v_campaign_performance_with_payouts view (default)
    if uploaded_data is None:
        df = execute_query("SELECT * FROM v_campaign_performance_with_payouts")  # This assumes the view is created
    else:
        df = uploaded_data  # Use uploaded data instead of the default DB data
    df = apply_filters(df)

    # Check if 'total_payout' exists in the DataFrame before using it
    if 'total_payout' in df.columns:
        cost = df['total_payout'].sum()  # Assign total payout as cost
    else:
        st.warning("The 'total_payout' column is missing in the data. Assigning cost = 0.")
        cost = 0  # Set default value for cost if the column is missing

    # Show KPIs
    st.subheader("📊 Key Performance Indicators")
    revenue = df['total_revenue'].sum()  # Adjust based on actual column name
    orders = df['total_orders'].sum() if 'total_orders' in df.columns else 0
    reach = df['unique_customers'].sum() if 'unique_customers' in df.columns else 0

    # Calculate KPIs
    roas = round(revenue / cost, 2) if cost > 0 else 0
    aov = round(revenue / orders, 2) if orders > 0 else 0
    cpa = round(cost / orders, 2) if orders > 0 else 0
    roi = round(calculate_roi(revenue, cost), 2)  # ROI calculation

    # Display KPIs in columns
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("💰 Total Revenue", f"₹{revenue:,.0f}")
    k2.metric("💸 Total Cost", f"₹{cost:,.0f}")
    k3.metric("📈 Overall ROAS", f"{roas}x", delta=f"{roas - 3:+.2f}x")
    k4.metric("🎯 Cost per Acquisition", f"₹{cpa:,.0f}")
    k5.metric("📱 Total Reach", f"{reach:,.0f}")  # Total Reach KPI
    k6.metric("💳 Average Order Value", f"₹{aov:,.0f}")

    # Additional KPI: ROI
    st.subheader("📊 ROI Calculation")
    st.write(f"🟢 **ROI**: {roi}%")

    st.markdown("---")

    # Top Influencers by Revenue
    st.subheader("🌟 Top Influencers by Revenue")
    top_inf = execute_query("""
        SELECT influencer_name, total_revenue, total_cost, roas
        FROM v_best_performing_influencers
        ORDER BY total_revenue DESC
        LIMIT 10
    """)
    
    fig_top = px.bar(top_inf, x='total_revenue', y='influencer_name', 
                     orientation='h', color='total_revenue',
                     title="Top 10 Influencers by Revenue Generated",
                     labels={'total_revenue': 'Revenue (₹)', 'influencer_name': 'Influencer'})
    st.plotly_chart(fig_top, use_container_width=True)

    st.markdown("---")

    # Campaign ROAS
    st.subheader("📊 Campaign ROAS")
    campaign_roas = execute_query("""
        SELECT campaign, SUM(campaign_revenue) AS total_revenue, SUM(campaign_cost) AS total_cost, 
               SUM(campaign_revenue) / SUM(campaign_cost) AS roas
        FROM v_campaign_roas
        GROUP BY campaign
    """)
    
    fig_roas = px.bar(campaign_roas, x='roas', y='campaign', 
                     orientation='h', color='roas',
                     title="Campaign ROAS",
                     labels={'roas': 'ROAS', 'campaign': 'Campaign'})
    st.plotly_chart(fig_roas, use_container_width=True)

    st.markdown("---")

    # Post Performance Tracking
    st.subheader("📊 Post Performance")
    post_performance_data = execute_query("""
        SELECT influencer_id, platform, post_date, caption, reach, impressions, engagement_rate, likes, comments, shares
        FROM v_post_performance
        ORDER BY engagement_rate DESC
    """)
    
    st.write(post_performance_data)

    # Display top posts based on engagement rate
    if not post_performance_data.empty:
        fig_posts = px.bar(post_performance_data, x='reach', y='caption', orientation='h', color='engagement_rate',
                           title="Top Posts by Engagement Rate",
                           labels={'reach': 'Reach', 'caption': 'Post Caption'})
        st.plotly_chart(fig_posts, use_container_width=True)

    st.markdown("---")

    # Footer with last updated info
    st.markdown(f"🕒 **Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("*Made with ❤️ by KARAN*")

# Run the dashboard
render_dashboard()
