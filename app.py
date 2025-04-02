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

        @st.cache_data
        def load_transactions():
            try:
                df = pd.read_csv(SHEET_URL)
                return df
            except Exception as e:
                st.error("Error loading data. Make sure the Google Sheet is publicly accessible.")
                return pd.DataFrame()

        # Load Data
        df = load_transactions()

        # Auto-detect date column
        possible_date_columns = ["Timestamp", "Date"]
        date_column = next((col for col in possible_date_columns if col in df.columns), None)
        if date_column:
            df[date_column] = pd.to_datetime(df[date_column])

        # Display raw data
        st.dataframe(df)

        # Filters (Apply only if columns exist)
        st.sidebar.header("Filters")

        if "userName" in df.columns or "Guest Name" in df.columns:
            name_column = "userName" if "userName" in df.columns else "Guest Name"
            users = df[name_column].unique()
            selected_users = st.sidebar.multiselect("Select Users/Guests", users, default=users)
            df = df[df[name_column].isin(selected_users)]

        if "type" in df.columns or "Status" in df.columns:
            type_column = "type" if "type" in df.columns else "Status"
            types = df[type_column].unique()
            selected_type = st.sidebar.multiselect("Select Type/Status", types, default=types)
            df = df[df[type_column].isin(selected_type)]

        if date_column:
            date_range = st.sidebar.date_input("Select Date Range", [])
            if len(date_range) == 2:
                start_date, end_date = date_range
                df = df[(df[date_column] >= pd.to_datetime(start_date)) & (df[date_column] <= pd.to_datetime(end_date))]

        # Charts
        st.subheader("Transaction Summary")

        # Bar Chart for Transactions
        if ("type" in df.columns or "Status" in df.columns) and ("amount" in df.columns or "Services" in df.columns):
            category_column = "type" if "type" in df.columns else "Status"
            value_column = "amount" if "amount" in df.columns else "Services"

            # Convert non-numeric columns to numeric (for charts)
            df[value_column] = pd.to_numeric(df[value_column], errors="coerce")

            bar_chart = alt.Chart(df).mark_bar().encode(
                x=alt.X(category_column, title="Category"),
                y=alt.Y(f"sum({value_column})", title="Total Amount/Services"),
                color=category_column
            ).properties(title="Total Amount per Category")
            st.altair_chart(bar_chart, use_container_width=True)

        st.success("Dashboard Updated ✅")

    else:
        st.error("Incorrect password. Access denied!")
