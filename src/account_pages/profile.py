import streamlit as st


if st.user.is_logged_in:
    st.user['email']
else:
    st.write("You don't have permission to view this page!")

conn = st.connection("postgresql", type="sql")
