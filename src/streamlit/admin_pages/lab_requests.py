import streamlit as st
import pandas as pd
from sqlalchemy import text, exc
from datetime import datetime
import time

from utils import (
    fetch_phlebotomists,
    fetch_doctors,
    search_tests,
    prepare_tests_df
)

st.set_page_config(page_title="RPWC|Lab Requests", layout="wide")

st.header("Lab Requests", divider="orange")

conn = st.session_state["conn"]

if "lr_mode" not in st.session_state:
    st.session_state.lr_mode = "view"

if "request_to_edit" not in st.session_state:
    st.session_state.request_to_edit = None

if "edited_request" not in st.session_state:
    st.session_state.edited_request = {}


def fetch_requests():
    """
    Fetches all patient requests along with doctor and phlebotomist details,
    returning the result as a pandas DataFrame.

    This function performs a SQL query that:
        - Joins the `requests` table with:
            * `doctors` (users with user_type='doctor')
            * `phlebotomists` (users with user_type='phlebotomist')
        - Combines patient name fields into a single "patient" column.
        - Includes key request fields such as demographics, tests,
          collection schedule, assigned staff, status, and timestamps.
        - Orders the results by most recently created requests.
    Returns:
        pd.DataFrame:
            A DataFrame with one column: "phlebotomist".

    Raises:
        On query failure, shows a Streamlit error message and stops execution
        to prevent downstream errors.
    """
    try:
        requests = conn.query(
            """
            WITH doctors as (
                select dkl_code, name from users where user_type='doctor'
            ),
            phlebotomists as (
                select dkl_code, name from users where user_type='phlebotomist'
            )

            SELECT 
                id,
                CONCAT(r.first_name,' ',r.middle_name, ' ',r.surname)  AS patient, 
                r.dob, r.gender, r.phone, r.email, r.location,
                r.selected_tests, r.collection_date, r.collection_time,priority,
                -- d.name as doctor,
                p.name as phlebotomist,
                r.request_status, r.created_at, r.updated_at          
            FROM requests r
            -- LEFT JOIN doctors d on d.dkl_code = r.doctor_dkl_code
            LEFT JOIN phlebotomists p on p.dkl_code = r.assign_to
            ORDER BY created_at DESC;	
            """,
            ttl=0,
        )
        return requests
    except Exception as e:
        st.error("Error fetching lab requests. Please try again or contact the admin")
        st.stop()


@st.dialog(":green[Request Details]")
def request_details(request):
    """
    Displays a modal dialog showing full details for a single request.

    The dialog presents:
        - Patient information (name, gender, DOB, contacts, location)
        - Assigned doctor and phlebotomist
        - Request metadata (created/updated timestamps, priority, collection schedule)
        - Selected tests rendered as badges

    Args:
        request (dict): A dictionary representing a single request record
        returned from fetch_requests(), containing all required fields.

    Note:
        This function only renders UI elements; it does not modify state
        or return any value.
    """
    with st.container(
        border=False, horizontal=False, horizontal_alignment="center", height=450
    ):
        st.caption("------------ Patient Details ------------ ")
        st.write(f":orange[**Name**]: **{request['patient'].strip()}**")
        st.write(f":orange[**Gender**]: **{request['gender']}**")
        st.write(f":orange[**DoB**]: **{request['dob']}**")
        st.write(f":orange[**Location**]: **{request['location'].strip()}**")
        st.write(
            f":orange[**Contacts**]: **{request['phone'].strip()}**"
        )

        # st.caption("------------ Doctor/Phlebotomist ------------ ")
        # st.write(f":orange[**Doctor**]: **{request['doctor']}**")
        # st.write(f":orange[**Phlebotomist**]: **{request['phlebotomist']}**")

        st.caption("------------ Test Details ------------ ")
        st.write(
            f":orange[**Created on**]: **{request['created_at'].strftime('%b %d, %Y • %I:%M %p')}**"
        )
        st.write(
            f":orange[**Updated on**]: **{request['updated_at'].strftime('%b %d, %Y • %I:%M %p') if request['updated_at'] else 'N/A'}**"
        )
        st.write(f":orange[**Request Priority**]: **{request['priority']}**")
        st.write(
            f":orange[**Collection Date**]: **{request['collection_date']} at {request['collection_time'].strftime('%H:%M %p')}**"
        )
        tests_badges = [f":gray-badge[{test}]" for test in request["selected_tests"]]
        st.markdown(f":orange[**Tests**]:\n {' '.join(tests_badges)}")


