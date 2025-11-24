import streamlit as st
import re
import pandas as pd


if st.user.is_logged_in:
    st.user["email"]
else:
    st.write("You don't have permission to view this page!")

conn = st.connection("postgresql", type="sql")


def fetch_doctors():
    try:
        doctors_df = conn.query(
            """
            SELECT CONCAT_WS('-', name, dkl_code
            FROM users
            WHERE user_type='doctor' AND active=true AND is_deleted=false
            ORDER BY name ASC;
            """
        )
        return doctors_df

    except Exception as e:
        st.error("Error fetching doctors")


df = fetch_doctors()
st.write(df)
