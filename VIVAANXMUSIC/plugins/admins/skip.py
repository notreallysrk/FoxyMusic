from pyrogram import filters
from pyrogram.types import Message

from VIVAANXMUSIC import app
from VIVAANXMUSIC.core.call import JARVIS
from VIVAANXMUSIC.misc import db
from VIVAANXMUSIC.utils.database import get_loop
from VIVAANXMUSIC.utils.decorators import AdminRightsCheck
from VIVAANXMUSIC.utils.inline import close_markup
from VIVAANXMUSIC.utils.stream.autoclear import auto_clean
from config import BANNED_USERS


@app.on_message(
    filters.command(
        ["skip", "cskip", "next", "cnext"],
        prefixes=["/", "!"],
    )
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def skip(cli, message: Message, _, chat_id):

    check = db.get(chat_id)

    if not check:
        return await message.reply_text(_["queue_2"])

    loop = await get_loop(chat_id)

    if loop != 0:
        return await message.reply_text(_["admin_8"])

    # /skip 2, /skip 3 etc.
    if len(message.command) >= 2:
        try:
            state = message.command[1].strip()
        except Exception:
            state = ""

        if not state.isnumeric():
            return await message.reply_text(_["admin_9"])

        state = int(state)

        if state < 1:
            return await message.reply_text(_["admin_9"])

        # Queue format:
        # index 0 = currently playing
        # /skip 2 means current + 1 extra next track skip
        available = len(check) - 1

        if available <= 0:
            return await message.reply_text(_["admin_10"])

        if state > available:
            return await message.reply_text(
                _["admin_11"].format(available)
            )

        # Current song ke baad requested songs remove karo.
        # Last current song ko JARVIS.play() remove karega.
        extra_to_remove = state - 1

        if extra_to_remove > 0:
            for _i in range(extra_to_remove):
                if len(check) <= 1:
                    break

                try:
                    popped = check.pop(1)
                except Exception:
                    break

                if popped:
                    try:
                        await auto_clean(popped)
                    except Exception:
                        pass

    # IMPORTANT:
    # Current track ko yahan pop mat karo.
    # JARVIS.play() current track remove karega aur:
    # Queue empty + Autoplay ON => related next song add karega.
    try:
        await JARVIS.play(
            cli,
            chat_id,
        )

    except Exception:
        try:
            await message.reply_text(_["call_6"])
        except Exception:
            pass

        return
