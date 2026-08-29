import asyncio
import random

from pyrogram import filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import (
    BANNED_USERS,
    lyrical,
    SOUNCLOUD_IMG_URL,
    STREAM_IMG_URL,
    SUPPORT_CHAT,
    TELEGRAM_AUDIO_URL,
    TELEGRAM_VIDEO_URL,
    adminlist,
    confirmer,
    votemode,
)

from strings import get_string

from VIVAANXMUSIC import YouTube, app
from VIVAANXMUSIC.core.call import JARVIS
from VIVAANXMUSIC.misc import SUDOERS, db

from VIVAANXMUSIC.utils.database import (
    get_active_chats,
    get_assistant,
    get_lang,
    get_upvote_count,
    is_active_chat,
    is_music_playing,
    is_muted,
    is_nonadmin_chat,
    is_autoplay_on,
    music_off,
    music_on,
    mute_off,
    mute_on,
    set_autoplay,
    set_loop,
)

from VIVAANXMUSIC.utils.decorators import (
    ActualAdminCB,
    languageCB,
)

from VIVAANXMUSIC.utils.formatters import seconds_to_min

from VIVAANXMUSIC.utils.inline import (
    close_markup,
    stream_markup,
    stream_markup_timer,
)

from VIVAANXMUSIC.utils.stream.autoclear import auto_clean

from VIVAANXMUSIC.utils.stream.autodelete import (
    delete_queue_message,
    remember_player_message,
)

from VIVAANXMUSIC.utils.stream.cards import (
    schedule_stream_card,
)


# ==========================================================
# GLOBALS
# ==========================================================

checker = {}
upvoters = {}


# ==========================================================
# SAFE HELPERS
# ==========================================================

async def _safe_edit_callback_message(
    callback: CallbackQuery,
    text: str,
    reply_markup=None,
):
    try:
        await callback.edit_message_text(
            text,
            reply_markup=reply_markup,
        )
    except Exception:
        pass


async def _safe_reply_callback_message(
    callback: CallbackQuery,
    text: str,
    reply_markup=None,
):
    try:
        return await callback.message.reply_text(
            text,
            reply_markup=reply_markup,
        )
    except Exception:
        try:
            return await app.send_message(
                callback.message.chat.id,
                text,
                reply_markup=reply_markup,
            )
        except Exception:
            return None


def parse_chat_info(chat_info: str):
    if "_" in chat_info:
        parts = chat_info.split("_", 1)

        try:
            return int(parts[0]), parts[1]
        except Exception:
            return int(parts[0]), None

    return int(chat_info), None


# ==========================================================
# ADMIN CHECK
# ==========================================================

async def _player_is_admin(
    callback: CallbackQuery,
    chat_id: int,
) -> bool:

    if callback.from_user.id in SUDOERS:
        return True

    try:
        admins = adminlist.get(chat_id)

        if admins and callback.from_user.id in admins:
            return True

    except Exception:
        pass

    return False


# ==========================================================
# PLAYER MORE MENU
# ==========================================================

def player_more_markup(chat_id: int):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="▷",
                    callback_data=f"ADMIN Resume|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="II",
                    callback_data=f"ADMIN Pause|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="‣‣I",
                    callback_data=f"ADMIN Skip|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="↻",
                    callback_data=f"ADMIN Replay|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="▢",
                    callback_data=f"ADMIN Stop|{chat_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="♫",
                    callback_data=f"ADMIN Autoplay|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="⎘",
                    callback_data=f"ADMIN Thumb|{chat_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="← BACK",
                    callback_data=f"ADMIN Back|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data="close",
                ),
            ],
        ]
    )


# ==========================================================
# NORMAL PLAYER MENU
# ==========================================================

def player_normal_markup(chat_id: int):

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="▷",
                    callback_data=f"ADMIN Resume|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="II",
                    callback_data=f"ADMIN Pause|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="‣‣I",
                    callback_data=f"ADMIN Skip|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="↻",
                    callback_data=f"ADMIN Replay|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="▢",
                    callback_data=f"ADMIN Stop|{chat_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="☰",
                    callback_data=f"ADMIN More|{chat_id}",
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data="close",
                ),
            ],
        ]
    )


# ==========================================================
# UPVOTE
# ==========================================================

