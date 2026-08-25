import asyncio
import json
import os
import re
import shutil
from typing import Any, Optional, Union
from urllib.parse import parse_qs, urlparse

import aiohttp
import yt_dlp
from py_yt import VideosSearch
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

import config
from VIVAANXMUSIC import LOGGER
from VIVAANXMUSIC.utils.formatters import time_to_seconds


API_URL = os.environ.get(
    "SHRUTI_API_URL",
    "https://api01.shrutibots.site",
)

API_KEY = os.environ.get(
    "SHRUTI_API_KEY",
    "ShrutiBotsAlSpfeG7JItQmu",
)


class YouTubeAPI:

    def __init__(self):
        self.api_url = API_URL.rstrip("/")
        self.api_key = API_KEY
        self._ytdlp_lock = asyncio.Lock()

    # =====================================================
    # URL / VIDEO ID
    # =====================================================

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        if not url:
            return None

        url = str(url).strip()

        # Already a YouTube video ID.
        if re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            url,
        ):
            return url

        try:
            parsed = urlparse(url)

            if parsed.hostname in {
                "youtu.be",
                "www.youtu.be",
            }:
                return parsed.path.strip("/").split("/")[0]

            if parsed.hostname and (
                "youtube.com" in parsed.hostname
                or "youtube-nocookie.com"
                in parsed.hostname
            ):

                query = parse_qs(
                    parsed.query
                )

                if query.get("v"):
                    return query["v"][0]

                parts = [
                    part
                    for part in parsed.path.split("/")
                    if part
                ]

                for marker in (
                    "shorts",
                    "embed",
                    "live",
                    "v",
                ):
                    if marker in parts:
                        index = parts.index(marker)

                        if len(parts) > index + 1:
                            return parts[index + 1]

        except Exception:
            pass

        patterns = [
            r"(?:v=|/)([A-Za-z0-9_-]{11})",
            r"youtu\.be/([A-Za-z0-9_-]{11})",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                url,
            )

            if match:
                return match.group(1)

        return None

    @staticmethod
    def normalize_youtube_url(
        value: str,
    ) -> Optional[str]:

        video_id = (
            YouTubeAPI.extract_video_id(
                value
            )
        )

        if not video_id:
            return None

        return (
            f"https://www.youtube.com/"
            f"watch?v={video_id}"
        )

    # =====================================================
    # AUTOPLAY HELPERS
    # =====================================================

    @staticmethod
    def _normalize_autoplay_title(
        value: str,
    ) -> str:

        value = str(
            value or ""
        ).lower()

        value = re.sub(
            r"\b("
            r"official|video|audio|lyrics?|lyric|music|"
            r"full|hd|4k|visualizer|"
            r"official music video|official audio"
            r")\b",
            " ",
            value,
        )

        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value,
        )

        return " ".join(
            value.split()
        )

    @staticmethod
    def _autoplay_duration_to_seconds(
        value,
    ) -> int:

        if value is None:
            return 0

        if isinstance(
            value,
            (int, float),
        ):
            return int(value)

        if isinstance(
            value,
            dict,
        ):

            for key in (
                "seconds",
                "duration",
                "durationSeconds",
            ):

                if key in value:
                    return (
                        YouTubeAPI
                        ._autoplay_duration_to_seconds(
                            value[key]
                        )
                    )

            return 0

        text = str(
            value
            or ""
        ).strip()

        if not text:
            return 0

        if text.isdigit():
            return int(text)

        try:

            parts = [
                int(x)
                for x in text.split(":")
            ]

            if len(parts) == 3:

                hours, minutes, seconds = (
                    parts
                )

                return (
                    hours * 3600
                    + minutes * 60
                    + seconds
                )

            if len(parts) == 2:

                minutes, seconds = parts

                return (
                    minutes * 60
                    + seconds
                )

            if len(parts) == 1:
                return parts[0]

        except Exception:
            pass

        return 0

    @staticmethod
    def _autoplay_seconds_to_time(
        seconds: int,
    ) -> str:

        seconds = max(
            int(seconds or 0),
            0,
        )

        hours, remainder = divmod(
            seconds,
            3600,
        )

        minutes, secs = divmod(
            remainder,
            60,
        )

        if hours > 0:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{secs:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    # =====================================================
    # SEARCH
    # =====================================================

    async def _search_youtube(
        self,
        query: str,
        limit: int = 10,
    ) -> list:

        try:

            search = VideosSearch(
                query,
                limit=limit,
            )

            result = await asyncio.to_thread(
                search.result
            )

            if not isinstance(
                result,
                dict,
            ):
                return []

            return (
                result.get("result")
                or result.get("videos")
                or []
            )

        except Exception as err:

            LOGGER(__name__).warning(
                "YouTube search failed | "
                "query=%s | error=%s",
                query,
                err,
            )

            return []

    # =====================================================
    # AUTOPLAY
    # =====================================================

    async def autoplay(
        self,
        videoid: str,
        title: str = "",
        max_duration=None,
        exclude_ids=None,
        exclude_titles=None,
    ) -> Optional[dict]:

        """
        Return a different YouTube song.

        Compatible with:
            await YouTube.autoplay(
                videoid,
                title,
                max_duration=...,
                exclude_ids=set(...),
                exclude_titles=set(...),
            )
        """

        exclude_ids = {
            str(item).strip()
            for item in (
                exclude_ids or set()
            )
            if item
        }

        exclude_titles = {
            self._normalize_autoplay_title(
                item
            )
            for item in (
                exclude_titles or set()
            )
            if item
        }

        videoid = str(
            videoid or ""
        ).strip()

        title = str(
            title or ""
        ).strip()

        if videoid:
            exclude_ids.add(
                videoid
            )

        current_title = title
        uploader = ""

        # Get current video information.
        if videoid:

            try:

                info = await self.details(
                    videoid
                )

                if isinstance(
                    info,
                    dict,
                ):

                    current_title = str(
                        info.get("title")
                        or current_title
                        or ""
                    ).strip()

                    uploader = str(
                        info.get("channel")
                        or info.get("uploader")
                        or info.get("author")
                        or info.get(
                            "channel_name"
                        )
                        or ""
                    ).strip()

            except Exception:
                pass

        current_normalized = (
            self._normalize_autoplay_title(
                current_title
            )
        )

        if current_normalized:
            exclude_titles.add(
                current_normalized
            )

        # Different queries increase chances
        # of finding another song.
        queries = []

        if uploader and current_title:

            queries.extend(
                [
                    (
                        f"{uploader} "
                        f"{current_title} "
                        "music"
                    ),
                    (
                        f"{uploader} "
                        f"{current_title}"
                    ),
                    (
                        f"{uploader} "
                        "songs"
                    ),
                ]
            )

        if current_title:

            queries.extend(
                [
                    (
                        f"{current_title} "
                        "official audio"
                    ),
                    (
                        f"{current_title} "
                        "official video"
                    ),
                    (
                        f"{current_title} "
                        "music"
                    ),
                ]
            )

        if videoid:
            queries.append(
                videoid
            )

        used_queries = set()

        for query in queries:

            query = str(
                query or ""
            ).strip()

            if not query:
                continue

            query_key = query.lower()

            if query_key in used_queries:
                continue

            used_queries.add(
                query_key
            )

            videos = (
                await self._search_youtube(
                    query,
                    limit=25,
                )
            )

            for item in videos:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                try:

                    rec_id = str(
                        item.get("id")
                        or item.get("videoId")
                        or item.get(
                            "video_id"
                        )
                        or ""
                    ).strip()

                    if not rec_id:
                        continue

                    # Never repeat the same video.
                    if (
                        rec_id
                        in exclude_ids
                    ):
                        continue

                    rec_title = str(
                        item.get("title")
                        or item.get("name")
                        or ""
                    ).strip()

                    if not rec_title:
                        continue

                    normalized_title = (
                        self
                        ._normalize_autoplay_title(
                            rec_title
                        )
                    )

                    # Prevent duplicate songs.
                    if (
                        normalized_title
                        and normalized_title
                        in exclude_titles
                    ):
                        continue

                    duration = (
                        item.get("duration")
                        or item.get(
                            "durationSeconds"
                        )
                        or item.get("length")
                        or ""
                    )

                    duration_sec = (
                        self
                        ._autoplay_duration_to_seconds(
                            duration
                        )
                    )

                    # Skip livestreams / invalid tracks.
                    if duration_sec <= 0:
                        continue

                    if (
                        max_duration is not None
                        and duration_sec
                        > int(max_duration)
                    ):
                        continue

                    return {
                        "vidid": rec_id,
                        "title": rec_title,
                        "duration_sec": (
                            duration_sec
                        ),
                        "duration_min": (
                            self
                            ._autoplay_seconds_to_time(
                                duration_sec
                            )
                        ),
                    }

                except Exception:
                    continue

        return None

    # =====================================================
    # DETAILS
    # =====================================================

    async def details(
        self,
        videoid: str,
    ) -> dict:

        videoid = (
            self.extract_video_id(
                videoid
            )
            or str(videoid or "")
        )

        if not videoid:
            return {}

        url = (
            f"https://www.youtube.com/"
            f"watch?v={videoid}"
        )

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }

        def extract():

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                return ydl.extract_info(
                    url,
                    download=False,
                )

        try:

            data = await asyncio.to_thread(
                extract
            )

            if not data:
                return {}

            duration = int(
                data.get("duration")
                or 0
            )

            return {
                "id": (
                    data.get("id")
                    or videoid
                ),
                "title": (
                    data.get("title")
                    or ""
                ),
                "duration": duration,
                "duration_sec": duration,
                "duration_min": (
                    self
                    ._autoplay_seconds_to_time(
                        duration
                    )
                ),
                "thumbnail": (
                    data.get("thumbnail")
                    or ""
                ),
                "channel": (
                    data.get("channel")
                    or data.get("uploader")
                    or ""
                ),
                "uploader": (
                    data.get("uploader")
                    or data.get("channel")
                    or ""
                ),
                "views": (
                    data.get("view_count")
                    or 0
                ),
            }

        except Exception as err:

            LOGGER(__name__).warning(
                "YouTube details failed | "
                "video=%s | error=%s",
                videoid,
                err,
            )

            return {}

    # =====================================================
    # VIDEO
    # =====================================================

    async def video(
        self,
        videoid: str,
        video: bool = False,
    ):

        videoid = (
            self.extract_video_id(
                videoid
            )
            or str(videoid or "")
        )

        if not videoid:
            return 0, None

        url = (
            f"https://www.youtube.com/"
            f"watch?v={videoid}"
        )

        options = {
            "quiet": True,
            "no_warnings": True,
            "format": (
                "best[protocol^=http]"
                if video
                else (
                    "bestaudio/"
                    "best[protocol^=http]"
                )
            ),
            "noplaylist": True,
        }

        def extract():

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                return ydl.extract_info(
                    url,
                    download=False,
                )

        try:

            data = await asyncio.to_thread(
                extract
            )

            if not data:
                return 0, None

            stream_url = (
                data.get("url")
            )

            if not stream_url:

                requested = (
                    data.get(
                        "requested_formats"
                    )
                    or []
                )

                if requested:
                    stream_url = (
                        requested[0].get(
                            "url"
                        )
                    )

            if not stream_url:
                return 0, None

            return 1, stream_url

        except Exception as err:

            LOGGER(__name__).warning(
                "YouTube stream URL failed | "
                "video=%s | error=%s",
                videoid,
                err,
            )

            return 0, None

    # =====================================================
    # DOWNLOAD
    # =====================================================

    async def download(
        self,
        link: str,
        mystic=None,
        videoid: bool = False,
        video: bool = False,
        title: str = "",
    ):

        if videoid:

            vid = (
                self.extract_video_id(
                    link
                )
                or str(link or "")
            )

            url = (
                f"https://www.youtube.com/"
                f"watch?v={vid}"
            )

        else:

            url = str(
                link or ""
            )

            vid = (
                self.extract_video_id(
                    url
                )
            )

        if not url:
            return None, False

        if mystic:

            try:

                await mystic.edit_text(
                    "Downloading..."
                )

            except Exception:
                pass

        try:

            n, direct_url = (
                await self.video(
                    vid or url,
                    video=video,
                )
            )

            if n and direct_url:

                # Returning direct stream URL.
                return direct_url, True

        except Exception:
            pass

        # Local yt-dlp fallback.
        os.makedirs(
            "downloads",
            exist_ok=True,
        )

        safe_id = (
            vid
            or str(
                abs(
                    hash(url)
                )
            )
        )

        output_template = os.path.join(
            "downloads",
            f"{safe_id}.%(ext)s",
        )

        options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "outtmpl": output_template,
            "retries": 3,
            "fragment_retries": 3,
            "concurrent_fragment_downloads": 3,
        }

        if video:

            options.update(
                {
                    "format": (
                        "bestvideo+bestaudio/"
                        "best"
                    ),
                    "merge_output_format": (
                        "mp4"
                    ),
                }
            )

        else:

            options.update(
                {
                    "format": (
                        "bestaudio/best"
                    ),
                }
            )

        def run_download():

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                data = ydl.extract_info(
                    url,
                    download=True,
                )

                return ydl.prepare_filename(
                    data
                )

        try:

            filename = (
                await asyncio.to_thread(
                    run_download
                )
            )

            # If extension changed after merge,
            # locate the newest matching file.
            if not os.path.exists(
                filename
            ):

                directory = os.path.dirname(
                    filename
                )

                prefix = os.path.splitext(
                    os.path.basename(
                        filename
                    )
                )[0]

                candidates = []

                if os.path.isdir(
                    directory
                ):

                    for file in os.listdir(
                        directory
                    ):

                        if file.startswith(
                            prefix
                        ):

                            path = os.path.join(
                                directory,
                                file,
                            )

                            if os.path.isfile(
                                path
                            ):

                                candidates.append(
                                    path
                                )

                if candidates:

                    filename = max(
                        candidates,
                        key=os.path.getmtime,
                    )

            if (
                filename
                and os.path.exists(
                    filename
                )
            ):
                return filename, False

        except Exception as err:

            LOGGER(__name__).warning(
                "YouTube download failed | "
                "video=%s | error=%s",
                vid or url,
                err,
            )

        return None, False

    # =====================================================
    # PLAYLIST
    # =====================================================

    async def playlist(
        self,
        url: str,
        limit: int = 50,
    ) -> list:

        options = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "playlistend": limit,
        }

        def extract():

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                return ydl.extract_info(
                    url,
                    download=False,
                )

        try:

            data = await asyncio.to_thread(
                extract
            )

            entries = (
                data.get("entries")
                or []
            )

            results = []

            for item in entries:

                if not item:
                    continue

                vid = (
                    item.get("id")
                )

                if not vid:
                    continue

                results.append(
                    {
                        "id": vid,
                        "title": (
                            item.get("title")
                            or "Unknown"
                        ),
                        "duration": (
                            int(
                                item.get(
                                    "duration"
                                )
                                or 0
                            )
                        ),
                        "thumbnail": (
                            item.get(
                                "thumbnail"
                            )
                            or ""
                        ),
                    }
                )

            return results

        except Exception:
            return []

    # =====================================================
    # SEARCH RESULT
    # =====================================================

    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list:

        return await self._search_youtube(
            query,
            limit=limit,
    )
