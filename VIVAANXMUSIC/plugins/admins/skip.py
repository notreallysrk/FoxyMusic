from pyrogram import filters
from pyrogram.types import Message

from config import BANNED_USERS
from VIVAANXMUSIC import LOGGER, app
from VIVAANXMUSIC.core.call import JARVIS
from VIVAANXMUSIC.misc import db
from VIVAANXMUSIC.utils.database import (
    get_loop,
    group_assistant,
)
from VIVAANXMUSIC.utils.decorators import AdminRightsCheck
from VIVAANXMUSIC.utils.stream.autoclear import auto_clean


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

    if not check or not isinstance(check, list):
        return await message.reply_text(_["queue_2"])

    loop = await get_loop(chat_id)

    if loop != 0:
        return await message.reply_text(_["admin_8"])

    skip_count = 1

    if len(message.command) > 1:

        state = str(message.command[1]).strip()

        if not state.isdigit():
            return await message.reply_text(_["admin_9"])

        skip_count = int(state)

        if skip_count < 1:
            return await message.reply_text(_["admin_9"])

    try:

        # /skip 2 = current + next 1 skip
        extra_to_skip = skip_count - 1

        available_extra = max(len(check) - 1, 0)

        if extra_to_skip > available_extra:
            return await message.reply_text(
                _["admin_11"].format(len(check))
            )

        # Current ke baad requested tracks remove karo
        for _ in range(extra_to_skip):

            if len(check) <= 1:
                break

            popped = check.pop(1)

            try:
                await auto_clean(popped)
            except Exception:
                pass

        assistant = await group_assistant(
            JARVIS,
            chat_id,
        )

        LOGGER(__name__).info(
            "Manual skip | chat=%s | count=%s | queue=%s",
            chat_id,
            skip_count,
            len(check),
        )

        # change_stream:
        # 1. current song remove karega
        # 2. next queued song play karega
        # 3. queue empty + autoplay ON -> new autoplay song
        await JARVIS.change_stream(
            assistant,
            chat_id,
        )

    except Exception as err:

        LOGGER(__name__).exception(
            "Skip failed | chat=%s | error=%s",
            chat_id,
            err,
        )

        try:
            await message.reply_text(
                _["call_6"]
            )
        except Exception:
            pass
