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

# Debugging output: Show selected restaurant and expected password
st.write(f"🔍 Debug: Selected Restaurant = {selected_restaurant}")
st.write(f"🔍 Debug: Expected Password = {correct_password}")

if st.button("Login"):
    if password_input == correct_password:
        st.success(f"Access granted to {selected_restaurant}!")

        # Load correct spreadsheet for the selected restaurant
        SHEET_ID = restaurants[selected_restaurant]["sheet_id"]
        SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv"

        # Debugging output: Show the loaded sheet ID and URL
        st.write(f"🔍 Debug: Loaded Sheet ID = {SHEET_ID}")
        st.write(f"🔍 Debug: Fetching data from = {SHEET_URL}")

        @st.cache_data(ttl=0)  # Forces fresh data load each time
        def load_transactions(sheet_url):
            try:
                df = pd.read_csv(sheet_url)
                st.write("✅ Data loaded successfully!")
                return df
            except Exception as e:
                st.error(f"❌ Error loading data: {str(e)}")
                return pd.DataFrame()

        # Refresh Button
        if st.sidebar.button("🔄 Refresh Data"):
            st.experimental_rerun()

        # Load Data
        df = load_transactions(SHEET_URL)

        # Debugging output: Show first few rows of loaded data
        st.write("🔍 Debug: First 5 rows of data:")
        st.write(df.head())

        # Convert date column if present
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

        # Filters
        st.sidebar.header("Filters")

        if "userName" in df.columns or "Guest Name" in df.columns:
            name_column = "userName" if "userName" in df.columns else "Guest Name"
            users = df[name_column].dropna().unique().tolist()
            selected_users = st.sidebar.multiselect("Select Users/Guests", users, default=users if users else [])
            df = df[df[name_column].isin(selected_users)]

        if "type" in df.columns or "Status" in df.columns:
            type_column = "type" if "type" in df.columns else "Status"
            types = df[type_column].dropna().unique().tolist()
            selected_type = st.sidebar.multiselect("Select Type/Status", types, default=types if types else [])
            df = df[df[type_column].isin(selected_type)]

        date_range = st.sidebar.date_input("Select Date Range", [])
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df["Timestamp"] >= pd.to_datetime(start_date)) & (df["Timestamp"] <= pd.to_datetime(end_date))]

        st.dataframe(df)

        # Debugging output: Show filtered data
        st.write("🔍 Debug: Filtered Data:")
        st.write(df.head())

        # Charts
        st.subheader("Transaction Summary")

        # Bar Chart for Transaction Types
        if "type" in df.columns and "amount" in df.columns:
            bar_chart = alt.Chart(df).mark_bar().encode(
                x=alt.X("type", title="Transaction Type"),
                y=alt.Y("sum(amount)", title="Total Amount"),
                color="type"
            ).properties(title="Total Amount per Transaction Type")
            st.altair_chart(bar_chart, use_container_width=True)

        # Pie Chart for User Transactions
        if "userName" in df.columns and "amount" in df.columns:
            user_pie = alt.Chart(df).mark_arc().encode(
                theta="sum(amount)",
                color="userName",
                tooltip=["userName", "sum(amount)"]
            ).properties(title="User-wise Transactions")
            st.altair_chart(user_pie, use_container_width=True)

        st.success("Dashboard Updated ✅")
    else:
        st.error("Incorrect password. Access denied!")
