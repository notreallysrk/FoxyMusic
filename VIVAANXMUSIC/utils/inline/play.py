import time
import random
from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton
from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.formatters import time_to_seconds

BUTTON_STYLES = [ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER]
LAST_UPDATE_TIME = {}


def random_button(text, callback_data=None, url=None):
    return InlineKeyboardButton(text=text, callback_data=callback_data, url=url, style=random.choice(BUTTON_STYLES))


def should_update_progress(chat_id):
    now = time.time()
    if now - LAST_UPDATE_TIME.get(chat_id, 0) >= 6:
        LAST_UPDATE_TIME[chat_id] = now
        return True
    return False


def generate_progress_bar(played_sec, duration_sec):
    if not duration_sec:
        percentage = 0
    else:
        percentage = min(max((played_sec / duration_sec) * 100, 0), 100)
    length = 10
    filled = int(length * percentage / 100)
    return "━" * filled + "●" + "━" * (length - filled)


def admin_buttons(chat_id, autoplay=True):
    auto = "ᴀᴜᴛᴏ : ᴏɴ" if autoplay else "ᴀᴜᴛᴏ : ᴏғғ"
    return [
        [
            random_button("ᴘᴀᴜsᴇ", f"ADMIN Pause|{chat_id}"),
            random_button("ʀᴇsᴜᴍᴇ", f"ADMIN Resume|{chat_id}"),
            random_button("sᴋɪᴘ", f"ADMIN Skip|{chat_id}"),
        ],
        [random_button(auto, f"ADMIN AutoPlay|{chat_id}")],
        [random_button("✖ ᴄʟᴏsᴇ", "close")],
    ]


def stream_markup(_, chat_id, autoplay=True, thumb=False, chat_filter=None, more=False):
    return admin_buttons(chat_id, autoplay)


def stream_markup_timer(_, chat_id, played, dur, autoplay=True, thumb=False, chat_filter=None, more=False):
    if not should_update_progress(chat_id):
        return None
    try:
        played_sec = time_to_seconds(played)
    except Exception:
        played_sec = 0
    try:
        duration_sec = time_to_seconds(dur)
    except Exception:
        duration_sec = 0
    remaining = max(duration_sec - played_sec, 0)
    remain = f"{remaining//60:02d}:{remaining%60:02d}"
    bar = generate_progress_bar(played_sec, duration_sec)
    return [[random_button(f"⏱ {played} {bar} {remain}", url=f"https://t.me/{app.username}?startgroup=true")]] + admin_buttons(chat_id, autoplay)
        
