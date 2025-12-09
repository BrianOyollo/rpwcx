import streamlit as st
import pandas as pd
import re
from datetime import datetime
import plotly.express as px

from utils import fetch_categories_and_tests

st.set_page_config(layout="wide")

conn = st.connection("postgresql", type="sql")

if "dashboard_title_extra" not in st.session_state:
    st.session_state.dashboard_title_extra = None

# dashboard filters
dash_period = st.sidebar.selectbox(
    "Dashboard Period", 
    options = ['This week', "This Month", "Yearly", 'All Time'],
    index = 0,
    label_visibility='visible'
)


dash_year = dash_month = None
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

if dash_period == 'Yearly':
    years = [y for y in range(2020,pd.Timestamp.now().year+1, 1)]
    dash_year = st.sidebar.selectbox(
        "Year",
        options = years,
        index = years.index(pd.Timestamp.now().year),
        label_visibility='visible'
    )

    dash_month = st.sidebar.selectbox(
        "Month",
        options = months,
        # index = months.index(pd.Timestamp.now().month_name()[:3]),
        index = None,
        label_visibility='visible'
    )

def end_of_month(year:int, month:int)-> pd.Timestamp:
    """
    Calculate the final moment of a given month.

    Given a specific year and month, this function returns a pandas Timestamp
    representing the **last day of that month at 23:59:59**. It correctly accounts
    for varying month lengths and leap years.

    Args:
        year (int): The target year (e.g., 2025).
        month (int): The target month (1–12).

    Returns:
        pandas.Timestamp: A timestamp set to the final second of the last day of
        the specified month. Example:
            end_of_month(2024, 2) → Timestamp('2024-02-29 23:59:59')
    """
    ts = pd.Timestamp(year=year, month=month, day=1)
    very_end_of_month = ts + pd.offsets.MonthEnd(1)
    very_end_of_month.replace(hour=23,minute=59,second=59)
    return very_end_of_month


def load_data(dash_period, dash_year, dash_month):
    """
    Fetches the main datasets from the database for the application.

    Returns:
        tuple:
            - users (DataFrame): All non-deleted users from the `users` table.
            - requests (DataFrame): All lab requests from the `requests` table.
            - tests (DataFrame): All test categories and available tests from the `tests` table.
    """
    users = conn.query("SELECT user_type, created_at, (telegram_chat_id IS NOT NULL) AS tg_active FROM users WHERE is_deleted = false", ttl=0)
    requests = conn.query("SELECT * FROM requests", ttl=0)
    tests = conn.query("SELECT * FROM tests", ttl=0)     
    
    if dash_period == 'This week':
        # weekly_users = users[users['created_at'] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
        weekly_requests = requests[requests['created_at'] >= pd.Timestamp.now() - pd.Timedelta(days=7)]
        weekly_tests = tests[tests['created_at'] >= pd.Timestamp.now() - pd.Timedelta(days=7)]

        st.session_state.dashboard_title_extra = "This Week"
        return users, weekly_requests, weekly_tests
    
    elif dash_period == 'This Month':
        month = pd.Timestamp.now().month
        # end_of_month = end_of_month(pd.Timestamp.now().year, month)

        monthly_users = users[users['created_at'].dt.month <= month ]
        monthly_requests = requests[requests['created_at'].dt.month == month]
        monthly_tests = tests[tests['created_at'].dt.month == month]

        st.session_state.dashboard_title_extra = "This Month"

        return monthly_users, monthly_requests, monthly_tests

    elif dash_period == 'Yearly':

        yearly_users = users[users['created_at'].dt.year <= dash_year]
        yearly_requests = requests[requests['created_at'].dt.year == dash_year]
        yearly_tests = tests[tests['created_at'].dt.year == dash_year]

        st.session_state.dashboard_title_extra = f"{dash_year}"

        if dash_month:
            dash_month_int = months.index(dash_month)+1
            yearly_users = yearly_users[yearly_users['created_at'].dt.month <= dash_month_int]
            yearly_requests = yearly_requests[yearly_requests['created_at'].dt.month == dash_month_int]
            yearly_tests = yearly_tests[yearly_tests['created_at'].dt.month == dash_month_int]

            st.session_state.dashboard_title_extra = f"{dash_month} {dash_year}"

            return yearly_users, yearly_requests, yearly_tests


        return yearly_users, yearly_requests, yearly_tests
    
    else:
        st.session_state.dashboard_title_extra = f"All Time"
        return users, requests, tests
    

    
users, requests, tests = load_data(dash_period, dash_year, dash_month)

with st.container(border=False, horizontal=False, horizontal_alignment='left'):
    st.markdown(
        f"""
        <div style="align-items:center; gap:5px;">
            <h1 style="margin:0; padding:0;">Dashboard</h1>
            <span style="font-size:15px; color:#666;">{st.session_state.dashboard_title_extra}</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.space("small")

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
    st.plotly_chart(fig_requests_overtime, config = {'scrollZoom': False})


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
        margin=dict(l=150, r=30, t=80, b=0),
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

    fig_test_popularity.update_layout(
        margin=dict(l=150, r=30, t=80, b=0),
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


with st.container(border=False, horizontal=True):
    
    users['user_type'] = users['user_type'].str.title()
    users['tg_active'] = users['tg_active'].map({True: 'Active', False: 'Not Active'})

    with st.container(border=True, horizontal=False, width=500):
        users_type = users['user_type'].value_counts().reset_index()
        if users_type.empty:
            
                st.write("**User Count**")
                st.info("No user data for this period")
        else:
            fig_user_type = px.pie(
                users_type,
                names='user_type',
                values='count',
                title="User Count",
            )

            fig_user_type.update_layout(
                margin=dict(l=30, r=30, t=80, b=0),
                height=300,
                width=300,
                showlegend = False
            )

            fig_user_type.update_traces(textposition='inside', textinfo='value+label')
            st.plotly_chart(fig_user_type)

    with st.container(border=True, horizontal=False):

        tg_active_users = users.groupby(['user_type', 'tg_active']).size().reset_index(name='count')
        
        if tg_active_users.empty:
            st.info("No user data for this period")
        else:
            fig = px.bar(
                tg_active_users,
                x='user_type',
                y='count',
                color='tg_active',
                title='Telegram Active Users by Role',
                text='count'
            )
            fig.update_layout(
                barmode='stack',
                height=300,
                xaxis_title='',
                yaxis_title='',
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=-0.50,
                    xanchor='center',
                    x=0.5,
                    title=""
                ),
                margin=dict(l=30, r=30, t=95, b=10)
            )

            fig.update_traces(textposition='inside', texttemplate='%{y}',)
            st.plotly_chart(fig)
        

    


