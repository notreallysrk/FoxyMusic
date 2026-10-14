from datetime import datetime

from pyrogram import filters
from pyrogram.types import Message
from config import *
from VIVAANXMUSIC import app
from VIVAANXMUSIC.core.call import JARVIS
from VIVAANXMUSIC.utils import bot_sys_stats
from VIVAANXMUSIC.utils.decorators.language import language
from VIVAANXMUSIC.utils.inline import supp_markup
from config import BANNED_USERS, PING_VID_URL


@app.on_message(filters.command("ping", prefixes=["/"]) & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = datetime.now()

    pytgping = await JARVIS.ping()
    UP, CPU, RAM, DISK = await bot_sys_stats()
    resp = (datetime.now() - start).total_seconds() * 1000

    caption = _["ping_2"].format(
        resp, app.mention, UP, RAM, CPU, DISK, pytgping
    )

    # Send normal photo instead of video
    response = await message.reply_photo(
        photo=PING_VID_URL,
        caption=caption,
        reply_markup=supp_markup(_),
    )
