import asyncio
import os
import re
from typing import Union

import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import Playlist


API_URL = os.environ.get(
    "SHRUTI_API_URL",
    "https://api.shrutibots.site",
).rstrip("/")

API_KEY = os.environ.get(
    "SHRUTI_API_KEY",
    "ShrutiBotsAlSpfeG7JItQmuoxCqKd",
)

DOWNLOAD_DIR = "downloads"


def time_to_seconds(value):
    if not value:
        return 0

    try:
        parts = str(value).split(":")
        total = 0

        for part in parts:
            total = total * 60 + int(part)

        return total

    except (ValueError, TypeError):
        return 0


def _clean_youtube_url(link: str) -> str:
    if not link:
        return ""

    link = str(link).strip()

    # Video ID passed directly
    if re.fullmatch(r"[\w-]{6,}", link):
        return f"https://www.youtube.com/watch?v={link}"

    # Remove tracking/query parameters
    if "youtube.com" in link or "youtu.be" in link:

        if "youtu.be/" in link:
            vid = (
                link.split("youtu.be/", 1)[1]
                .split("?", 1)[0]
                .split("&", 1)[0]
            )

            return f"https://www.youtube.com/watch?v={vid}"

        if "v=" in link:
            vid = link.split("v=", 1)[1].split("&", 1)[0]

            return f"https://www.youtube.com/watch?v={vid}"

    return link


def _video_id(link: str) -> str:
    clean = _clean_youtube_url(link)

    if "v=" in clean:
        return clean.split("v=", 1)[1].split("&", 1)[0]

    if "youtu.be/" in clean:
        return clean.split("youtu.be/", 1)[1].split("?", 1)[0]

    return ""


def _ydl_opts():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            },
        },
    }


async def _extract_info(link: str, download=False, opts=None):
    def run():
        options = dict(_ydl_opts())

        if opts:
            options.update(opts)

        options["skip_download"] = not download

        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(
                link,
                download=download,
            )

    return await asyncio.to_thread(run)


async def _search_youtube(query: str):
    def run():
        options = _ydl_opts()
        options["extract_flat"] = True

        with yt_dlp.YoutubeDL(options) as ydl:
            data = ydl.extract_info(
                f"ytsearch1:{query}",
                download=False,
            )

            entries = data.get("entries") or []

            return entries[0] if entries else None

    return await asyncio.to_thread(run)


async def download_song(link: str) -> Union[str, None]:
    url = _clean_youtube_url(link)
    vid = _video_id(url)

    if not vid:
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    cached = os.path.join(
        DOWNLOAD_DIR,
        f"{vid}.mp3",
    )

    if (
        os.path.exists(cached)
        and os.path.getsize(cached) > 0
    ):
        return cached

    # API downloader
    if API_URL and API_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{API_URL}/download",
                    params={
                        "url": vid,
                        "type": "audio",
                        "api_key": API_KEY,
                    },
                    timeout=aiohttp.ClientTimeout(total=300),
                ) as resp:

                    if resp.status == 200:
                        data_type = resp.headers.get(
                            "content-type",
                            "",
                        )

                        if (
                            "text/" not in data_type.lower()
                            and "json" not in data_type.lower()
                        ):
                            tmp = cached + ".part"

                            with open(tmp, "wb") as f:
                                async for chunk in (
                                    resp.content.iter_chunked(131072)
                                ):
                                    if chunk:
                                        f.write(chunk)

                            if (
                                os.path.exists(tmp)
                                and os.path.getsize(tmp) > 0
                            ):
                                os.replace(tmp, cached)
                                return cached

        except Exception:
            pass

    # yt-dlp fallback
    try:
        def run():
            base = os.path.join(
                DOWNLOAD_DIR,
                vid,
            )

            opts = {
                "format": (
                    "bestaudio[ext=m4a]/"
                    "bestaudio/best"
                ),
                "outtmpl": base + ".%(ext)s",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": [
                            "android",
                            "web",
                        ],
                    },
                },
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            candidates = [
                base + ".m4a",
                base + ".webm",
                base + ".opus",
                base + ".mp3",
            ]

            return next(
                (
                    path
                    for path in candidates
                    if (
                        os.path.exists(path)
                        and os.path.getsize(path) > 0
                    )
                ),
                None,
            )

        return await asyncio.to_thread(run)

    except Exception:
        return None


