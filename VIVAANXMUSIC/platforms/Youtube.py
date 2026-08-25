import asyncio
import os
import re
from typing import Optional

import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

try:
    from py_yt import VideosSearch
except ImportError:
    from youtubesearchpython import VideosSearch


API_URL = os.environ.get(
    "SHRUTI_API_URL",
    "https://api01.shrutibots.site"
)

API_KEY = os.environ.get(
    "SHRUTI_API_KEY",
    "ShrutiBotsAlSpfeG7JItQmu"
)


class YouTubeAPI:

    def __init__(self):
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

    async def url(self, message: Message) -> Optional[str]:
        """
        Extract a YouTube URL from the current message or replied message.
        Supports:
        - youtube.com
        - youtu.be
        - music.youtube.com
        - Shorts
        """

        if message.reply_to_message:
            message = message.reply_to_message

        text = ""

        if message.text:
            text = message.text
        elif message.caption:
            text = message.caption

        if not text:
            return None

        pattern = (
            r"(https?://"
            r"(?:www\.)?"
            r"(?:youtube\.com|music\.youtube\.com|youtu\.be)"
            r"/[^\s]+)"
        )

        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(1).strip()

        return None

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract YouTube video ID.
        """

        if not url:
            return None

        patterns = [
            r"(?:v=)([A-Za-z0-9_-]{11})",
            r"youtu\.be/([A-Za-z0-9_-]{11})",
            r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
            r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
            r"youtube\.com/live/([A-Za-z0-9_-]{11})",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def normalize_youtube_url(self, url: str) -> str:
        """
        Normalize YouTube URL.
        """

        video_id = self.extract_video_id(url)

        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

        return url

    async def search(self, query: str, limit: int = 1):
        """
        Search YouTube videos.
        """

        try:
            search = VideosSearch(query, limit=limit)
            results = await asyncio.to_thread(search.result)

            if not results:
                return []

            return results.get("result", [])

        except Exception:
            return []

    async def details(self, url: str, videoid: Optional[str] = None):
        """
        Get YouTube video details.
        """

        if videoid:
            url = f"https://www.youtube.com/watch?v={videoid}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "nocheckcertificate": True,
        }

        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            data = await asyncio.to_thread(extract)

            return {
                "id": data.get("id"),
                "title": data.get("title"),
                "duration": data.get("duration", 0),
                "thumbnail": data.get("thumbnail"),
                "url": data.get("webpage_url") or url,
                "channel": data.get("channel"),
            }

        except Exception:
            return None

    async def title(self, url: str):
        """
        Get video title.
        """

        data = await self.details(url)

        if not data:
            return None

        return data.get("title")

    async def duration(self, url: str):
        """
        Get video duration.
        """

        data = await self.details(url)

        if not data:
            return 0

        return data.get("duration", 0)

    async def thumbnail(self, url: str):
        """
        Get video thumbnail.
        """

        data = await self.details(url)

        if not data:
            return None

        return data.get("thumbnail")

    async def playlist(self, url: str, limit: int = 50):
        """
        Get playlist information.
        """

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "nocheckcertificate": True,
        }

        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            data = await asyncio.to_thread(extract)

            results = []

            for entry in data.get("entries", [])[:limit]:

                if not entry:
                    continue

                video_id = entry.get("id")

                if not video_id:
                    continue

                results.append(
                    {
                        "id": video_id,
                        "title": entry.get("title") or "Unknown",
                        "duration": entry.get("duration", 0),
                        "thumbnail": (
                            f"https://i.ytimg.com/vi/"
                            f"{video_id}/hqdefault.jpg"
                        ),
                        "url": (
                            f"https://www.youtube.com/watch?"
                            f"v={video_id}"
                        ),
                    }
                )

            return results

        except Exception:
            return []

    async def get_related_videos(
        self,
        video_id: str,
        limit: int = 10,
    ):
        """
        Get different related videos for autoplay.
        """

        if not video_id:
            return []

        url = (
            "https://www.youtube.com/watch?"
            f"v={video_id}"
        )

        try:
            info = await self.details(url)

            if not info:
                return []

            title = info.get("title")

            if not title:
                return []

            results = await self.search(
                title,
                limit=limit + 10,
            )

            videos = []

            seen = {video_id}

            for video in results:

                result_url = (
                    video.get("link")
                    or video.get("url")
                )

                result_id = (
                    video.get("id")
                    or self.extract_video_id(
                        result_url or ""
                    )
                )

                if not result_id:
                    continue

                if result_id in seen:
                    continue

                seen.add(result_id)

                videos.append(
                    {
                        "id": result_id,
                        "title": (
                            video.get("title")
                            or "Unknown"
                        ),
                        "duration": (
                            video.get("duration")
                            or "0:00"
                        ),
                        "thumbnail": (
                            video.get("thumbnails", [{}])[0]
                            .get("url")
                            if video.get("thumbnails")
                            else (
                                f"https://i.ytimg.com/vi/"
                                f"{result_id}/hqdefault.jpg"
                            )
                        ),
                        "url": (
                            f"https://www.youtube.com/watch?"
                            f"v={result_id}"
                        ),
                    }
                )

                if len(videos) >= limit:
                    break

            return videos

        except Exception:
            return []

    async def download_song(
        self,
        videoid: str,
        path: str = "downloads",
    ) -> Optional[str]:
        """
        Download audio using yt-dlp.
        """

        os.makedirs(path, exist_ok=True)

        url = videoid

        if not videoid.startswith("http"):
            url = (
                "https://www.youtube.com/watch?"
                f"v={videoid}"
            )

        output = os.path.join(
            path,
            "%(id)s.%(ext)s",
        )

        ydl_opts = {
            "format": (
                "bestaudio[ext=m4a]/"
                "bestaudio/best"
            ),
            "outtmpl": output,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "noplaylist": True,
            "retries": 3,
            "socket_timeout": 30,
        }

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    url,
                    download=True,
                )
                return ydl.prepare_filename(info)

        try:
            return await asyncio.to_thread(download)

        except Exception:
            return None

    async def download_video(
        self,
        videoid: str,
        path: str = "downloads",
    ) -> Optional[str]:
        """
        Download video using yt-dlp.
        """

        os.makedirs(path, exist_ok=True)

        url = videoid

        if not videoid.startswith("http"):
            url = (
                "https://www.youtube.com/watch?"
                f"v={videoid}"
            )

        output = os.path.join(
            path,
            "%(id)s.%(ext)s",
        )

        ydl_opts = {
            "format": (
                "bestvideo[height<=720]+"
                "bestaudio/"
                "best[height<=720]/best"
            ),
            "outtmpl": output,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "noplaylist": True,
            "retries": 3,
            "socket_timeout": 30,
        }

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    url,
                    download=True,
                )
                return ydl.prepare_filename(info)

        try:
            return await asyncio.to_thread(download)

        except Exception:
            return None

    async def stream_url(
        self,
        url: str,
        video: bool = False,
    ) -> Optional[str]:
        """
        Get direct stream URL without downloading.
        """

        if not url:
            return None

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "noplaylist": True,
            "retries": 3,
            "socket_timeout": 30,
        }

        if video:
            ydl_opts["format"] = (
                "best[height<=720]/best"
            )
        else:
            ydl_opts["format"] = (
                "bestaudio/best"
            )

        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    url,
                    download=False,
                )

                if "url" in info:
                    return info["url"]

                formats = info.get("formats", [])

                for fmt in reversed(formats):
                    if fmt.get("url"):
                        return fmt["url"]

                return None

        try:
            return await asyncio.to_thread(extract)

        except Exception:
            return None

    async def formats(self, url: str):
        """
        Get available YouTube formats.
        """

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "nocheckcertificate": True,
        }

        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    url,
                    download=False,
                )

                return info.get("formats", [])

        try:
            return await asyncio.to_thread(extract)

        except Exception:
            return []


YouTube = YouTubeAPI()
