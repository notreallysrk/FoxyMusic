from pyrogram import filters
from pyrogram.types import Message

from config import BANNED_USERS
from VIVAANXMUSIC import LOGGER, app
from VIVAANXMUSIC.core.call import JARVIS
from VIVAANXMUSIC.misc import db
from VIVAANXMUSIC.utils.database import (
    get_autoplay,
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

    # /skip 2, /skip 3 ...
    if len(message.command) > 1:
        state = str(message.command[1]).strip()

        if not state.isdigit():
            return await message.reply_text(_["admin_9"])

        skip_count = int(state)

        if skip_count < 1:
            return await message.reply_text(_["admin_9"])

    try:
        # Queue:
        # index 0 = currently playing song
        #
        # JARVIS.play() current song ko remove karta hai.
        # Isliye /skip 2 ka matlab:
        # current remove + 1 queued song remove
        #
        # /skip 3:
        # current remove + 2 queued songs remove
        #
        # IMPORTANT:
        # Yahan current song pop(0) nahi karna.

        extra_to_skip = skip_count - 1

        # Queue me current ke baad jitne songs hain unko skip karo.
        # Autoplay ON ho aur queue khatam ho jaye to JARVIS.play()
        # automatically related next song generate karega.
        if extra_to_skip > 0:
            available_extra = max(len(check) - 1, 0)

            if extra_to_skip > available_extra:
                return await message.reply_text(
                    _["admin_11"].format(len(check))
                )

            for _index in range(extra_to_skip):
                if len(check) <= 1:
                    break

                try:
                    popped = check.pop(1)

                    if popped:
                        await auto_clean(popped)

                except Exception as err:
                    LOGGER(__name__).warning(
                        "Failed to remove skipped queue item | "
                        "chat_id=%s | error=%s",
                        chat_id,
                        err,
                    )

        assistant = await group_assistant(JARVIS, chat_id)

        LOGGER(__name__).info(
            "Manual skip requested | chat_id=%s | "
            "skip_count=%s | queue_before_play=%s | autoplay=%s",
            chat_id,
            skip_count,
            len(db.get(chat_id) or []),
            await get_autoplay(chat_id),
        )

        # IMPORTANT:
        # JARVIS.play() hi current song remove karega
        # aur queue empty hone par autoplay next song add karega.
        await JARVIS.play(assistant, chat_id)

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