async def handle_upvote(
    callback: CallbackQuery,
    chat_id: int,
    counter,
    _,
):

    message_id = callback.message.id

    votemode.setdefault(
        chat_id,
        {},
    ).setdefault(
        message_id,
        0,
    )

    upvoters.setdefault(
        chat_id,
        {},
    ).setdefault(
        message_id,
        [],
    )

    user_id = callback.from_user.id

    if user_id in upvoters[chat_id][message_id]:

        upvoters[chat_id][message_id].remove(
            user_id
        )

        votemode[chat_id][message_id] -= 1

    else:

        upvoters[chat_id][message_id].append(
            user_id
        )

        votemode[chat_id][message_id] += 1

    required_upvotes = await get_upvote_count(
        chat_id
    )

    current_upvotes = int(
        votemode[chat_id][message_id]
    )

    if current_upvotes >= required_upvotes:

        votemode[chat_id][message_id] = (
            required_upvotes
        )

        try:
            stored = confirmer[
                chat_id
            ][message_id]

            current = db[
                chat_id
            ][0]

        except Exception:
            return await callback.edit_message_text(
                "ғᴀɪʟᴇᴅ."
            )

        try:

            if (
                current["vidid"]
                != stored["vidid"]
                or current["file"]
                != stored["file"]
            ):
                return await callback.edit_message_text(
                    _["admin_35"]
                )

        except Exception:

            return await callback.edit_message_text(
                _["admin_36"]
            )

        try:
            await callback.edit_message_text(
                _["admin_37"].format(
                    required_upvotes
                )
            )
        except Exception:
            pass

        return (
            counter
            if counter is not None
            else "UpVote",
            "ᴜᴘᴠᴏᴛᴇs",
        )

    else:

        if user_id in upvoters[
            chat_id
        ][message_id]:

            await callback.answer(
                _["admin_38"],
                show_alert=True,
            )

        else:

            await callback.answer(
                _["admin_39"],
                show_alert=True,
            )

        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=f"👍 {current_upvotes}",
                        callback_data=(
                            "ADMIN UpVote|"
                            f"{chat_id}_"
                            f"{counter if counter is not None else chat_id}"
                        ),
                    )
                ]
            ]
        )

        await callback.answer(
            _["admin_40"],
            show_alert=True,
        )

        try:
            await callback.edit_message_reply_markup(
                reply_markup=markup
            )
        except Exception:
            pass

        return None, None


# ==========================================================
# UNBAN ASSISTANT
# ==========================================================

@app.on_callback_query(
    filters.regex("unban_assistant")
    & ~BANNED_USERS
)
async def unban_assistant(
    _,
    callback: CallbackQuery,
):

    chat_id = callback.message.chat.id

    userbot = await get_assistant(
        chat_id
    )

    try:

        await app.unban_chat_member(
            chat_id,
            userbot.id,
        )

        await callback.answer(
            "ᴍʏ ᴀssɪsᴛᴀɴᴛ ɪᴅ ᴜɴʙᴀɴɴᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ🥰🥳\n\n"
            "➻ ɴᴏᴡ ʏᴏᴜ ᴄᴀɴ ᴘʟᴀʏ sᴏɴɢs🫠🔉\n\n"
            "Tʜᴀɴᴋ ʏᴏᴜ💗",
            show_alert=True,
        )

    except Exception:

        await callback.answer(
            "Fᴀɪʟᴇᴅ ᴛᴏ ᴜɴʙᴀɴ ᴍʏ ᴀssɪsᴛᴀɴᴛ\n\n"
            "➻ Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴍᴇ ʙᴀɴ ᴘᴏᴡᴇʀ",
            show_alert=True,
        )


# ==========================================================
# MORE CALLBACK
# ==========================================================

@app.on_callback_query(
    filters.regex(
        r"^(?:player_more\||ADMIN More\|)(-?\d+)$"
    )
    & ~BANNED_USERS
)
async def player_more_callback(
    client,
    callback: CallbackQuery,
):

    chat_id = int(
        callback.matches[0].group(1)
    )

    if callback.message.chat.id != chat_id:

        return await callback.answer(
            "❌ ɪɴᴠᴀʟɪᴅ ᴘʟᴀʏᴇʀ ᴍᴇɴᴜ.",
            show_alert=True,
        )

    if not await is_active_chat(chat_id):

        return await callback.answer(
            "❌ ɴᴏ ᴀᴄᴛɪᴠᴇ sᴛʀᴇᴀᴍ.",
            show_alert=True,
        )

    if not await _player_is_admin(
        callback,
        chat_id,
    ):

        return await callback.answer(
            "❌ sɪʀғ ᴀᴅᴍɪɴs ᴋᴏ ʏᴇ ᴍᴇɴᴜ ᴜsᴇ ᴋᴀʀɴᴇ ᴋɪ ᴘᴇʀᴍɪssɪᴏɴ ʜᴀɪ.",
            show_alert=True,
        )

    await callback.answer()

    try:

        await callback.message.edit_reply_markup(
            reply_markup=player_more_markup(
                chat_id
            )
        )

    except Exception as e:

        print(
            f"Player MORE menu error: {e}"
        )