@st.dialog("Delete Lab Request")
def delete_lab_request(request_id):
    """
    Displays a confirmation dialog to delete a lab request by ID.

    Workflow:
        - Shows a warning that deletion is irreversible.
        - Provides a "Confirm" button to execute deletion.
        - On confirmation, deletes the request from the database.
        - Handles rollback on errors and displays a toast notification.
        - Reruns the app after deletion or error.

    Args:
        request_id (int): The ID of the lab request to delete.

    Note:
        This function performs database modification and updates the UI.
    """
    st.warning(
        "Are you sure you want to delete this request? \n\n :red[**This action can't be done!**]"
    )

    with st.container(border=False, horizontal=True, horizontal_alignment="center"):
        confirm_delete = st.button("Confirm", type="primary")

        if confirm_delete:
            delete_query = text("DELETE FROM requests WHERE id=:id")
            with conn.session as session:
                try:
                    session.execute(delete_query, {"id": request_id})
                    session.commit()
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    print(e)
                    st.toast(":red[Error deleted lab request. Please try again]")
                    time.sleep(5)
                    st.rerun()


# st.write(requests)
if st.session_state.lr_mode == "edit" and st.session_state.get("request_to_edit"):
    with st.container(border=False, horizontal=False, horizontal_alignment="left"):
        request_to_edit = st.session_state.request_to_edit
        st.session_state.selected_tests = set(
            st.session_state.request_to_edit["selected_tests"]
        )

        @st.fragment
        def edit_request():
            """
            Displays a multi-tab form to edit an existing lab request.

            Tabs:
                1. Patient Details: Edit patient name, DOB, gender, location, phone, email.
                2. Appointment Details: Edit status, assigned doctor, phlebotomist, priority, collection date/time.
                3. Test Details: Search and select tests for the request.

            Features:
                - Pre-fills fields with current request values.
                - Validates required fields and test selection before saving.
                - Updates the request in the database on "Save Changes".
                - Cancels edit and resets session state on "Cancel Edit".

            Notes:
                - Uses Streamlit session state to manage temporary selections.
                - Performs database updates with rollback on errors.
                - UI height, layout, and alignment are customized for usability.
            """

            def patient_details():
                patient_to_edit = request_to_edit["patient"].split(" ")
                with st.container(border=True, horizontal=False):
                    with st.container(border=False, horizontal=True, width="stretch"):
                        first_name = st.text_input(
                            "First Name", 
                            placeholder="First Name", 
                            label_visibility="visible", 
                            key="first_name",
                            value=patient_to_edit[0].strip().replace("_", " "),
                        )
                        surname = st.text_input(
                            "Surname", 
                            placeholder="Surname", 
                            label_visibility="visible", 
                            key="surname",
                            value=patient_to_edit[2].strip().replace("_", " ")
                        )

                    with st.container(border=False, horizontal=True, width="stretch"):
                        gender_options = ["Male", "Female", "Other"]
                        gender = st.selectbox(
                            "Gender*",
                            options=gender_options,
                            index=gender_options.index(request_to_edit["gender"]),
                            width='stretch',
                            key="gender",
                        )
                        dob = st.date_input(
                            "Date of Birth", 
                            label_visibility="visible", 
                            width="stretch", 
                            key='dob',
                            format="DD/MM/YYYY",
                            min_value=datetime(1900, 1, 1),
                            value=request_to_edit["dob"],
                        )
                        phone = st.text_input(
                            "Phone", 
                            width="stretch", 
                            key="phone",
                            value=request_to_edit["phone"]
                        )

                    location = st.text_input(
                        "Location", 
                        width="stretch", 
                        key="location",
                        value=request_to_edit["location"]
                    )

                return first_name, surname, gender, dob, phone, location

            def appointment_details() -> tuple:
                with st.container(border=True, horizontal=True):
                    phlebotomist_options = fetch_phlebotomists(conn)["phlebotomist"].to_list()
                    current_phlebotomist = request_to_edit["phlebotomist"]
                    phlebotomist_match = None

                    for p in phlebotomist_options:
                        if current_phlebotomist in p:
                            phlebotomist_match = p

                    phlebotomist = st.selectbox(
                        "Phlebotomist:*",
                        options=fetch_phlebotomists(conn),
                        index=phlebotomist_options.index(phlebotomist_match) if phlebotomist_match else None,
                        key="assign_to",
                        width=350
                    )

                    collection_date = st.date_input(
                        "Collection date", 
                        width="stretch", 
                        value = request_to_edit["collection_date"],
                        key="collection_date",
                        format="DD/MM/YYYY",
                        min_value=datetime(1900, 1, 1),
                    )
                    collection_time = st.time_input(
                        "Test Collection Time",
                        value = request_to_edit["collection_time"],
                        width="stretch", 
                        key="collection_time"
                    )

                    priority_options = ["Routine", "Urgent"]
                    priority = st.selectbox(
                        "Priority", 
                        options=priority_options, 
                        index=priority_options.index(request_to_edit["priority"]),
                        width='stretch', 
                        key="priority"
                    )

                    request_status_options = ["pending","in-progress","completed","cancelled"]
                    request_status = st.selectbox(
                        "Status:*",
                        options=request_status_options,
                        index=request_status_options.index(
                            request_to_edit["request_status"]
                        ),
                        key="edit_request_status",
                        format_func=lambda x: x.title(),
                    )

                return phlebotomist, collection_date, collection_time, priority, request_status

            def add_tests() -> None:
                with st.container(border=True, horizontal=True):
                    tests_df = prepare_tests_df(conn)
                    search_tests(tests_df)

            first_name, surname, gender, dob, phone, location = patient_details()
            phlebotomist, collection_date, collection_time, priority, request_status = appointment_details()
            add_tests()



            with st.container(
                border=False, horizontal=True, horizontal_alignment="center"
            ):
                cancel_edit = st.button("Cancel Edit")
                if cancel_edit:
                    st.session_state.lr_mode = "view"
                    st.session_state.request_to_edit = None
                    st.session_state.selected_tests = set()
                    st.rerun()

                save_edit = st.button("Save Changes")
                if save_edit:
                    if not first_name:
                        st.toast(" ⚠️ :red[**Please provide patient's first name**]")
                        st.stop()
                    if not surname:
                        st.toast(" ⚠️ :red[**Please provide patient's surname**]")
                        st.stop()
                    if not gender:
                        st.toast(" ⚠️ :red[**Please provide patient's gender**]")
                        st.stop()
                    if not dob:
                        st.toast(" ⚠️ :red[**Please provide patient's Date of birth**]")
                        st.stop()
                    if not phone:
                        st.toast(" ⚠️ :red[**Please provide patient's phone number**]")
                        st.stop()
                    if not location:
                        st.toast(" ⚠️ :red[**Please provide patient's location**]")
                        st.stop()
                    if not phlebotomist:
                        st.toast(" ⚠️ :red[**Please assign a phlebotomist**]")
                        st.stop()
                    if not collection_date or not collection_time:
                        st.toast(" ⚠️ :red[**Please provide collection_date/time**]")
                        st.stop()
                    
                    if not st.session_state.selected_tests:
                        st.toast(" ⚠️ :red[**Please add tests**]")
                        st.stop()

                    selected_tests = st.session_state.selected_tests

        
                    form_data = {
                        "first_name": first_name.strip().replace(" ", "_"),
                        "surname": surname.strip().replace(" ", "_"),
                        "dob": dob,
                        "gender": gender.strip(),
                        "phone": phone.strip(),
                        "location": location.strip(),
                        "selected_tests": list(selected_tests),
                        "assign_to": phlebotomist.split("-")[1].strip(),
                        "priority": priority,
                        "collection_date": collection_date,
                        "collection_time": collection_time,
                        "request_status": request_status,
                        "request_id": request_to_edit["id"]
                    }

                    with conn.session as session:
                        try:
                            insert_query = text(
                                """
                                UPDATE requests 
                                SET 
                                    first_name=:first_name, surname=:surname, dob=:dob, 
                                    gender=:gender, phone=:phone,location=:location, request_status=:request_status,
                                    selected_tests=:selected_tests, assign_to=:assign_to, priority=:priority, 
                                    collection_date=:collection_date, collection_time=:collection_time, updated_at=now()
                                WHERE id=:request_id
                                """
                            )
                            session.execute(insert_query, form_data)
                            session.commit()

                            st.session_state.lr_mode = "view"
                            st.session_state.selected_tests = set()
                            st.rerun()
                        except Exception as e:
                            print(e)
                            st.toast(
                                ":red[**Error saving lab request. Please try again or contact system admin for support**]"
                            )
                            st.stop()

            


            # tabs = st.tabs(["Patient Details", "Appointment Details", "Test Details"])

            # st.write(st.session_state.edited_request)

            # with tabs[0]:
            #     # =========================== PATIENT DETAILS =========================================
            #     patient_to_edit = request_to_edit["patient"].split(" ")
            #     with st.container(
            #         border=True,
            #         horizontal=False,
            #         horizontal_alignment="left",
            #         vertical_alignment="top",
            #         height=465,
            #     ):
            #         with st.container(border=False, horizontal=True):
            #             f_name = st.text_input(
            #                 "First Name*",
            #                 value=patient_to_edit[0].strip().replace("_", " "),
            #                 width=350,
            #                 key="edit_patient_first_name",
            #             )
            #             surname = st.text_input(
            #                 "Surname*",
            #                 value=patient_to_edit[2].strip().replace("_", " "),
            #                 width=350,
            #                 key="edit_patient_surname",
            #             )
            #             m_name = st.text_input(
            #                 "Middle Name",
            #                 value=patient_to_edit[1].strip().replace("_", " "),
            #                 width=350,
            #                 placeholder="optional",
            #                 key="edit_patient_middle_name",
            #             )
            #         with st.container(border=False, horizontal=True):
            #             dob = st.date_input(
            #                 "Date of Birth*",
            #                 format="DD/MM/YYYY",
            #                 value=request_to_edit["dob"],
            #                 min_value=datetime(1900, 1, 1),
            #                 width=350,
            #                 key="edit_patient_dob",
            #             )

                        # gender_options = ["Male", "Female", "Other"]
                        # gender = st.selectbox(
                        #     "Gender*",
                        #     options=gender_options,
                        #     index=gender_options.index(request_to_edit["gender"]),
                        #     width=350,
                        #     key="edit_patient_gender",
                        # )

                        # location = st.text_input(
                        #     "Location*",
                        #     width=350,
                        #     value=request_to_edit["location"],
                        #     key="edit_patient_location",
                        # )
            #         with st.container(border=False, horizontal=True):
            #             phone = st.text_input(
            #                 "Phone No:*",
            #                 width=350,
            #                 value=request_to_edit["phone"],
            #                 key="edit_patient_phone",
            #             )

            #             email = st.text_input(
            #                 "Email",
            #                 width=350,
            #                 value=request_to_edit["email"],
            #                 key="edit_patient_email",
            #             )

            # with tabs[1]:
            #     # =========================== APPOINTMENT DETAILS =========================================
            #     with st.container(
            #         border=True,
            #         horizontal=False,
            #         horizontal_alignment="left",
            #         vertical_alignment="top",
            #         height=465,
            #     ):
            #         request_status_options = [
            #             "pending",
            #             "in-progress",
            #             "completed",
            #             "cancelled",
            #         ]
            #         request_status = st.selectbox(
            #             "Status:*",
            #             options=request_status_options,
            #             index=request_status_options.index(
            #                 request_to_edit["request_status"]
            #             ),
            #             key="edit_request_status",
            #             format_func=lambda x: x.title(),
            #         )

            #         # doctor_options = fetch_doctors(conn)["doctor"].to_list()
            #         # current_doctor = request_to_edit["doctor"]
            #         # doctor_match = None

            #         # for doctor in doctor_options:
            #         #     if current_doctor.lower() in doctor.lower():
            #         #         doctor_match = doctor

            #         # doctor = st.selectbox(
            #         #     "Doctor*",
            #         #     options=doctor_options,
            #         #     index=doctor_options.index(doctor_match),
            #         #     placeholder="Select an existing doctor",
            #         #     key="edit_doctor",
            #         # )

            #         # st.divider()
                    # phlebotomist_options = fetch_phlebotomists(conn)[
                    #     "phlebotomist"
                    # ].to_list()
                    # current_phlebotomist = request_to_edit["phlebotomist"]
                    # phlebotomist_match = None

                    # for p in phlebotomist_options:
                    #     if current_phlebotomist in p:
                    #         phlebotomist_match = p

                    # phlebotomist = st.selectbox(
                    #     "Phlebotomist:*",
                    #     options=fetch_phlebotomists(conn),
                    #     index=phlebotomist_options.index(phlebotomist_match),
                    #     key="edit_phlebotomist",
                    # )
            #         # st.divider()

            #         with st.container(
            #             border=False, horizontal=True, horizontal_alignment="distribute"
            #         ):
            #             priorit_options = ["Routine", "Urgent"]
            #             priority = st.selectbox(
            #                 "Priority*",
            #                 options=priorit_options,
            #                 index=priorit_options.index(request_to_edit["priority"]),
            #                 width=400,
            #                 key="edit_priority",
            #             )
            #             collection_date = st.date_input(
            #                 "Collection Date*",
            #                 width=400,
            #                 value=request_to_edit["collection_date"],
            #                 key="edit_collection_date",
            #             )
            #             collection_time = st.time_input(
            #                 "Collection Time*",
            #                 width=400,
            #                 value=request_to_edit["collection_time"],
            #                 key="edit_collection_time",
            #             )

            # with tabs[2]:
            #     # =========================== Test DETAILS =========================================
            #     with st.container(
            #         border=True,
            #         horizontal=False,
            #         horizontal_alignment="left",
            #         vertical_alignment="top",
            #         height=400,
            #     ):
            #         df = prepare_tests_df(conn)
            #         search_tests(df)

            # with st.container(
            #     border=False, horizontal=True, horizontal_alignment="center"
            # ):
            #     cancel_edit = st.button("Cancel Edit")
            #     if cancel_edit:
            #         st.session_state.lr_mode = "view"
            #         st.session_state.request_to_edit = None
            #         st.session_state.selected_tests = set()
            #         st.rerun()

            #     save_edit = st.button("Save Changes")
            #     if save_edit:
            #         if (
            #             not f_name
            #             or not surname
            #             or not dob
            #             or not gender
            #             or not phone
            #             or not location
            #             # or not doctor
            #             or not phlebotomist
            #             or not priority
            #             or not collection_date
            #             or not collection_time
            #             or not request_status
            #         ):
            #             st.toast(":red[Please fill all required details]")
            #             st.stop()

            #         if not st.session_state.get("selected_tests"):
            #             st.toast(":red[Please add tests]")
            #             st.stop()

            #         db_data = {
            #             "first_name": f_name.strip().replace(" ", "_"),
            #             "surname": surname.strip().replace(" ", "_"),
            #             "middle_name": m_name.strip().replace(" ", "_"),
            #             "dob": dob,
            #             "gender": gender.strip(),
            #             "phone": phone.strip(),
            #             "email": email.strip(),
            #             "location": location.strip(),
            #             # doctor in the system
            #             # "doctor_dkl_code": doctor.split("-")[1].strip(),
            #             # tests
            #             "selected_tests": list(
            #                 st.session_state.get("selected_tests", [])
            #             ),
            #             "assign_to": phlebotomist.split("-")[1].strip(),
            #             "priority": priority.strip(),
            #             "collection_date": collection_date,
            #             "collection_time": collection_time,
            #             "request_status": request_status,
            #             "request_id": request_to_edit["id"],
            #         }

                    # with conn.session as session:
                    #     try:
                    #         insert_query = text(
                    #             """
                    #             UPDATE requests 
                    #             SET 
                    #                 first_name=:first_name, surname=:surname, middle_name=:middle_name, dob=:dob, 
                    #                 gender=:gender, phone=:phone, email=:email, location=:location, request_status=:request_status,
                    #                 selected_tests=:selected_tests, assign_to=:assign_to, priority=:priority, 
                    #                 collection_date=:collection_date, collection_time=:collection_time, updated_at=now()
                    #             WHERE id=:request_id
                    #             """
                    #         )
                    #         session.execute(insert_query, db_data)
                    #         session.commit()

                    #         st.session_state.lr_mode = "view"
                    #         st.session_state.selected_tests = set()
                    #         st.rerun()
                    #     except Exception as e:
                    #         print(e)
                    #         st.error(
                    #             "Error saving lab request. Please try again or contact system admin for support"
                    #         )
                    #         st.stop()

        edit_request()


