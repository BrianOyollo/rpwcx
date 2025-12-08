import streamlit as st
from sqlalchemy import text, exc

from utils import load_tests_from_db, fetch_tests

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
    st.header("Tests", divider="orange")

# -------------------- SUBHEADER ---------------------------------------


@st.dialog("New Test Category")
def new_test_category():
    """
    Displays a form to create a new test category.

    Workflow:
        - Collects category name, description, and a comma-separated list of tests.
        - Validates that required fields (name and tests) are provided.
        - Inserts the new category into the `tests` table.
        - Clears cached test data and reruns the app on success.
        - Handles unique constraint violations and general database errors with messages.

    Notes:
        - Uses a Streamlit form for input collection.
        - Splits and trims comma-separated test names before storing.
        - Provides user feedback via warnings and error messages.
    """
    with st.form("new_category"):
        category_name = st.text_input("Category")
        category_description = st.text_area("Description")
        available_tests = st.text_area(
            "Tests", height=250, placeholder="Add a list of comma seperated tests"
        )
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
                            "available_tests": [
                                test.strip() for test in available_tests.split(",")
                            ],
                        },
                    )
                    session.commit()
                    load_tests_from_db.clear()
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
    """
    Displays a form to edit and update an existing test category.

    Workflow:
        - Fetches current category details (name, description, available tests) from the database.
        - Populates a Streamlit form with current values for editing.
        - Validates that the category name and tests are provided.
        - Updates the category in the `tests` table with new values.
        - Clears cached test data and reruns the app on success.
        - Handles unique constraint violations (duplicate category name) and general database errors with feedback.
    
    Notes:
        - Splits and trims comma-separated test names before updating the database.
        - Provides user warnings and error messages for missing or invalid inputs.
    """
    try:
        category_details = conn.query(
            "SELECT * FROM tests WHERE id=:category_id",
            params={"category_id": category_id},
            ttl=0,
        ).to_dict(orient="records")
    except Exception as e:
        st.error("Error fetching update details. Please try again or contact admin")
        st.stop()
    

    category_id = category_details[0]["id"]
    current_category_name = category_details[0]["category_name"]
    current_category_description = category_details[0]["category_description"]
    current_available_tests = category_details[0]["available_tests"]

    with st.form("update_category"):
        category_name = st.text_input("Category", value=current_category_name)
        category_description = st.text_area(
            "Description", value=current_category_description, width=500
        )
        available_tests = st.text_area(
            "Tests", value=",\n".join(current_available_tests), height=250
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
                            "available_tests": [
                                test.strip() for test in available_tests.split(",")
                            ],
                        },
                    )
                    session.commit()
                    load_tests_from_db.clear()
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
    """
    Displays a confirmation dialog to delete a test category.

    Workflow:
        - Shows a warning that the category and its tests will be permanently deleted.
        - Provides a checkbox to skip future warnings (stored in session state).
        - Executes deletion from the `tests` table when user confirms.
        - Clears cached test data and reruns the app on success.
        - Handles database errors gracefully with a user-friendly message.
    
    Notes:
        - This action is irreversible; the deleted category and tests cannot be recovered.
    """
    delete_query = text("DELETE FROM tests WHERE id=:id")

    st.warning(
        "Are you sure you want to delete this **category and its tests**?\n\n **:red[This action can't be undone!]**"
    )
    show_delete_category_dialog_check = st.checkbox(
        "Don't show me this again", value=False
    )
    if show_delete_category_dialog_check:
        st.session_state["show_delete_category_dialog"] = False

    with st.container(horizontal=True, horizontal_alignment="center"):
        confirm_delete_category = st.button(":red[Confirm Delete]")

    if confirm_delete_category:
        with conn.session as session:
            try:
                session.execute(delete_query, {"id": category_id})
                session.commit()
                load_tests_from_db.clear()
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
    test_search = st.text_input(
        "Search",
        placeholder="Search by category or test or code",
        label_visibility="hidden",
        icon=":material/search:",
    )
    add_category = st.button("Category", icon=":material/add:")
    if add_category:
        new_test_category()


# ------------------------ TESTS -------------------------------------------------------------------


# @st.cache_data(ttl=60 * 10)
# def load_tests_from_db(_conn):
#     try:
#         tests_df = conn.query(
#             "SELECT id, category_name, category_description, available_tests FROM tests ORDER BY category_name ASC;",
#             ttl=0,
#         )
#         return tests_df
#     except Exception as e:
#         st.error(
#             "Error fetching tests from the db. Contact system admin if issue persists"
#         )
#         st.stop()


# def fetch_tests(conn, filter: str = None):
#     tests_df = load_tests_from_db(conn)

#     if filter is None:
#         return tests_df.to_dict(orient="records")

#     filtered_tests = tests_df[
#         tests_df["category_name"].str.contains(str(filter), case=False, na=False)
#         | tests_df["available_tests"].apply(
#             lambda tests: any(filter.lower() in test.lower() for test in tests)
#         )
#     ]
#     return filtered_tests.to_dict(orient="records")


tests_list_container = st.container(
    key="tests_list_ctn",
    border=False,
    horizontal=False,
    horizontal_alignment="distribute",
    vertical_alignment="top",
    height=500,
)

categories = fetch_tests(conn, test_search)


with tests_list_container:
    for category in categories:
        with st.expander(f"**:orange[{category['category_name']}]**"):
            with st.container(
                key=f"ctn_{category}",
                border=False,
                horizontal=True,
                horizontal_alignment="distribute",
                vertical_alignment="center",
            ):
                
                with st.container(
                    horizontal=True,
                    horizontal_alignment="distribute",
                    vertical_alignment="top",
                    width=900,
                ):
                    st.caption(category['category_description'] if category['category_description'] else "No description added" )
                    st.pills(
                        category["category_description"],
                        category["available_tests"],
                        label_visibility="collapsed",
                    )

                # st.write(", ".join(category["available_tests"]))
                with st.container(
                    border=False,
                    horizontal_alignment="center",
                    horizontal=True,
                    key=f"{category}_btns",
                ):
                    edit = st.button(
                        "Edit",
                        key=f"edit_{category}",
                        type="secondary",
                        icon=":material/edit:",
                    )
                    if edit:
                        update_category(category["id"])

                    delete = st.button(
                        "Delete Category",
                        key=f"delete_{category}",
                        type="primary",
                        icon=":material/delete:",
                    )
                    if delete:
                        if not st.session_state["show_delete_category_dialog"]:
                            with conn.session as session:
                                try:
                                    delete_query = text(
                                        "DELETE FROM tests WHERE id=:id"
                                    )
                                    session.execute(
                                        delete_query, {"id": category["id"]}
                                    )
                                    session.commit()
                                    st.rerun()
                                except Exception:
                                    st.error(
                                        "Error deleting category. \nPlease contact system admin for support if the issue persists"
                                    )
                                    session.rollback()
                        else:
                            delete_category(category["id"])