# ==========================================================
# BACK CALLBACK
# ==========================================================

@app.on_callback_query(
    filters.regex(
        r"^ADMIN Back\|(-?\d+)$"
    )
    & ~BANNED_USERS
)
async def player_back_callback(
    client,
    callback: CallbackQuery,
):

    chat_id = int(
        callback.matches[0].group(1)
    )

    if callback.message.chat.id != chat_id:

        return await callback.answer(
            "❌ ɪɴᴠᴀʟɪᴅ ᴘʟᴀʏᴇʀ.",
            show_alert=True,
        )

    if not await _player_is_admin(
        callback,
        chat_id,
    ):

        return await callback.answer(
            "❌ sɪʀғ ᴀᴅᴍɪɴs ʜɪ ʏᴇ ʙᴜᴛᴛᴏɴ ᴜsᴇ ᴋᴀʀ sᴀᴋᴛᴇ ʜᴀɪɴ.",
            show_alert=True,
        )

    await callback.answer()

    try:

        await callback.message.edit_reply_markup(
            reply_markup=player_normal_markup(
                chat_id
            )
        )

    except Exception as e:

        print(
            f"Player BACK error: {e}"
        )


# ==========================================================
# MAIN ADMIN CALLBACK
# ==========================================================

@app.on_callback_query(
    filters.regex("ADMIN")
    & ~BANNED_USERS
)
@languageCB
async def manage_callback(
    client,
    callback: CallbackQuery,
    _,
):

    try:

        data = callback.data.strip().split(
            None,
            1,
        )[1]

        command, chat_info = data.split(
            "|",
            1,
        )

        chat_id, counter = parse_chat_info(
            chat_info
        )

    except Exception:

        return await callback.answer(
            "❌ Invalid callback.",
            show_alert=True,
        )

    if not await is_active_chat(
        chat_id
    ):

        return await callback.answer(
            _["general_5"],
            show_alert=True,
        )

    user_mention = (
        callback.from_user.mention
    )

    # ======================================================
    # UPVOTE
    # ======================================================

    if command == "UpVote":

        new_command, new_mention = (
            await handle_upvote(
                callback,
                chat_id,
                counter,
                _,
            )
        )

        if new_command is None:
            return

        command = new_command
        user_mention = new_mention

    # ======================================================
    # ADMIN CHECK
    # ======================================================

    else:

        if (
            not await is_nonadmin_chat(
                callback.message.chat.id
            )
            and callback.from_user.id
            not in SUDOERS
        ):

            admins = adminlist.get(
                callback.message.chat.id
            )

            if not admins:

                return await callback.answer(
                    _["admin_13"],
                    show_alert=True,
                )

            if (
                callback.from_user.id
                not in admins
            ):

                return await callback.answer(
                    _["admin_14"],
                    show_alert=True,
                )

    # ======================================================
    # PAUSE
    # ======================================================

    if command == "Pause":

        if not await is_music_playing(
            chat_id
        ):

            return await callback.answer(
                _["admin_1"],
                show_alert=True,
            )

        await callback.answer()

        await music_off(
            chat_id
        )

        await JARVIS.pause_stream(
            chat_id
        )

        await callback.message.reply_text(
            _["admin_2"].format(
                user_mention
            ),
            reply_markup=close_markup(_),
        )

    # ======================================================
    # RESUME
    # ======================================================

    elif command == "Resume":

        if await is_music_playing(
            chat_id
        ):

            return await callback.answer(
                _["admin_3"],
                show_alert=True,
            )

        await callback.answer()

        await music_on(
            chat_id
        )

        await JARVIS.resume_stream(
            chat_id
        )

        await callback.message.reply_text(
            _["admin_4"].format(
                user_mention
            ),
            reply_markup=close_markup(_),
        )

    # ======================================================
    # STOP
    # ======================================================

    elif command in [
        "Stop",
        "End",
    ]:

        await callback.answer()

        await JARVIS.stop_stream(
            chat_id
        )

        await set_loop(
            chat_id,
            0,
        )

        await _safe_reply_callback_message(
            callback,
            _["admin_5"].format(
                user_mention
            ),
            reply_markup=close_markup(_),
        )

        try:
            await callback.message.delete()
        except Exception:
            pass

    # ======================================================
    # MUTE
    # ======================================================

    elif command == "Mute":

        if await is_muted(chat_id):

            return await callback.answer(
                _["admin_45"],
                show_alert=True,
            )

        await callback.answer()

        await mute_on(
            chat_id
        )

        await JARVIS.mute_stream(
            chat_id
        )

        await callback.message.reply_text(
            _["admin_46"].format(
                user_mention
            )
        )

    # ======================================================
    # UNMUTE
    # ======================================================

    elif command == "Unmute":

        if not await is_muted(chat_id):

            return await callback.answer(
                _["admin_47"],
                show_alert=True,
            )

        await callback.answer()

        await mute_off(
            chat_id
        )

        await JARVIS.unmute_stream(
            chat_id
        )

        await callback.message.reply_text(
            _["admin_48"].format(
                user_mention
            )
        )

    # ======================================================
    # LOOP
    # ======================================================

    elif command == "Loop":

        await callback.answer()

        await set_loop(
            chat_id,
            3,
        )

        await callback.message.reply_text(
            _["admin_41"].format(
                user_mention,
                3,
            )
        )

    # ======================================================
    # SHUFFLE
    # ======================================================

    elif command == "Shuffle":

        playlist = db.get(
            chat_id
        )

        if not playlist:

            return await callback.answer(
                _["admin_42"],
                show_alert=True,
            )

        try:

            popped = playlist.pop(
                0
            )

        except Exception:

            return await callback.answer(
                _["admin_43"],
                show_alert=True,
            )

        if not playlist:

            playlist.insert(
                0,
                popped,
            )

            return await callback.answer(
                _["admin_43"],
                show_alert=True,
            )

        await callback.answer()

        random.shuffle(
            playlist
        )

        playlist.insert(
            0,
            popped,
        )

        await callback.message.reply_text(
            _["admin_44"].format(
                user_mention
            )
        )

    # ======================================================
    # AUTOPLAY
    #
    # IMPORTANT:
    # NO SETTINGS MESSAGE
    # NO STATUS MESSAGE
    # ONLY TOGGLE
    # ======================================================

    elif command == "Autoplay":

        try:

            current = await is_autoplay_on(
                chat_id
            )

        except Exception:

            current = False

        try:

            await set_autoplay(
                chat_id,
                not current,
            )

        except TypeError:

            try:

                await set_autoplay(
                    chat_id
                )

            except Exception as e:

                print(
                    f"Autoplay toggle error: {e}"
                )

                return await callback.answer(
                    "❌ Autoplay change nahi ho saka.",
                    show_alert=True,
                )

        except Exception as e:

            print(
                f"Autoplay toggle error: {e}"
            )

            return await callback.answer(
                "❌ Autoplay change nahi ho saka.",
                show_alert=True,
            )

        # ----------------------------------------------
        # NO MESSAGE EDIT
        # NO SETTINGS SCREEN
        # ----------------------------------------------

        await callback.answer(
            "🟢 AUTO PLAY ON"
            if not current
            else "🔴 AUTO PLAY OFF",
            show_alert=False,
        )

        try:

            await callback.message.edit_reply_markup(
                reply_markup=player_more_markup(
                    chat_id
                )
            )

        except Exception:
            pass

    # ======================================================
    # THUMB
    #
    # Keep your existing thumb callback if another file
    # handles it. Do NOT send it to seek.
    # ======================================================

    elif command == "Thumb":

        await callback.answer(
            "⎘",
            show_alert=False,
        )

    # ======================================================
    # BACK
    # ======================================================

    elif command == "Back":

        await callback.answer()

        try:

            await callback.message.edit_reply_markup(
                reply_markup=player_normal_markup(
                    chat_id
                )
            )

        except Exception as e:

            print(
                f"Back error: {e}"
            )

    # ======================================================
    # SKIP / REPLAY
    # ======================================================

    elif command in [
        "Skip",
        "Replay",
    ]:

        await handle_skip_replay(
            callback,
            _,
            chat_id,
            command,
            user_mention,
        )

    # ======================================================
    # SEEK
    # ======================================================

    else:

        # Never allow text commands such as More,
        # Back, Autoplay etc. to reach handle_seek.

        if command in [
            "More",
            "Back",
            "Autoplay",
            "Thumb",
        ]:
            return

        try:

            int(command)

        except ValueError:

            return await callback.answer(
                "❌ Invalid player command.",
                show_alert=True,
            )

        await handle_seek(
            callback,
            _,
            chat_id,
            command,
            user_mention,
        )


