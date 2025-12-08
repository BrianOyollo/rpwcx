import streamlit as st


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