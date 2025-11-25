import streamlit as st
import pandas as pd
from sqlalchemy import text, exc
from datetime import datetime

st.set_page_config(page_title="RPWC|Lab Requests", layout="wide")

st.header("Lab Requests", divider="orange")

conn = st.session_state["conn"]


def fetch_requests():
    requests = conn.query("""
        WITH doctors as (
            select dkl_code, name from users where user_type='doctor'
        ),
        phlebotomists as (
            select dkl_code, name from users where user_type='phlebotomist'
        )

        SELECT 
            CONCAT(r.first_name,' ',r.surname, ' ',r.middle_name)  AS patient, 
            r.dob, r.gender, r.phone, r.email, r.location,
            r.selected_tests, r.collection_date, r.collection_time,
            d.name as doctor,
            p.name as phlebotomist,
            r.request_status, r.created_at, r.updated_at          
        FROM requests r
        JOIN doctors d on d.dkl_code = r.doctor_dkl_code
        JOIN phlebotomists p on p.dkl_code = r.assign_to
        ORDER BY created_at DESC;	
        """, ttl=0
    )
    return requests

# st.write(requests)
tabs = st.tabs(['Card View', 'Editor View'])
requests_df = fetch_requests()

with tabs[0]:
    requests = requests_df.to_dict(orient='records')
    for row in requests:

        with st.container(border=True, horizontal=True, horizontal_alignment='center'):  # main card
            with st.container(border=False, horizontal=False):
                st.markdown(f"<h5 style='padding:5px 0px; margin:0px;'>{row['patient']}</h5>", unsafe_allow_html=True)
                st.markdown(f"<p style='padding:2.5px 0px; margin:0px;'> {row['gender']}, {row['dob']}, {row['location']}</p>", unsafe_allow_html=True)
                st.markdown(f"<p> {row['phone']} / {row['email'] if row['email'] else 'N/A'}</p>", unsafe_allow_html=True)
                st.markdown(f"<p> Doctor/Phlebotomist: {row['doctor']} / {row['phlebotomist']}</p>", unsafe_allow_html=True)
                tests = [f":grey-badge[{test}]" for test in row['selected_tests']]
                st.markdown(''.join(tests))




with tabs[1]:
    with st.container(border=False, horizontal=False, horizontal_alignment='center', vertical_alignment='top', height=475):
        q = st.text_input('search', label_visibility='collapsed', placeholder="search by patient's name")
        st.data_editor(
            requests_df,
            hide_index = True,
            num_rows='dynamic',
            column_order = [
                'patient', 'dob', 'gender','phone','email', 
                'selected_tests','collection_date', 'collection_time', 'phlebotomist','doctor',
                'request_status'
            ],
            column_config={
                "id": st.column_config.NumberColumn("request_id", disabled=True),
                "patient": st.column_config.TextColumn("Patient", pinned=True, width=130),
                "dob": st.column_config.DateColumn("DoB"),
                "gender": st.column_config.SelectboxColumn("Gender", options=["Male", 'Female', 'Other']),
                "phone": st.column_config.TextColumn("Phone"),
                "email": st.column_config.TextColumn("Email"),
                "tests": st.column_config.MultiselectColumn("Tests", options=[], accept_new_options=True),
                "collection_date": st.column_config.DateColumn("Collection Date"),
                "collection_time": st.column_config.TimeColumn("Collection Time"),
                "doctor": st.column_config.TextColumn("Doctor"),
                "phlebotomist": st.column_config.TextColumn("Phlebotomist"),
                "request_status": st.column_config.SelectboxColumn(
                    "Status", 
                    options=['pending', 'in-progress', 'completed', 'cancelled'],
                    format_func = lambda x: x.title()
                )
            }
        )
        st.caption(f"Total: {len(requests_df)}")

    with st.container(border=False, horizontal=True, horizontal_alignment='center'):
        new_request_btn = st.button("New Request")
        if new_request_btn:
            on_click=st.switch_page("admin_pages/new_request.py")

        save_changes_btn = st.button("Save Changes")