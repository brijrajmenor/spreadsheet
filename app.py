import streamlit as st
import pandas as pd
import altair as alt
import json

# Load restaurant data from config.json
with open("config.json", "r") as file:
    config = json.load(file)
restaurants = config["restaurants"]
st.header("Netcreators Automation", divider="gray")
st.subheader("📊 Restaurant Transaction Dashboard")

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'selected_restaurant' not in st.session_state:
    st.session_state.selected_restaurant = None
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'filtered_df' not in st.session_state:
    st.session_state.filtered_df = pd.DataFrame()

# Only show login form if not authenticated
if not st.session_state.authenticated:
    with st.form("login_form"):
        # Step 1: Select restaurant
        dropdown_options = list(restaurants.keys())
        selected_restaurant = st.selectbox("Select your restaurant:", dropdown_options)
        
        # Step 2: Enter password
        password_input = st.text_input("Enter password:", type="password")
        
        login_button = st.form_submit_button("Login")

    if login_button:
        # Fetch correct password securely from Streamlit secrets
        correct_password = st.secrets["restaurants"].get(selected_restaurant.lower().replace(" ", "_"), "")
        
        if password_input == correct_password:
            st.session_state.authenticated = True
            st.session_state.selected_restaurant = selected_restaurant
            st.success(f"Access granted to {selected_restaurant}!")
            st.rerun()  # Rerun to hide the login form
        else:
            st.error("Incorrect password. Access denied!")

# Only show dashboard if authenticated
if st.session_state.authenticated:
    # Add logout button
    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.selected_restaurant = None
        st.session_state.df = pd.DataFrame()
        st.session_state.filtered_df = pd.DataFrame()
        st.rerun()
    
    # Load correct spreadsheet for the selected restaurant
    SHEET_ID = restaurants[st.session_state.selected_restaurant]["sheet_id"]
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
    if st.session_state.df.empty:
        st.session_state.df = load_transactions(SHEET_URL)
        st.session_state.filtered_df = st.session_state.df.copy()
        
        if st.session_state.df.empty:
            st.warning("No data loaded or all data filtered out!")
            st.stop()

    # Refresh Button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.session_state.df = load_transactions(SHEET_URL)
        st.session_state.filtered_df = st.session_state.df.copy()
        st.rerun()

    # Filters
    st.sidebar.header("Filters")
    
    # Work with a copy of the data for filtering
    filtered_df = st.session_state.df.copy()

    # User filter
    name_col = next((col for col in ["userName", "Guest Name"] if col in filtered_df.columns), None)
    if name_col:
        users = filtered_df[name_col].dropna().unique().tolist()
        selected_users = st.sidebar.multiselect("Select Users/Guests", users, default=users)
        if selected_users:
            filtered_df = filtered_df[filtered_df[name_col].isin(selected_users)]

    # Type filter
    type_col = next((col for col in ["type", "Status"] if col in filtered_df.columns), None)
    if type_col:
        types = filtered_df[type_col].dropna().unique().tolist()
        selected_type = st.sidebar.multiselect("Select Type/Status", types, default=types)
        if selected_type:
            filtered_df = filtered_df[filtered_df[type_col].isin(selected_type)]

    # Date filter
    if "Timestamp" in filtered_df.columns:
        min_date = filtered_df["Timestamp"].min().date()
        max_date = filtered_df["Timestamp"].max().date()
        date_range = st.sidebar.date_input(
            "Select Date Range",
            [min_date, max_date],
            min_value=min_date,
            max_value=max_date
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                (filtered_df["Timestamp"].dt.date >= start_date) & 
                (filtered_df["Timestamp"].dt.date <= end_date)
            ]

    # Update the filtered dataframe in session state
    st.session_state.filtered_df = filtered_df

    # Display data
    st.dataframe(st.session_state.filtered_df)

    # Charts
    st.subheader("Transaction Summary")

    # Bar Chart for Transaction Types
    if "type" in st.session_state.filtered_df.columns and "amount" in st.session_state.filtered_df.columns and not st.session_state.filtered_df.empty:
        bar_chart = alt.Chart(st.session_state.filtered_df).mark_bar().encode(
            x=alt.X("type", title="Transaction Type"),
            y=alt.Y("sum(amount)", title="Total Amount"),
            color="type"
        ).properties(title="Total Amount per Transaction Type")
        st.altair_chart(bar_chart, use_container_width=True)

    # Pie Chart for User Transactions
    if "userName" in st.session_state.filtered_df.columns and "amount" in st.session_state.filtered_df.columns and not st.session_state.filtered_df.empty:
        user_pie = alt.Chart(st.session_state.filtered_df).mark_arc().encode(
            theta="sum(amount)",
            color="userName",
            tooltip=["userName", "sum(amount)"]
        ).properties(title="User-wise Transactions")
        st.altair_chart(user_pie, use_container_width=True)

    st.success("Dashboard Updated ✅")
