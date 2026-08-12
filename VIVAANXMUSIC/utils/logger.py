from html import escape

from pyrogram.enums import ParseMode

from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.database import is_on_off
from config import LOGGER_ID


def _safe(value, fallback="—"):
    """Convert a value to safe HTML text for Telegram logs."""
    if value is None or value == "":
        return fallback
    return escape(str(value))


async def play_logs(message, streamtype, query: str = None):
    """Send a safe, detailed play log to LOGGER_ID when logging is enabled."""
    if not await is_on_off(2):
        return

    # Get the played query when it wasn't supplied by the caller.
    if query is None:
        try:
            query = message.text.split(None, 1)[1]
        except (AttributeError, IndexError):
            query = "—"

    chat = message.chat
    user = message.from_user

    chat_id = getattr(chat, "id", "—")
    chat_title = _safe(getattr(chat, "title", None))
    chat_username = getattr(chat, "username", None)
    chat_username = f"@{_safe(chat_username)}" if chat_username else "—"

    user_id = getattr(user, "id", "—")
    user_name = getattr(user, "mention", None) or getattr(user, "first_name", None)
    user_name = _safe(user_name)

    username = getattr(user, "username", None)
    username = f"@{_safe(username)}" if username else "—"

    logger_text = f"""
<b>{_safe(app.mention, "VIVAANXMUSIC")} ᴘʟᴀʏ ʟᴏɢ</b>

<b>ᴄʜᴀᴛ ɪᴅ :</b> <code>{chat_id}</code>
<b>ᴄʜᴀᴛ ɴᴀᴍᴇ :</b> {chat_title}
<b>ᴄʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ :</b> {chat_username}

<b>ᴜsᴇʀ ɪᴅ :</b> <code>{user_id}</code>
<b>ɴᴀᴍᴇ :</b> {user_name}
<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {username}

<b>ǫᴜᴇʀʏ :</b> {_safe(query)}
<b>sᴛʀᴇᴀᴍᴛʏᴘᴇ :</b> {_safe(streamtype)}
""".strip()

    # Avoid sending the same log back into the logger chat.
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
        # Logging must never break the actual play command.
        return
    
