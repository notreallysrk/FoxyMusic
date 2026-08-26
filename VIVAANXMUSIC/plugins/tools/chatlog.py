import asyncio
import random
from typing import Optional

from pyrogram import filters, errors, types
from pyrogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import LOGGER_ID as LOG_GROUP_ID
from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.database import remove_served_chat


BOT_INFO: Optional[types.User] = None
BOT_ID: Optional[int] = None

PHOTOS = [
    "https://files.catbox.moe/y2briy.jpg",
    "https://files.catbox.moe/1evnbn.jpg",
]


async def _ensure_bot_info():
    global BOT_INFO, BOT_ID

    if BOT_INFO is None:
        BOT_INFO = await app.get_me()
        BOT_ID = BOT_INFO.id


async def safe_get_member_count(chat_id):
    try:
        return await app.get_chat_members_count(chat_id)

    except errors.FloodWait as e:
        await asyncio.sleep(e.value + 1)
        return await app.get_chat_members_count(chat_id)

    except Exception:
        return "Unknown"


async def safe_export_invite_link(chat_id):
    try:
        return await app.export_chat_invite_link(chat_id)

    except errors.FloodWait as e:
        await asyncio.sleep(e.value + 1)
        try:
            return await app.export_chat_invite_link(chat_id)
        except Exception:
            return None

    except Exception:
        return None


@app.on_message(filters.new_chat_members, group=2)
async def join_watcher(_, message: Message):
    try:
        await _ensure_bot_info()

        if BOT_ID is None:
            return

        chat = message.chat

        for member in message.new_chat_members:

            if member.id != BOT_ID:
                continue

            count = await safe_get_member_count(chat.id)
            link = await safe_export_invite_link(chat.id)

            username = (
                f"@{chat.username}"
                if chat.username
                else "Private"
            )

            added_by = (
                message.from_user.mention
                if message.from_user
                else "Unknown User"
            )

            chat_link = (
                f"[ᴄʟɪᴄᴋ]({link})"
                if link
                else "Private Group"
            )

            msg = (
                "#𝗕𝗢𝗧_𝗔𝗗𝗗𝗘𝗗_𝗡𝗘𝗪_𝗚𝗥𝗢𝗨𝗣\n\n"
                "⦿───────────────────⦿\n\n"
                f"◎ ᴄʜᴀᴛ ɴᴀᴍᴇ ▸ {chat.title}\n"
                f"◎ ᴄʜᴀᴛ ɪᴅ ▸ `{chat.id}`\n"
                f"◎ ᴄʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ ▸ {username}\n"
                f"◎ ᴄʜᴀᴛ ʟɪɴᴋ ▸ {chat_link}\n"
                f"◎ ɢʀᴏᴜᴘ ᴍᴇᴍʙᴇʀs ▸ {count}\n"
                f"◎ ᴀᴅᴅᴇᴅ ʙʏ ▸ {added_by}\n\n"
                "⦿───────────────────⦿"
            )

            reply_markup = None

            if link:
                reply_markup = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "#𝗚𝗥𝗢𝗨𝗣 #𝗟𝗜𝗡𝗞",
                                url=link,
                            )
                        ]
                    ]
                )

            await app.send_photo(
                LOG_GROUP_ID,
                photo=random.choice(PHOTOS),
                caption=msg,
                reply_markup=reply_markup,
            )

    except errors.FloodWait as e:
        await asyncio.sleep(e.value + 1)

    except Exception as e:
        print(f"Error in join_watcher: {e}")


@app.on_message(filters.left_chat_member)
async def on_left_chat_member(_, message: Message):
    try:
        await _ensure_bot_info()

        if BOT_ID is None:
            return

        if message.left_chat_member.id != BOT_ID:
            return

        chat = message.chat

        try:
            await remove_served_chat(chat.id)
        except Exception as e:
            print(f"Failed to remove served chat: {e}")

        remove_by = (
            message.from_user.mention
            if message.from_user
            else "𝐔ɴᴋɴᴏᴡɴ 𝐔sᴇʀ"
        )

        title = chat.title or "Unknown"

        username = (
            f"@{chat.username}"
            if chat.username
            else "𝐏ʀɪᴠᴀᴛᴇ 𝐂ʜᴀᴛ"
        )

        bot_username = (
            f"@{BOT_INFO.username}"
            if BOT_INFO and BOT_INFO.username
            else "Unknown"
        )

        left = (
            "✫ <b><u>#𝗟𝗘𝗙𝗧_𝗚𝗥𝗢𝗨𝗣</u></b> ✫\n\n"
            f"ᴄʜᴀᴛ ᴛɪᴛʟᴇ : {title}\n\n"
            f"ᴄʜᴀᴛ ɪᴅ : <code>{chat.id}</code>\n\n"
            f"ᴄʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ : {username}\n\n"
            f"ʀᴇᴍᴏᴠᴇᴅ ʙʏ : {remove_by}\n\n"
            f"ʙᴏᴛ : {bot_username}"
        )

        await app.send_photo(
            LOG_GROUP_ID,
            photo=random.choice(PHOTOS),
            caption=left,
        )

    except errors.FloodWait as e:
        await asyncio.sleep(e.value + 1)

    except Exception as e:
        print(f"Error in on_left_chat_member: {e}")
