from pyrogram import filters
from pyrogram.types import Message

from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.database import (
    get_autoplay,
    get_cmode,
    set_autoplay,
)
from VIVAANXMUSIC.utils.decorators.admins import AdminActual
from VIVAANXMUSIC.utils.inline import close_markup
from config import BANNED_USERS


@app.on_message(
    filters.command(["autoplay", "cautoplay"])
    & filters.group
    & ~BANNED_USERS
)
@AdminActual
async def autoplay_control(_, message: Message, strings):

    # Safe fallback: admin_49 missing hone par error nahi aayega
    usage = strings.get(
        "admin_49",
        "ᴜsᴀɢᴇ : /autoplay [on | off]"
    )

    command = message.command[0].lower()

    if command.startswith("c"):
        chat_id = await get_cmode(message.chat.id)

        if chat_id is None:
            return await message.reply_text(
                strings.get(
                    "setting_7",
                    "❖ ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ ɪs ɴᴏᴛ ᴇɴᴀʙʟᴇᴅ."
                ),
                reply_markup=close_markup(strings),
            )

        try:
            await app.get_chat(chat_id)
        except Exception:
            return await message.reply_text(
                strings.get(
                    "cplay_4",
                    "❖ ᴄʜᴀɴɴᴇʟ ɴᴏᴛ ғᴏᴜɴᴅ."
                ),
                reply_markup=close_markup(strings),
            )

    else:
        chat_id = message.chat.id

    # /autoplay bina argument ke
    if len(message.command) < 2:
        status = (
            "enabled"
            if await get_autoplay(chat_id)
            else "disabled"
        )

        text = strings.get(
            "admin_52",
            "❖ ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴄᴜʀʀᴇɴᴛʟʏ {}."
        ).format(status)

        return await message.reply_text(
            text,
            reply_markup=close_markup(strings),
        )

    # Safe argument extraction
    state = message.command[1].strip().lower()

    if state in {
        "on",
        "enable",
        "enabled",
        "yes",
        "true",
    }:
        await set_autoplay(chat_id, True)

        text = strings.get(
            "admin_50",
            "❖ ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ ʙʏ {}."
        ).format(message.from_user.mention)

        return await message.reply_text(
            text,
            reply_markup=close_markup(strings),
        )

    if state in {
        "off",
        "disable",
        "disabled",
        "no",
        "false",
    }:
        await set_autoplay(chat_id, False)

        text = strings.get(
            "admin_51",
            "❖ ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ ʙʏ {}."
        ).format(message.from_user.mention)

        return await message.reply_text(
            text,
            reply_markup=close_markup(strings),
        )

    return await message.reply_text(
        usage,
        reply_markup=close_markup(strings),
        )
