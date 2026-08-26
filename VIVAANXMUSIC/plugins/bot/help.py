import re
from typing import Union

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.database import (
    get_autoplay,
    get_lang,
    set_autoplay,
)
from VIVAANXMUSIC.utils.decorators.language import (
    LanguageStart,
    languageCB,
)
from VIVAANXMUSIC.utils.inline.help import (
    action_sub_menu,
    first_page,
    help_back_markup,
    private_help_panel,
    second_page,
)
from VIVAANXMUSIC.utils.inline.start import private_panel
from config import BANNED_USERS, HELP_IMG_URL, SUPPORT_CHAT
from strings import get_string, helpers


@app.on_message(
    filters.command(["help"])
    & filters.private
    & ~BANNED_USERS
)
@app.on_callback_query(
    filters.regex(r"^open_help$")
    & ~BANNED_USERS
)
@LanguageStart
async def helper_private(
    client: Client,
    update: Union[Message, CallbackQuery],
    _,
):
    is_callback = isinstance(update, CallbackQuery)

    # FIX: CallbackQuery me .chat nahi hota
    if is_callback:
        chat_id = update.message.chat.id
        user_id = update.from_user.id
    else:
        chat_id = update.chat.id
        user_id = update.from_user.id

    language = await get_lang(user_id)
    _ = get_string(language)

    keyboard = await first_page(_, chat_id)
    caption = _["help_1"].format(SUPPORT_CHAT)

    if is_callback:
        await update.answer()

        try:
            await update.message.edit_caption(
                caption=caption,
                reply_markup=keyboard,
            )
        except Exception:
            await update.message.edit_text(
                text=caption,
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
        return

    try:
        await update.delete()
    except Exception:
        pass

    await update.reply_photo(
        photo=HELP_IMG_URL,
        caption=caption,
        reply_markup=keyboard,
    )


@app.on_message(
    filters.command(["help"])
    & filters.group
    & ~BANNED_USERS
)
@LanguageStart
async def help_com_group(
    client: Client,
    message: Message,
    _,
):
    keyboard = private_help_panel(_)

    await message.reply_text(
        _["help_2"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )


@app.on_callback_query(
    filters.regex(r"^help_callback hb(\d+)_p(\d+)$")
    & ~BANNED_USERS
)
@languageCB
async def helper_cb(
    client: Client,
    callback_query: CallbackQuery,
    _,
):
    match = re.match(
        r"^help_callback hb(\d+)_p(\d+)$",
        callback_query.data,
    )

    if not match:
        await callback_query.answer(
            "Invalid callback.",
            show_alert=True,
        )
        return

    number = int(match.group(1))
    current_page = int(match.group(2))

    if number == 1:
        await callback_query.edit_message_text(
            text=_["S_B_M"],
            reply_markup=action_sub_menu(_, current_page),
            disable_web_page_preview=True,
        )
        return

    help_text = getattr(
        helpers,
        f"HELP_{number}",
        None,
    )

    if not help_text:
        await callback_query.answer(
            "Invalid help topic.",
            show_alert=True,
        )
        return

    await callback_query.edit_message_text(
        text=help_text,
        reply_markup=help_back_markup(
            _,
            current_page,
        ),
        disable_web_page_preview=True,
    )


# =====================================================
# ACTUAL AUTOPLAY ON / OFF TOGGLE BUTTON
# =====================================================
@app.on_callback_query(
    filters.regex(r"^toggle_autoplay$")
    & ~BANNED_USERS
)
@languageCB
async def toggle_autoplay_cb(
    client: Client,
    callback_query: CallbackQuery,
    _,
):
    chat_id = callback_query.message.chat.id

    try:
        current_status = await get_autoplay(chat_id)
        new_status = not bool(current_status)

        await set_autoplay(
            chat_id,
            new_status,
        )

        status = (
            "🟢 ON"
            if new_status
            else "🔴 OFF"
        )

        await callback_query.answer(
            f"Aᴜᴛᴏᴘʟᴀʏ {status}",
            show_alert=False,
        )

        keyboard = await second_page(
            _,
            chat_id,
        )

        try:
            await callback_query.message.edit_reply_markup(
                reply_markup=keyboard,
            )
        except Exception:
            pass

    except Exception as e:
        print(
            f"Autoplay Toggle Error: {e}"
        )

        await callback_query.answer(
            "Failed to change autoplay.",
            show_alert=True,
        )


# =====================================================
# NEXT HELP PAGE
# =====================================================
@app.on_callback_query(
    filters.regex(r"^help_next_(\d+)$")
    & ~BANNED_USERS
)
@languageCB
async def help_next_cb(
    client: Client,
    callback_query: CallbackQuery,
    _,
):
    page = int(
        callback_query.data.split("_")[-1]
    )

    if page != 2:
        await callback_query.answer(
            "No more pages.",
            show_alert=True,
        )
        return

    chat_id = callback_query.message.chat.id

    keyboard = await second_page(
        _,
        chat_id,
    )

    await callback_query.edit_message_text(
        text=_["help_1"].format(SUPPORT_CHAT),
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


# =====================================================
# PREVIOUS HELP PAGE
# =====================================================
@app.on_callback_query(
    filters.regex(r"^help_prev_(\d+)$")
    & ~BANNED_USERS
)
@languageCB
async def help_prev_cb(
    client: Client,
    callback_query: CallbackQuery,
    _,
):
    page = int(
        callback_query.data.split("_")[-1]
    )

    if page != 1:
        await callback_query.answer(
            "No previous page.",
            show_alert=True,
        )
        return

    chat_id = callback_query.message.chat.id

    keyboard = await first_page(
        _,
        chat_id,
    )

    await callback_query.edit_message_text(
        text=_["help_1"].format(SUPPORT_CHAT),
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


# =====================================================
# BACK FROM HELP SECTION
# =====================================================
@app.on_callback_query(
    filters.regex(r"^help_back_(\d+)$")
    & ~BANNED_USERS
)
@languageCB
async def help_back_cb(
    client: Client,
    callback_query: CallbackQuery,
    _,
):
    page = int(
        callback_query.data.split("_")[-1]
    )

    chat_id = callback_query.message.chat.id

    if page == 1:
        keyboard = await first_page(
            _,
            chat_id,
        )

    elif page == 2:
        keyboard = await second_page(
            _,
            chat_id,
        )

    else:
        await callback_query.answer(
            "Invalid page.",
            show_alert=True,
        )
        return

    await callback_query.edit_message_text(
        text=_["help_1"].format(SUPPORT_CHAT),
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


# =====================================================
# ACTION SUB MENU
# =====================================================
@app.on_callback_query(
    filters.regex(r"^action_prom_1$")
    & ~BANNED_USERS
)
@languageCB
async def action_prom_cb(
    client: Client,
    callback_query: CallbackQuery,
    _,
):
    await callback_query.edit_message_text(
        text=helpers.HELP_1_PROMO,
        reply_markup=help_back_markup(_, 1),
        disable_web_page_preview=True,
    )


@app.on_callback_query(
    filters.regex(r"^action_pun_1$")
    & ~BANNED_USERS
)
@languageCB
async def action_pun_cb(
    client: Client,
    callback_query: CallbackQuery,
    _,
):
    await callback_query.edit_message_text(
        text=helpers.HELP_1_PUNISH,
        reply_markup=help_back_markup(_, 1),
        disable_web_page_preview=True,
    )


# =====================================================
# BACK TO MAIN MENU
# =====================================================
@app.on_callback_query(
    filters.regex(r"^back_to_main$")
    & ~BANNED_USERS
)
@languageCB
async def back_to_main_cb(
    client: Client,
    callback_query: CallbackQuery,
    _,
):
    try:
        await callback_query.answer()
    except Exception:
        pass

    out = private_panel(_)

    caption = _["start_2"].format(
        callback_query.from_user.mention,
        app.mention,
    )

    try:
        await callback_query.message.edit_caption(
            caption=caption,
            reply_markup=InlineKeyboardMarkup(out),
        )
    except Exception:
        await callback_query.message.edit_text(
            text=caption,
            reply_markup=InlineKeyboardMarkup(out),
            disable_web_page_preview=True,
    )
