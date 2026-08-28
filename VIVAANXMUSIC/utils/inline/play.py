import time

from pyrogram.types import InlineKeyboardButton

from VIVAANXMUSIC.button_styles import (
    danger_button,
    primary_button,
    success_button,
)
from VIVAANXMUSIC.utils.formatters import time_to_seconds


# ==========================================================
# PROGRESS UPDATE CACHE
# ==========================================================

LAST_UPDATE_TIME = {}


# ==========================================================
# TRACK MARKUP
# ==========================================================

def track_markup(_, videoid, user_id, channel, fplay):
    return [
        [
            success_button(
                text=_["P_B_1"],
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|a|{channel}|{fplay}"
                ),
            ),
            primary_button(
                text=_["P_B_2"],
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|v|{channel}|{fplay}"
                ),
            ),
        ],
        [
            danger_button(
                text=_["CLOSE_BUTTON"],
                callback_data=(
                    f"forceclose {videoid}|{user_id}"
                ),
            ),
        ],
    ]


# ==========================================================
# CHECK PROGRESS UPDATE
# ==========================================================

def should_update_progress(chat_id):
    now = time.time()
    last = LAST_UPDATE_TIME.get(chat_id, 0)

    if now - last >= 6:
        LAST_UPDATE_TIME[chat_id] = now
        return True

    return False


# ==========================================================
# PROGRESS BAR
# ==========================================================

def generate_progress_bar(played_sec, duration_sec):
    if not duration_sec or duration_sec <= 0:
        percentage = 0
    else:
        percentage = min(
            max(
                (played_sec / duration_sec) * 100,
                0,
            ),
            100,
        )

    bar_length = 8

    filled = int(
        round(
            bar_length * percentage / 100
        )
    )

    filled = max(
        0,
        min(
            filled,
            bar_length,
        ),
    )

    return (
        "▰" * filled
        + "▱" * (bar_length - filled)
    )


# ==========================================================
# MAIN PLAYER BUTTONS
# ==========================================================

def control_buttons(_, chat_id):
    return [
        [
            # PLAY
            success_button(
                text="▷",
                callback_data=(
                    f"ADMIN Resume|{chat_id}"
                ),
            ),

            # PAUSE
            primary_button(
                text="Ⅱ",
                callback_data=(
                    f"ADMIN Pause|{chat_id}"
                ),
            ),

            # SKIP
            primary_button(
                text="‣‣I",
                callback_data=(
                    f"ADMIN Skip|{chat_id}"
                ),
            ),

            # REPLAY
            InlineKeyboardButton(
                text="↻",
                callback_data=(
                    f"ADMIN Replay|{chat_id}"
                ),
            ),

            # STOP
            danger_button(
                text="▢",
                callback_data=(
                    f"ADMIN Stop|{chat_id}"
                ),
            ),
        ],
        [
            # MORE
            primary_button(
                text="☰ MORE",
                callback_data=(
                    f"ADMIN More|{chat_id}"
                ),
            ),

            # DELETE
            danger_button(
                text="🗑️",
                callback_data="close",
            ),
        ],
    ]


# ==========================================================
# MORE MENU
# ==========================================================

def more_markup(_, chat_id):
    return [
        [
            success_button(
                text="🔵 AUTO PLAY ON",
                callback_data=(
                    f"autoplay_on_{chat_id}"
                ),
            ),
            danger_button(
                text="🔴 AUTO PLAY OFF",
                callback_data=(
                    f"autoplay_off_{chat_id}"
                ),
            ),
        ],
        [
            primary_button(
                text="🔙 BACK",
                callback_data=(
                    f"player_back_{chat_id}"
                ),
            ),
        ],
    ]


# ==========================================================
# MORE MENU - COMPACT VERSION
# ==========================================================

def more_markup_compact(_, chat_id):
    return [
        [
            success_button(
                text="▶️ AUTO PLAY ON",
                callback_data=(
                    f"autoplay_on_{chat_id}"
                ),
            ),
        ],
        [
            danger_button(
                text="⛔ AUTO PLAY OFF",
                callback_data=(
                    f"autoplay_off_{chat_id}"
                ),
            ),
        ],
        [
            primary_button(
                text="🔙 BACK",
                callback_data=(
                    f"player_back_{chat_id}"
                ),
            ),
        ],
    ]


# ==========================================================
# STREAM TIMER MARKUP
# ==========================================================

def stream_markup_timer(_, chat_id, played, dur):
    if not should_update_progress(chat_id):
        return None

    played_sec = time_to_seconds(played)
    duration_sec = time_to_seconds(dur)

    bar = generate_progress_bar(
        played_sec,
        duration_sec,
    )

    return [
        [
            InlineKeyboardButton(
                text=f"{played} {bar} {dur}",
                callback_data="GetTimer",
            )
        ]
    ] + control_buttons(_, chat_id)


# ==========================================================
# NORMAL STREAM MARKUP
# ==========================================================

def stream_markup(_, chat_id):
    return control_buttons(_, chat_id)


# ==========================================================
# PLAYLIST MARKUP
# ==========================================================

def playlist_markup(
    _,
    videoid,
    user_id,
    ptype,
    channel,
    fplay,
):
    return [
        [
            success_button(
                text=_["P_B_1"],
                callback_data=(
                    f"VivaanPlaylists "
                    f"{videoid}|{user_id}|"
                    f"{ptype}|a|{channel}|{fplay}"
                ),
            ),
            primary_button(
                text=_["P_B_2"],
                callback_data=(
                    f"VivaanPlaylists "
                    f"{videoid}|{user_id}|"
                    f"{ptype}|v|{channel}|{fplay}"
                ),
            ),
        ],
        [
            danger_button(
                text=_["CLOSE_BUTTON"],
                callback_data=(
                    f"forceclose "
                    f"{videoid}|{user_id}"
                ),
            ),
        ],
    ]


# ==========================================================
# LIVESTREAM MARKUP
# ==========================================================

def livestream_markup(
    _,
    videoid,
    user_id,
    mode,
    channel,
    fplay,
):
    return [
        [
            success_button(
                text=_["P_B_3"],
                callback_data=(
                    f"LiveStream "
                    f"{videoid}|{user_id}|"
                    f"{mode}|{channel}|{fplay}"
                ),
            ),
        ],
        [
            danger_button(
                text=_["CLOSE_BUTTON"],
                callback_data=(
                    f"forceclose "
                    f"{videoid}|{user_id}"
                ),
            ),
        ],
    ]


# ==========================================================
# SLIDER MARKUP
# ==========================================================

def slider_markup(
    _,
    videoid,
    user_id,
    query,
    query_type,
    channel,
    fplay,
):
    short_query = query[:20]

    return [
        [
            success_button(
                text=_["P_B_1"],
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|a|"
                    f"{channel}|{fplay}"
                ),
            ),
            primary_button(
                text=_["P_B_2"],
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|v|"
                    f"{channel}|{fplay}"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="◁",
                callback_data=(
                    f"slider B|"
                    f"{query_type}|"
                    f"{short_query}|"
                    f"{user_id}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            danger_button(
                text=_["CLOSE_BUTTON"],
                callback_data=(
                    f"forceclose "
                    f"{short_query}|{user_id}"
                ),
            ),
            primary_button(
                text="▷",
                callback_data=(
                    f"slider F|"
                    f"{query_type}|"
                    f"{short_query}|"
                    f"{user_id}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
        ],
    ]


# ==========================================================
# RESET PROGRESS CACHE
# ==========================================================

def reset_progress(chat_id):
    LAST_UPDATE_TIME.pop(chat_id, None)
