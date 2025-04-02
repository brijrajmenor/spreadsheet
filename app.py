import streamlit as st
import pandas as pd
import altair as alt
import json
import requests

# Load restaurant data from config.json
with open("config.json", "r") as file:
    config = json.load(file)
restaurants = config["restaurants"]

st.title("📊 Restaurant Transaction Dashboard")

# Step 1: Select restaurant
dropdown_options = list(restaurants.keys())
selected_restaurant = st.selectbox("Select your restaurant:", dropdown_options)

# Step 2: Enter password
password_input = st.text_input("Enter password:", type="password")

# Fetch correct password securely from Streamlit secrets
correct_password = st.secrets["restaurants"].get(selected_restaurant.lower().replace(" ", "_"), "")

if st.button("Login"):
    if password_input == correct_password:
        st.success(f"Access granted to {selected_restaurant}!")

        # Load correct spreadsheet for the selected restaurant
        SHEET_ID = restaurants[selected_restaurant]["sheet_id"]
        SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

        @st.cache_data(ttl=300)  # Cache for 5 minutes
        def load_transactions(sheet_url):
            try:
                df = pd.read_csv(sheet_url)
                if not df.empty and "Timestamp" in df.columns:
                    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce', dayfirst=True)
                    df = df.dropna(subset=["Timestamp"])
                return df
            except Exception as e:
                st.error(f"❌ Error loading data: {str(e)}")
                return pd.DataFrame()

        # Load Data
        df = load_transactions(SHEET_URL)
        
        if df.empty:
            st.warning("No data loaded or all data filtered out!")
            st.stop()

        # Refresh Button
        if st.sidebar.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.experimental_rerun()

        # Filters
        st.sidebar.header("Filters")

        # User filter
        name_col = next((col for col in ["userName", "Guest Name"] if col in df.columns), None)
        if name_col:
            users = df[name_col].dropna().unique().tolist()
            selected_users = st.sidebar.multiselect("Select Users/Guests", users, default=users)
            df = df[df[name_col].isin(selected_users)] if selected_users else df

        # Type filter
        type_col = next((col for col in ["type", "Status"] if col in df.columns), None)
        if type_col:
            types = df[type_col].dropna().unique().tolist()
            selected_type = st.sidebar.multiselect("Select Type/Status", types, default=types)
            df = df[df[type_col].isin(selected_type)] if selected_type else df

        # Date filter
        if "Timestamp" in df.columns:
            min_date = df["Timestamp"].min().date()
            max_date = df["Timestamp"].max().date()
            date_range = st.sidebar.date_input(
                "Select Date Range",
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
                df = df[(df["Timestamp"].dt.date >= start_date) & (df["Timestamp"].dt.date <= end_date)]

        # Display data
        st.dataframe(df)

        # Charts
        st.subheader("Transaction Summary")

        # Bar Chart for Transaction Types
        if "type" in df.columns and "amount" in df.columns and not df.empty:
            bar_chart = alt.Chart(df).mark_bar().encode(
                x=alt.X("type", title="Transaction Type"),
                y=alt.Y("sum(amount)", title="Total Amount"),
                color="type"
            ).properties(title="Total Amount per Transaction Type")
            st.altair_chart(bar_chart, use_container_width=True)

        # Pie Chart for User Transactions
        if "userName" in df.columns and "amount" in df.columns and not df.empty:
            user_pie = alt.Chart(df).mark_arc().encode(
                theta="sum(amount)",
                color="userName",
                tooltip=["userName", "sum(amount)"]
            ).properties(title="User-wise Transactions")
            st.altair_chart(user_pie, use_container_width=True)

        st.success("Dashboard Updated ✅")
    else:
        st.error("Incorrect password. Access denied!")
