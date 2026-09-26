#
# Copyright (C) 2021-2022 by TheAloneteam@Github.
#
# This file is part of AloneMusic project.
# Released under GNU v3.0 License Agreement.
#

import time
import random
from typing import Union

from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton

from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.formatters import time_to_seconds


# ==========================================================
# RANDOM BUTTON STYLE
# ==========================================================
BUTTON_STYLES = [
    ButtonStyle.PRIMARY,
    ButtonStyle.SUCCESS,
    ButtonStyle.DANGER,
]


def random_button(text, callback_data=None, url=None):
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        url=url,
        style=random.choice(BUTTON_STYLES),
    )


# ==========================================================
# PROGRESS UPDATE CACHE
# ==========================================================

LAST_UPDATE_TIME = {}


def should_update_progress(chat_id):
    now = time.time()
    last = LAST_UPDATE_TIME.get(chat_id, 0)

    if now - last >= 6:
        LAST_UPDATE_TIME[chat_id] = now
        return True

    return False


def reset_progress(chat_id):
    LAST_UPDATE_TIME.pop(chat_id, None)


# ==========================================================
# PROGRESS BAR
# ==========================================================

def generate_progress_bar(played_sec, duration_sec):
    if not duration_sec or duration_sec <= 0:
        percentage = 0
    else:
        percentage = (played_sec / duration_sec) * 100
        percentage = min(max(percentage, 0), 100)

    bar_length = 9

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
        "—" * filled
        + "♬"
        + "—" * (bar_length - filled)
    )


# ==========================================================
# TRACK MARKUP
# ==========================================================

def track_markup(
    _,
    videoid,
    user_id,
    channel,
    fplay,
    thumb: Union[bool, str] = None,
):
    return [
        [
            random_button(
                text="🎵",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|a|{channel}|{fplay}"
                ),
            ),
            random_button(
                text="🎥",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|v|{channel}|{fplay}"
                ),
            ),
        ],
        [
            random_button(
                text="⎘",
                callback_data=(
                    f"MusicThumb "
                    f"{videoid}|{user_id}|"
                    f"{channel}|{fplay}"
                ),
            ),
            random_button(
                text="⌯✖",
                callback_data=(
                    f"forceclose {videoid}|{user_id}"
                ),
            ),
        ],
    ]


# ==========================================================
# PLAYER CONTROLS
# ==========================================================

def player_controls(_, chat_id):
    return [
        [
            random_button(
                text="▷",
                callback_data=(
                    f"ADMIN Resume|{chat_id}"
                ),
            ),
            random_button(
                text="II",
                callback_data=(
                    f"ADMIN Pause|{chat_id}"
                ),
            ),
            random_button(
                text="‣‣I",
                callback_data=(
                    f"ADMIN Skip|{chat_id}"
                ),
            ),
            random_button(
                text="↻",
                callback_data=(
                    f"ADMIN Replay|{chat_id}"
                ),
            ),
            random_button(
                text="▢",
                callback_data=(
                    f"ADMIN Stop|{chat_id}"
                ),
            ),
        ],
        [
            random_button(
                text="☰",
                callback_data=(
                    f"ADMIN More|{chat_id}"
                ),
            ),
            random_button(
                text="🗑",
                callback_data="close",
            ),
        ],
    ]


# ==========================================================
# MORE MENU
#
# EXACT LAYOUT:
#
#        ♫       ⎘
#
#       ⟵       🗑
#
# ==========================================================

def more_player_markup(_, chat_id):
    return [
        [
            random_button(
                text="♫",
                callback_data=(
                    f"ADMIN Autoplay|{chat_id}"
                ),
            ),
            random_button(
                text="⎘",
                callback_data=(
                    f"ADMIN Thumb|{chat_id}"
                ),
            ),
        ],
        [
            random_button(
                text="⟵",
                callback_data=(
                    f"ADMIN Back|{chat_id}"
                ),
            ),
            random_button(
                text="🗑",
                callback_data="close",
            ),
        ],
    ]


# ==========================================================
# CONTROL BUTTONS
# ==========================================================

def control_buttons(
    _,
    chat_id,
    autoplay: Union[bool, str] = False,
    thumb: Union[bool, str] = False,
    more: bool = False,
):
    if not more:
        return player_controls(_, chat_id)

    return more_player_markup(_, chat_id)


# ==========================================================
# MORE MARKUP
# ==========================================================

def more_markup(
    _,
    chat_id,
    autoplay: Union[bool, str] = False,
    thumb: Union[bool, str] = False,
):
    return more_player_markup(_, chat_id)


