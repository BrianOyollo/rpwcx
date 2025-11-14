import streamlit as st
from sqlalchemy import text, exc

st.set_page_config(page_title="RPWC | Tests", layout="wide")


conn = st.session_state["conn"]


# -------------------- HEADER -----------------------------------------
header_container = st.container(
    border=False,
    horizontal=True,
    horizontal_alignment="distribute",
    vertical_alignment="bottom",
)

with header_container:
    st.header("Tests", divider="grey")

# -------------------- SUBHEADER ---------------------------------------


@st.dialog("New Test Category")
def new_test_category():
    with st.form("new_category"):
        category_name = st.text_input("Category")
        category_description = st.text_area("Description")
        available_tests = st.multiselect("Tests", options=[], accept_new_options=True)
        with st.container(horizontal=True, horizontal_alignment="center"):
            save_category = st.form_submit_button("Save Category", type="primary")

        if save_category:
            if not category_name or not available_tests:
                st.warning("Please provide both category name and available tests")
                st.stop()

            insert_query = text(
                """
                INSERT INTO tests(category_name, category_description, available_tests)
                VALUES(:category_name, :category_description, :available_tests)
                """
            )
            with conn.session as session:
                try:
                    session.execute(
                        insert_query,
                        {
                            "category_name": category_name,
                            "category_description": category_description,
                            "available_tests": available_tests,
                        },
                    )
                    session.commit()
                    st.rerun()
                except exc.IntegrityError:
                    st.error("Category already exists!")
                    session.rollback()
                except Exception:
                    st.error(
                        "Error adding new category. \nPlease contact system admin for support if the issue persists"
                    )
                    session.rollback()


@st.dialog("Edit/Update Category")
def update_category(category_id: int):
    category_details = conn.query(
        "SELECT * FROM tests WHERE id=:category_id",
        params={"category_id": category_id},
        ttl=0,
    ).to_dict(orient="records")

    category_id = category_details[0]["id"]
    current_category_name = category_details[0]["category_name"]
    current_category_description = category_details[0]["category_description"]
    current_available_tests = category_details[0]["available_tests"]

    with st.form("update_category"):
        category_name = st.text_input("Category", value=current_category_name)
        category_description = st.text_area(
            "Description", value=current_category_description
        )
        available_tests = st.multiselect(
            "Tests",
            default=current_available_tests,
            options=current_available_tests,
            accept_new_options=True,
        )
        with st.container(horizontal=True, horizontal_alignment="center"):
            update_category = st.form_submit_button("Update")

        if update_category:
            if not category_name or not available_tests:
                st.warning(
                    "Please provide both **category name** and **available tests**"
                )
                st.stop()

            query = text(
                """
                UPDATE tests
                SET category_name=:category_name, category_description=:category_description, available_tests=:available_tests
                WHERE id=:id
                """
            )
            with conn.session as session:
                try:
                    session.execute(
                        query,
                        {
                            "id": category_id,
                            "category_name": category_name,
                            "category_description": category_description,
                            "available_tests": available_tests,
                        },
                    )
                    session.commit()
                    st.rerun()
                except exc.IntegrityError:
                    session.rollback()
                    st.error(
                        f"A category with the name **{category_name}** already exists"
                    )
                    st.stop()
                except Exception:
                    st.error(
                        "Error updating category. \nPlease contact system admin for support if the issue persists"
                    )
                    session.rollback()


@st.dialog("Delete Category")
def delete_category(category_id: int):
    delete_query = text("DELETE FROM tests WHERE id=:id")

    st.warning(
        "Are you sure you want to delete this category? This action can't be undone!"
    )
    show_delete_category_dialog_check = st.checkbox(
        "Don't show me this again", value=False
    )
    if show_delete_category_dialog_check:
        st.session_state["show_delete_category_dialog"] = False

    with st.container(horizontal=True, horizontal_alignment="center"):
        confirm_delete_category = st.button("Confirm Delete")

    if confirm_delete_category:
        with conn.session as session:
            try:
                session.execute(delete_query, {"id": category_id})
                session.commit()
                st.rerun()
            except Exception:
                st.error(
                    "Error deleting category. \nPlease contact system admin for support if the issue persists"
                )
                session.rollback()


actions_container = st.container(
    key="actions_ctn",
    border=False,
    horizontal=True,
    horizontal_alignment="distribute",
    vertical_alignment="bottom",
)

with actions_container:
    st.text_input(
        "Search", placeholder="Search by category or test", label_visibility="hidden"
    )
    add_category = st.button("Add Category")
    if add_category:
        new_test_category()


# ------------------------ TESTS -------------------------------------------------------------------


def fetch_tests():
    categories = conn.query(
        "SELECT id, category_name, category_description, available_tests FROM tests ORDER BY category_name ASC;",
        ttl=0,
    )
    return categories.to_dict(orient="records")


tests_list_container = st.container(
    key="tests_list_ctn",
    border=False,
    horizontal=False,
    horizontal_alignment="distribute",
    vertical_alignment="top",
    height=500,
)


categories = fetch_tests()


with tests_list_container:
    for category in categories:
        with st.container(
            key=f"ctn_{category}",
            border=True,
            horizontal=True,
            horizontal_alignment="distribute",
            vertical_alignment="center",
        ):
            with st.container(border=False, width=800, key=f"{category}_contents"):
                st.write(f"**:orange[{category['category_name']}]**")
                st.write(", ".join(category["available_tests"]))
            with st.container(
                border=False,
                horizontal_alignment="center",
                horizontal=True,
                key=f"{category}_btns",
            ):
                edit = st.button("Edit", key=f"edit_{category}")
                if edit:
                    update_category(category["id"])

                delete = st.button("Delete", key=f"delete_{category}")
                if delete:
                    if not st.session_state["show_delete_category_dialog"]:
                        with conn.session as session:
                            try:
                                delete_query = text("DELETE FROM tests WHERE id=:id")
                                session.execute(delete_query, {"id": category["id"]})
                                session.commit()
                                st.rerun()
                            except Exception:
                                st.error(
                                    "Error deleting category. \nPlease contact system admin for support if the issue persists"
                                )
                                session.rollback()
                    else:
                        delete_category(category["id"])
