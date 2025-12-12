import streamlit as st
from sqlalchemy import text, exc
import pandas as pd
import random
import time

st.set_page_config(page_title="RPWC|Users", layout="wide")

conn = st.session_state["conn"]
duck_conn = st.session_state["duck_conn"]

if "users_upated" not in st.session_state:
    st.session_state.users_updated = False

st.title("Users")


@st.cache_data(ttl=60 * 2)
def fetch_all_users():
    """
    Fetches all active, non-deleted users from the database.

    Returns:
        pd.DataFrame: A DataFrame containing user details with columns:
            - dkl_code: Unique identifier for the user
            - name: Full name of the user
            - email: User's email address
            - contact: User's phone/contact number
            - user_type: Role of the user (e.g., doctor, phlebotomist)
            - active: Boolean indicating if the user is active
            - created_at: Timestamp of when the user was created

    Notes:
        - The results are sorted by name in descending order.
        - Data is cached for 2 minutes to reduce repeated database calls.
        - If fetching fails, the function stops execution and shows an error message.
    """
    try:
        users = conn.query(
            "SELECT dkl_code, name, email, contact, user_type,active, created_at FROM users WHERE is_deleted=false;",
            show_spinner=True,
            ttl=0,
        )
        users = users.sort_values("name", ascending=False).reset_index(drop=True)
        return users
    except Exception as e:
        st.error(
            "Error fetching users from the db. Contact system admin for assistance if the issue persists"
        )
        st.stop()


users_df = fetch_all_users()
users_df["user_type"] = users_df["user_type"].astype("str").str.title()

tab1, tab2 = st.tabs([f"All Users({len(users_df)})", "Edit Users"])

with tab1:
    with st.container(
        border=False,
        horizontal=False,
        horizontal_alignment="center",
        vertical_alignment="top",
        height=500,
    ):
        with st.container(
            horizontal=True, horizontal_alignment="left", vertical_alignment="bottom"
        ):
            search = st.text_input(
                "Search", width=500, label_visibility="collapsed", placeholder="search"
            )
            if search:
                users_df = users_df[
                    users_df["dkl_code"]
                    .astype("str")
                    .str.contains(search, case=False, na=False)
                    | users_df["name"]
                    .astype("str")
                    .str.contains(search, case=False, na=False)
                    | users_df["email"]
                    .astype("str")
                    .str.contains(search, case=False, na=False)
                ]

        with st.sidebar:
            st.write("Filter")
            role = st.selectbox(
                "Role", options=["Admin", "Phlebotomist", "Doctor"], index=None
            )
            if role:
                users_df = users_df[users_df["user_type"].str.lower() == role.lower()]

            active = st.selectbox(
                "Active Status", options=["Active", "Inactive"], index=None
            )
            if active:
                if active == "Active":
                    users_df = users_df[users_df["active"] == True]
                else:
                    users_df = users_df[users_df["active"] == False]

        st.dataframe(
            users_df,
            hide_index=True,
            # height="stretch",
            column_order=(
                "dkl_code",
                "name",
                "email",
                "contact",
                "user_type",
                "active",
            ),
            column_config={
                "dkl_code": st.column_config.TextColumn(
                    "DKL Code", pinned=True, width="small"
                ),
                "name": st.column_config.TextColumn("Name", pinned=True),
                "email": st.column_config.TextColumn("Email"),
                "contact": st.column_config.TextColumn("Phone No."),
                "user_type": st.column_config.TextColumn("Role"),
                "active": st.column_config.CheckboxColumn("Active"),
                "created_at": st.column_config.DatetimeColumn(
                    "Created", disabled=True, format="calendar"
                ),
            },
        )
        total_users = len(fetch_all_users())
        st.caption(f"Showing {len(users_df)} of {total_users}")

    @st.dialog("New User")
    def add_new_user():
        """
        Displays a dialog form to add a new user to the system.

        Functionality:
            - Collects user details: DKL Code, Full Name, Email, Phone, and Role.
            - Validates that all fields are filled before submission.
            - Inserts the new user into the `users` table in the database.
            - Handles integrity errors for duplicate DKL code or email.
            - Clears the cached list of users and refreshes the page upon successful addition.

        Notes:
            - Roles are limited to "Doctor", "Phlebotomist", or "Admin".
            - All DKL codes are stored in lowercase.
            - On error, displays an appropriate message and stops further execution.
        """
        with st.form("add-user"):
            dkl_code = st.text_input("DKL Code", key="dkl_code")
            full_name = st.text_input("Full Names", key="full_name")
            email = st.text_input("Email", key="email")
            phone = st.text_input("Phone", key="phone")
            role = st.selectbox("Role", options=["Doctor", "Phlebotomist", "Admin"])

            with st.container(horizontal=True, horizontal_alignment="center"):
                save_user = st.form_submit_button("Save User")

            if save_user:
                if not dkl_code or not full_name or not email or not phone or not role:
                    st.error("Please fill all the fields")
                    st.stop()

                with conn.session as session:
                    query = text(
                        """
                        INSERT INTO users(dkl_code, name, contact, email, user_type)
                        VALUES(:dkl_code, :name, :contact, :email, :user_type)
                        """
                    )
                    try:
                        session.execute(
                            query,
                            {
                                "dkl_code": dkl_code.lower(),
                                "name": full_name,
                                "contact": phone,
                                "email": email,
                                "user_type": role.lower(),
                            },
                        )
                        session.commit()
                        fetch_all_users.clear()
                        st.rerun()
                    except exc.IntegrityError as e1:
                        err_msg = str(e1.orig)
                        if ("dkl_code") in err_msg:
                            st.error("This DKL code already exists")
                            st.stop()
                        elif "(email)" in err_msg:
                            st.error("A user with this email already exists")
                            st.stop()
                        else:
                            st.error("Database error. Contact system admin for support")
                            st.stop()
                    except Exception as e2:
                        st.error(
                            "Error adding new user. Contact system admin for support if the issue persists"
                        )
                        st.stop()

    with st.container(horizontal=True, horizontal_alignment="center"):
        st.button("Add User", on_click=add_new_user)
        refresh = st.button(
            "Refresh Users", icon=":material/refresh:", key="tab1_refresh"
        )
        if refresh:
            fetch_all_users.clear()
            st.rerun()


