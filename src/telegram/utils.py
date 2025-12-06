import os
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
