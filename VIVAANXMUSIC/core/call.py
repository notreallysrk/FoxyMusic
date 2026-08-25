# -----------------------------------------------
# 🔸 StrangerMusic Project
# 🔹 Developed & Maintained by: Shashank Shukla
# -----------------------------------------------

import asyncio
import os
from datetime import datetime, timedelta
from typing import Union

from ntgcalls import ConnectionNotFound, TelegramServerError
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

import config
from VIVAANXMUSIC import LOGGER, YouTube, app
from VIVAANXMUSIC.misc import db
from VIVAANXMUSIC.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    is_autoplay_on,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from VIVAANXMUSIC.utils.exceptions import AssistantErr
from VIVAANXMUSIC.utils.formatters import (
    check_duration,
    seconds_to_min,
    speed_converter,
)
from VIVAANXMUSIC.utils.inline.play import stream_markup
from VIVAANXMUSIC.utils.stream.autoclear import auto_clean
from VIVAANXMUSIC.utils.stream.queue import put_queue
from VIVAANXMUSIC.utils.thumbnails import get_thumb as gen_thumb
from strings import get_string


autoend = {}
counter = {}

# =================================================
# AUTOPLAY HISTORY
# =================================================

autoplay_history = {}


def remember_played(chat_id: int, video_id: str):
    if not chat_id or not video_id:
        return

    video_id = str(video_id)
    history = autoplay_history.setdefault(chat_id, [])

    if video_id in history:
        history.remove(video_id)

    history.append(video_id)

    if len(history) > 50:
        autoplay_history[chat_id] = history[-50:]


async def fetch_autoplay_track(
    chat_id: int,
    seed_title: str,
    seed_vidid: str = None,
):
    """
    Current song ke related videos me se
    next unplayed track return karta hai.
    """

    if not seed_title:
        return None

    try:
        related = None

        # -------------------------------------------------
        # 1. RELATED VIDEO METHOD
        # -------------------------------------------------
        if seed_vidid:
            for method_name in (
                "get_related_videos",
                "related_videos",
                "related",
            ):
                method = getattr(YouTube, method_name, None)

                if not method:
                    continue

                try:
                    related = await method(seed_vidid)

                    if related:
                        break

                except Exception:
                    continue

        # -------------------------------------------------
        # 2. TITLE SEARCH FALLBACK
        # -------------------------------------------------
        if not related:

            for method_name in (
                "search",
                "details",
                "playlist",
            ):
                method = getattr(YouTube, method_name, None)

                if not method:
                    continue

                try:
                    related = await method(seed_title)

                    if related:
                        break

                except Exception:
                    continue

        if not related:
            return None

        # -------------------------------------------------
        # NORMALIZE RESULT
        # -------------------------------------------------
        if isinstance(related, dict):

            for key in (
                "results",
                "videos",
                "items",
                "data",
                "result",
            ):
                if related.get(key):
                    related = related[key]
                    break

        if not isinstance(related, list):
            return None

        history = autoplay_history.get(chat_id, [])

        candidates = []

        # -------------------------------------------------
        # FIND NEW TRACK
        # -------------------------------------------------
        for item in related:

            if not isinstance(item, dict):
                continue

            video_id = (
                item.get("vidid")
                or item.get("video_id")
                or item.get("videoId")
                or item.get("id")
            )

            if not video_id:
                continue

            video_id = str(video_id)

            # Same current song skip
            if seed_vidid and video_id == str(seed_vidid):
                continue

            # Recent songs skip
            if video_id in history:
                continue

            title = (
                item.get("title")
                or item.get("name")
                or item.get("video_title")
            )

            if not title:
                continue

            duration = (
                item.get("duration_min")
                or item.get("duration")
                or item.get("duration_string")
                or item.get("length")
                or "0:00"
            )

            candidates.append(
                {
                    "vidid": video_id,
                    "title": str(title),
                    "duration_min": str(duration),
                }
            )

        # -------------------------------------------------
        # RESET HISTORY IF ALL SONGS PLAYED
        # -------------------------------------------------
        if not candidates:

            autoplay_history[chat_id] = []

            for item in related:

                if not isinstance(item, dict):
                    continue

                video_id = (
                    item.get("vidid")
                    or item.get("video_id")
                    or item.get("videoId")
                    or item.get("id")
                )

                if not video_id:
                    continue

                video_id = str(video_id)

                if seed_vidid and video_id == str(seed_vidid):
                    continue

                title = (
                    item.get("title")
                    or item.get("name")
                    or item.get("video_title")
                )

                if not title:
                    continue

                duration = (
                    item.get("duration_min")
                    or item.get("duration")
                    or item.get("duration_string")
                    or "0:00"
                )

                candidates.append(
                    {
                        "vidid": video_id,
                        "title": str(title),
                        "duration_min": str(duration),
                    }
                )

        if not candidates:
            return None

        track = candidates[0]

        remember_played(
            chat_id,
            track["vidid"],
        )

        return track

    except Exception as e:

        LOGGER(__name__).error(
            f"Autoplay error: {e}"
        )

        return None


