import streamlit as st
import re, time
import pandas as pd


if not st.user.is_logged_in:
    st.write("You don't have permission to view this page!")
    st.stop()

conn = st.connection("postgresql", type="sql")
user_info = conn.query(
    "select * from users where email=:email", params={"email": st.user.email}
)

# user_info
user_data = user_info.to_dict(orient="records")[0]

with st.container(
    border=False,
    horizontal=False,
    horizontal_alignment="left",
    vertical_alignment="top",
):
    with st.container(border=False, horizontal=True, vertical_alignment='top', height='content'):
        with st.container(
            border=True,
            horizontal=False,
            horizontal_alignment="center",
            vertical_alignment="center",
            width=400, 
            height=280
        ):
            st.image(st.user.picture)
            st.header(st.user["name"].title(), width="content")
            st.caption(user_data['user_type'].title(), width='content')

        with st.container(border=True, horizontal=False, height=280):
            st.markdown("#### :orange[Account Details]")

            with st.container(border=False, horizontal=True):
            # email_cols = st.columns([.8,2], gap='small')
                st.markdown(f"**Email:**", width=120)
                st.markdown(st.user.email)

            with st.container(border=False, horizontal=True):
                st.markdown("**Phone:**", width=120)
                st.markdown(user_data['contact'])

            with st.container(border=False, horizontal=True):
                st.markdown("**Account Status:**", width=120)
                st.markdown(":green[Verified]" if st.user.email_verified else 'Not Verified')

            with st.container(border=False, horizontal=True):
                st.markdown("**Telegram Status:**", width=120)
                st.markdown(":green[Linked]" if user_data["telegram_chat_id"] else 'Not Linked')

            with st.container(border=False, horizontal=True):
                st.markdown("**Date Joined:**", width=120)
                st.markdown(user_data['created_at'])
    
    with st.container(border=True):
        st.markdown("#### :orange[Activity Overview]")
        st.write("Coming soon: recent logins, tasks, actions…")
