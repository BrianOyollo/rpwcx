import streamlit as st
import re
import pandas as pd


if not st.user.is_logged_in:
    st.write("You don't have permission to view this page!")
    st.stop()

conn = st.connection("postgresql", type="sql")
user_info = conn.query("select * from users where email=:email", params={"email":st.user.email})

# user_info 
user_data = user_info.to_dict(orient='records')[0]

# user_data

with st.container(border=False, horizontal=False, vertical_alignment='top'):
    with st.container(border=False, horizontal=False, horizontal_alignment="center",vertical_alignment='top'):
        st.image(st.user.picture)
        st.header(st.user['name'], width='content')

    with st.container(border=False, horizontal=False, horizontal_alignment="left",vertical_alignment='top'):
        st.write(f":orange[Email]: {st.user.email}")
        st.write(f":orange[Phone]: {user_data['contact']}")
        st.write(f":orange[Status]: {"Verified" if st.user.email_verified else "Not Verified"}")
        st.write(f":orange[Role]: {user_data['user_type'].title()}")
        st.write(f":orange[Date Joined]: {user_data['created_at']}")

# st.write(st.user)