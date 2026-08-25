from pyrogram import filters
from pyrogram.types import Message

from config import BANNED_USERS
from VIVAANXMUSIC import app
from VIVAANXMUSIC.core.call import JARVIS
from VIVAANXMUSIC.misc import db
from VIVAANXMUSIC.utils.database import get_loop, group_assistant
from VIVAANXMUSIC.utils.decorators import AdminRightsCheck
from VIVAANXMUSIC.utils.inline import close_markup
from VIVAANXMUSIC.utils.stream.autoclear import auto_clean


async def _skip_tracks(message: Message, _, chat_id: int, amount: int = 1):
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(_["queue_2"])

    if amount < 1:
        return await message.reply_text(_["admin_9"])

    # Keep the current item in the queue. JARVIS.play() owns the complete
    # transition: pop current -> add autoplay if needed -> switch stream.
    if amount > 1:
        removable = min(amount - 1, max(len(check) - 1, 0))
        for _index in range(removable):
            try:
                item = check.pop(1)
            except IndexError:
                break
            if item:
                await auto_clean(item)

    try:
        assistant = await group_assistant(JARVIS, chat_id)
        await JARVIS.play(assistant, chat_id)
    except Exception:
        # JARVIS.play is decorated and may return None after reporting the
        # internal error. Do not stop/clear the call here, otherwise autoplay
        # gets destroyed on the last queued song.
        return await message.reply_text(_["call_6"])


@app.on_message(
    filters.command(["skip", "cskip", "next", "cnext"], prefixes=["/", "!"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def skip(cli, message: Message, _, chat_id):
    if len(message.command) > 1:
        loop = await get_loop(chat_id)
        if loop != 0:
            return await message.reply_text(_["admin_8"])

        try:
            amount = int(message.command[1])
        except (ValueError, TypeError):
            return await message.reply_text(_["admin_9"])

        if amount < 1:
            return await message.reply_text(_["admin_9"])

        check = db.get(chat_id)
        if not check:
            return await message.reply_text(_["queue_2"])

        # Never stop the stream merely because the queue becomes empty.
        # The last current track is intentionally left for JARVIS.play(),
        # which invokes autoplay before deciding to leave the VC.
        return await _skip_tracks(message, _, chat_id, amount)

    return await _skip_tracks(message, _, chat_id, 1)
            
