import asyncio
import os
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from psycopg2 import errors
import utils

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_ID = int(os.getenv("TELEGRAM_GROUP_ID"))

auth_router = Router()


@auth_router.message(Command("register"))
async def register_new_user(message: Message, command: CommandObject):
    if message.chat.type != "group":
        await message.answer("Unauthorized! This command is only available from group")
        return

    if message.chat.id != GROUP_ID:
        await message.answer("Unauthorized! This is a private bot")
        return

    sender_id = message.from_user.id
    sender_name = message.from_user.first_name
    args = command.args

    if args is None:
        await message.answer(
            f"Hello {sender_name}, \nPlease provide your email to register your account",
            parse_mode="markdown",
        )
        return

    try:
        with utils.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email=%s", (args,))
                email_valid = cur.fetchone()

                # user tries registering an email not in the system
                if not email_valid:
                    await message.answer(
                        f"""Hello {sender_name}, 
                        \nThe email you entered does not exist in our system. 
                        \nPlease provide the correct email as follows: /register <email>
                        """
                    )
                    return

                # user tries register an email that is already linked to a telegram account
                if email_valid[9]:
                    ## case 1: same user but from a different device(same chat id)
                    if email_valid[9] == sender_id:
                        await message.answer(
                            f"""Hello {sender_name}, 
                            \nYou are already registered. You can continue using the bot privately"""
                        )
                        return
                    else:
                        ## case 2: DIFFERENT USER trying to steal the account (block!)
                        await message.answer(
                            f"""Hello {sender_name}, 
                            \nThis email is already linked to another Telegram account.  
                            \nIf this wasn't you, contact admin."""
                        )
                        return

                cur.execute(
                    "UPDATE users SET telegram_chat_id=%s WHERE email=%s",
                    (sender_id, args),
                )
                conn.commit()
                await message.answer(
                    f"""Hello {sender_name}, 
                    \nYour registration was successful.
                    \nYou can now communicate with the bot privately to view and update your assignments"""
                )

    # user tries to register another email from the same telegram account
    except errors.UniqueViolation as e:
        await message.answer(
            f"""Hello {sender_name},
            \nYou already have a registered account.
            \nIf this wasn't you, contact admin"""
        )
    except Exception as e:
        print(e)
        await message.answer(
            f"""Hello {sender_name},
            \nWe experienced an error while registering your account.
            \nPlease try again later or contact the admin for support"""
        )


async def user_is_group_member(user_id, bot: Bot) -> bool:
    """
    Checks if a user is a member of the specified Telegram group.

    :param user-id: The user_id to check.
    :param bot: The Bot instance (injected by aiogram).
    :param group_id: The target group ID (passed in the filter arguments).
    :return: True if the user is a member, False otherwise.
    """

    try:
        chat_member = await bot.get_chat_member(GROUP_ID, user_id)
        return chat_member.status in ["member", "creator", "administrator"]
    except Exception as e:
        print(e)
        return False


def user_is_in_db(user_id: int) -> bool:
    """
    Checks if the user exists in the custom database.

    :param message: The incoming message object.
    :return: True if the user is found in the database, False otherwise.
    """

    try:
        with utils.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE telegram_chat_id=%s", (user_id,))
                user_exists = cur.fetchone()
                return user_exists is not None

    except Exception as e:
        print(e)
