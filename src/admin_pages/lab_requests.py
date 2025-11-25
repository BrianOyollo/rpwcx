import streamlit as st
import pandas as pd
from sqlalchemy import text, exc
from datetime import datetime

st.set_page_config(page_title="RPWC|Lab Requests", layout="wide")

st.header("Lab Requests", divider="orange")

conn = st.session_state["conn"]


with conn.session as session:
    requests = session.execute(text("""
        WITH doctors as (
            select dkl_code, name from users where user_type='doctor'
        ),
        phlebotomists as (
            select dkl_code, name from users where user_type='phlebotomist'
        )

        SELECT 
            CONCAT(r.first_name,' ',r.surname, ' ',r.middle_name)  AS patient, 
            r.dob, r.gender, r.phone, r.email, 
            r.selected_tests, r.collection_date, r.collection_time,
            d.name as doctor,
            p.name as phlebotomist,
            r.request_status, r.created_at, r.updated_at          
        FROM requests r
        JOIN doctors d on d.dkl_code = r.doctor_dkl_code
        JOIN phlebotomists p on p.dkl_code = r.assign_to
        ORDER BY created_at DESC;	
        """)
    ).fetchall()

# st.write(requests)

with st.container(border=False, horizontal=False, horizontal_alignment='center'):
    for row in requests:
        with st.container(border=True, horizontal=False, horizontal_alignment='left'):
            st.write(f"{row[0]} :grey[({row[2]}, {row[1]}])")
            st.write("Contacts:", row[3], row[4])
            # tests = [f":grey-badge[{test}]" for test in row[5]]
            st.markdown(f" ".join([f":grey-badge[{test}]" for test in row[5]]))
            st.write("Collection time:", row[6], row[7])
            st.write('Doctor:', row[8])
            st.write('Phlebotomist:', row[9])

            

# st.data_editor(
#     requests,
#     hide_index = True,
#     column_order = [
#         'patient', 'dob', 'gender','phone','email', 
#         'selected_tests','collection_date', 'collection_time', 'phlebotomist','doctor',
#         'request_status'
#     ],
#     column_config={
#         "id": st.column_config.NumberColumn("request_id", disabled=True),
#         "patient": st.column_config.TextColumn("Patient", pinned=True, width=150),
#         "dob": st.column_config.DateColumn("DoB"),
#         "gender": st.column_config.SelectboxColumn("Gender", options=["Male", 'Female', 'Other']),
#         "phone": st.column_config.TextColumn("Phone"),
#         "email": st.column_config.TextColumn("Email"),
#         "tests": st.column_config.MultiselectColumn("Tests", options=[], accept_new_options=True),
#         "collection_date": st.column_config.DateColumn("Collection Date"),
#         "collection_time": st.column_config.TimeColumn("Collection Time"),
#     }
# )