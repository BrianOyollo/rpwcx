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

st.header("Users", divider="orange")

@st.cache_data(ttl=60 * 2)
def fetch_all_users():
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
            height="stretch",
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

    @st.dialog("New User")
    def add_new_user():
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
        """Only updates name, email, phone and active status
        dkl code is used to update the fields in the db
        """

        duck_conn.register("original", users_df)
        duck_conn.register("modified", modified_df)

        deleted_users = duck_conn.sql(
            """
        SELECT dkl_code FROM original
        WHERE dkl_code NOT IN (SELECT dkl_code FROM modified);
        """
        ).fetchall()

        print("----------- ORINAL DF IN DUCKDB-----------")
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
                height="stretch",
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

            # st.dataframe(modified_df)

        with st.container(horizontal=True, horizontal_alignment="center"):
            if modified_df.equals(users_df):
                with st.container(horizontal=False):
                    st.caption("Click any cell to edit")
                    st.caption(
                        ":red[**Note:**] Any new rows added here will not be saved"
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


# def prepare_users_updates(original_df, modified_df):

#     # check for duplicate emails or dkl_codes
#     modified_df_emails = modified_df['email'].to_list()
#     duplicate_emails = [ e for e in modified_df_emails if modified_df_emails.count(e)>1]

#     modified_df_dkl_codes = modified_df['dkl_code'].to_list()
#     duplicate_dkl_codes = [ c for c in modified_df_dkl_codes if modified_df_dkl_codes.count(c)>1 ]

#     if duplicate_emails:
#         message = f":red[Duplicate emails detected in the update]"
#         st.session_state['update_users_msg'] = message
#         st.rerun()

#     if duplicate_dkl_codes:
#         message = f":red[Duplicate DKL codes detected in the update]. \n {', '.join(set(duplicate_dkl_codes))}"
#         st.session_state['update_users_msg'] = message
#         st.rerun()


#     duck_conn.register("original_df", original_df)
#     duck_conn.register("modified_df", modified_df)

#     # new_users
#     new_users = duck_conn.sql("""
#         SELECT dkl_code, name, email, contact, user_type
#         FROM modified_df
#         WHERE email NOT IN (SELECT email FROM original_df)
#     """).fetchall()

#     # # modified users
#     modified_users = duck_conn.sql("""
#         SELECT m.*,
#         FROM modified_df m
#         JOIN original_df o ON o.email=m.email
#         WHERE m.name != o.name OR m.contact != o.contact OR m.user_type != o.user_type OR m.active != o.active
#         """).fetchall()

#     # # deleted users
#     deleted_users = duck_conn.sql("""
#         SELECT email,
#         FROM  original_df
#         WHERE email NOT IN (SELECT email FROM modified_df)
#     """).fetchall()

#     return new_users, modified_users,deleted_users


# @st.dialog("Review Changes")
# def save_user_updates(new_users, modified_users, deleted_users):
#     warning_texts = []
#     if new_users:
#         warning_texts.append(f"Add {len(new_users)} new user(s)")
#     if modified_users:
#         warning_texts.append(f"Modify {len(modified_users)} user(s)")
#     if deleted_users:
#         warning_texts.append(f"Delete {len(deleted_users)} user(s)")

#     st.warning(
#         "### Are you sure you want to make the following changes: \n"
#         + "\n".join(f"- {text}" for text in warning_texts)
#     )

#     with st.container(
#         border=False,
#         horizontal=True,
#         horizontal_alignment="center",
#         vertical_alignment="center",
#     ):
#         cancel_btn = st.button("Cancel", type="secondary")
#         save_btn = st.button("Confirm", type="secondary")

#     if cancel_btn:
#         st.rerun()

#     if save_btn:
#         with conn.session as session:
#             # --- Add users ---
#             if new_users:
#                 new_users_query = text(
#                     """
#                     INSERT INTO users(dkl_code, name, email, contact, user_type)
#                     VALUES(:dkl_code, :name, :email, :contact, :user_type);
#                     """
#                 )
#                 new_users_data = [
#                     {
#                         "dkl_code": new_user[0],
#                         "name": new_user[1],
#                         "email": new_user[2],
#                         "contact": new_user[3],
#                         "user_type": new_user[4],
#                     }
#                     for new_user in new_users
#                 ]
#                 print(new_users_data)
#                 session.execute(new_users_query, new_users_data)

#             # --- Modify users ---
#             if modified_users:
#                 modify_users_query = text(
#                     """
#                     UPDATE users
#                     SET name=:name, contact=:contact, user_type=:user_type, active=:active
#                     WHERE email=:email AND dkl_code=:dkl_code
#                     """
#                 )
#                 modified_users_data = [
#                     {   "dkl_code": row[0],
#                         "name": row[1],
#                         "email": row[2],
#                         "contact": row[3],
#                         "user_type": row[4],
#                         "active": row[4],
#                     }
#                     for row in modified_users
#                 ]
#                 session.execute(modify_users_query, modified_users_data)

#             # --- Delete users ---
#             if deleted_users:
#                 # Soft-delete users instead of removing them from the database.
#                 # In this system, historical audit trails matter — doctors or staff
#                 # might leave, but their past actions (requests, approvals, etc.)
#                 # must remain traceable. Therefore, we mark them inactive and is_deleted instead of deleting.
#                 # delete_query = text("DELETE FROM users WHERE email=:email;")
#                 delete_query = text("UPDATE users SET is_deleted=true, active=false WHERE email=:email")
#                 data = [{"email": row[0]} for row in deleted_users]
#                 session.execute(delete_query, data)

#             session.commit()
#             st.rerun()


# st.subheader(":orange[Users]")
# users = fetch_all_users()

# modified_df = st.data_editor(
#     users,
#     num_rows="dynamic",
#     hide_index=True,
#     column_order=("dkl_code","name", "email", "contact", "user_type", "active"),
#     column_config={
#         "dkl_code": st.column_config.TextColumn("DKL Code", pinned=True, width='small'),
#         "name": st.column_config.TextColumn("Name", pinned=True),
#         "email": st.column_config.TextColumn("Email"),
#         "contact": st.column_config.TextColumn("Phone No."),
#         "user_type": st.column_config.SelectboxColumn(
#             "Role", options=["admin", "phlebotomist", 'doctor']
#         ),
#         "active": st.column_config.CheckboxColumn("Active"),
#         "created_at": st.column_config.DatetimeColumn(
#             "Created", disabled=True, format="calendar"
#         ),
#     },
# )


# buttons_container = st.container(
#     border=False,
#     horizontal=True,
#     horizontal_alignment="center",
#     vertical_alignment="center",
# )

# with buttons_container:
#     save_changes_btn = st.button("Update Users")
#     if save_changes_btn:

#         new_users, modified_users, deleted_users = prepare_users_updates(
#             users, modified_df
#         )
#         if not new_users and not modified_users and not deleted_users:
#             st.rerun()
#         else:
#             save_user_updates(new_users, modified_users, deleted_users)
