import streamlit as st

conn = st.connection("postgresql", type="sql")

# st.title("RPWC")


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
    "admin_pages/requests.py", title="Requests", icon=":material/assignment:"
)

# general user
user_tasks = st.Page("user_pages/tasks.py", title="Tasks", icon=":material/assignment:")

# account
profile_page = st.Page(
    "account_pages/profile.py", title="Profile", icon=":material/account_circle:"
)


if st.user.is_logged_in:
    user = st.user

    pg = st.navigation(
        {
            "Admin": [dashboard, users, requests],
            "User": [user_tasks],
            "Account": [profile_page, logout_page],
        }
    )
else:
    pg = st.navigation({"Account": [login_page]})
pg.run()
