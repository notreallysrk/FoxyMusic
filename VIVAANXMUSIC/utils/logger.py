from html import escape

from pyrogram.enums import ParseMode

from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.database import is_on_off
from config import LOGGER_ID


async def play_logs(message, streamtype, query: str = None):
    """Send a premium play log to LOGGER_ID."""
    if not await is_on_off(2):
        return

    if query is None:
        try:
            query = message.text.split(None, 1)[1]
        except Exception:
            query = "—"

    chat = getattr(message, "chat", None)
    user = getattr(message, "from_user", None)

    chat_id = getattr(chat, "id", "—")
    chat_name = getattr(chat, "title", None) or getattr(chat, "first_name", None) or "Private Chat"
    chat_username = getattr(chat, "username", None)

    user_id = getattr(user, "id", "—")
    user_name = getattr(user, "mention", None) or getattr(user, "first_name", None) or "Unknown"
    user_username = getattr(user, "username", None)

    chat_name = escape(str(chat_name))
    chat_username = escape(str(chat_username)) if chat_username else "None"
    user_name = escape(str(user_name))
    user_username = escape(str(user_username)) if user_username else "None"
    query = escape(str(query))
    streamtype = escape(str(streamtype))

    logger_text = f"""
<b>╭━━━━━━━━━━━━━━━━━━╮</b>
<b>┃ 🎧 {escape(app.mention)} ᴘʟᴀʏ ʟᴏɢ</b>
<b>╰━━━━━━━━━━━━━━━━━━╯</b>

<b>╭─「 💬 ᴄʜᴀᴛ ɪɴғᴏ 」</b>
<b>├ 🆔 ᴄʜᴀᴛ ɪᴅ :</b> <code>{chat_id}</code>
<b>├ 🏷 ᴄʜᴀᴛ ɴᴀᴍᴇ :</b> {chat_name}
<b>╰ 🔗 ᴜsᴇʀɴᴀᴍᴇ :</b> @{chat_username}

<b>╭─「 👤 ᴜsᴇʀ ɪɴғᴏ 」</b>
<b>├ 🆔 ᴜsᴇʀ ɪᴅ :</b> <code>{user_id}</code>
<b>├ 👑 ɴᴀᴍᴇ :</b> {user_name}
<b>╰ 🔗 ᴜsᴇʀɴᴀᴍᴇ :</b> @{user_username}

<b>╭─「 🎵 ᴛʀᴀᴄᴋ ɪɴғᴏ 」</b>
<b>├ 🔎 ǫᴜᴇʀʏ :</b> {query}
<b>╰ 🎶 sᴛʀᴇᴀᴍᴛʏᴘᴇ :</b> {streamtype}

<b>╰━━━━━━━━━━━━━━━━━━╯</b>
"""

    if chat_id == LOGGER_ID:
        return

    try:
        await app.send_message(
            chat_id=LOGGER_ID,
            text=logger_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception:
        pass
        
