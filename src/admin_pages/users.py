import streamlit as st
from sqlalchemy import text

st.set_page_config(page_title="RPWC|Users", layout="wide")


conn = st.connection("postgresql", type="sql")


def fetch_all_users():
    users = conn.query(
        "SELECT name, email, contact, user_type,active, created_at FROM users;",
        show_spinner=True,
        ttl=0
    )
    return users


@st.dialog("Add new user")
def add_user():

    with st.form("New User", clear_on_submit=False):
        name = st.text_input("Full Names:", key="user_full_names")
        email = st.text_input("Email:", key="user_email")
        phone = st.text_input("Phone No::", key="user_phone")
        role = st.selectbox("Role", options=("Phlebotomist"), index=0)
        submit = st.form_submit_button("Submit")

    if submit:
        if not name or not email or not phone:
            st.warning("Please provide all details")
        else:
            # save user
            query = text(
                "INSERT INTO users(name, email, contact, user_type) VALUES(:name, :email, :contact, :user_type);"
            )
            with conn.session as session:
                session.execute(
                    query,
                    {
                        "name": name,
                        "email": email,
                        "contact": phone,
                        "user_type": role.lower(),
                    },
                )
                session.commit()
                session.close()

            # update refresh flag
            st.session_state['refresh_users'] = True

            # rerun page
            st.rerun()


st.title("Users")

st.subheader(":orange[Users]")
users = fetch_all_users()
st.dataframe(users)


st.subheader("New User")
add_user_btn = st.button("Add User")
if add_user_btn:
    add_user()
