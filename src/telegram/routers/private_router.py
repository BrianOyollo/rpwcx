import asyncio
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, Chat, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.formatting import Spoiler, Text
from psycopg2 import errors
import utils

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID"))

private_router = Router()
private_router.message.filter(F.chat.type == 'private')


async def user_is_group_member(user_id, bot:Bot) -> bool:
    """
    Checks if a user is a member of the specified Telegram group.
    
    :param user-id: The user_id to check.
    :param bot: The Bot instance (injected by aiogram).
    :param group_id: The target group ID (passed in the filter arguments).
    :return: True if the user is a member, False otherwise.
    """

    try:
        chat_member = await bot.get_chat_member(GROUP_ID, user_id)
        return chat_member.status in ['member', 'creator', 'administrator']
    except Exception as e:
        print(e)
        return False

def user_is_in_db(user_id:int) -> bool:
    """
    Checks if the user exists in the custom database.
    
    :param message: The incoming message object.
    :return: True if the user is found in the database, False otherwise.
    """

    try:
        with utils.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM users WHERE telegram_chat_id=%s', (user_id, ))
                user_exists = cur.fetchone()
                return user_exists is not None
            
    except Exception as e:
        print(e)


@private_router.message(Command("start"))
async def private_start_command(message:Message, bot:Bot) -> None:

    user_name = message.chat.first_name
    user_id = message.chat.id

    if not await user_is_group_member(user_id, bot):
        await message.answer("You must mem a registered member of RPWC-DKL to interact with this bot")
        return
    
    if not user_is_in_db(user_id):
        await message.answer("Unauthorized! You must be registered in our system")
        return 
    
    await message.answer(
        f"""
        👋 Hello {user_name}
        
Your account is verified and you're a member of *RPWC DKL*

Here’s what I can help you with:

• 📋 View your current assignments  
• 🔄 Submit updates and progress reports  
• 📨 Receive reminders and important notifications  
• 🆘 Get assistance using the /help command

Type **/help** anytime to see a full list of available commands
        """,
        parse_mode="MarkdownV2"
    )

@private_router.message(Command("help"))
async def private_help(message: Message)->None:

    await message.answer("""
        *RPWC DKL Assistant Bot*
        
*Available Commands*
                         
*/start* : Begin interacting with the bot in private chat
*/help* : Display this help message
*/assignments*: View your current assignments, tasks, or activities
*/update \<message\>*: Submit progress updates or status reports to the coordinator
*/profile*: View the information linked to your registered account
*/support*: Get instructions on how to contact the admin for help
                         
*Need Assistance?*
If something doesn’t work or you believe there’s an error, contact the admin
""",
    parse_mode="MarkdownV2"
    )


@private_router.message(Command("tasks"))
async def all_user_tasks(message:Message, bot:Bot)->None:
    user_name = message.chat.first_name
    user_id = message.chat.id

    if not await user_is_group_member(user_id, bot):
        await message.answer("You must be a registered member of RPWC-DKL to interact with this bot")
        return
    
    if not user_is_in_db(user_id):
        await message.answer("Unauthorized! You must be registered in our system")
        return 
    try:
        with utils.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.* FROM requests r
                    JOIN users u ON u.dkl_code=r.assign_to
                    WHERE u.telegram_chat_id=%s
                    ORDER BY r.created_at DESC;
                    """, (user_id,)
                )
                
                tasks = cur.fetchall()
                if not tasks:
                    await message.answer("You don't have any tasks")
                    return

                await message.answer("Here are your tasks, most recent first")

                
                for task in tasks:
                    task_id = task[0]
                    patient = f"{task[1]} {task[2]}"
                    urgency = task[12]
                    appointment_date = task[13]
                    appointment_time = task[14]
                    status = task[-1]

                    # Build keyboard
                    builder = InlineKeyboardBuilder()
                    builder.button(text="👁 View", callback_data=f"view_{task_id}")

                    # # Status buttons (row 2)
                    # builder.row(
                    #     InlineKeyboardButton(text="✔ Completed", callback_data=f"status_completed_{task_id}"),
                    #     InlineKeyboardButton(text="⏳ Pending", callback_data=f"status_pending_{task_id}"),
                    #     InlineKeyboardButton(text="🔧 In Progress", callback_data=f"status_progress_{task_id}")
                    # )

                    preview = (
                        # f"🧾 *Task #{task_id}*\n"
                        f"👤 *{patient}*\n"
                        f"⚠️ *Urgency:* {urgency}\n"
                        f"📅 *Appointment:* {appointment_date} at {appointment_time}\n"
                        f"📌 *Status:* {status}"
                    )

                    await message.answer(preview, parse_mode="Markdown", reply_markup=builder.as_markup())


    except Exception as e:
        print(e)
        await message.answer("Error fetching your assigned tasks. Please try again later or contact the admin")



@private_router.message(Command("pending"))
async def pending_user_tasks(message:Message, bot:Bot)->None:
    user_name = message.chat.first_name
    user_id = message.chat.id

    if not await user_is_group_member(user_id, bot):
        await message.answer("You must be registered member of RPWC-DKL to interact with this bot")
        return
    
    if not user_is_in_db(user_id):
        await message.answer("Unauthorized! You must be registered in our system")
        return 
    try:
        with utils.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.* FROM requests r
                    JOIN users u ON u.dkl_code=r.assign_to
                    WHERE u.telegram_chat_id=%s AND request_status='pending'
                    ORDER BY r.created_at DESC;
                    """, (user_id,)
                )
                
                tasks = cur.fetchall()
                if not tasks:
                    await message.answer("You don't have any pending tasks")
                    return

                await message.answer("Here are your pending tasks, most recent first")

                
                for task in tasks:
                    task_id = task[0]
                    patient = f"{task[1]} {task[2]}"
                    urgency = task[12]
                    appointment_date = task[13]
                    appointment_time = task[14]
                    status = task[-1]

                    # Build keyboard
                    builder = InlineKeyboardBuilder()
                    builder.button(text="👁 View", callback_data=f"view_{task_id}")

                    # # Status buttons (row 2)
                    # builder.row(
                    #     InlineKeyboardButton(text="✔ Completed", callback_data=f"status_completed_{task_id}"),
                    #     InlineKeyboardButton(text="⏳ Pending", callback_data=f"status_pending_{task_id}"),
                    #     InlineKeyboardButton(text="🔧 In Progress", callback_data=f"status_progress_{task_id}")
                    # )

                    preview = (
                        # f"🧾 *Task #{task_id}*\n"
                        f"👤 *{patient}*\n"
                        f"⚠️ *Urgency:* {urgency}\n"
                        f"📅 *Appointment:* {appointment_date} at {appointment_time}\n"
                        f"📌 *Status:* {status}"
                    )

                    await message.answer(preview, parse_mode="Markdown", reply_markup=builder.as_markup())


    except Exception as e:
        print(e)
        await message.answer("Error fetching your assigned tasks. Please try again later or contact the admin")


