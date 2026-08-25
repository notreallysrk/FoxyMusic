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

    # =========================================
    # /skip 2, /skip 3, etc.
    # =========================================
    if len(message.command) > 1:

        state = str(message.command[1]).strip()

        if not state.isdigit():
            return await message.reply_text(_["admin_9"])

        skip_count = int(state)

        if skip_count < 1:
            return await message.reply_text(_["admin_9"])

    try:

        # =========================================
        # REMOVE EXTRA QUEUE SONGS
        #
        # db[0] = current playing song
        #
        # /skip 1:
        #   remove current using change_stream()
        #
        # /skip 2:
        #   remove index 1 first
        #   then change_stream removes current
        #
        # /skip 3:
        #   remove index 1 and index 2
        #   then change_stream removes current
        # =========================================

        extra_to_skip = skip_count - 1

        if extra_to_skip > 0:

            available_extra = len(check) - 1

            if extra_to_skip > available_extra:
                return await message.reply_text(
                    _["admin_11"].format(len(check))
                )

            for _ in range(extra_to_skip):

                if len(check) <= 1:
                    break

                popped = check.pop(1)

                try:
                    if popped:
                        await auto_clean(popped)
                except Exception as err:
                    LOGGER(__name__).warning(
                        "Failed to clean skipped track | "
                        "chat_id=%s | error=%s",
                        chat_id,
                        err,
                    )

        # =========================================
        # GET CURRENT ASSISTANT
        # =========================================

        assistant = await group_assistant(
            JARVIS,
            chat_id,
        )

        # =========================================
        # IMPORTANT:
        #
        # change_stream() will:
        #
        # 1. Remove current song db[0]
        # 2. Check normal queue
        # 3. If queue exists → play next
        # 4. If queue empty + autoplay ON
        #    → start related autoplay
        # 5. Autoplay OFF → leave call
        # =========================================

        LOGGER(__name__).info(
            "Manual skip | chat_id=%s | "
            "skip_count=%s | queue=%s",
            chat_id,
            skip_count,
            len(db.get(chat_id) or []),
        )

        await JARVIS.change_stream(
            assistant,
            chat_id,
        )

        try:
            await message.delete()
        except Exception:
            pass

    except Exception as err:

        LOGGER(__name__).exception(
            "Skip failed | chat_id=%s | error=%s",
            chat_id,
            err,
        )

        try:
            await message.reply_text(
                _["call_6"]
            )
        except Exception:
            pass
