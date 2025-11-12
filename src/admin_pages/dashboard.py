import streamlit as st


conn = st.connection("postgresql", type="sql")

st.subheader("Requests")
df = conn.query("select * from requests;")
st.dataframe(df)
