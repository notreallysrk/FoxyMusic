#
# Copyright (C) 2021-2022 by TheAloneteam@Github.
#
# This file is part of AloneMusic project.
# Released under GNU v3.0 License Agreement.
#

import math
import time
from typing import Union

from pyrogram.types import InlineKeyboardButton

from VIVAANXMUSIC import app
from VIVAANXMUSIC.utils.formatters import time_to_seconds


# ==========================================================
# PROGRESS UPDATE CACHE
# ==========================================================

LAST_UPDATE_TIME = {}


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
    buttons = [
        [
            InlineKeyboardButton(
                text="🎵",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|a|{channel}|{fplay}"
                ),
            ),
            InlineKeyboardButton(
                text="🎥",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|{user_id}|v|{channel}|{fplay}"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="⎘",
                callback_data=(
                    f"MusicThumb "
                    f"{videoid}|{user_id}|"
                    f"{channel}|{fplay}"
                ),
            ),
            InlineKeyboardButton(
                text="⌯✖",
                callback_data=(
                    f"forceclose {videoid}|{user_id}"
                ),
            ),
        ],
    ]

    return buttons


# ==========================================================
# PROGRESS CACHE CHECK
# ==========================================================

def should_update_progress(chat_id):
    """
    Prevents Telegram message from being edited too frequently.
    """

    now = time.time()
    last = LAST_UPDATE_TIME.get(chat_id, 0)

    if now - last >= 6:
        LAST_UPDATE_TIME[chat_id] = now
        return True

    return False


# ==========================================================
# RESET PROGRESS
# ==========================================================

def reset_progress(chat_id):
    LAST_UPDATE_TIME.pop(chat_id, None)


# ==========================================================
# PROGRESS BAR
# ==========================================================

