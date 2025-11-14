import streamlit as st
from sqlalchemy import text

st.set_page_config(page_title="RPWC|Users", layout="wide")


conn = st.session_state["conn"]
duck_conn = st.session_state["duck_conn"]


def fetch_all_users():
    users = conn.query(
        "SELECT name, email, contact, user_type,active, created_at FROM users;",
        show_spinner=True,
        ttl=0,
    )
    users = users.sort_values("created_at", ascending=False).reset_index(drop=True)
    users.index += 1
    return users


def prepare_users_updates(original_df, modified_df):
    duck_conn.register("original_df", original_df)
    duck_conn.register("modified_df", modified_df)

    # new_users
    new_users = duck_conn.sql("""
        select name, email, contact, user_type
        from modified_df 
        where Email not in (select email from original_df)
    """).fetchall()

    # modified users
    modified_users = duck_conn.sql("""
            select m.name, m.email, m.contact, m.user_type, m.active,
            from modified_df m
            join original_df o on o.email=m.email
            where m.name != o.name OR m.contact != o.contact OR m.user_type != o.user_type OR m.active != o.active
        """).fetchall()

    # deleted users
    deleted_users = duck_conn.sql("""
        select email,
        from original_df 
        where Email not in (select email from modified_df)
    """).fetchall()

    return new_users, modified_users, deleted_users


@st.dialog("Review Changes")
def save_user_updates(new_users, modified_users, deleted_users):
    warning_texts = []
    if new_users:
        warning_texts.append(f"Add {len(new_users)} new user(s)")
    if modified_users:
        warning_texts.append(f"Modify {len(modified_users)} user(s)")
    if deleted_users:
        warning_texts.append(f"Delete {len(deleted_users)} user(s)")

    st.warning(
        "### Are you sure you want to make the following changes: \n"
        + "\n".join(f"- {text}" for text in warning_texts)
    )

    with st.container(
        border=False,
        horizontal=True,
        horizontal_alignment="center",
        vertical_alignment="center",
    ):
        cancel_btn = st.button("Cancel", type="secondary")
        save_btn = st.button("Confirm", type="secondary")

    if cancel_btn:
        st.rerun()

    if save_btn:
        with conn.session as session:
            # --- Add users ---
            if new_users:
                new_users_query = text(
                    """
                    INSERT INTO users(name, email, contact, user_type)
                    VALUES(:name, :email, :contact, :user_type);
                    """
                )
                new_users_data = [
                    {
                        "name": new_user[0],
                        "email": new_user[1],
                        "contact": new_user[2],
                        "user_type": new_user[3],
                    }
                    for new_user in new_users
                ]
                session.execute(new_users_query, new_users_data)

            # --- Modify users ---
            if modified_users:
                modify_users_query = text(
                    """
                    UPDATE users
                    SET name=:name, email=:email, contact=:contact, user_type=:user_type, active=:active
                    WHERE email=:email
                    """
                )
                modified_users_data = [
                    {
                        "name": row[0],
                        "email": row[1],
                        "contact": row[2],
                        "user_type": row[3],
                        "active": row[4],
                    }
                    for row in modified_users
                ]
                session.execute(modify_users_query, modified_users_data)

            # --- Delete users ---
            if deleted_users:
                delete_query = text("DELETE FROM users WHERE email=:email;")
                data = [{"email": row[0]} for row in deleted_users]
                session.execute(delete_query, data)

            session.commit()
            st.rerun()


st.subheader(":orange[Users]")
users = fetch_all_users()

modified_df = st.data_editor(
    users,
    num_rows="dynamic",
    hide_index=True,
    column_order=("name", "email", "contact", "user_type", "active"),
    column_config={
        "name": st.column_config.TextColumn("Name", pinned=True),
        "email": st.column_config.TextColumn("Email"),
        "contact": st.column_config.TextColumn("Phone No."),
        "user_type": st.column_config.SelectboxColumn(
            "Role", options=["admin", "phlebotomist"]
        ),
        "active": st.column_config.CheckboxColumn("Active"),
        "created_at": st.column_config.DatetimeColumn(
            "Created", disabled=True, format="calendar"
        ),
    },
)

buttons_container = st.container(
    border=False,
    horizontal=True,
    horizontal_alignment="center",
    vertical_alignment="center",
)

with buttons_container:
    save_changes_btn = st.button("Make Changes")
    if save_changes_btn:
        new_users, modified_users, deleted_users = prepare_users_updates(
            users, modified_df
        )
        if not new_users and not modified_users and not deleted_users:
            st.rerun()
        else:
            save_user_updates(new_users, modified_users, deleted_users)
