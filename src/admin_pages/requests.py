import streamlit as st
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import pandas as pd

from admin_pages.tests import fetch_tests

st.set_page_config(page_title="RPWC | Lab Requests", layout="wide")


st.title("Requests")

conn = st.session_state["conn"]


def prepare_tests_df():
    """
    Fetches tests from DB and flattens into a DataFrame with:
    - name
    - code
    - category
    """
    raw_tests = fetch_tests()  # from your DB

    rows = []

    for category in raw_tests:
        cat_name = category['category_name']
        for test in category['available_tests']:
            # extract test code inside brackets e.g. [5050]
            match = re.search(r"\[(\d+)\]", test)
            code = match.group(1) if match else ""

            rows.append({
                "name": test,
                "code": code,
                "category": cat_name
            })

    df = pd.DataFrame(rows)
    return df
    


available_tests_df = prepare_tests_df()

lab_req_formm_ctn = st.container(
    border = True,
    horizontal=False,
    horizontal_alignment="center",
    vertical_alignment='top',
)

with lab_req_formm_ctn:
    with st.container(horizontal_alignment='center'):
        st.markdown("#### Lab Request Form", width='content')


    with st.form("LRF-patient-doctor-details",border=False, enter_to_submit=False):
        patient_details,doctor_details,test_details = st.tabs(['Patient Details', 'Doctor Details', 'Test Details'])

        # =========== patient details ==========================
        with patient_details:
            with st.container(horizontal=True, horizontal_alignment='left'):
                f_name = st.text_input("First Name", width=350)
                s_name = st.text_input("Surname", width=350)
                m_name = st.text_input("Middle Name", width=350)

            with st.container(horizontal=True,horizontal_alignment="left"):
                dob = st.date_input("Date of Birth", format="DD/MM/YYYY", min_value=datetime(1900,1,1), key='dob', width=350)
                gender = st.selectbox("Gender", options=['Male', 'Female', 'Other'], width=350)
                location = st.text_input("Location", width=350)

            with st.container(horizontal=True, horizontal_alignment='left'):
                contact = st.text_input("Phone No:", key="phone", width=350)
                email = st.text_input("Email", key='email', width=350)
                
        # =========== Doctor/Clinic details ==========================
        with doctor_details:
            with st.container(horizontal=True, horizontal_alignment='distribute'):
                doc_full_names = st.text_input("Full Names", key='doc_full_names', width=500)
                doc_dkl_code = st.text_input("DKL Code", key='doc_dkl_code', width=500)
                doc_contacts = st.text_input("Phone/Email", key='doc_contacts', width=500)


        with test_details:

            with st.container(height=250):
                selected_tests:list = st.multiselect(
                    "Matching tests",
                    options=available_tests_df,
                    key="test_selector",
                    label_visibility='hidden',
                    placeholder='Search by test or code'
                )

            with st.container(horizontal=True, horizontal_alignment='center'):
                submitted = st.form_submit_button("**:blue[Submit]**", width='stretch', icon=':material/save:')
        
         



                


