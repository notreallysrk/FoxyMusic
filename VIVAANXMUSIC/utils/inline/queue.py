from typing import Union
import random

from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from VIVAANXMUSIC.button_styles import (
    danger_button,
    primary_button,
    success_button,
)


# ==========================================================
# RANDOM BUTTON STYLE
# Blue / Green / Red
# ==========================================================

BUTTON_STYLES = [
    ButtonStyle.PRIMARY,
    ButtonStyle.SUCCESS,
    ButtonStyle.DANGER,
]


def random_button(
    text,
    callback_data=None,
    url=None,
):
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        url=url,
        style=random.choice(BUTTON_STYLES),
    )


# ==========================================================
# QUEUE MARKUP
# ==========================================================

def queue_markup(
    _,
    DURATION,
    CPLAY,
    videoid,
    played: Union[bool, int] = None,
    dur: Union[bool, int] = None,
):
    not_dur = [
        [
            random_button(
                text=_["QU_B_1"],
                callback_data=f"GetQueued {CPLAY}|{videoid}",
            ),
            random_button(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
            ),
        ]
    ]

    dur = [
        [
            random_button(
                text=_["QU_B_2"].format(played, dur),
                callback_data="GetTimer",
            )
        ],
        [
            random_button(
                text=_["QU_B_1"],
                callback_data=f"GetQueued {CPLAY}|{videoid}",
            ),
            random_button(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
            ),
        ],
    ]

    upl = InlineKeyboardMarkup(
        not_dur if DURATION == "Unknown" else dur
    )

    return upl


# ==========================================================
# QUEUE BACK
# ==========================================================

def queue_back_markup(_, CPLAY):
    upl = InlineKeyboardMarkup(
        [
            [
                random_button(
                    text=_["BACK_BUTTON"],
                    callback_data=f"queue_back_timer {CPLAY}",
                ),
                random_button(
                    text=_["CLOSE_BUTTON"],
                    callback_data="close",
                ),
            ]
        ]
    )

    return upl


# ==========================================================
# ADMIN QUEUE CONTROLS
# ==========================================================

def aq_markup(_, chat_id):
    buttons = [
        [
            random_button(
                text="▷",
                callback_data=f"ADMIN Resume|{chat_id}",
            ),
            random_button(
                text="II",
                callback_data=f"ADMIN Pause|{chat_id}",
            ),
            random_button(
                text="‣‣I",
                callback_data=f"ADMIN Skip|{chat_id}",
            ),
            random_button(
                text="▢",
                callback_data=f"ADMIN Stop|{chat_id}",
            ),
        ],
        [
            random_button(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
            )
        ],
    ]

    return buttons