else:
    requests_df = fetch_requests()

    with st.container(
        border=False,
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="bottom",
    ):
        q = st.text_input("Search", placeholder="Search", label_visibility="collapsed")
        if q:
            requests = [
                request
                for request in requests_df.to_dict(orient="records")
                if q.lower() in request["patient"].lower()
            ]
        else:
            requests = requests_df.to_dict(orient="records")

        new_req_btn = st.button("+ Request", icon=":material/add:")
        if new_req_btn:
            st.session_state.lrf_form = {}
            st.session_state.selected_tests = set()
            st.switch_page("admin_pages/new_request.py")

    total_requests = len(requests_df)
    showing_requests = len(requests)
    st.caption(f"Showing {showing_requests}/{total_requests}")

    with st.container(
        border=False, horizontal=True, horizontal_alignment="left", height=450
    ):
        for request in requests:
            with st.container(border=True, width=500):
                with st.container(
                    border=False,
                    horizontal=True,
                    horizontal_alignment="distribute",
                    vertical_alignment="center",
                ):
                    with st.container(
                        border=False, horizontal=False, horizontal_alignment="left"
                    ):
                        req_details_btn = st.button(
                            f":blue[**{request['patient'].strip().replace('_', ' ')}**]",
                            type="tertiary",
                            key=f"{request['id']}",
                        )
                        if req_details_btn:
                            request_details(request)

                    with st.container(
                        border=False,
                        horizontal=True,
                        horizontal_alignment="right",
                        width=110,
                    ):
                        status_color = {
                            "pending": "orange",
                            "in-progress": "blue",
                            "completed": "green",
                            "cancelled": "red",
                        }
                        req_status = request["request_status"]
                        st.badge(req_status.title(), color=status_color[req_status])

                # st.write(f"**👨‍⚕️ Doctor:** {request['doctor']}")
                st.write(f"**🧪 Phlebotomist:** {request['phlebotomist']}")
                st.write(
                    f"📅 **Date:** {request['collection_date']}  "
                    f"⏰ **Time:** {request['collection_time'].strftime('%H:%M %p')}"
                )

                # st.write("")
                with st.container(border=False, horizontal=True):
                    req_edit_btn = st.button(
                        ":blue[Edit]",
                        icon=":material/edit:",
                        type="secondary",
                        key=f"edit{request['id']}",
                    )
                    if req_edit_btn:
                        st.session_state.lr_mode = "edit"
                        st.session_state.request_to_edit = request
                        st.rerun()

                    req_del_btn = st.button(
                        ":red[Delete]",
                        icon=":material/delete:",
                        type="secondary",
                        key=f"del{request['id']}",
                    )
                    if req_del_btn:
                        delete_lab_request(request["id"])