# ==========================================================
# SKIP / REPLAY
# ==========================================================

async def handle_skip_replay(
    callback: CallbackQuery,
    _,
    chat_id: int,
    command: str,
    user_mention: str,
):

    playlist = db.get(
        chat_id
    )

    if not playlist:

        return await callback.answer(
            _["queue_2"],
            show_alert=True,
        )

    if command == "Skip":

        text_msg = (
            "➻ sᴛʀᴇᴀᴍ sᴋɪᴩᴩᴇᴅ 🎄\n"
            "│ \n"
            f"└ʙʏ : {user_mention} 🥀"
        )

        try:

            popped = playlist.pop(
                0
            )

            if popped:
                await auto_clean(
                    popped
                )

            # --------------------------------------------------
            # QUEUE EMPTY
            # --------------------------------------------------

            if not playlist:

                # IMPORTANT:
                # Do not kill autoplay here if autoplay is ON.
                # Call core skip handler first.
                try:

                    autoplay_enabled = (
                        await is_autoplay_on(
                            chat_id
                        )
                    )

                except Exception:

                    autoplay_enabled = False

                if autoplay_enabled:

                    await callback.answer()

                    try:
                        await _safe_edit_callback_message(
                            callback,
                            text_msg,
                            reply_markup=close_markup(_),
                        )
                    except Exception:
                        pass

                    # Let JARVIS/core autoplay logic continue.
                    try:
                        await JARVIS.skip_stream(
                            chat_id,
                            None,
                        )
                        return
                    except Exception:
                        # If the core does not accept None,
                        # stop only as final fallback.
                        pass

                await _safe_edit_callback_message(
                    callback,
                    text_msg,
                )

                await _safe_reply_callback_message(
                    callback,
                    _["admin_6"].format(
                        user_mention,
                        callback.message.chat.title,
                    ),
                    reply_markup=close_markup(_),
                )

                return await JARVIS.stop_stream(
                    chat_id
                )

        except Exception as e:

            print(
                f"Skip queue error: {e}"
            )

            try:

                await _safe_edit_callback_message(
                    callback,
                    text_msg,
                    reply_markup=close_markup(_),
                )

                await _safe_reply_callback_message(
                    callback,
                    _["admin_6"].format(
                        user_mention,
                        callback.message.chat.title,
                    ),
                    reply_markup=close_markup(_),
                )

                return await JARVIS.stop_stream(
                    chat_id
                )

            except Exception:
                return

    else:

        text_msg = (
            "➻ sᴛʀᴇᴀᴍ ʀᴇ-ᴘʟᴀʏᴇᴅ 🎄\n"
            "│ \n"
            f"└ʙʏ : {user_mention} 🥀"
        )

    await callback.answer()

    if not playlist:

        return await callback.answer(
            _["queue_2"],
            show_alert=True,
        )

    current_track = playlist[
        0
    ]

    queued = current_track[
        "file"
    ]

    title = current_track[
        "title"
    ].title()

    user = current_track[
        "by"
    ]

    requester_id = current_track.get(
        "user_id"
    )

    duration = current_track[
        "dur"
    ]

    streamtype = current_track[
        "streamtype"
    ]

    videoid = current_track[
        "vidid"
    ]

    status = (
        True
        if str(streamtype) == "video"
        else None
    )

    try:

        db[chat_id][0][
            "played"
        ] = 0

    except Exception:
        pass

    try:

        await delete_queue_message(
            chat_id,
            current_track,
        )

    except Exception:
        pass

    if current_track.get(
        "old_dur"
    ):

        try:

            db[chat_id][0][
                "dur"
            ] = current_track[
                "old_dur"
            ]

            db[chat_id][0][
                "seconds"
            ] = current_track[
                "old_second"
            ]

            db[chat_id][0][
                "speed_path"
            ] = None

            db[chat_id][0][
                "speed"
            ] = 1.0

        except Exception:
            pass

    # ======================================================
    # LIVE
    # ======================================================

    if "live_" in queued:

        n, new_link = await YouTube.video(
            videoid,
            True,
        )

        if n == 0:

            return await callback.message.reply_text(
                _["admin_7"].format(
                    title
                ),
                reply_markup=close_markup(_),
            )

        try:

            image = await YouTube.thumbnail(
                videoid,
                True,
            )

        except Exception:

            image = None

        try:

            await JARVIS.skip_stream(
                chat_id,
                new_link,
                video=status,
                image=image,
            )

        except Exception:

            return await callback.message.reply_text(
                _["call_6"]
            )

        buttons = stream_markup(
            _,
            chat_id,
        )

        schedule_stream_card(
            chat_id=chat_id,
            original_chat_id=callback.message.chat.id,
            videoid=videoid,
            user_id=requester_id,
            caption=_["stream_1"].format(
                (
                    f"https://t.me/"
                    f"{app.username}"
                    f"?start=info_{videoid}"
                ),
                title[:23],
                duration,
                user,
            ),
            button=buttons,
            markup="tg",
        )

        await _safe_edit_callback_message(
            callback,
            text_msg,
            reply_markup=close_markup(_),
        )

    # ======================================================
    # YOUTUBE VIDEO
    # ======================================================

    elif "vid_" in queued:

        mystic = await callback.message.reply_text(
            _["call_7"],
            disable_web_page_preview=True,
        )

        try:

            file_path, direct = (
                await YouTube.download(
                    videoid,
                    mystic,
                    videoid=True,
                    video=status,
                    stream=True,
                    title=title,
                )
            )

        except Exception:

            return await mystic.edit_text(
                _["call_6"]
            )

        try:

            image = await YouTube.thumbnail(
                videoid,
                True,
            )

        except Exception:

            image = None

        try:

            await JARVIS.skip_stream(
                chat_id,
                file_path,
                video=status,
                image=image,
            )

        except Exception:

            if direct:

                return await mystic.edit_text(
                    _["call_6"]
                )

            try:

                fallback_path, fallback_direct = (
                    await YouTube.download(
                        videoid,
                        mystic,
                        videoid=True,
                        video=status,
                        title=title,
                    )
                )

            except Exception:

                return await mystic.edit_text(
                    _["call_6"]
                )

            if not fallback_path:

                return await mystic.edit_text(
                    _["call_6"]
                )

            file_path = fallback_path
            direct = fallback_direct

            try:

                await JARVIS.skip_stream(
                    chat_id,
                    file_path,
                    video=status,
                    image=image,
                )

            except Exception:

                return await mystic.edit_text(
                    _["call_6"]
                )

        buttons = stream_markup(
            _,
            chat_id,
        )

        schedule_stream_card(
            chat_id=chat_id,
            original_chat_id=callback.message.chat.id,
            videoid=videoid,
            user_id=requester_id,
            caption=_["stream_1"].format(
                (
                    f"https://t.me/"
                    f"{app.username}"
                    f"?start=info_{videoid}"
                ),
                title[:23],
                duration,
                user,
            ),
            button=buttons,
            markup="stream",
        )

        await _safe_edit_callback_message(
            callback,
            text_msg,
            reply_markup=close_markup(_),
        )

        try:
            await mystic.delete()
        except Exception:
            pass

    # ======================================================
    # INDEX
    # ======================================================

    elif "index_" in queued:

        try:

            await JARVIS.skip_stream(
                chat_id,
                videoid,
                video=status,
            )

        except Exception:

            return await callback.message.reply_text(
                _["call_6"]
            )

        buttons = stream_markup(
            _,
            chat_id,
        )

        run = await callback.message.reply_photo(
            photo=STREAM_IMG_URL,
            caption=_["stream_2"].format(
                user
            ),
            reply_markup=InlineKeyboardMarkup(
                buttons
            ),
        )

        db[chat_id][0][
            "mystic"
        ] = run

        remember_player_message(
            chat_id,
            run,
        )

        db[chat_id][0][
            "markup"
        ] = "tg"

        await _safe_edit_callback_message(
            callback,
            text_msg,
            reply_markup=close_markup(_),
        )

    # ======================================================
    # NORMAL STREAM
    # ======================================================

    else:

        if videoid in [
            "telegram",
            "soundcloud",
        ]:

            image = None

        else:

            try:

                image = await YouTube.thumbnail(
                    videoid,
                    True,
                )

            except Exception:

                image = None

        try:

            await JARVIS.skip_stream(
                chat_id,
                queued,
                video=status,
                image=image,
            )

        except Exception:

            return await callback.message.reply_text(
                _["call_6"]
            )

        buttons = stream_markup(
            _,
            chat_id,
        )

        if videoid == "telegram":

            run = await callback.message.reply_photo(
                photo=(
                    TELEGRAM_AUDIO_URL
                    if str(streamtype) == "audio"
                    else TELEGRAM_VIDEO_URL
                ),
                caption=_["stream_1"].format(
                    SUPPORT_CHAT,
                    title[:23],
                    duration,
                    user,
                ),
                reply_markup=InlineKeyboardMarkup(
                    buttons
                ),
            )

            db[chat_id][0][
                "mystic"
            ] = run

            remember_player_message(
                chat_id,
                run,
            )

            db[chat_id][0][
                "markup"
            ] = "tg"

        elif videoid == "soundcloud":

            run = await callback.message.reply_photo(
                photo=(
                    SOUNCLOUD_IMG_URL
                    if str(streamtype) == "audio"
                    else TELEGRAM_VIDEO_URL
                ),
                caption=_["stream_1"].format(
                    SUPPORT_CHAT,
                    title[:23],
                    duration,
                    user,
                ),
                reply_markup=InlineKeyboardMarkup(
                    buttons
                ),
            )

            db[chat_id][0][
                "mystic"
            ] = run

            remember_player_message(
                chat_id,
                run,
            )

            db[chat_id][0][
                "markup"
            ] = "tg"

        else:

            schedule_stream_card(
                chat_id=chat_id,
                original_chat_id=callback.message.chat.id,
                videoid=videoid,
                user_id=requester_id,
                caption=_["stream_1"].format(
                    (
                        f"https://t.me/"
                        f"{app.username}"
                        f"?start=info_{videoid}"
                    ),
                    title[:23],
                    duration,
                    user,
                ),
                button=buttons,
                markup="stream",
            )

        await _safe_edit_callback_message(
            callback,
            text_msg,
            reply_markup=close_markup(_),
        )


