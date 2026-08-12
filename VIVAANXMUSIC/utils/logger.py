from pyrogram.enums import ParseMode

from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.database import is_on_off
from config import LOGGER_ID


async def play_logs(message, streamtype, query: str = None):
    if await is_on_off(2):
        if query is None:
            try:
                query = message.text.split(None, 1)[1]
            except Exception:
                query = "—"

        logger_text = f"""
<b>{app.mention} ᴘʟᴀʏ ʟᴏɢ</b>

<b>ᴄʜᴀᴛ ɪᴅ :</b> <code>{message.chat.id}</code>
<b>ᴄʜᴀᴛ ɴᴀᴍᴇ :</b> {message.chat.title}
<b>ᴄʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.chat.username}

<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>
<b>ɴᴀᴍᴇ :</b> {message.from_user.mention}
<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}

<b>ǫᴜᴇʀʏ :</b> {query}
<b>sᴛʀᴇᴀᴍᴛʏᴘᴇ :</b> {streamtype}"""

        if message.chat.id != LOGGER_ID:
            try:
                await app.send_message(
                    chat_id=LOGGER_ID,
                    text=logger_text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
        return


async def failure_logs(message, reason=None, area="Playback"):
    """Log playback failures without allowing logging errors to crash the bot."""
    try:
        if not await is_on_off(2):
            return

        chat = getattr(message, "chat", None)
        user = getattr(message, "from_user", None)

        chat_id = getattr(chat, "id", "—")
        chat_title = getattr(chat, "title", None) or "—"
        chat_username = getattr(chat, "username", None) or "—"
        user_id = getattr(user, "id", "—")
        user_name = (
            getattr(user, "mention", None)
            or getattr(user, "first_name", None)
            or "—"
        )
        user_username = getattr(user, "username", None) or "—"

        logger_text = f"""
<b>{app.mention} ғᴀɪʟᴜʀᴇ ʟᴏɢ</b>

<b>ᴀʀᴇᴀ :</b> {area}
<b>ʀᴇᴀsᴏɴ :</b> {reason or 'Unknown error'}

<b>ᴄʜᴀᴛ ɪᴅ :</b> <code>{chat_id}</code>
<b>ᴄʜᴀᴛ ɴᴀᴍᴇ :</b> {chat_title}
<b>ᴄʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ :</b> @{chat_username}

<b>ᴜsᴇʀ ɪᴅ :</b> <code>{user_id}</code>
<b>ɴᴀᴍᴇ :</b> {user_name}
<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{user_username}"""

        if chat_id != LOGGER_ID:
            try:
                await app.send_message(
                    chat_id=LOGGER_ID,
                    text=logger_text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
    except Exception:
        pass
            
