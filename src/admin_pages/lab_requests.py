import streamlit as st
import pandas as pd
from sqlalchemy import text, exc
from datetime import datetime

from admin_pages.new_request import fetch_phlebotomists, fetch_doctors, search_tests, prepare_tests_df

st.set_page_config(page_title="RPWC|Lab Requests", layout="wide")

st.header("Lab Requests", divider="orange")

conn = st.session_state["conn"]

if "lr_mode" not in st.session_state:
    st.session_state.lr_mode = 'view'

if 'request_to_edit' not in st.session_state:
    st.session_state.request_to_edit = None

if 'edited_request' not in st.session_state:
    st.session_state.edited_request = {}

def fetch_requests():
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
            d.name as doctor,
            p.name as phlebotomist,
            r.request_status, r.created_at, r.updated_at          
        FROM requests r
        JOIN doctors d on d.dkl_code = r.doctor_dkl_code
        JOIN phlebotomists p on p.dkl_code = r.assign_to
        ORDER BY created_at DESC;	
        """,
        ttl=0,
    )
    return requests

@st.dialog(":green[Request Details]")
def request_details(request):
    
    with st.container(border=False, horizontal=False, horizontal_alignment='center', height=450):
        st.caption("------------ Patient Details ------------ ")
        st.write(f":orange[**Name**]: **{request['patient'].strip()}**")
        st.write(f":orange[**Gender**]: **{request['gender']}**")
        st.write(f":orange[**DoB**]: **{request['dob']}**")
        st.write(f":orange[**Location**]: **{request['location'].strip()}**")
        st.write(f":orange[**Contacts**]: **{request['phone'].strip()}, {request['email'].strip()}**")
        
        st.caption("------------ Doctor/Phlebotomist ------------ ")
        st.write(f":orange[**Dcotor**]: **{request['doctor']}**")
        st.write(f":orange[**Phlebotomist**]: **{request['phlebotomist']}**")

        st.caption("------------ Test Details ------------ ")
        st.write(f":orange[**Created on**]: **{request['created_at'].strftime("%b %d, %Y • %I:%M %p")}**")
        st.write(f":orange[**Updated on**]: **{request['updated_at'].strftime("%b %d, %Y • %I:%M %p") if request['updated_at']  else "N/A"}**")
        st.write(f":orange[**Request Priority**]: **{request['priority']}**")
        st.write(f":orange[**Collection Date**]: **{request['collection_date']} at {request['collection_time'].strftime("%H:%M %p")}**")
        tests_badges = [f":gray-badge[{test}]" for test in request['selected_tests']]
        st.markdown(f":orange[**Tests**]: {' '.join(tests_badges)}")


def edit_request(request):
    pass

@st.dialog("Delete Lab Request")
def delete_lab_request(request_id):
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
                    st.rerun()


# st.write(requests)
if st.session_state.lr_mode == 'edit' and st.session_state.get('request_to_edit'):
    with st.container(border=False, horizontal=False, horizontal_alignment='left'):

        request_to_edit = st.session_state.request_to_edit
                      
        @st.fragment
        def edit_request():
            tabs = st.tabs(['Patient Details', 'Appointment Details', 'Test Details'])
            
            # st.write(st.session_state.edited_request)

            with tabs[0]:
                # =========================== PATIENT DETAILS =========================================
                patient_to_edit = request_to_edit['patient'].split(" ")
                with st.container(border=True, horizontal=False, horizontal_alignment='left', vertical_alignment='top', height=465):

                    with st.container(border=False, horizontal=True):
                        f_name = st.text_input(
                            "First Name*",
                            value=patient_to_edit[0].strip().replace("_", " "),
                            width=350,
                            key = "edit_patient_first_name"
                        )
                        surname = st.text_input(
                            "Surname*", 
                            value=patient_to_edit[2].strip().replace("_", " "), 
                            width=350,
                            key = 'edit_patient_surname'
                        )
                        m_name = st.text_input(
                            "Middle Name", 
                            value=patient_to_edit[1].strip().replace("_", " "),
                            width=350, 
                            placeholder="optional",
                            key = 'edit_patient_middle_name'
                        )
                    with st.container(border=False, horizontal=True):
                        dob = st.date_input(
                            "Date of Birth*",
                            format="DD/MM/YYYY",
                            value = request_to_edit['dob'],
                            min_value=datetime(1900, 1, 1),
                            width=350,
                            key = "edit_patient_dob"
                        )

                        gender_options = ["Male", "Female", "Other"]
                        gender = st.selectbox(
                            "Gender*",
                            options=gender_options,
                            index=gender_options.index(request_to_edit['gender']),
                            width=350,
                            key = 'edit_patient_gender'
                        )

                        location = st.text_input(
                            "Location*", 
                            width=350,
                            value = request_to_edit['location'],
                            key = 'edit_patient_location'
                        )
                    with st.container(border=False, horizontal=True):
                        phone = st.text_input(
                            "Phone No:*", 
                            width=350,
                            value = request_to_edit['phone'],
                            key = "edit_patient_phone"
                        )

                        email = st.text_input(
                            "Email", 
                            width=350,
                            value = request_to_edit['email'] ,
                            key = 'edit_patient_email'
                        ) 

            with tabs[1]:
                # =========================== APPOINTMENT DETAILS =========================================
                with st.container(border=True, horizontal=False, horizontal_alignment='left', vertical_alignment='top', height=465):
                    doctor_options = fetch_doctors()['doctor'].to_list()
                    current_doctor = request_to_edit['doctor']
                    doctor_match = None

                    for doctor in doctor_options:
                        if current_doctor.lower() in doctor.lower():
                            doctor_match = doctor

                    doctor = st.selectbox(
                        "Doctor*",
                        options=doctor_options,
                        index=doctor_options.index(doctor_match),
                        placeholder="Select an existing doctor",
                        key = 'edit_doctor'
                    )

                    # st.divider()
                    phlebotomist_options = fetch_phlebotomists()['phlebotomist'].to_list()
                    current_phlebotomist = request_to_edit['phlebotomist']
                    phlebotomist_match = None

                    for p in phlebotomist_options:
                        if current_phlebotomist in p:
                            phlebotomist_match = p

                    phlebotomist = st.selectbox(
                        "Phlebotomist:*", 
                        options=fetch_phlebotomists(), 
                        index=phlebotomist_options.index(phlebotomist_match),
                        key = 'edit_phlebotomist'
                    )
                    # st.divider()

                    with st.container(border=False, horizontal=True, horizontal_alignment="distribute"):
                        priorit_options = ["Routine", "Urgent"]
                        priority = st.selectbox(
                            "Priority*",
                            options=priorit_options,
                            index=priorit_options.index(request_to_edit['priority']),
                            width=400,
                            key = 'edit_priority'
                        )
                        collection_date = st.date_input("Collection Date*", width=400, value=request_to_edit['collection_date'], key = 'edit_collection_date')
                        collection_time = st.time_input("Collection Time*", width=400, value=request_to_edit['collection_time'], key = 'edit_collection_time')

            with tabs[2]:
            # =========================== APPOINTMENT DETAILS =========================================
                with st.container(border=True, horizontal=False, horizontal_alignment='left', vertical_alignment='top', height=465):
                    st.session_state.selected_tests = set(request_to_edit['selected_tests'])
                    df = prepare_tests_df()
                    search_tests(df)

            with st.container(border=False, horizontal=True, horizontal_alignment='center'):
                cancel_edit = st.button("Cancel Edit")
                if cancel_edit:
                    st.session_state.lr_mode = 'view'
                    st.session_state.request_to_edit = None
                    st.session_state.selected_tests = set()
                    st.rerun()
                
                save_edit = st.button("Save Changes")
                if save_edit:
                    
                    db_data = {
                        "first_name": f_name.strip().replace(" ", "_"),
                        "surname": surname.strip().replace(" ", "_"),
                        "middle_name": m_name.strip().replace(" ", "_"),
                        "dob": dob,
                        "gender": gender.strip(),
                        "phone": phone.strip(),
                        "email": email.strip(),
                        "location": location.strip(),
                        # doctor in the system
                        "doctor_dkl_code": doctor.split("-")[1].strip() ,
                        # tests
                        "selected_tests": list(st.session_state.get("selected_tests", [])),
                        "assign_to": phlebotomist.split("-")[1].strip(),
                        "priority": priority.strip(),
                        "collection_date": collection_date,
                        "collection_time": collection_time,
                        "request_id":request_to_edit['id']
                    }

                    with conn.session as session:
                        try:
                            insert_query = text(
                                """
                                UPDATE requests 
                                SET 
                                    first_name=:first_name, surname=:surname, middle_name=:middle_name, dob=:dob, 
                                    gender=:gender, phone=:phone, email=:email, location=:location, 
                                    doctor_dkl_code=:doctor_dkl_code,selected_tests=:selected_tests, assign_to=:assign_to, priority=:priority, 
                                    collection_date=:collection_date, collection_time=:collection_time, updated_at=now()
                                WHERE id=:request_id
                                """
                            )
                            session.execute(insert_query, db_data)
                            session.commit()

                            st.session_state.lr_mode = 'view'
                            st.session_state.selected_tests = set()
                            st.rerun()
                        except Exception as e:
                            print(e)
                            st.error(
                                "Error saving lab request. Please try again or contact system admin for support"
                            )
                            st.stop()
                    
        edit_request()

        

else:
    requests_df = fetch_requests()

    with st.container(border=False, horizontal=True, horizontal_alignment='distribute', vertical_alignment='bottom'):
        q = st.text_input("Search", placeholder='Search', label_visibility='collapsed')
        if q:
            requests = [request for request in requests_df.to_dict(orient="records") if q.lower() in request['patient'].lower()]
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
    
    with st.container(border=False, horizontal=True, horizontal_alignment='left', height=450):
        for request in requests:
            with st.container(border=True, width=600):
                with st.container(border=False, horizontal=True, horizontal_alignment='distribute', vertical_alignment='center'):
                    with st.container(border=False, horizontal=False, horizontal_alignment='left'):
                        req_details_btn = st.button(f":blue[**{request['patient'].strip().replace("_", " ")}**]", type='tertiary', key=f"{request['id']}")
                        if req_details_btn:
                            request_details(request)

                    with st.container(border=False, horizontal=True, horizontal_alignment='right', width=110):
                        status_color = {
                            "pending": "orange",
                            "in-progress": "blue",
                            "completed": "green",
                            "cancelled": "red"
                        }
                        req_status = request['request_status']
                        st.badge(req_status.title(), color=status_color[req_status])

                st.write(f"**👨‍⚕️ Doctor:** {request['doctor']}")
                st.write(f"**🧪 Phlebotomist:** {request['phlebotomist']}")
                st.write(
                    f"📅 **Date:** {request['collection_date']}  "
                    f"⏰ **Time:** {request['collection_time'].strftime("%H:%M %p")}"
                )
                
                # st.write("")
                with st.container(border=False, horizontal=True):
                    req_edit_btn = st.button(":blue[Edit]", icon=":material/edit:", type="secondary",key=f"edit{request['id']}")
                    if req_edit_btn:
                        st.session_state.lr_mode = 'edit'
                        st.session_state.request_to_edit = request
                        st.rerun()

                    req_del_btn = st.button(":red[Delete]", icon=":material/delete:", type="secondary",key=f"del{request['id']}")
                    if req_del_btn:
                        delete_lab_request(request['id'])