# ==========================================================
# SEEK
# ==========================================================

async def handle_seek(
    callback: CallbackQuery,
    _,
    chat_id: int,
    command: str,
    user_mention: str,
):

    playing = db.get(
        chat_id
    )

    if not playing:

        return await callback.answer(
            _["queue_2"],
            show_alert=True,
        )

    try:

        duration_seconds = int(
            playing[0]["seconds"]
        )

    except Exception:

        return await callback.answer(
            _["admin_22"],
            show_alert=True,
        )

    if duration_seconds == 0:

        return await callback.answer(
            _["admin_22"],
            show_alert=True,
        )

    file_path = playing[0][
        "file"
    ]

    if (
        "index_" in file_path
        or "live_" in file_path
    ):

        return await callback.answer(
            _["admin_22"],
            show_alert=True,
        )

    try:

        duration_played = int(
            playing[0]["played"]
        )

    except Exception:

        duration_played = 0

    duration_to_skip = (
        10
        if int(command) in [1, 2]
        else 30
    )

    duration = playing[0][
        "dur"
    ]

    if int(command) in [
        1,
        3,
    ]:

        if (
            duration_played
            - duration_to_skip
        ) <= 10:

            bet = seconds_to_min(
                duration_played
            )

            return await callback.answer(
                (
                    "» ʙᴏᴛ ɪs ᴜɴᴀʙʟᴇ ᴛᴏ sᴇᴇᴋ.\n\n"
                    f"ᴄᴜʀʀᴇɴᴛʟʏ ᴩʟᴀʏᴇᴅ : "
                    f"{bet} ᴏᴜᴛ ᴏғ {duration}."
                ),
                show_alert=True,
            )

        to_seek = (
            duration_played
            - duration_to_skip
            + 1
        )

    else:

        if (
            duration_seconds
            - (
                duration_played
                + duration_to_skip
            )
        ) <= 10:

            bet = seconds_to_min(
                duration_played
            )

            return await callback.answer(
                (
                    "» ʙᴏᴛ ɪs ᴜɴᴀʙʟᴇ ᴛᴏ sᴇᴇᴋ.\n\n"
                    f"ᴄᴜʀʀᴇɴᴛʟʏ ᴩʟᴀʏᴇᴅ : "
                    f"{bet} ᴏᴜᴛ ᴏғ {duration}."
                ),
                show_alert=True,
            )

        to_seek = (
            duration_played
            + duration_to_skip
            + 1
        )

    await callback.answer()

    mystic = await callback.message.reply_text(
        _["admin_24"]
    )

    if "vid_" in file_path:

        n, file_path = await YouTube.video(
            playing[0]["vidid"],
            True,
        )

        if n == 0:

            return await mystic.edit_text(
                _["admin_22"]
            )

    try:

        await JARVIS.seek_stream(
            chat_id,
            file_path,
            seconds_to_min(
                to_seek
            ),
            duration,
            playing[0][
                "streamtype"
            ],
        )

    except Exception:

        return await mystic.edit_text(
            _["admin_26"]
        )

    if int(command) in [
        1,
        3,
    ]:

        db[chat_id][0][
            "played"
        ] -= duration_to_skip

    else:

        db[chat_id][0][
            "played"
        ] += duration_to_skip

    seek_message = _[
        "admin_25"
    ].format(
        seconds_to_min(
            to_seek
        )
    )

    await mystic.edit_text(
        (
            f"{seek_message}\n\n"
            f"ᴄʜᴀɴɢᴇs ᴅᴏɴᴇ ʙʏ : "
            f"{user_mention} !"
        )
    )


