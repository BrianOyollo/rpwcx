import streamlit as st
import pandas as pd
from sqlalchemy import text, exc
from datetime import datetime

from admin_pages.new_request import fetch_phlebotomists, fetch_doctors

st.set_page_config(page_title="RPWC|Lab Requests", layout="wide")

st.header("Lab Requests", divider="orange")

conn = st.session_state["conn"]


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
        """,
        ttl=0,
    )
    return requests


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
requests_df = fetch_requests()
requests = requests_df.to_dict(orient="records")

q = st.text_input("Search", placeholder='Search', label_visibility='collapsed')
with st.container(border=False, horizontal=True, horizontal_alignment='left', height=450):
    for request in requests:
        with st.container(border=True, width=550):
            with st.container(border=False, horizontal=True, horizontal_alignment='distribute', vertical_alignment='center'):
                with st.container(border=False, horizontal=False, horizontal_alignment='left'):
                    btn = st.button(f":blue[**{request['patient'].strip()}**]", type='tertiary', key=f"{request['id']}")

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
            
            st.write("")
            with st.container(border=False, horizontal=True):
                req_edit_btn = st.button(":blue[Edit]", icon=":material/edit:", type="tertiary",key=f"edit{request['id']}")
                req_del_btn = st.button(":red[Delete]", icon=":material/delete:", type="tertiary",key=f"del{request['id']}")