import os
from cachetools import cached, TTLCache
import psycopg2


DB_CONFIG = {
    "dbname": os.getenv("DB"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", 5432),
}

def get_connection():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(e)

def get_user_by_chat_id(chat_id:int) -> str|None:
    db_conn = get_connection()

    try:
        with db_conn as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM users WHERE telegram_chat_id=%s", (chat_id,))
                user = cur.fetchone()
                if user:
                    return user[0]
                else:
                    return None
    except Exception as e:
        print(e)

test_category_map_cache = TTLCache(maxsize=1, ttl=60*5)

@cached(cache=test_category_map_cache)
def fetch_categories_and_tests():

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT category_name, available_tests FROM tests")
            categories_tests = cur.fetchall()

    test_category_map = {}
    for row in categories_tests:
        category = row[0]
        for test in row[1]:
            test_category_map[test]=category

    return test_category_map

def categorize_selected_tests(selected_tests):
    test_category_map = fetch_categories_and_tests()

    categorized = {}
    for test in selected_tests:
        category = test_category_map.get(test, "Uncategorized")
        categorized.setdefault(category, []).append(test)
    
    return categorized