# ==========================================================
# PROGRESS TIMER
# ==========================================================

async def markup_timer():

    while True:

        await asyncio.sleep(
            6
        )

        active_chats = (
            await get_active_chats()
        )

        for chat_id in active_chats:

            try:

                if not await is_music_playing(
                    chat_id
                ):
                    continue

                playing = db.get(
                    chat_id
                )

                if not playing:
                    continue

                duration_seconds = int(
                    playing[0]["seconds"]
                )

                if duration_seconds == 0:
                    continue

                mystic = playing[0].get(
                    "mystic"
                )

                if not mystic:
                    continue

                if (
                    chat_id in checker
                    and mystic.id
                    in checker[chat_id]
                ):

                    if (
                        checker[chat_id][
                            mystic.id
                        ]
                        is False
                    ):
                        continue

                try:

                    language = await get_lang(
                        chat_id
                    )

                    _lang = get_string(
                        language
                    )

                except Exception:

                    _lang = get_string(
                        "en"
                    )

                try:

                    buttons = (
                        stream_markup_timer(
                            _lang,
                            chat_id,
                            seconds_to_min(
                                playing[0][
                                    "played"
                                ]
                            ),
                            playing[0][
                                "dur"
                            ],
                        )
                    )

                    if buttons:

                        await mystic.edit_reply_markup(
                            reply_markup=InlineKeyboardMarkup(
                                buttons
                            )
                        )

                except Exception:

                    continue

            except Exception:

                continue


