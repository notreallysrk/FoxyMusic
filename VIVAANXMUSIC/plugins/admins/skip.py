from pyrogram import filters
from pyrogram.types import Message

from VIVAANXMUSIC import LOGGER, app
from VIVAANXMUSIC.core.call import JARVIS
from VIVAANXMUSIC.misc import db
from VIVAANXMUSIC.utils.database import (
    get_loop,
    group_assistant,
)
from VIVAANXMUSIC.utils.decorators import AdminRightsCheck
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

    skip_count = 1

    # /skip 2, /skip 3 ...
    if len(message.command) > 1:
        state = str(message.command[1]).strip()

        if not state.isdigit():
            return await message.reply_text(_["admin_9"])

        skip_count = int(state)

        if skip_count < 1:
            return await message.reply_text(_["admin_9"])

        # Queue index 0 = current playing song.
        # Current song JARVIS.play() remove karega.
        # Isliye additional songs index 1 se remove honge.
        if skip_count > len(check):
            return await message.reply_text(
                _["admin_11"].format(len(check))
            )

        extra_to_skip = skip_count - 1

        for _index in range(extra_to_skip):
            if len(check) <= 1:
                break

            try:
                popped = check.pop(1)

                if popped:
                    try:
                        await auto_clean(popped)
                    except Exception:
                        pass

            except Exception as err:
                LOGGER(__name__).warning(
                    "Failed to remove skipped queue item | "
                    "chat_id=%s | error=%s",
                    chat_id,
                    err,
                )

    # IMPORTANT:
    # Current song ko yahan pop(0) mat karo.
    #
    # JARVIS.play():
    # 1. Current song remove karega
    # 2. Queue ka next song play karega
    # 3. Queue empty + Autoplay ON ho to
    #    YouTube autoplay se new related song add karega
    try:
        assistant = await group_assistant(
            JARVIS,
            chat_id,
        )

        await JARVIS.play(
            assistant,
            chat_id,
        )

    except Exception as err:
        LOGGER(__name__).exception(
            "Skip failed | chat_id=%s | error=%s",
            chat_id,
            err,
        )

        try:
            await message.reply_text(_["call_6"])
        except Exception:
            pass