# =================================================
# CLEAR STREAM
# =================================================

async def _clear_(chat_id: int):

    db[chat_id] = []

    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


# =================================================
# CALL CLASS
# =================================================

class Call(PyTgCalls):

    def __init__(self):

        PyTgCallsSession.notice_displayed = True

        self.userbot1 = Client(
            name="ShiviAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )

        self.one = PyTgCalls(
            self.userbot1,
            cache_duration=100,
        )

        self.userbot2 = Client(
            name="ShiviAss2",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING2),
        )

        self.two = PyTgCalls(
            self.userbot2,
            cache_duration=100,
        )

        self.userbot3 = Client(
            name="ShiviAss3",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING3),
        )

        self.three = PyTgCalls(
            self.userbot3,
            cache_duration=100,
        )

        self.userbot4 = Client(
            name="ShiviAss4",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING4),
        )

        self.four = PyTgCalls(
            self.userbot4,
            cache_duration=100,
        )

        self.userbot5 = Client(
            name="ShiviAss5",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING5),
        )

        self.five = PyTgCalls(
            self.userbot5,
            cache_duration=100,
        )


    # =================================================
    # BUILD STREAM
    # =================================================

    def _build_stream(
        self,
        source: str,
        video: bool,
        ffmpeg: str | None = None,
    ) -> types.MediaStream:

        return types.MediaStream(
            media_path=source,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT
                if video
                else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=ffmpeg,
        )


    async def _play_on_assistant(
        self,
        client: PyTgCalls,
        chat_id: int,
        stream: types.MediaStream,
    ):

        await client.play(
            chat_id=chat_id,
            stream=stream,
            config=types.GroupCallConfig(
                auto_start=False
            ),
        )


    # =================================================
    # PAUSE / RESUME
    # =================================================

    async def pause_stream(
        self,
        chat_id: int,
    ):

        assistant = await group_assistant(
            self,
            chat_id,
        )

        await assistant.pause(chat_id)


    async def resume_stream(
        self,
        chat_id: int,
    ):

        assistant = await group_assistant(
            self,
            chat_id,
        )

        await assistant.resume(chat_id)


    # =================================================
    # STOP
    # =================================================

    async def stop_stream(
        self,
        chat_id: int,
    ):

        assistant = await group_assistant(
            self,
            chat_id,
        )

        try:

            await _clear_(chat_id)

            await assistant.leave_call(
                chat_id,
                close=False,
            )

        except Exception:
            pass


    async def stop_stream_force(
        self,
        chat_id: int,
    ):

        clients = [
            (config.STRING1, self.one),
            (config.STRING2, self.two),
            (config.STRING3, self.three),
            (config.STRING4, self.four),
            (config.STRING5, self.five),
        ]

        for string, client in clients:

            if not string:
                continue

            try:

                await client.leave_call(
                    chat_id,
                    close=False,
                )

            except Exception:
                pass

        try:
            await _clear_(chat_id)
        except Exception:
            pass


    async def force_stop_stream(
        self,
        chat_id: int,
    ):

        assistant = await group_assistant(
            self,
            chat_id,
        )

        try:

            if db.get(chat_id):
                db[chat_id].pop(0)

        except Exception:
            pass

        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)

        try:

            await assistant.leave_call(
                chat_id,
                close=False,
            )

        except Exception:
            pass


    # =================================================
    # SKIP STREAM
    # =================================================

    async def skip_stream(
        self,
        chat_id: int,
        link: str,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ):

        assistant = await group_assistant(
            self,
            chat_id,
        )

        stream = self._build_stream(
            link,
            video=bool(video),
        )

        await self._play_on_assistant(
            assistant,
            chat_id,
            stream,
        )


    # =================================================
    # SEEK
    # =================================================

    async def seek_stream(
        self,
        chat_id,
        file_path,
        to_seek,
        duration,
        mode,
    ):

        assistant = await group_assistant(
            self,
            chat_id,
        )

        ffmpeg = (
            f"-ss {to_seek} "
            f"-to {duration}"
        )

        stream = self._build_stream(
            file_path,
            video=(mode == "video"),
            ffmpeg=ffmpeg,
        )

        await self._play_on_assistant(
            assistant,
            chat_id,
            stream,
        )


    # =================================================
    # AUTOPLAY
    # =================================================

    async def autoplay_start(
        self,
        chat_id: int,
        original_chat_id: int,
        seed_title: str,
        seed_vidid: str = None,
        client: PyTgCalls = None,
    ) -> bool:

        if seed_vidid:
            remember_played(
                chat_id,
                seed_vidid,
            )

        status_msg = None

        try:

            status_msg = await app.send_message(
                original_chat_id,
                "ʜσʟᴅ ση...\n\n"
                "ᴅσᴡηʟσᴧᴅɪηɢ ηєxᴛ ϻєᴅɪᴧ "
                "ғʀσϻ ᴛʜє ǫυєυє.",
            )

        except Exception:
            pass

        async def _fail():

            if status_msg:

                try:
                    await status_msg.delete()
                except Exception:
                    pass

            return False

        track = await fetch_autoplay_track(
            chat_id,
            seed_title,
            seed_vidid,
        )

        if not track:
            return await _fail()

        try:

            file_path, direct = await YouTube.download(
                track["vidid"],
                None,
                videoid=True,
            )

        except Exception as e:

            LOGGER(__name__).error(
                f"Autoplay download error: {e}"
            )

            return await _fail()

        if not file_path:
            return await _fail()

        remember_played(
            chat_id,
            track["vidid"],
        )

        language = await get_lang(chat_id)

        _ = get_string(language)

        title = track.get(
            "title",
            "Unknown Track",
        ).title()

        duration_min = track.get(
            "duration_min",
            "0:00",
        )

        await put_queue(
            chat_id,
            original_chat_id,
            file_path if direct else f"vid_{track['vidid']}",
            title,
            duration_min,
            "🔁 𝐀ᴜᴛᴏᴘʟᴀʏ",
            track["vidid"],
            1,
            "audio",
            forceplay=True,
        )

        if db.get(chat_id):

            db[chat_id][0]["played"] = 0
            db[chat_id][0]["seconds"] = 0
            db[chat_id][0]["speed"] = 1.0
            db[chat_id][0]["speed_path"] = None
            db[chat_id][0]["old_dur"] = None
            db[chat_id][0]["old_second"] = 0

        stream = self._build_stream(
            file_path,
            video=False,
        )

        assistant = (
            client
            or await group_assistant(
                self,
                chat_id,
            )
        )

        try:

            await self._play_on_assistant(
                assistant,
                chat_id,
                stream,
            )

        except Exception:

            return await _fail()

        try:

            img = await gen_thumb(
                track["vidid"]
            )

            button = stream_markup(
                _,
                chat_id,
            )

            run = await app.send_photo(
                chat_id=original_chat_id,
                photo=img,
                caption=_["stream_1"].format(
                    f"https://t.me/{app.username}"
                    f"?start=info_{track['vidid']}",
                    title[:23],
                    duration_min,
                    "𝐀ᴜᴛᴏᴘʟᴀʏ 🚩",
                    "🎵 Aᴜᴅɪᴏ",
                ),
                reply_markup=InlineKeyboardMarkup(
                    button
                ),
            )

            if db.get(chat_id):

                db[chat_id][0]["mystic"] = run

                db[chat_id][0]["markup"] = (
                    "stream"
                )

        except Exception:
            pass

        if status_msg:

            try:
                await status_msg.delete()
            except Exception:
                pass

        try:

            await add_active_chat(chat_id)

            await music_on(chat_id)

        except Exception:
            pass

        return True


    # =================================================
    # JOIN CALL
    # =================================================

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ):

        assistant = await group_assistant(
            self,
            chat_id,
        )

        language = await get_lang(chat_id)

        _ = get_string(language)

        stream = self._build_stream(
            link,
            video=bool(video),
        )

        try:

            await self._play_on_assistant(
                assistant,
                chat_id,
                stream,
            )

        except exceptions.NoActiveGroupCall:
            raise AssistantErr(_["call_8"])

        except exceptions.NoAudioSourceFound:
            raise AssistantErr(_["call_10"])

        except (
            ConnectionNotFound,
            TelegramServerError,
        ):
            raise AssistantErr(_["call_10"])

        except Exception:
            raise AssistantErr(_["call_10"])

        await add_active_chat(chat_id)

        await music_on(chat_id)

        if video:
            await add_active_video_chat(chat_id)


    # =================================================
    # CHANGE STREAM
    # =================================================

    async def change_stream(
        self,
        client: PyTgCalls,
        chat_id: int,
    ):

        check = db.get(chat_id)

        if not check:
            return

        popped = None

        try:

            loop = await get_loop(chat_id)

            if loop == 0:

                popped = check.pop(0)

            else:

                await set_loop(
                    chat_id,
                    loop - 1,
                )

                return

            if popped:

                old_mystic = popped.get("mystic")

                if old_mystic:

                    try:
                        await old_mystic.delete()
                    except Exception:
                        pass

                try:
                    await auto_clean(popped)
                except Exception:
                    pass

            # =====================================
            # QUEUE EMPTY → AUTOPLAY
            # =====================================

            if not check:

                if (
                    popped
                    and await is_autoplay_on(chat_id)
                ):

                    started = await self.autoplay_start(
                        chat_id,
                        popped.get(
                            "chat_id",
                            chat_id,
                        ),
                        popped.get(
                            "title",
                            "",
                        ),
                        popped.get(
                            "vidid",
                        ),
                        client,
                    )

                    if started:
                        return

                await _clear_(chat_id)

                return await client.leave_call(
                    chat_id,
                    close=False,
                )

        except Exception as e:

            LOGGER(__name__).error(
                f"Change stream error: {e}"
            )

            await _clear_(chat_id)

            try:

                return await client.leave_call(
                    chat_id,
                    close=False,
                )

            except Exception:
                return

        # =====================================
        # NEXT QUEUE SONG
        # =====================================

        queued = check[0]["file"]

        language = await get_lang(chat_id)

        _ = get_string(language)

        title = (
            check[0]["title"]
        ).title()

        user = check[0]["by"]

        original_chat_id = check[0]["chat_id"]

        streamtype = check[0]["streamtype"]

        stype = (
            streamtype.title()
            if streamtype
            else "Audio"
        )

        videoid = check[0]["vidid"]

        db[chat_id][0]["played"] = 0

        video = (
            str(streamtype) == "video"
        )

        # =====================================
        # DOWNLOAD YOUTUBE SONG
        # =====================================

        if "vid_" in queued:

            mystic = await app.send_message(
                original_chat_id,
                _["call_7"],
            )

            try:

                file_path, direct = (
                    await YouTube.download(
                        videoid,
                        mystic,
                        videoid=True,
                        video=video,
                    )
                )

            except Exception:

                try:
                    await mystic.edit_text(
                        _["call_6"]
                    )
                except Exception:
                    pass

                return

            if not file_path:

                return

            stream = self._build_stream(
                file_path,
                video=video,
            )

            try:

                await self._play_on_assistant(
                    client,
                    chat_id,
                    stream,
                )

            except Exception:

                return

            try:

                img = await gen_thumb(videoid)

                button = stream_markup(
                    _,
                    chat_id,
                )

                await mystic.delete()

                run = await app.send_photo(
                    chat_id=original_chat_id,
                    photo=img,
                    caption=_["stream_1"].format(
                        f"https://t.me/{app.username}"
                        f"?start=info_{videoid}",
                        title[:23],
                        check[0]["dur"],
                        user,
                        stype,
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        button
                    ),
                )

                db[chat_id][0]["mystic"] = run

                db[chat_id][0]["markup"] = (
                    "stream"
                )

            except Exception:
                pass

            return

        # =====================================
        # LOCAL / TELEGRAM FILE
        # =====================================

        stream = self._build_stream(
            queued,
            video=video,
        )

        try:

            await self._play_on_assistant(
                client,
                chat_id,
                stream,
            )

        except Exception:

            return await app.send_message(
                original_chat_id,
                _["call_6"],
            )


    # =================================================
    # START
    # =================================================

    async def start(self):

        LOGGER(__name__).info(
            "Starting PyTgCalls Client..."
        )

        if config.STRING1:
            await self.one.start()

        if config.STRING2:
            await self.two.start()

        if config.STRING3:
            await self.three.start()

        if config.STRING4:
            await self.four.start()

        if config.STRING5:
            await self.five.start()


    # =================================================
    # DECORATORS
    # =================================================

    async def decorators(self):

        clients = [
            (config.STRING1, self.one),
            (config.STRING2, self.two),
            (config.STRING3, self.three),
            (config.STRING4, self.four),
            (config.STRING5, self.five),
        ]

        for string, client in clients:

            if not string:
                continue

            @client.on_update()
            async def _update_handler(
                _,
                update: types.Update,
                _client=client,
            ):

                if isinstance(
                    update,
                    types.StreamEnded,
                ):

                    if (
                        update.stream_type
                        == types.StreamEnded.Type.AUDIO
                    ):

                        await self.change_stream(
                            _client,
                            update.chat_id,
                        )

                elif isinstance(
                    update,
                    types.ChatUpdate,
                ):

                    if update.status in [

                        types.ChatUpdate.Status.KICKED,

                        types.ChatUpdate.Status.LEFT_GROUP,

                        types.ChatUpdate.Status.CLOSED_VOICE_CHAT,

                    ]:

                        await self.stop_stream(
                            update.chat_id
                        )


JARVIS = Call()