# ==========================================================
# START TIMER
# ==========================================================

asyncio.create_task(
    markup_timer()
)


# ==========================================================
# CLOSE BUTTON
# ==========================================================

@app.on_callback_query(
    filters.regex("^close$")
    & ~BANNED_USERS
)
async def close_menu(
    _,
    query: CallbackQuery,
):

    try:

        await query.answer()

        await query.message.delete()

        msg = await query.message.reply_text(
            (
                "✅ ᴄʟᴏꜱᴇᴅ ʙʏ : "
                f"{query.from_user.mention}"
            )
        )

        await asyncio.sleep(
            2
        )

        await msg.delete()

    except Exception:
        pass


# ==========================================================
# STOP DOWNLOAD
# ==========================================================

@app.on_callback_query(
    filters.regex(
        "^stop_downloading$"
    )
    & ~BANNED_USERS
)
@ActualAdminCB
async def stop_download(
    _,
    query: CallbackQuery,
    _lang,
):

    task = lyrical.get(
        query.message.id
    )

    if not task:

        return await query.answer(
            _lang["tg_4"],
            show_alert=True,
        )

    if (
        task.done()
        or task.cancelled()
    ):

        return await query.answer(
            _lang["tg_5"],
            show_alert=True,
        )

    try:

        task.cancel()

        lyrical.pop(
            query.message.id,
            None,
        )

        await query.answer(
            _lang["tg_6"],
            show_alert=True,
        )

        return await query.edit_message_text(
            _lang["tg_7"].format(
                query.from_user.mention
            )
        )

    except Exception:

        return await query.answer(
            _lang["tg_8"],
            show_alert=True,
    )
