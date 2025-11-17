import streamlit as st
import time
import duckdb

# st.title("RPWC")

# create a persistent DuckDB and SQL connections
if "conn" not in st.session_state:
    st.session_state["conn"] = st.connection("postgresql", type="sql")

if "duck_conn" not in st.session_state:
    st.session_state["duck_conn"] = duckdb.connect()

if "show_delete_category_dialog" not in st.session_state:
    st.session_state["show_delete_category_dialog"] = True


conn = st.session_state["conn"]


def login():
    st.header("This app is private.")
    st.subheader("Please log in.")
    st.button("Log in with Google", on_click=st.login)


def logout():
    st.logout()
    st.rerun()


# login & logout
login_page = st.Page(login, title="Login", icon=":material/login:")
logout_page = st.Page(logout, title="Logout", icon=":material/logout:")

# admin
dashboard = st.Page(
    "admin_pages/dashboard.py", title="Dashboard", icon=":material/dashboard:"
)
users = st.Page("admin_pages/users.py", title="Users", icon=":material/group:")
requests = st.Page(
    "admin_pages/new_request.py", title="Lab Request Form", icon=":material/assignment:"
)
tests = st.Page("admin_pages/tests.py", title="Tests", icon=":material/lab_panel:")

# general user
user_tasks = st.Page("user_pages/tasks.py", title="Tasks", icon=":material/assignment:")

# account
profile_page = st.Page(
    "account_pages/profile.py", title="Profile", icon=":material/account_circle:"
)


if st.user.is_logged_in:
    user = st.user
    try:
        db_user = conn.query(
            "SELECT email, user_type,active, is_deleted FROM users WHERE email=:email",
            params={"email": user["email"]},
            ttl=0,
        )
    except Exception as e:
        st.error(
            "Error fetching users from the db. Contact system admin for assistance if the issue persists"
        )
        st.stop()

    # Check if the user exists in the users table
    if db_user.empty:
        st.error("Access denied: You are not authorized to use this app.")
        time.sleep(2)
        logout()

    user_active = db_user.iloc[0]["active"]
    user_deleted = db_user.iloc[0]["is_deleted"]
    if not user_active or user_deleted:
        st.error("Your account is deactivated. Contact an admin for assistance.")
        time.sleep(2)
        logout()

    user_type = db_user.iloc[0]["user_type"]
    if user_type == "admin":
        pages = {
            "Admin": [dashboard, users, requests, tests],
            # "Users": [users],
            "Account": [profile_page, logout_page],
        }
    elif user_type == "phlebotomist":
        pages = {
            "User": [user_tasks],
            "Account": [profile_page, logout_page],
        }
    else:
        pages = {
            "Account": [profile_page, logout_page],
        }
else:
    pages = {
        "Account": [login_page],
    }

pg = st.navigation(pages)
pg.run()
