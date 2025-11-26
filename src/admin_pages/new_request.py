import streamlit as st
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import pandas as pd
from sqlalchemy import text, exc
import secrets

from admin_pages.tests import fetch_tests

st.set_page_config(page_title="RPWC | Lab Request Form", layout="wide")

if "lrf_form" not in st.session_state:
    st.session_state.lrf_form = {}

if "selected_tests" not in st.session_state:
    st.session_state.selected_tests = set()


st.header("Requests", divider="orange")

conn = st.session_state["conn"]


@st.cache_data(ttl=60 * 2)
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
        cat_name = category["category_name"]
        for test in category["available_tests"]:
            # extract test code inside brackets e.g. [5050]
            match = re.search(r"\[(\d+)\]", test)
            code = match.group(1) if match else ""

            rows.append({"name": test, "code": code, "category": cat_name})

    df = pd.DataFrame(rows)
    return df


@st.fragment
def search_tests(df):
    if "search_key" not in st.session_state:
        st.session_state.search_key = 0

    q = st.text_input(
        "Search",
        placeholder="search",
        label_visibility="collapsed",
        key=f"search{st.session_state.search_key}",
    )

    with st.container(border=False, horizontal=False, horizontal_alignment="center"):
        if q:
            results = df[
                df["name"].str.lower().str.contains(q.lower())
                | df["code"].astype(str).str.contains(q.lower())
                | df["category"].str.lower().str.contains(q.lower())
            ]

            options = results["name"].to_list()
            with st.container(
                border=False, horizontal=True, horizontal_alignment="left"
            ):
                selected = st.pills(
                    "results",
                    options=options,
                    selection_mode="multi",
                    label_visibility="collapsed",
                    key=f"pills{st.session_state.search_key}",
                )

            if selected:
                add_selected_btn = st.button("Add selected")
                if add_selected_btn:
                    st.session_state.selected_tests.update(selected)
                    st.session_state.search_key += 1
                    st.rerun(scope="fragment")

    with st.expander("Selected Tests", expanded=False):
        with st.container(border=False, horizontal=True, height=200):
            for idx, test in enumerate(st.session_state.selected_tests):
                checkbox = st.checkbox(test, key=f"{test}{idx}", value=True, width=350)
                if not checkbox:
                    st.session_state.selected_tests.remove(test)
                    st.rerun(scope="fragment")

        with st.container(horizontal=True, horizontal_alignment="center"):
            if st.session_state.selected_tests:
                clear = st.button("Clear selection")
                if clear:
                    st.session_state.selected_tests = []
                    st.rerun()


@st.cache_data(ttl=60)
def fetch_doctors():
    try:
        doctors_df = conn.query(
            """
            SELECT CONCAT_WS(' - ', name, dkl_code) AS doctor
            FROM users
            WHERE user_type='doctor' AND active=true AND is_deleted=false
            ORDER BY name ASC;
            """,
            ttl=0,
        )
        return doctors_df

    except Exception as e:
        st.error("Error fetching doctors")


@st.cache_data(ttl=60)
def fetch_phlebotomists():
    try:
        phlebotomists_df = conn.query(
            """
            SELECT CONCAT_WS(' - ', name, dkl_code) AS  phlebotomist
            FROM users
            WHERE user_type='phlebotomist' AND active=true AND is_deleted=false
            ORDER BY name ASC;
            """,
            ttl=0,
        )
        return phlebotomists_df

    except Exception as e:
        st.error("Error fetching phlebotomists")


def create_request():
    data = st.session_state.lrf_form
    data["tests"] = st.session_state.selected_tests

    # ignore new doctor details if a doctor in the system is also selected
    doctor = data["doctor"]
    if doctor:
        data["new_doctor_doc_full_names"] = None
        data["new_doctor_doc_phone"] = None
        data["new_doctor_doc_email"] = None

    db_data = {
        "first_name": data.get("patient_first_name").strip(),
        "surname": data.get("patient_first_surname").strip(),
        "middle_name": data.get("patient_middle_name").strip(),
        "dob": data.get("patient_dob").strip(),
        "gender": data.get("patient_gender").strip(),
        "phone": data.get("patient_phone").strip(),
        "email": data.get("patient_email").strip(),
        "location": data.get("patient_location").strip(),
        # doctor in the system
        "doctor_dkl_code": data.get("doctor").split("-")[1].strip(),
        # tests
        "selected_tests": list(data.get("tests", [])),
        "assign_to": data.get("assign_to").split("-")[1].strip(),
        "priority": data.get("priority"),
        "collection_date": data.get("collection_date"),
        "collection_time": data.get("collection_time"),
    }

    with conn.session as session:
        try:
            insert_query = text(
                """
                INSERT INTO requests (first_name, surname, middle_name, dob, gender, phone, email, location, 
                doctor_dkl_code,selected_tests, assign_to, priority, collection_date, collection_time)
                VALUES(:first_name, :surname, :middle_name, :dob, :gender, :phone, :email, :location, 
                :doctor_dkl_code,:selected_tests, :assign_to, :priority, :collection_date, :collection_time)
                """
            )
            session.execute(insert_query, db_data)
            session.commit()

            st.session_state.lrf_form = {}
            st.session_state.selected_tests = set()
            st.rerun()
        except Exception as e:
            st.print(e)
            st.error(
                "Error saving lab request. Please try again or contact system admin for support"
            )


available_tests_df = prepare_tests_df()

