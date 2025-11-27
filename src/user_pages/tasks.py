import streamlit as st
from datetime import datetime
from dateutil.relativedelta import relativedelta


conn = st.session_state["conn"]

st.title("My Tasks")


lab_requests = conn.query(
    """
    WITH user_info AS(
        SELECT dkl_code FROM users WHERE email=:email
    )
    SELECT r.* 
    FROM requests r
    INNER JOIN user_info ui ON ui.dkl_code = r.assign_to
    """,
    params = {'email':st.user.email},
    ttl=0
)
lab_requests_list = lab_requests.to_dict(orient='records')

@st.cache_data(ttl=0)
def fetch_categories_and_tests():
    categories_tests = conn.query("select category_name, available_tests from tests", ttl=0)

    test_category_map = {}
    for _, row in categories_tests.iterrows():
        category = row['category_name']
        for test in row['available_tests']:
            test_category_map[test]=category

    return test_category_map

def categorize_selected_tests(selected_tests):
    test_category_map = fetch_categories_and_tests()

    categorized = {}
    for test in selected_tests:
        category = test_category_map.get(test, "Uncategorized")
        categorized.setdefault(category, []).append(test)
    
    return categorized


def requests_list(tab:str = None):
    with st.container(border=False, horizontal=False, horizontal_alignment='left', height=450):
        
        
        for test in lab_requests_list:
            if tab is None:
                tab_list = lab_requests_list
            else:
                tab_list = [test for test in lab_requests_list if test['request_status'].strip().lower() == tab.strip().lower()]

        for test in tab_list:
            with st.container(border=True, horizontal=False):
                patient = f"{test['first_name'].replace("_", " ")} {test['middle_name'].replace("_", " ")} {test['surname'].replace("_", " ")}"
                gender = test['gender']
                age = relativedelta(datetime.today(), test['dob']).years
                collection_date = test['collection_date'].strftime('%b %d, %Y')
                collection_time = test['collection_time'].strftime('%I:%M %p')
                if test['priority'] == 'Urgent':
                    test_priority = "🚨 :red[Urgent]"
                else:
                    test_priority = "📋 Routine"

                st.write(f":blue[**{patient}** ({gender[0]}, {age})]")

                st.markdown(f"""
                    :gray-badge[**☎️ {test['phone']}**]
                    :gray-badge[**📍 {test['location']}**]
                    :gray-badge[**⏰ {collection_date} • {collection_time}**]
                    :gray-badge[**{test_priority}**]
                """)

                # with st.expander("Tests"):

                with st.container(border=False, horizontal=True, horizontal_alignment='left', vertical_alignment='center'):

                    with st.popover("🧪 Tests"):
                        categorized_tests = categorize_selected_tests(test['selected_tests'])
                        for k,v in categorized_tests.items():
                            st.write(f"**:orange[{k}]**")
                            st.markdown(f",".join([f":blue-badge[{test}]" for test in v ]))

                    test_status = test['request_status']
                    test_status_color = {
                        "pending": "orange",
                        "in-progress": "blue",
                        "completed": "green",
                        "cancelled": "red",
                    }

                    with st.popover(f":{test_status_color[test_status]}[{test_status.title()}]", type='secondary', help="No idea"):
                        st.write('hello')


            
tabs = st.tabs(['All', 'Pending', 'In Progress', "Completed", "Cancelled"])

with tabs[0]:
    requests_list()

with tabs[1]:
    requests_list(tab='Pending')

with tabs[2]:
    requests_list(tab='In-Progress')

with tabs[3]:
    requests_list(tab='Completed')

with tabs[4]:
    requests_list(tab='Cancelled')