async def download_video(link: str) -> Union[str, None]:
    url = _clean_youtube_url(link)
    vid = _video_id(url)

    if not vid:
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # API downloader
    if API_URL and API_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{API_URL}/download",
                    params={
                        "url": vid,
                        "type": "video",
                        "api_key": API_KEY,
                    },
                    timeout=aiohttp.ClientTimeout(total=600),
                ) as resp:

                    if resp.status == 200:
                        tmp = os.path.join(
                            DOWNLOAD_DIR,
                            f"{vid}.mp4.part",
                        )

                        path = os.path.join(
                            DOWNLOAD_DIR,
                            f"{vid}.mp4",
                        )

                        with open(tmp, "wb") as f:
                            async for chunk in (
                                resp.content.iter_chunked(131072)
                            ):
                                if chunk:
                                    f.write(chunk)

                        if (
                            os.path.exists(tmp)
                            and os.path.getsize(tmp) > 0
                        ):
                            os.replace(tmp, path)
                            return path

        except Exception:
            pass

    # yt-dlp fallback
    try:
        def run():
            path = os.path.join(
                DOWNLOAD_DIR,
                f"{vid}.mp4",
            )

            opts = {
                "format": (
                    "bestvideo+bestaudio/"
                    "best"
                ),
                "merge_output_format": "mp4",
                "outtmpl": path,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": [
                            "android",
                            "web",
                        ],
                    },
                },
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            if (
                os.path.exists(path)
                and os.path.getsize(path) > 0
            ):
                return path

            return None

        return await asyncio.to_thread(run)

    except Exception:
        return None