def generate_progress_bar(
    played_sec,
    duration_sec,
):
    if not duration_sec or duration_sec <= 0:
        percentage = 0
    else:
        percentage = (
            played_sec / duration_sec
        ) * 100

        percentage = min(
            max(percentage, 0),
            100,
        )

    bar_length = 9

    filled = int(
        round(
            bar_length
            * percentage
            / 100
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
# MAIN PLAYER BUTTONS
# ==========================================================

def control_buttons(
    _,
    chat_id,
    autoplay: Union[bool, str] = False,
    thumb: Union[bool, str] = False,
    more: bool = False,
):

    # ======================================================
    # NORMAL PLAYER
    # ======================================================

    if not more:

        buttons = [
            [
                # RESUME
                InlineKeyboardButton(
                    text="▷",
                    callback_data=(
                        f"ADMIN Resume|{chat_id}"
                    ),
                ),

                # PAUSE
                InlineKeyboardButton(
                    text="II",
                    callback_data=(
                        f"ADMIN Pause|{chat_id}"
                    ),
                ),

                # SKIP
                InlineKeyboardButton(
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
                InlineKeyboardButton(
                    text="▢",
                    callback_data=(
                        f"ADMIN Stop|{chat_id}"
                    ),
                ),
            ],
            [
                # MORE
                InlineKeyboardButton(
                    text="☰",
                    callback_data=(
                        f"ADMIN More|{chat_id}"
                    ),
                ),

                # CLOSE
                InlineKeyboardButton(
                    text="🗑",
                    callback_data="close",
                ),
            ],
        ]

        return buttons

    # ======================================================
    # MORE MENU
    # FILTER REMOVED
    # ======================================================

    buttons = [
        [
            # AUTOPLAY
            InlineKeyboardButton(
                text="♫",
                callback_data=(
                    f"ADMIN Autoplay|{chat_id}"
                ),
            ),

            # THUMB
            InlineKeyboardButton(
                text="⎘",
                callback_data=(
                    f"ADMIN Thumb|{chat_id}"
                ),
            ),
        ],
        [
            # BACK
            InlineKeyboardButton(
                text="⟵",
                callback_data=(
                    f"ADMIN Back|{chat_id}"
                ),
            ),

            # CLOSE
            InlineKeyboardButton(
                text="🗑",
                callback_data="close",
            ),
        ],
    ]

    return buttons


# ==========================================================
# MORE MARKUP
# ==========================================================

def more_markup(
    _,
    chat_id,
    autoplay: Union[bool, str] = False,
    thumb: Union[bool, str] = False,
):
    return control_buttons(
        _,
        chat_id,
        autoplay=autoplay,
        thumb=thumb,
        more=True,
    )


# ==========================================================
# COMPACT MORE MARKUP
# ==========================================================

def more_markup_compact(
    _,
    chat_id,
    autoplay: Union[bool, str] = False,
    thumb: Union[bool, str] = False,
):
    return [
        [
            InlineKeyboardButton(
                text="🟢 AUTO",
                callback_data=(
                    f"ADMIN Autoplay|{chat_id}"
                ),
            ),
            InlineKeyboardButton(
                text="🖼️ THUMB",
                callback_data=(
                    f"ADMIN Thumb|{chat_id}"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 BACK",
                callback_data=(
                    f"ADMIN Back|{chat_id}"
                ),
            ),
        ],
    ]


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

    # ======================================================
    # UPDATE LIMIT
    # ======================================================

    if not should_update_progress(chat_id):
        return None

    # ======================================================
    # TIME
    # ======================================================

    played_sec = time_to_seconds(
        played
    )

    duration_sec = time_to_seconds(
        dur
    )

    # ======================================================
    # REMAINING TIME
    # ======================================================

    remaining_sec = (
        duration_sec - played_sec
    )

    if remaining_sec < 0:
        remaining_sec = 0

    rem_min = (
        remaining_sec // 60
    )

    rem_sec = (
        remaining_sec % 60
    )

    remaining = (
        f"{rem_min:02d}:"
        f"{rem_sec:02d}"
    )

    # ======================================================
    # PROGRESS BAR
    # ======================================================

    bar = generate_progress_bar(
        played_sec,
        duration_sec,
    )

    # ======================================================
    # TIMER BUTTON
    # ======================================================

    buttons = [
        [
            InlineKeyboardButton(
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

    # ======================================================
    # NORMAL MENU
    # ======================================================

    if not more:

        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="▷",
                        callback_data=(
                            f"ADMIN Resume|{chat_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        text="II",
                        callback_data=(
                            f"ADMIN Pause|{chat_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        text="‣‣I",
                        callback_data=(
                            f"ADMIN Skip|{chat_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        text="↻",
                        callback_data=(
                            f"ADMIN Replay|{chat_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        text="▢",
                        callback_data=(
                            f"ADMIN Stop|{chat_id}"
                        ),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="<-𝟤𝟢 s",
                        callback_data=(
                            "seek_backward_20"
                        ),
                    ),
                    InlineKeyboardButton(
                        text="☰",
                        callback_data=(
                            f"ADMIN More|{chat_id}"
                        ),
                    ),
                    InlineKeyboardButton(
                        text="𝟤𝟢s+ >",
                        callback_data=(
                            "seek_forward_20"
                        ),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🗑",
                        callback_data="close",
                    ),
                ],
            ]
        )

        return buttons

    # ======================================================
    # MORE MENU
    # FILTER REMOVED
    # ======================================================

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="♫",
                    callback_data=(
                        f"ADMIN Autoplay|{chat_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="⎘",
                    callback_data=(
                        f"ADMIN Thumb|{chat_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⟵",
                    callback_data=(
                        f"ADMIN Back|{chat_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data="close",
                ),
            ],
        ]
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

    # ======================================================
    # NORMAL PLAYER
    # ======================================================

    if not more:

        return [
            [
                InlineKeyboardButton(
                    text="▷",
                    callback_data=(
                        f"ADMIN Resume|{chat_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="II",
                    callback_data=(
                        f"ADMIN Pause|{chat_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="‣‣I",
                    callback_data=(
                        f"ADMIN Skip|{chat_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="↻",
                    callback_data=(
                        f"ADMIN Replay|{chat_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="▢",
                    callback_data=(
                        f"ADMIN Stop|{chat_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="☰",
                    callback_data=(
                        f"ADMIN More|{chat_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data="close",
                ),
            ],
        ]

    # ======================================================
    # MORE MENU
    # ======================================================

    return [
        [
            InlineKeyboardButton(
                text="♫",
                callback_data=(
                    f"ADMIN Autoplay|{chat_id}"
                ),
            ),
            InlineKeyboardButton(
                text="⎘",
                callback_data=(
                    f"ADMIN Thumb|{chat_id}"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                text="⟵",
                callback_data=(
                    f"ADMIN Back|{chat_id}"
                ),
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data="close",
            ),
        ],
    ]


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

    buttons = [
        [
            InlineKeyboardButton(
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
            InlineKeyboardButton(
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
            InlineKeyboardButton(
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
            InlineKeyboardButton(
                text="✖",
                callback_data=(
                    f"forceclose "
                    f"{videoid}|{user_id}"
                ),
            ),
        ],
    ]

    return buttons


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

    buttons = [
        [
            InlineKeyboardButton(
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
            InlineKeyboardButton(
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
            InlineKeyboardButton(
                text="✖",
                callback_data=(
                    f"forceclose "
                    f"{videoid}|{user_id}"
                ),
            ),
        ],
    ]

    return buttons


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

    buttons = [
        [
            InlineKeyboardButton(
                text="🎵",
                callback_data=(
                    f"MusicStream "
                    f"{videoid}|"
                    f"{user_id}|a|"
                    f"{channel}|"
                    f"{fplay}"
                ),
            ),
            InlineKeyboardButton(
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
            InlineKeyboardButton(
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
            InlineKeyboardButton(
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
            InlineKeyboardButton(
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
            InlineKeyboardButton(
                text="✖",
                callback_data=(
                    f"forceclose "
                    f"{query}|{user_id}"
                ),
            ),
        ],
    ]

    return buttons
