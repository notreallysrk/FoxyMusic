# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 🚀
# ===========================================================

from pyrogram import enums, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.database import (
    autoplay_off,
    autoplay_on,
    is_autoplay_on,
)
from config import BANNED_USERS


def autoplay_markup(chat_id: int, status: bool):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="✅ ᴇɴᴀʙʟᴇᴅ" if status else "ᴇɴᴀʙʟᴇ ✅",
                    callback_data=f"autoplay_on_{chat_id}",
                ),
                InlineKeyboardButton(
                    text="ᴅɪsᴀʙʟᴇ ❌" if status else "❌ ᴅɪsᴀʙʟᴇᴅ",
                    callback_data=f"autoplay_off_{chat_id}",
                ),
            ]
        ]
    )


def autoplay_text(status: bool) -> str:
    return (
        "**🎧 ᴀᴜᴛᴏᴘʟᴀʏ sᴇᴛᴛɪɴɢs**\n\n"
        f"**ᴄᴜʀʀᴇɴᴛ sᴛᴀᴛᴜs :** "
        f"{'🟢 ᴏɴ' if status else '🔴 ᴏꜰꜰ'}\n\n"
        "**ᴡʜᴇɴ ᴇɴᴀʙʟᴇᴅ**, ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ "
        "ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴘʟᴀʏ ᴀ ʀᴇʟᴀᴛᴇᴅ sᴏɴɢ "
        "ᴏɴᴄᴇ ᴛʜᴇ ǫᴜᴇᴜᴇ ᴇɴᴅs.\n\n"
        "ᴛᴏɢɢʟᴇ ɪᴛ ᴜsɪɴɢ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ 👇"
    )


async def _is_admin(chat_id: int, user_id: int) -> bool:
    try:
        member = await app.get_chat_member(chat_id, user_id)
    except Exception:
        return False

    return member.status in (
        enums.ChatMemberStatus.ADMINISTRATOR,
        enums.ChatMemberStatus.OWNER,
    )


@app.on_message(
    filters.command(["autoplay", "aplay"])
    & filters.group
    & ~BANNED_USERS
)
async def autoplay_cmd(client, message: Message):

    chat_id = message.chat.id

    if len(message.command) > 1 and message.from_user:

        if not await _is_admin(
            chat_id,
            message.from_user.id,
        ):
            return await message.reply_text(
                "❌ **sɪʀꜰ ᴀᴅᴍɪɴs ʜɪ "
                "ᴀᴜᴛᴏᴘʟᴀʏ ᴏɴ/ᴏꜰꜰ ᴋᴀʀ "
                "sᴀᴋᴛᴇ ʜᴀɪɴ.**"
            )

        mode = message.command[1].lower()

        if mode in ("on", "enable"):

            await autoplay_on(chat_id)

            return await message.reply_text(
                "🟢 **ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ "
                "ꜰᴏʀ ᴛʜɪs ᴄʜᴀᴛ.**"
            )

        if mode in ("off", "disable"):

            await autoplay_off(chat_id)

            return await message.reply_text(
                "🔴 **ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ "
                "ꜰᴏʀ ᴛʜɪs ᴄʜᴀᴛ.**"
            )

        return await message.reply_text(
            "**ᴜsᴀɢᴇ :**\n"
            "`/autoplay on`\n"
            "`/autoplay off`"
        )

    status = await is_autoplay_on(chat_id)

    await message.reply_text(
        autoplay_text(status),
        reply_markup=autoplay_markup(
            chat_id,
            status,
        ),
    )