lab_req_formm_ctn = st.container(
    border=True,
    horizontal=False,
    horizontal_alignment="center",
    vertical_alignment="top",
)

with lab_req_formm_ctn:
    with st.container(horizontal_alignment="center"):
        st.markdown("#### Lab Request Form", width="content")

        patient_details, appointment_details, test_details = st.tabs(
            ["Patient Details", "Appointment Details", "Tests Selection"]
        )

        # =========== patient details ==========================
        with patient_details:
            with st.form("LRF-patient-details", border=False, enter_to_submit=False):
                with st.container(
                    border=False,
                    horizontal=False,
                    horizontal_alignment="center",
                    vertical_alignment="top",
                    height=450,
                ):
                    with st.container(horizontal=True, horizontal_alignment="left"):
                        f_name = st.text_input(
                            "First Name*",
                            value=st.session_state.lrf_form.get(
                                "patient_first_name", None
                            ),
                            width=350,
                        )
                        s_name = st.text_input("Surname*", value="", width=350)
                        m_name = st.text_input(
                            "Middle Name", value="", width=350, placeholder="optional"
                        )

                    with st.container(horizontal=True, horizontal_alignment="left"):
                        dob = st.date_input(
                            "Date of Birth*",
                            format="DD/MM/YYYY",
                            min_value=datetime(1900, 1, 1),
                            key="dob",
                            width=350,
                        )
                        gender = st.selectbox(
                            "Gender*",
                            options=["Male", "Female", "Other"],
                            index=None,
                            width=350,
                        )
                        location = st.text_input("Location*", width=350)

                    with st.container(horizontal=True, horizontal_alignment="left"):
                        contact = st.text_input("Phone No:*", key="phone", width=350)
                        email = st.text_input("Email", key="email", width=350)

                    with st.container(horizontal=False, horizontal_alignment="center"):
                        save_patient_details_btn = st.form_submit_button(
                            "Save", width=250
                        )
                        if save_patient_details_btn:
                            if (
                                not f_name
                                or not s_name
                                or not dob
                                or not gender
                                or not location
                                or not contact
                            ):
                                st.toast(
                                    ":red[Please provide all the required details]"
                                )
                            else:
                                st.session_state.lrf_form["patient_first_name"] = f_name
                                st.session_state.lrf_form["patient_first_surname"] = (
                                    s_name
                                )
                                st.session_state.lrf_form["patient_middle_name"] = (
                                    m_name
                                )
                                st.session_state.lrf_form["patient_dob"] = dob
                                st.session_state.lrf_form["patient_phone"] = contact
                                st.session_state.lrf_form["patient_email"] = email
                                st.session_state.lrf_form["patient_gender"] = gender
                                st.session_state.lrf_form["patient_location"] = location

                                st.toast(":green[Patient details saved]")

        # =========== Doctor/Clinic details ==========================
        with appointment_details:
            with st.form("LRF_clinic_details", border=False, height=450):
                with st.container(horizontal=True, horizontal_alignment="distribute"):
                    doctor = st.selectbox(
                        "Doctor*",
                        options=fetch_doctors(),
                        index=None,
                        placeholder="Select an existing doctor",
                    )

                st.divider()
                assign_to = st.selectbox(
                    "Assign to:*", options=fetch_phlebotomists(), index=None
                )
                st.divider()

                with st.container(
                    border=False, horizontal=True, horizontal_alignment="distribute"
                ):
                    priority = st.selectbox(
                        "Priority*",
                        options=["Routine", "Urgent"],
                        index=None,
                        width=400,
                    )
                    collection_date = st.date_input("Collection Date*", width=400)
                    collection_time = st.time_input("Collection Time*", width=400)

                st.space()
                with st.container(horizontal=False, horizontal_alignment="center"):
                    if "patient_first_name" not in st.session_state.lrf_form:
                        st.form_submit_button(
                            "Please fill required fields in patient details",
                            disabled=True,
                        )

                    else:
                        save_clinic_details_btn = st.form_submit_button(
                            "Save", width=250
                        )
                        if save_clinic_details_btn:
                            if not doctor:
                                st.toast(":red[Please select a doctor]")
                                st.stop()

                            # ---- Phlebotomist validation ----
                            if not assign_to:
                                st.toast(":red[Please assign a phlebotomist]")
                                st.stop()

                            # ---- Priority, date, time validation ----
                            if (
                                not priority
                                or not collection_date
                                or not collection_time
                            ):
                                st.toast(
                                    ":red[Please provide priority, collection date, and collection time]"
                                )
                                st.stop()

                            st.session_state.lrf_form["doctor"] = doctor
                            st.session_state.lrf_form["assign_to"] = assign_to
                            st.session_state.lrf_form["priority"] = priority
                            st.session_state.lrf_form["collection_date"] = (
                                collection_date
                            )
                            st.session_state.lrf_form["collection_time"] = (
                                collection_time
                            )

                            st.toast(":green[Appointment details saved]")

        with test_details:
            tests_df = prepare_tests_df()
            search_tests(tests_df)

            with st.container(
                border=False, horizontal=True, horizontal_alignment="center"
            ):
                if (
                    "patient_first_name" not in st.session_state.lrf_form
                    or "assign_to" not in st.session_state.lrf_form
                ):
                    submit_lrf = st.button(
                        "Please fill all required fields in the previous tabs",
                        width=500,
                        disabled=True,
                    )
                else:
                    submit_lrf = st.button("Save Lab Request", width=500)
                    if submit_lrf:
                        create_request()