# ==========================================================
# COMPACT MORE MARKUP
# ==========================================================

def more_markup_compact(
    _,
    chat_id,
    autoplay: Union[bool, str] = False,
    thumb: Union[bool, str] = False,
):
    return more_player_markup(_, chat_id)


# ==========================================================
# STREAM TIMER MARKUP
# ==========================================================

def stream_markup_timer(
    _,
    chat_id,
    played,
    dur,
    autoplay: Union[bool, str] = False,
    thumb: Union[bool, str] = False,
    chat_filter: Union[bool, str] = None,
    more: bool = False,
):
    # ------------------------------------------------------
    # Progress update limit
    # ------------------------------------------------------

    if not should_update_progress(chat_id):
        return None

    # ------------------------------------------------------
    # Convert time
    # ------------------------------------------------------

    try:
        played_sec = time_to_seconds(played)
    except Exception:
        played_sec = 0

    try:
        duration_sec = time_to_seconds(dur)
    except Exception:
        duration_sec = 0

    # ------------------------------------------------------
    # Remaining time
    # ------------------------------------------------------

    remaining_sec = duration_sec - played_sec

    if remaining_sec < 0:
        remaining_sec = 0

    rem_min = remaining_sec // 60
    rem_sec = remaining_sec % 60

    remaining = (
        f"{rem_min:02d}:"
        f"{rem_sec:02d}"
    )

    # ------------------------------------------------------
    # Progress bar
    # ------------------------------------------------------

    bar = generate_progress_bar(
        played_sec,
        duration_sec,
    )

    # ------------------------------------------------------
    # Timer button
    # ------------------------------------------------------

    buttons = [
        [
            random_button(
                text=(
                    f"{played} "
                    f"{bar} "
                    f"{remaining}"
                ),
                url=(
                    f"https://t.me/"
                    f"{app.username}"
                    f"?startgroup=true"
                ),
            )
        ]
    ]

    # ------------------------------------------------------
    # Normal player
    # ------------------------------------------------------

    if not more:
        buttons.extend(
            player_controls(
                _,
                chat_id,
            )
        )

        return buttons

    # ------------------------------------------------------
    # More menu
    # ------------------------------------------------------

    buttons.extend(
        more_player_markup(
            _,
            chat_id,
        )
    )

    return buttons


# ==========================================================
# NORMAL STREAM MARKUP
# ==========================================================

def stream_markup(
    _,
    chat_id,
    autoplay: Union[bool, str] = False,
    thumb: Union[bool, str] = False,
    chat_filter: Union[bool, str] = None,
    more: bool = False,
):
    if not more:
        return player_controls(
            _,
            chat_id,
        )

    return more_player_markup(
        _,
        chat_id,
    )


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
    thumb: Union[bool, str] = None,
):
    return [
        [
            random_button(
                text="🎵",
                callback_data=(
                    f"AlonePlaylists "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{ptype}|a|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            random_button(
                text="🎥",
                callback_data=(
                    f"AlonePlaylists "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{ptype}|v|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
        ],
        [
            random_button(
                text="⎘",
                callback_data=(
                    f"PlaylistThumb "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{ptype}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            random_button(
                text="✖",
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
    thumb: Union[bool, str] = None,
):
    return [
        [
            random_button(
                text="🎬",
                callback_data=(
                    f"LiveStream "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{mode}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
        ],
        [
            random_button(
                text="⎘",
                callback_data=(
                    f"LiveThumb "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{mode}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            random_button(
                text="✖",
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
    thumb: Union[bool, str] = None,
):
    query = str(query)[:20]

    return [
        [
            random_button(
                text="🎵",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|"
                    f"{user_id}|a|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            random_button(
                text="🎥",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|"
                    f"{user_id}|v|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
        ],
        [
            random_button(
                text="◁",
                callback_data=(
                    f"slider B|"
                    f"{query_type}|"
                    f"{query}|"
                    f"{user_id}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            random_button(
                text="⎘",
                callback_data=(
                    f"SliderThumb "
                    f"{videoid}|"
                    f"{user_id}|"
                    f"{query}|"
                    f"{query_type}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            random_button(
                text="▷",
                callback_data=(
                    f"slider F|"
                    f"{query_type}|"
                    f"{query}|"
                    f"{user_id}|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
        ],
        [
            random_button(
                text="✖",
                callback_data=(
                    f"forceclose "
                    f"{query}|{user_id}"
                ),
            ),
        ],
    ]
