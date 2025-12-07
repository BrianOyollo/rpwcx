import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandObject
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, Chat, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.formatting import Spoiler, Text
from psycopg2 import errors

import utils
from routers.auth_router import user_is_group_member, user_is_in_db

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID"))

callback_router = Router()


class TaskDetailsCallbackData(CallbackData, prefix="task_details"):
    task_id: int

class TaskStatusCallbackData(CallbackData, prefix='task_status'):
    status: str
    task_id: int


@callback_router.callback_query(TaskDetailsCallbackData.filter())
async def show_task_details(callback_query:CallbackQuery, callback_data:TaskDetailsCallbackData, bot:Bot):
    chat_id = callback_query.from_user.id
    task_id = callback_data.task_id

    if not await user_is_group_member(chat_id, bot):
        await callback_query.answer("You must mem a registered member of RPWC-DKL to interact with this bot")
        return

    if not user_is_in_db(chat_id):
        await callback_query.answer("Unauthorized! You must be registered in our system")
        return 

    await callback_query.answer("Fetching task details...")
    # print(callback_data)

    try:
        with utils.get_connection() as conn:
            with conn.cursor() as cur:
                # Fetch full task details
                cur.execute(
                    "SELECT * FROM requests WHERE id=%s",
                    (task_id,)
                )
                task = cur.fetchone()

                if not task:
                    await callback_query.message.answer("❌ Task not found.")
                    return
                
                # Build detailed message
                patient = f"{task[1]} {task[2].replace("_", " ")}"
                urgency = task[12]
                appointment_date = task[13].strftime('%b %d, %Y')
                appointment_time = task[14].strftime('%I:%M %p')
                status = task[-1].title()
                location = task[8]
                # tests = ", ".join(task[10]) if task[10] else "N/A"

                # categorize tests
                raw_tests = task[10]
                categorized_tests = utils.categorize_selected_tests(raw_tests)

                tests_html = ""
                for cat, tests in categorized_tests.items():
                    tests_html += f"<b>{cat}</b>\n"
                    for t in tests:
                        tests_html += f"• <i>{t}</i>\n"
                    tests_html += f"\n"
                text = (

                    f"👤 <b>Patient:</b>\n"
                    f"{patient}\n\n"

                    f"📍<b>Location:</b>\n"
                    f"{location}\n\n"

                    f"⚠️ <b>Urgency:</b>\n"
                    f"{urgency}\n\n"

                    f"📅 <b>Appointment:</b>\n"
                    f"{appointment_date} • {appointment_time}\n\n"

                    f"🧪 <b>Tests:</b>\n"
                    f"{tests_html}\n\n"

                    f"📌 <b>Status:</b>"
                    f"{status}"
                )


                builder = InlineKeyboardBuilder()
                builder.row(
                    InlineKeyboardButton(text="Completed", callback_data=TaskStatusCallbackData(status='completed', task_id=task_id).pack()),
                    InlineKeyboardButton(text="Pending", callback_data=TaskStatusCallbackData(status='pending', task_id=task_id).pack()),
                    InlineKeyboardButton(text="In progress", callback_data=TaskStatusCallbackData(status='in-progress', task_id=task_id).pack())
                )

                await bot.send_message(
                    chat_id=callback_query.from_user.id,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=builder.as_markup()
                )


    except Exception as e:
        print(e)
        await callback_query.answer("Error fetching task details. Please try again later")


@callback_router.callback_query(TaskStatusCallbackData.filter())
async def update_task_status(callback_query:CallbackQuery, callback_data:TaskStatusCallbackData, bot:Bot)->None:
    chat_id = callback_query.from_user.id
    task_id = callback_data.task_id
    task_status = callback_data.status

    if not await user_is_group_member(chat_id, bot):
        await callback_query.answer("You must mem a registered member of RPWC-DKL to interact with this bot")
        return

    if not user_is_in_db(chat_id):
        await callback_query.answer("Unauthorized! You must be registered in our system")
        return 

    await callback_query.answer("Updating task status...")
    
    with utils.get_connection() as  conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH current_tg_user AS(
                    SELECT dkl_code 
                    FROM users 
                    WHERE telegram_chat_id=%s
                )
                UPDATE requests 
                SET request_status=%s, 
                    updated_at=now() 
                FROM current_tg_user
                WHERE 
                    requests.assign_to=current_tg_user.dkl_code AND 
                    requests.id=%s;
                """,
                (chat_id,task_status,task_id)
            )
            conn.commit()
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text=f"Task {task_id} status updated to {task_status}"
            )

