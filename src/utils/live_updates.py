import os
import select
import requests
import psycopg2
import json


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def send_tg_new_request_message(chat_id: int, message: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})


conn = psycopg2.connect(
    dbname=os.getenv("DB"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute("LISTEN new_requests_channel;")
print("Waiting for notifications on channel 'new_requests_channel'...")


while True:
    # wait for notifications
    # if nothing changes, loop again
    if select.select([conn], [], [], 5) == ([], [], []):
        continue
    else:
        conn.poll()
        while conn.notifies:
            notify = conn.notifies.pop(0)
            payload = json.loads(notify.payload)
            print(payload)

            # get notification details
            task_id = payload.get("task_id")
            priority = payload.get("priority")
            assigned_to = payload.get("assigned_to")

            # find assigned user's telegram chat id
            cur.execute(
                """
                SELECT telegram_chat_id 
                FROM users 
                WHERE dkl_code=%s
                """,
                (assigned_to,),
            )
            tg_chat_id = cur.fetchone()
            if not tg_chat_id:
                print("Assigned phlebotomist has not linked their Telegram account")
            else:
                chat_id = tg_chat_id[0]
                message = f"""
                    New Request Assigned. 
                    \nTask ID: {task_id}
                    \nPriority: {priority}
                """
                send_tg_new_request_message(chat_id, message)
