import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import text, exc

from utils import fetch_categories_and_tests, categorize_selected_tests

conn = st.session_state["conn"]

st.title("My Tasks")


def requests_list(tab: str = None):
    """
    Displays a list of lab requests assigned to the currently logged-in user
    with detailed patient, appointment, and test information.

    Features:
        - Fetches lab requests assigned to the current user (`st.user.email`).
        - Optional filtering by request status via the `tab` parameter
          (e.g., 'pending', 'in-progress', 'completed').
        - Displays patient details: name, gender, age, phone, and location.
        - Shows collection date/time and priority (Routine or Urgent) with visual badges.
        - Displays categorized tests in a popover with color-coded badges.
        - Allows updating the request status directly using a `selectbox`
          (status changes are saved to the database immediately).

    Parameters:
        tab (str, optional): Filter requests by status. Defaults to None (all requests).
    """
    lab_requests = conn.query(
        """
        WITH user_info AS(
            SELECT dkl_code FROM users WHERE email=:email
        )
        SELECT r.* 
        FROM requests r
        INNER JOIN user_info ui ON ui.dkl_code = r.assign_to
        """,
        params={"email": st.user.email},
        ttl=0,
    )
    lab_requests_list = lab_requests.to_dict(orient="records")

    with st.container(
        border=False, horizontal=False, horizontal_alignment="left", height=450
    ):
        if tab is None:
            tab_list = lab_requests_list
        else:
            tab_list = [
                req
                for req in lab_requests_list
                if req["request_status"].strip().lower() == tab.strip().lower()
            ]

        for req in tab_list:
            with st.container(border=True, horizontal=False):
                patient = f"{req['first_name'].replace('_', ' ')} {req['middle_name'].replace('_', ' ')} {req['surname'].replace('_', ' ')}"
                gender = req["gender"]
                age = relativedelta(datetime.today(), req["dob"]).years
                collection_date = req["collection_date"].strftime("%b %d, %Y")
                collection_time = req["collection_time"].strftime("%I:%M %p")
                if req["priority"] == "Urgent":
                    req_priority = "🚨 :red[Urgent]"
                else:
                    req_priority = "📋 Routine"

                st.write(f":blue[**{patient}** ({gender[0]}, {age})]")

                st.markdown(f"""
                    :gray-badge[**☎️ {req["phone"]}**]
                    :gray-badge[**📍 {req["location"]}**]
                    :gray-badge[**⏰ {collection_date} • {collection_time}**]
                    :gray-badge[**{req_priority}**]
                """)

                # with st.expander("Tests"):

                with st.container(
                    border=False,
                    horizontal=True,
                    horizontal_alignment="left",
                    vertical_alignment="center",
                ):
                    with st.popover("🧪 Tests"):
                        categorized_tests = categorize_selected_tests(
                            conn, req["selected_tests"]
                        )
                        for k, v in categorized_tests.items():
                            st.write(f"**:orange[{k}]**")
                            st.markdown(f",".join([f":blue-badge[{req}]" for req in v]))

                    req_status = req["request_status"]
                    req_status_color = {
                        "pending": "orange",
                        "in-progress": "blue",
                        "completed": "green",
                        "cancelled": "red",
                    }

                    def update_req_status(id: int, radio_key: str):
                        new_status = st.session_state[radio_key]
                        with conn.session as session:
                            try:
                                query = text(
                                    "UPDATE requests SET request_status=:request_status WHERE id=:id"
                                )
                                session.execute(
                                    query, {"request_status": new_status, "id": id}
                                )
                                session.commit()
                            except Exception as e:
                                print(e)
                                st.toast(
                                    ":red['Error updating request status. Please try again']"
                                )

                    # with st.popover(f":{req_status_color[req_status]}[{req_status.title()}]", type='secondary'):
                    request_status_options = ["pending", "in-progress", "completed"]
                    radio_key = f"status_radio_{req['id']}_{tab}"
                    st.selectbox(
                        "Update Status",
                        key=radio_key,
                        options=request_status_options,
                        index=request_status_options.index(req_status),
                        format_func=lambda x: x.title(),
                        on_change=update_req_status,
                        args=(req["id"], radio_key),
                        label_visibility="collapsed",
                        width=135,
                    )


tabs = st.tabs(["All", "Pending", "In Progress", "Completed", "Cancelled"])

with tabs[0]:
    requests_list()

with tabs[1]:
    requests_list(tab="Pending")

with tabs[2]:
    requests_list(tab="In-Progress")

with tabs[3]:
    requests_list(tab="Completed")

with tabs[4]:
    requests_list(tab="Cancelled")
