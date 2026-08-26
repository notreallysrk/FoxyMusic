from pyrogram.types import InlineKeyboardMarkup

from VIVAANXMUSIC import app
from VIVAANXMUSIC.button_styles import (
    danger_button,
    primary_button,
    success_button,
)
from VIVAANXMUSIC.utils.database import get_autoplay


TOTAL_SECTIONS = 33

BUTTON_LABEL_OVERRIDES = {
    25: "Dᴏᴡɴʟᴏᴀᴅ",
}


async def generate_help_buttons(
    _,
    start: int,
    end: int,
    current_page: int,
    chat_id: int | None = None,
):
    buttons = []
    per_row = 3

    for idx, section in enumerate(range(start, end + 1)):
        if idx % per_row == 0:
            buttons.append([])

        # SECTION 21: REPO INFO -> ACTUAL AUTOPLAY BUTTON
        if section == 21:
            autoplay_enabled = False

            if chat_id is not None:
                try:
                    autoplay_enabled = bool(
                        await get_autoplay(chat_id)
                    )
                except Exception as error:
                    print(
                        f"HELP AUTOPLAY STATUS ERROR: {error}"
                    )

            status = "🟢 ON" if autoplay_enabled else "🔴 OFF"

            button = success_button(
                text=f"Aᴜᴛᴏᴘʟᴀʏ {status}",
                callback_data="toggle_autoplay",
            )

        else:
            text = BUTTON_LABEL_OVERRIDES.get(
                section,
                _[f"H_B_{section}"],
            )

            callback_data = (
                f"help_callback hb{section}_p{current_page}"
            )

            style_position = idx % 3

            if style_position == 0:
                button = primary_button(
                    text=text,
                    callback_data=callback_data,
                )

            elif style_position == 1:
                button = success_button(
                    text=text,
                    callback_data=callback_data,
                )

            else:
                button = danger_button(
                    text=text,
                    callback_data=callback_data,
                )

        buttons[-1].append(button)

    return buttons


async def first_page(
    _,
    chat_id: int | None = None,
):
    buttons = await generate_help_buttons(
        _,
        1,
        15,
        current_page=1,
        chat_id=chat_id,
    )

    buttons.append(
        [
            primary_button(
                text="๏ ᴍᴇɴᴜ ๏",
                callback_data="back_to_main",
            ),
            success_button(
                text="๏ ɴᴇxᴛ ๏",
                callback_data="help_next_2",
            ),
        ]
    )

    return InlineKeyboardMarkup(buttons)


async def second_page(
    _,
    chat_id: int | None = None,
):
    buttons = await generate_help_buttons(
        _,
        16,
        TOTAL_SECTIONS,
        current_page=2,
        chat_id=chat_id,
    )

    buttons.append(
        [
            primary_button(
                text="๏ ʙᴀᴄᴋ ๏",
                callback_data="help_prev_1",
            ),
            primary_button(
                text="๏ ᴍᴇɴᴜ ๏",
                callback_data="back_to_main",
            ),
        ]
    )

    return InlineKeyboardMarkup(buttons)


def action_sub_menu(_, current_page: int):
    return InlineKeyboardMarkup(
        [
            [
                primary_button(
                    text=_["H_B_S_1"],
                    callback_data="action_prom_1",
                ),
                primary_button(
                    text=_["H_B_S_2"],
                    callback_data="action_pun_1",
                ),
            ],
            [
                primary_button(
                    text=_["BACK_BUTTON"],
                    callback_data=f"help_back_{current_page}",
                )
            ],
        ]
    )


def help_back_markup(_, current_page: int):
    return InlineKeyboardMarkup(
        [
            [
                primary_button(
                    text=_["BACK_BUTTON"],
                    callback_data=f"help_back_{current_page}",
                ),
                danger_button(
                    text=_["CLOSE_BUTTON"],
                    callback_data="close",
                ),
            ]
        ]
    )


def private_help_panel(_):
    return [
        [
            primary_button(
                text=_["S_B_3"],
                url=f"https://t.me/{app.username}?start=help",
            )
        ]
    ]