class YouTubeAPI:

    def __init__(self):
        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.regex = (
            r"(?:youtube\.com|youtu\.be)"
        )

        self.status = (
            "https://www.youtube.com/oembed?url="
        )

        self.listbase = (
            "https://youtube.com/playlist?list="
        )

        self.reg = re.compile(
            r"\x1B(?:[@-Z\\-_]|"
            r"\[[0-?]*[ -/]*[@-~])"
        )

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link

        return bool(
            re.search(
                self.regex,
                str(link),
            )
        )

    async def url(
        self,
        message_1: Message,
    ) -> Union[str, None]:

        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(
                message_1.reply_to_message
            )

        for message in messages:
            text = (
                message.text
                or message.caption
                or ""
            )

            if message.entities:
                for entity in message.entities:

                    if (
                        entity.type
                        == MessageEntityType.URL
                    ):
                        return text[
                            entity.offset:
                            entity.offset
                            + entity.length
                        ]

                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                        and entity.url
                    ):
                        return entity.url

            if message.caption_entities:
                for entity in (
                    message.caption_entities
                ):
                    if (
                        entity.type
                        == MessageEntityType.TEXT_LINK
                        and entity.url
                    ):
                        return entity.url

        return None

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        url = (
            self.base + link
            if videoid
            else _clean_youtube_url(link)
        )

        try:
            info = await _extract_info(url)

        except Exception:
            info = None

        if not info:
            info = await _search_youtube(link)

        if not info:
            raise ValueError(
                "YouTube track details could not be fetched"
            )

        title = (
            info.get("title")
            or "Unknown Title"
        )

        duration = info.get("duration")
        duration_sec = int(duration or 0)

        duration_min = (
            f"{duration_sec // 60}:"
            f"{duration_sec % 60:02d}"
            if duration_sec
            else "00:00"
        )

        vidid = (
            info.get("id")
            or _video_id(url)
        )

        thumbnail = (
            info.get("thumbnail")
            or (
                f"https://i.ytimg.com/vi/"
                f"{vidid}/hqdefault.jpg"
                if vidid
                else ""
            )
        )

        return (
            title,
            duration_min,
            duration_sec,
            thumbnail,
            vidid,
        )

    async def title(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        return (
            await self.details(
                link,
                videoid,
            )
        )[0]

    async def duration(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        return (
            await self.details(
                link,
                videoid,
            )
        )[1]

    async def thumbnail(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        return (
            await self.details(
                link,
                videoid,
            )
        )[3]

    async def video(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        url = (
            self.base + link
            if videoid
            else _clean_youtube_url(link)
        )

        try:
            downloaded_file = await download_video(
                url
            )

            if downloaded_file:
                return 1, downloaded_file

            return (
                0,
                "Video download failed",
            )

        except Exception as e:
            return (
                0,
                f"Video download error: {e}",
            )

    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.listbase + link

        if "&" in link:
            link = link.split("&")[0]

        try:
            plist = await Playlist.get(link)

            videos = (
                plist.get("videos")
                or []
            )

            return [
                video.get("id")
                for video in videos[:limit]
                if video
                and video.get("id")
            ]

        except Exception:
            return []

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        url = (
            self.base + link
            if videoid
            else _clean_youtube_url(link)
        )

        info = None

        try:
            if (
                videoid
                or re.search(
                    self.regex,
                    str(url),
                )
            ):
                info = await _extract_info(
                    url
                )

        except Exception:
            info = None

        if not info:
            info = await _search_youtube(link)

        if not info:
            raise ValueError(
                "YouTube track details could not be fetched"
            )

        vidid = info.get("id")

        if not vidid:
            raise ValueError(
                "YouTube video ID not found"
            )

        title = (
            info.get("title")
            or "Unknown Title"
        )

        duration_sec = int(
            info.get("duration") or 0
        )

        duration_min = (
            f"{duration_sec // 60}:"
            f"{duration_sec % 60:02d}"
            if duration_sec
            else "00:00"
        )

        yturl = (
            f"https://www.youtube.com/watch?v="
            f"{vidid}"
        )

        thumbnail = (
            info.get("thumbnail")
            or (
                f"https://i.ytimg.com/vi/"
                f"{vidid}/hqdefault.jpg"
            )
        )

        return {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }, vidid

    # ==========================================
    # AUTOPLAY
    # ==========================================

    async def autoplay(
        self,
        videoid: str,
        title: str = "",
        max_duration: Union[int, None] = None,
        exclude_ids=None,
    ):
        """
        Find a different YouTube song for autoplay.

        `exclude_ids` contains recently played video IDs so autoplay does not
        loop back to the same songs.
        """
        seed_id = str(videoid or "").strip()
        query = str(title or "").strip() or seed_id

        if not query:
            return None

        excluded = {
            str(item).strip()
            for item in (exclude_ids or set())
            if str(item).strip()
        }
        excluded.add(seed_id)

        def run():
            options = _ydl_opts()
            options["extract_flat"] = True

            with yt_dlp.YoutubeDL(options) as ydl:
                data = ydl.extract_info(
                    f"ytsearch30:{query}",
                    download=False,
                )
                return data.get("entries") or []

        try:
            entries = await asyncio.to_thread(run)
        except Exception:
            return None

        # Search in returned order, but never use a recently played ID.
        for entry in entries:
            if not entry:
                continue

            candidate = str(entry.get("id") or "").strip()
            if not candidate or candidate in excluded:
                continue

            try:
                duration_sec = int(entry.get("duration") or 0)
            except (TypeError, ValueError):
                duration_sec = 0

            if duration_sec <= 0:
                continue

            if max_duration and duration_sec > int(max_duration):
                continue

            song_title = str(entry.get("title") or "Unknown Title").strip()
            if not song_title:
                continue

            thumbnail = (
                entry.get("thumbnail")
                or f"https://i.ytimg.com/vi/{candidate}/hqdefault.jpg"
            )

            return {
                "title": song_title,
                "link": f"https://www.youtube.com/watch?v={candidate}",
                "vidid": candidate,
                "duration_sec": duration_sec,
                "duration_min": (
                    f"{duration_sec // 60}:{duration_sec % 60:02d}"
                ),
                "thumb": thumbnail,
            }

        return None

    async def formats(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):
        url = (
            self.base + link
            if videoid
            else _clean_youtube_url(link)
        )

        try:
            result = await _extract_info(
                url
            )

            formats_available = []

            for fmt in (
                result.get("formats", [])
            ):
                if (
                    "dash"
                    in str(
                        fmt.get(
                            "format",
                            "",
                        )
                    ).lower()
                ):
                    continue

                formats_available.append({
                    "format": fmt.get(
                        "format"
                    ),
                    "filesize": fmt.get(
                        "filesize"
                    ),
                    "format_id": fmt.get(
                        "format_id"
                    ),
                    "ext": fmt.get(
                        "ext"
                    ),
                    "format_note": fmt.get(
                        "format_note"
                    ),
                    "yturl": url,
                })

            return (
                formats_available,
                url,
            )

        except Exception:
            return [], url

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        url = (
            self.base + link
            if videoid
            else _clean_youtube_url(link)
        )

        def run():
            opts = _ydl_opts()
            opts["extract_flat"] = True

            with yt_dlp.YoutubeDL(
                opts
            ) as ydl:

                data = ydl.extract_info(
                    (
                        url
                        if videoid
                        else f"ytsearch10:{link}"
                    ),
                    download=False,
                )

                entries = (
                    data.get("entries")
                    or []
                )

                return entries[
                    query_type
                ]

        result = await asyncio.to_thread(
            run
        )

        vidid = result["id"]

        duration = int(
            result.get("duration")
            or 0
        )

        duration_min = (
            f"{duration // 60}:"
            f"{duration % 60:02d}"
            if duration
            else "00:00"
        )

        thumb = (
            result.get("thumbnail")
            or (
                f"https://i.ytimg.com/vi/"
                f"{vidid}/hqdefault.jpg"
            )
        )

        return (
            result.get(
                "title",
                "Unknown Title",
            ),
            duration_min,
            thumb,
            vidid,
        )

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ):
        url = (
            self.base + link
            if videoid
            else _clean_youtube_url(link)
        )

        try:
            if video:
                file_path = await download_video(
                    url
                )
            else:
                file_path = await download_song(
                    url
                )

            if file_path:
                return (
                    file_path,
                    True,
                )

            return (
                None,
                False,
            )

        except Exception:
            return (
                None,
                False,
            )


YouTube = YouTubeAPI()
