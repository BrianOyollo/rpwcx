import streamlit as st
import re
import pandas as pd


@st.cache_data(ttl=0)
def fetch_categories_and_tests(_conn):
    """
    Fetches all test categories and their associated tests from the database,
    and returns a dictionary mapping each test to its category.

    This function is cached to avoid querying the database repeatedly.

    Parameters:
    -----------
    conn : object
        Database connection or wrapper that supports a `.query()` method returning a DataFrame.

    Returns:
    --------
    test_category_map : dict
        Dictionary where keys are individual test names (strings) and values
        are their corresponding category names (strings).
    
    Example:
    --------
    {
        "PSA (Total) [4304]": "Cancer Tests",
        "PBF (Peripheral Blood Film) [6971]": "Hematology",
        ...
    }
    """
    categories_tests = _conn.query("select category_name, available_tests from tests", ttl=0)

    test_category_map = {}
    for _, row in categories_tests.iterrows():
        category = row['category_name']
        for test in row['available_tests']:
            test_category_map[test]=category

    return test_category_map

def categorize_selected_tests(conn, selected_tests):
    """
    Categorizes a list of selected tests into their corresponding categories.

    Parameters:
    -----------
    conn : object
        Database connection or wrapper that supports a `.query()` method.
        Used internally to fetch the test-category mapping.
    selected_tests : list of str
        List of test names (as strings) to categorize.

    Returns:
    --------
    categorized : dict
        Dictionary where keys are category names (strings) and values are
        lists of tests (strings) that fall under each category.

    Notes:
    ------
    - Tests not found in the mapping are labeled as "Uncategorized".
    - Useful for summarizing requests, generating dashboards, or grouping tests
      for analysis.

    Example:
    --------
    selected_tests = ["PSA (Total) [4304]", "PBF (Peripheral Blood Film) [6971]"]
    categorized = categorize_selected_tests(conn, selected_tests)
    # Output:
    # {
    #     "Cancer Tests": ["PSA (Total) [4304]"],
    #     "Hematology": ["PBF (Peripheral Blood Film) [6971]"]
    # }
    """
    test_category_map = fetch_categories_and_tests(conn)

    categorized = {}
    for test in selected_tests:
        category = test_category_map.get(test, "Uncategorized")
        categorized.setdefault(category, []).append(test)
    
    return categorized


@st.cache_data(ttl=60 * 10)
def load_tests_from_db(_conn):
    try:
        tests_df = _conn.query(
            "SELECT id, category_name, category_description, available_tests FROM tests ORDER BY category_name ASC;",
            ttl=0,
        )
        return tests_df
    except Exception as e:
        st.error(
            "Error fetching tests from the db. Contact system admin if issue persists"
        )
        st.stop()


def fetch_tests(conn, filter: str = None):
    tests_df = load_tests_from_db(conn)

    if filter is None:
        return tests_df.to_dict(orient="records")

    filtered_tests = tests_df[
        tests_df["category_name"].str.contains(str(filter), case=False, na=False)
        | tests_df["available_tests"].apply(
            lambda tests: any(filter.lower() in test.lower() for test in tests)
        )
    ]
    return filtered_tests.to_dict(orient="records")


@st.cache_data(ttl=60 * 2)
def prepare_tests_df(_conn):
    """
    Fetches tests from DB and flattens into a DataFrame with:
    - name
    - code
    - category
    """
    raw_tests = fetch_tests(_conn)

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
        with st.container(
            border=True,
            horizontal=True,
            horizontal_alignment="left",
            vertical_alignment="top",
        ):
            for idx, test in enumerate(st.session_state.selected_tests):
                checkbox = st.checkbox(test, key=f"{test}{idx}", value=True)
                if not checkbox:
                    st.session_state.selected_tests.remove(test)
                    st.rerun(scope="fragment")

        with st.container(horizontal=True, horizontal_alignment="center"):
            if st.session_state.selected_tests:
                clear = st.button("Clear Tests")
                if clear:
                    st.session_state.selected_tests = set()
                    st.rerun(scope="fragment")

@st.cache_data(ttl=60)
def fetch_doctors(_conn) -> pd.DataFrame:
    try:
        doctors_df = _conn.query(
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
def fetch_phlebotomists(_conn) -> pd.DataFrame:
    try:
        phlebotomists_df = _conn.query(
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