with tab2:
    if "editor_key" not in st.session_state:
        st.session_state.editor_key = 0

    if "update_message" not in st.session_state:
        st.session_state.update_message = ""

    def update_users(users_df, modified_df):
        """
        Updates users in the database based on differences between the original and modified dataframes.
        Only updates: name, email, contact, user_type, and active status.
        The dkl_code is used as the unique identifier for matching records.

        Args:
            users_df (pd.DataFrame): Original users dataframe.
            modified_df (pd.DataFrame): Modified users dataframe with edits to apply.

        Notes:
            - Rows missing in modified_df but present in users_df are marked as deleted (is_deleted=True, active=False).
            - Only fields that differ between original and modified dataframes are updated.

        By the way:
            Streamlit provides an easy way to detect added, deleted, or modified rows using
            `st.data_editor` with a session key. This can sometimes save you from
            doing the full comparison yourself:
                st.data_editor(df, key="my_key", num_rows="dynamic")
                st.session_state["my_key"]  # contains the edited data
            I didn’t know this when I wrote this function 😅
        """

        duck_conn.register("original", users_df)
        duck_conn.register("modified", modified_df)

        deleted_users = duck_conn.sql(
            """
        SELECT dkl_code FROM original
        WHERE dkl_code NOT IN (SELECT dkl_code FROM modified);
        """
        ).fetchall()

        print("----------- ORIGINAL DF IN DUCKDB-----------")
        duck_conn.sql("select * from original")

        print("----------- modified DF IN DUCKDB-----------")
        duck_conn.sql("select * from modified")

        modified_users = duck_conn.sql(
            """
            SELECT m.dkl_code, m.name, m.email, m.contact, m.user_type, m.active
            FROM modified m
            INNER JOIN original o ON m.dkl_code=o.dkl_code
            WHERE 
                m.name != o.name 
                OR m.email != o.email 
                OR m.contact != o.contact 
                OR m.user_type != o.user_type 
                OR m.active != o.active
            """
        ).fetchall()
        print(modified_users)

        with conn.session as session:
            try:
                if deleted_users:
                    deleted_codes = list(row[0] for row in deleted_users if row)
                    delete_query = text(
                        "UPDATE users SET is_deleted=true, active=false WHERE dkl_code = ANY(:deleted_codes)"
                    )
                    session.execute(delete_query, {"deleted_codes": deleted_codes})

                if modified_users:
                    update_query = text(
                        """
                        UPDATE users
                        SET name=:name, email=:email, contact=:contact, user_type=:user_type, active=:active
                        WHERE dkl_code=:dkl_code
                        """
                    )
                    modified_user_data = [
                        {
                            "dkl_code": row[0],
                            "name": row[1],
                            "email": row[2],
                            "contact": row[3],
                            "user_type": row[4],
                            "active": row[5],
                        }
                        for row in modified_users
                    ]
                    session.execute(update_query, modified_user_data)

                session.commit()  # commit changes
                st.session_state.editor_key += 1  # reset editor key
                fetch_all_users.clear()  # clearch cached users
                st.session_state.users_updated = True
                st.session_state.update_message = f":green['Users updated!']"
                st.rerun(scope="fragment")
            except exc.IntegrityError as e1:
                e1_msg = str(e1.orig)
                if "(email)" in e1_msg:
                    st.session_state.update_message = (
                        f":red['Duplicated emails detected']"
                    )
                else:
                    st.session_state.update_message = (
                        f":red['Database error. Contact system admin for support']"
                    )
                st.rerun(scope="fragment")
            except Exception as e:
                st.session_state.update_message = (
                    f":red['System error. Contact system admin for support']"
                )
                st.rerun(scope="fragment")

    @st.fragment
    def users_editor():
        """
        Provides an interactive interface to view, search, edit, and update users in the system.

        Features:
            - Displays all active users in a data editor table with editable columns:
            name, email, contact, user_type, and active status.
            - Search functionality for DKL code, name, or email.
            - Dynamic addition of new rows (note: new rows added here are not saved automatically).
            - Tracks modifications and allows undoing changes before saving.
            - Validates that required fields are not empty before saving.
            - Saves changes to the database using `update_users`.

        Columns Configuration:
            - dkl_code: non-editable, pinned
            - name, email, contact, user_type, active: editable
            - created_at: non-editable, datetime display

        By the way:
            Streamlit’s `st.data_editor` automatically stores changes in session state when a `key` is set.
            This makes it easy to access only the modified rows rather than the full dataframe:
                st.data_editor(df, key="my_key", num_rows="dynamic")
                st.session_state["my_key"]  # contains the edited data
            Handy for detecting new, deleted, or changed rows without manual comparison.
        """
        if st.session_state.update_message:
            st.toast(st.session_state.update_message)
            st.session_state.update_message = ""

        users_df = fetch_all_users()

        tab2_ctn = st.container(
            border=False,
            horizontal=False,
            horizontal_alignment="center",
            vertical_alignment="top",
            height=500,
        )
        with tab2_ctn:
            with st.container(
                horizontal=True,
                horizontal_alignment="left",
                vertical_alignment="bottom",
            ):
                search = st.text_input(
                    "Search",
                    width=500,
                    label_visibility="collapsed",
                    placeholder="search",
                    key="tab2_search",
                )
                if search:
                    users_df = users_df[
                        users_df["dkl_code"]
                        .astype("str")
                        .str.contains(search, case=False, na=False)
                        | users_df["name"]
                        .astype("str")
                        .str.contains(search, case=False, na=False)
                        | users_df["email"]
                        .astype("str")
                        .str.contains(search, case=False, na=False)
                    ]

            modified_df = st.data_editor(
                users_df,
                key=f"tab2_editor_{st.session_state['editor_key']}",
                hide_index=True,
                # height="stretch",
                num_rows="dynamic",
                column_order=(
                    "dkl_code",
                    "name",
                    "email",
                    "contact",
                    "user_type",
                    "active",
                ),
                column_config={
                    "dkl_code": st.column_config.TextColumn(
                        "DKL Code", pinned=True, width="small", disabled=True
                    ),
                    "name": st.column_config.TextColumn(
                        "Name", pinned=True, required=True
                    ),
                    "email": st.column_config.TextColumn("Email", required=True),
                    "contact": st.column_config.TextColumn("Phone No.", required=True),
                    "user_type": st.column_config.SelectboxColumn(
                        "Role",
                        options=["admin", "phlebotomist", "doctor"],
                        required=True,
                        format_func=lambda x: x.title(),
                    ),
                    "active": st.column_config.CheckboxColumn("Active", required=True),
                    "created_at": st.column_config.DatetimeColumn(
                        "Created", disabled=True, format="calendar"
                    ),
                },
            )
            st.caption(f"Total users {len(modified_df)}")

            # st.dataframe(modified_df)

        with st.container(horizontal=True, horizontal_alignment="center"):
            if modified_df.equals(users_df):
                with st.container(horizontal=False):
                    st.caption(
                        "Click any cell to edit. :red[Any new rows added here will not be saved]"
                    )

            else:
                undo = st.button("Reset", icon=":material/undo:", key="tab2_refresh")
                if undo:
                    st.session_state.editor_key += 1
                    st.rerun(scope="fragment")

                save_changes_btn = st.button("Save Changes", icon=":material/save:")
                if save_changes_btn:
                    # check for empty null or empty values
                    cols_to_check = ["name", "email", "contact", "user_type", "active"]
                    for col in cols_to_check:
                        if (
                            modified_df[col].isnull().any()
                            or (modified_df[col].astype(str).str.strip() == "").any()
                        ):
                            st.toast(f":red[**{col.title()}** can not be empty!]")
                            st.stop()

                    update_users(users_df, modified_df)

    users_editor()
