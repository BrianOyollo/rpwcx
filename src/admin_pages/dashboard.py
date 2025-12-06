import streamlit as st
import pandas as pd
import re


conn = st.connection("postgresql", type="sql")

st.title("Dashboard")


#  dashboard filters
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
    users = conn.query("SELECT * FROM users WHERE is_deleted = false", ttl=0)
    requests = conn.query("SELECT * FROM requests", ttl=0)
    tests = conn.query("SELECT * FROM tests", ttl=0)
    return users, requests, tests

users, requests, tests = load_data()

st.write(":gray[Requests Breakdown]")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Requests", len(requests), border=True)
col2.metric("Pending", len(requests[requests["request_status"] == "pending"]), border=True)
col3.metric("In Progress", len(requests[requests["request_status"] == "in-progress"]), border=True)
col4.metric("Completed", len(requests[requests["request_status"] == "completed"]), border=True)

# st.markdown("---")


col5,col6 = st.columns(2, gap="medium", border=True)
with col5:
    # st.write(":gray[Requests Over Time]")
    requests["created_date"] = pd.to_datetime(requests["created_at"]).dt.date
    col5_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
        "title": "Requests Over Time",
        "mark": {"type":"line", "point":"true" },
        "encoding": {
            "x": {"field": "created_date", "type":"temporal"},
            "y": {"field": "count", "type":"quantitative"}
        }
    }
    daily = requests.groupby("created_date").size().reset_index(name="count")
    # st.line_chart(daily, x="created_date", y="count", x_label="", y_label="")
    st.vega_lite_chart(daily, spec=col5_spec)


with col6:
    col6_tabs = st.tabs(['Most Requested Tests', 'Most Requested Categories'])
    with col6_tabs[0]:
        # st.write(":gray[Most Requested Tests]")

        tests_exploded = requests.explode("selected_tests")
        test_popularity = (
            tests_exploded.groupby("selected_tests")
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
        )

        # top_n = st.selectbox("Show top:", [5, 10, 20], index=1)

        # st.bar_chart(
        #     test_popularity.head(10).set_index("selected_tests"),
        #     x_label="",
        #     y_label="Count"
        # )
        test_popularity.columns = ['Test', "Count"]
        st.dataframe(test_popularity, hide_index=True)

with st.container(border=True):
    st.write("**User Type Breakdown**")
    pie_data = users["user_type"].value_counts().reset_index()
    pie_data.columns = ["Type", "Count"]
    st.dataframe(pie_data, hide_index=True)
