import streamlit as st
import pandas as pd
import re
import plotly.express as px

from utils import fetch_categories_and_tests

st.set_page_config(layout="wide")

conn = st.connection("postgresql", type="sql")

st.title("Dashboard")


# dashboard filters
dash_period = st.sidebar.selectbox(
    "Dashboard Period", 
    options = ['This week', "This Month", "Yearly", 'All Time'], 
    label_visibility='visible'
)

if dash_period == 'Yearly':
    dash_year = st.sidebar.selectbox(
        "Year",
        options = [2023, 2024, 2025,2026],
        label_visibility='visible'
    )

    dash_month = st.sidebar.selectbox(
        "Month",
        options = ["Jan", "Feb", "Mar"],
        label_visibility='visible'
    )

st.write(" ")

def load_data():
    """
    Fetches the main datasets from the database for the application.

    Returns:
        tuple:
            - users (DataFrame): All non-deleted users from the `users` table.
            - requests (DataFrame): All lab requests from the `requests` table.
            - tests (DataFrame): All test categories and available tests from the `tests` table.
    """
    users = conn.query("SELECT * FROM users WHERE is_deleted = false", ttl=0)
    requests = conn.query("SELECT * FROM requests", ttl=0)
    tests = conn.query("SELECT * FROM tests", ttl=0)
    return users, requests, tests

users, requests, tests = load_data()

st.write("**Requests Breakdown**")

with st.container(border=False, horizontal=True, horizontal_alignment='distribute'):
# col1, col2, col3, col4 = st.columns(4)

    with st.container(border=False, horizontal=True, horizontal_alignment='distribute'):
        st.metric("Total Requests", len(requests), border=True)
        st.metric("Pending", len(requests[requests["request_status"] == "pending"]), border=True)
    with st.container(border=False, horizontal=True, horizontal_alignment='distribute'):
        st.metric("In Progress", len(requests[requests["request_status"] == "in-progress"]), border=True)
        st.metric("Completed", len(requests[requests["request_status"] == "completed"]), border=True)

# st.markdown("---")


col5,col6 = st.columns(2, gap="medium", border=True)
with col5:
    # st.write(":gray[Requests Over Time]")
    requests["created_date"] = pd.to_datetime(requests["created_at"]).dt.date
    requests_overtime = requests.groupby("created_date").size().reset_index(name="count")
    fig_requests_overtime = px.line(
        requests_overtime, 
        x="created_date", 
        y="count", 
        markers=True,
        title="Requests Over Time"
    )
    fig_requests_overtime.update_yaxes(
        range=[0, requests_overtime['count'].max()+1],
        # dtick=2,
        nticks=10
    )
    fig_requests_overtime.update_layout(
        margin=dict(t=80),
        xaxis_title="",
        yaxis_title="",
        height=300
    )
    st.plotly_chart(fig_requests_overtime)


with col6:
    requests_exploded = requests.explode("selected_tests")
    test_category_map = fetch_categories_and_tests(conn)
    requests_exploded['category'] = requests_exploded['selected_tests'].apply(
        lambda x: test_category_map.get(x, "Uncategorized")
    )
    category_popularity = requests_exploded.groupby('category').size().reset_index(name="count").sort_values("count", ascending=True)
    
    fig_category_popularity = px.bar(
        category_popularity.head(5).sort_values("count", ascending=True), 
        x='count', 
        y='category', 
        orientation='h',
        title="Top 5 Requested Categories",
    )
    fig_category_popularity.update_layout(
        margin=dict(l=150, r=30, t=45, b=0),
        xaxis_title="",                       
        yaxis_title="",
        plot_bgcolor="white",
        height=300
    )

    fig_category_popularity.update_xaxes(showgrid=False)
    fig_category_popularity.update_yaxes(showgrid=False)

    # Add data labels on bars
    fig_category_popularity.update_traces(
        texttemplate='%{x}',
        textposition='outside'
    )

    st.plotly_chart(fig_category_popularity)


with st.container(border=True):
    tests_exploded = requests.explode("selected_tests")

    test_popularity = (
        tests_exploded.groupby("selected_tests")
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )

    test_popularity.columns = ['Test', "Count"]
    test_popularity['Test'] = test_popularity['Test'].str.replace(r"\s*\[.*?\]$", "", regex=True)

    fig_test_popularity = px.bar(
        test_popularity.head(10).sort_values("Count", ascending=True),
        x="Count",
        y="Test",
        orientation="h",
        title="Top 10 Requested Tests",
    )

    # Improve readability and aesthetics
    fig_test_popularity.update_layout(
        margin=dict(l=150, r=30, t=45, b=0),
        xaxis_title="",                       
        yaxis_title="",
        plot_bgcolor="white",
        height=350
    )

    # Remove gridlines to clean up look
    fig_test_popularity.update_xaxes(showgrid=False)
    fig_test_popularity.update_yaxes(showgrid=False)

    # Add data labels on bars
    fig_test_popularity.update_traces(
        texttemplate='%{x}',
        textposition='outside'
    )

    st.plotly_chart(fig_test_popularity, width='stretch')