@private_router.message(Command("completed"))
async def completed_user_tasks(message:Message, bot:Bot)->None:
    user_name = message.chat.first_name
    user_id = message.chat.id

    if not await user_is_group_member(user_id, bot):
        await message.answer("You must be registered member of RPWC-DKL to interact with this bot")
        return
    
    if not user_is_in_db(user_id):
        await message.answer("Unauthorized! You must be registered in our system")
        return 
    try:
        with utils.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.* FROM requests r
                    JOIN users u ON u.dkl_code=r.assign_to
                    WHERE u.telegram_chat_id=%s AND request_status='completed'
                    ORDER BY r.created_at DESC;
                    """, (user_id,)
                )
                
                tasks = cur.fetchall()
                if not tasks:
                    await message.answer("You don't have any completed tasks")
                    return

                await message.answer("Here are your completed tasks, most recent first")

                
                for task in tasks:
                    task_id = task[0]
                    patient = f"{task[1]} {task[2]}"
                    urgency = task[12]
                    appointment_date = task[13]
                    appointment_time = task[14]
                    status = task[-1]

                    # Build keyboard
                    builder = InlineKeyboardBuilder()
                    builder.button(text="👁 View", callback_data=f"view_{task_id}")

                    # # Status buttons (row 2)
                    # builder.row(
                    #     InlineKeyboardButton(text="✔ Completed", callback_data=f"status_completed_{task_id}"),
                    #     InlineKeyboardButton(text="⏳ Pending", callback_data=f"status_pending_{task_id}"),
                    #     InlineKeyboardButton(text="🔧 In Progress", callback_data=f"status_progress_{task_id}")
                    # )

                    preview = (
                        # f"🧾 *Task #{task_id}*\n"
                        f"👤 *{patient}*\n"
                        f"⚠️ *Urgency:* {urgency}\n"
                        f"📅 *Appointment:* {appointment_date} at {appointment_time}\n"
                        f"📌 *Status:* {status}"
                    )

                    await message.answer(preview, parse_mode="Markdown", reply_markup=builder.as_markup())


    except Exception as e:
        print(e)
        await message.answer("Error fetching your assigned tasks. Please try again later or contact the admin")

@private_router.message(Command("in-progress"))
async def in_progress_user_tasks(message:Message, bot:Bot)->None:
    user_name = message.chat.first_name
    user_id = message.chat.id

    if not await user_is_group_member(user_id, bot):
        await message.answer("You must be registered member of RPWC-DKL to interact with this bot")
        return
    
    if not user_is_in_db(user_id):
        await message.answer("Unauthorized! You must be registered in our system")
        return 
    try:
        with utils.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.* FROM requests r
                    JOIN users u ON u.dkl_code=r.assign_to
                    WHERE u.telegram_chat_id=%s AND request_status='in-progress'
                    ORDER BY r.created_at DESC;
                    """, (user_id,)
                )
                
                tasks = cur.fetchall()
                if not tasks:
                    await message.answer("You don't have any tasks in progress")
                    return

                await message.answer("Here are your tasks, most recent first")

                
                for task in tasks:
                    task_id = task[0]
                    patient = f"{task[1]} {task[2]}"
                    urgency = task[12]
                    appointment_date = task[13]
                    appointment_time = task[14]
                    status = task[-1]

                    # Build keyboard
                    builder = InlineKeyboardBuilder()
                    builder.button(text="👁 View", callback_data=f"view_{task_id}")

                    # # Status buttons (row 2)
                    # builder.row(
                    #     InlineKeyboardButton(text="✔ Completed", callback_data=f"status_completed_{task_id}"),
                    #     InlineKeyboardButton(text="⏳ Pending", callback_data=f"status_pending_{task_id}"),
                    #     InlineKeyboardButton(text="🔧 In Progress", callback_data=f"status_progress_{task_id}")
                    # )

                    preview = (
                        # f"🧾 *Task #{task_id}*\n"
                        f"👤 *{patient}*\n"
                        f"⚠️ *Urgency:* {urgency}\n"
                        f"📅 *Appointment:* {appointment_date} at {appointment_time}\n"
                        f"📌 *Status:* {status}"
                    )

                    await message.answer(preview, parse_mode="Markdown", reply_markup=builder.as_markup())


    except Exception as e:
        print(e)
        await message.answer("Error fetching your assigned tasks. Please try again later or contact the admin")