@app.on_callback_query(
    filters.regex(r"^autoplay_(on|off)_(-?\d+)$")
    & ~BANNED_USERS
)
async def autoplay_toggle_cb(
    client,
    query: CallbackQuery,
):

    action = query.matches[0].group(1)
    chat_id = int(
        query.matches[0].group(2)
    )

    if query.message.chat.id != chat_id:
        return await query.answer(
            "❌ ʏᴇ ʙᴜᴛᴛᴏɴ ɪs ᴄʜᴀᴛ "
            "ᴋᴇ ʟɪᴇ ɴᴀʜɪ ʜᴀɪ.",
            show_alert=True,
        )

    if not await _is_admin(
        chat_id,
        query.from_user.id,
    ):
        return await query.answer(
            "❌ sɪʀꜰ ᴀᴅᴍɪɴs ʜɪ "
            "ᴀᴜᴛᴏᴘʟᴀʏ ᴄʜᴀɴɢᴇ "
            "ᴋᴀʀ sᴀᴋᴛᴇ ʜᴀɪɴ.",
            show_alert=True,
        )

    if action == "on":

        await autoplay_on(chat_id)
        status = True

        await query.answer(
            "🟢 ᴀᴜᴛᴏᴘʟᴀʏ ᴇɴᴀʙʟᴇᴅ"
        )

    else:

        await autoplay_off(chat_id)
        status = False

        await query.answer(
            "🔴 ᴀᴜᴛᴏᴘʟᴀʏ ᴅɪsᴀʙʟᴇᴅ"
        )

    try:
        await query.message.edit_text(
            autoplay_text(status),
            reply_markup=autoplay_markup(
                chat_id,
                status,
            ),
        )
    except Exception:
        pass


# ===========================================================
# PLAYER AUTOPLAY TOGGLE BUTTON
# ===========================================================

@app.on_callback_query(
    filters.regex(r"^autoplay_toggle_(-?\d+)$")
    & ~BANNED_USERS
)
async def player_autoplay_toggle(
    client,
    query: CallbackQuery,
):

    chat_id = int(
        query.matches[0].group(1)
    )

    if query.message.chat.id != chat_id:
        return await query.answer(
            "❌ ɪɴᴠᴀʟɪᴅ ᴀᴜᴛᴏᴘʟᴀʏ ʙᴜᴛᴛᴏɴ.",
            show_alert=True,
        )

    if not await _is_admin(
        chat_id,
        query.from_user.id,
    ):
        return await query.answer(
            "❌ sɪʀꜰ ᴀᴅᴍɪɴs ᴀᴜᴛᴏᴘʟᴀʏ "
            "ᴄʜᴀɴɢᴇ ᴋᴀʀ sᴀᴋᴛᴇ ʜᴀɪɴ.",
            show_alert=True,
        )

    current_status = await is_autoplay_on(
        chat_id
    )

    new_status = not current_status

    if new_status:

        await autoplay_on(chat_id)

        await query.answer(
            "🟢 ᴀᴜᴛᴏᴘʟᴀʏ ᴏɴ",
            show_alert=False,
        )

    else:

        await autoplay_off(chat_id)

        await query.answer(
            "🔴 ᴀᴜᴛᴏᴘʟᴀʏ ᴏғғ",
            show_alert=False,
        )

    try:

        old_markup = query.message.reply_markup

        if not old_markup:
            return

        new_keyboard = []

        for row in old_markup.inline_keyboard:

            new_row = []

            for button in row:

                if (
                    button.callback_data
                    == f"autoplay_toggle_{chat_id}"
                ):

                    if new_status:

                        new_row.append(
                            InlineKeyboardButton(
                                text="🟢 ᴀᴜᴛᴏᴘʟᴀʏ ᴏɴ",
                                callback_data=(
                                    f"autoplay_toggle_{chat_id}"
                                ),
                            )
                        )

                    else:

                        new_row.append(
                            InlineKeyboardButton(
                                text="🔴 ᴀᴜᴛᴏᴘʟᴀʏ ᴏғғ",
                                callback_data=(
                                    f"autoplay_toggle_{chat_id}"
                                ),
                            )
                        )

                else:

                    new_row.append(button)

            new_keyboard.append(new_row)

        await query.message.edit_reply_markup(
            InlineKeyboardMarkup(
                new_keyboard
            )
        )

    except Exception as e:
        print(
            f"Player autoplay button error: {e}"
        )


# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder)
# ===========================================================
