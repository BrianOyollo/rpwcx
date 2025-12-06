import asyncio
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
from routers.callbacks_router import TaskDetailsCallbackData
from routers.auth_router import user_is_group_member, user_is_in_db

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID"))

private_router = Router()
private_router.message.filter(F.chat.type == 'private')


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
*/tasks* : View all your tasks
*/completed* : View assignments you have completed  
*/pending* : View assignments that are still pending
*/profile* : View the information linked to your registered account

*Need Assistance?*
If something doesn’t work or you believe there’s an error, contact the admin
""",
    parse_mode="MarkdownV2"
    )


@private_router.message(Command("tasks", "pending", "completed", "in_progress"))
async def all_user_tasks(message:Message, bot:Bot, command:CommandObject)->None:
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

                task_status = command.command

                if task_status.strip() == 'in_progress':
                    query = f"""
                        SELECT r.* FROM requests r
                        JOIN users u ON u.dkl_code=r.assign_to
                        WHERE u.telegram_chat_id=%s AND request_status='in-progress'
                        ORDER BY r.created_at DESC;
                    """
                elif task_status.strip() == 'pending':
                    query = f"""
                        SELECT r.* FROM requests r
                        JOIN users u ON u.dkl_code=r.assign_to
                        WHERE u.telegram_chat_id=%s AND request_status='pending'
                        ORDER BY r.created_at DESC;
                    """
                elif task_status.strip() == 'completed':
                    query = f"""
                        SELECT r.* FROM requests r
                        JOIN users u ON u.dkl_code=r.assign_to
                        WHERE u.telegram_chat_id=%s AND request_status='completed'
                        ORDER BY r.created_at DESC;
                    """
                else:
                    query = f"""
                        SELECT r.* FROM requests r
                        JOIN users u ON u.dkl_code=r.assign_to
                        WHERE u.telegram_chat_id=%s
                        ORDER BY r.created_at DESC;
                    """
                cur.execute(query, (user_id,))
                
                tasks = cur.fetchall()
                if not tasks:
                    await message.answer("You don't have any tasks")
                    return

                # await message.answer("Here are your tasks, most recent first")

                
                for task in tasks:
                    task_id = task[0]
                    patient = f"{task[1]} {task[2]}"
                    location = task[8]
                    urgency = task[12]
                    appointment_date = task[13].strftime('%b %d, %Y')
                    appointment_time = task[14].strftime('%I:%M %p')
                    status = task[-1].title()

                    # Build keyboard
                    builder = InlineKeyboardBuilder()
                    task_callback_data = TaskDetailsCallbackData(task_id=task_id).pack()
                    builder.button(text="👁 View", callback_data=task_callback_data)

                    # # Status buttons (row 2)
                    # builder.row(
                    #     InlineKeyboardButton(text="✔ Completed", callback_data=f"status_completed_{task_id}"),
                    #     InlineKeyboardButton(text="⏳ Pending", callback_data=f"status_pending_{task_id}"),
                    #     InlineKeyboardButton(text="🔧 In Progress", callback_data=f"status_progress_{task_id}")
                    # )

                    preview = (
                        # f"🧾 *Task #{task_id}*\n"
                        f"👤 *{patient}*\n"
                        f"📍 *{location}*\n"
                        f"⚠️ *Urgency:* {urgency}\n"
                        f"📅 *Appointment:* {appointment_date} • {appointment_time}\n"
                        f"📌 *Status:* {status}"
                    )

                    await message.answer(preview, parse_mode="Markdown", reply_markup=builder.as_markup())


    except Exception as e:
        print(e)
        await message.answer("Error fetching your assigned tasks. Please try again later or contact the admin")
