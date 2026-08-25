import asyncio
import os
import re
from typing import Any, Dict, List, Optional, Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

try:
    from py_yt import VideosSearch
except ImportError:
    from youtubesearchpython import VideosSearch


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
        self.ydl_base_opts = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "noplaylist": True,
            "retries": 3,
            "socket_timeout": 30,
        }

    async def url(self, message: Message) -> Optional[str]:
        """
        Return a YouTube URL found in the message or replied message.
        """

        source = message

        if message.reply_to_message:
            source = message.reply_to_message

        text = source.text or source.caption or ""

        if not text:
            return None

        # Pyrogram entities support
        entities = source.entities or source.caption_entities or []

        for entity in entities:
            if entity.type == MessageEntityType.TEXT_LINK and entity.url:
                if self.is_youtube_url(entity.url):
                    return entity.url

        pattern = (
            r"https?://(?:www\.)?"
            r"(?:youtube\.com|music\.youtube\.com|m\.youtube\.com|youtu\.be)"
            r"/[^\s<>]+"
        )

        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(0).rstrip(".,!?)\"]}'")

        return None

    def is_youtube_url(self, url: str) -> bool:
        if not url:
            return False

        return bool(
            re.search(
                r"(?:youtube\.com|music\.youtube\.com|m\.youtube\.com|youtu\.be)",
                url,
                re.IGNORECASE,
            )
        )

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract the 11-character YouTube video ID.
        """

        if not url:
            return None

        if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
            return url

        patterns = [
            r"(?:youtube\.com/watch\?(?:.*&)?v=)([A-Za-z0-9_-]{11})",
            r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
            r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
            r"(?:youtube\.com/live/)([A-Za-z0-9_-]{11})",
            r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
            r"(?:youtube\.com/v/)([A-Za-z0-9_-]{11})",
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)

            if match:
                return match.group(1)

        return None

    def normalize_youtube_url(self, url: str) -> str:
        video_id = self.extract_video_id(url)

        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"

        return url

    async def _yt_dlp_extract(
        self,
        url: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        opts = dict(self.ydl_base_opts)

        if options:
            opts.update(options)

        def extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            return await asyncio.to_thread(extract)

        except Exception as error:
            print(f"yt-dlp extract error: {error}")
            return None

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        try:
            searcher = VideosSearch(query, limit=limit)

            result = await asyncio.to_thread(
                searcher.result
            )

            return result.get("result", [])

        except Exception as error:
            print(f"YouTube search error: {error}")
            return []

    async def details(
        self,
        url: str,
        videoid: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        if videoid:
            url = f"https://www.youtube.com/watch?v={videoid}"

        data = await self._yt_dlp_extract(
            url,
            {
                "skip_download": True,
            },
        )

        if not data:
            return None

        return {
            "id": data.get("id"),
            "videoid": data.get("id"),
            "title": data.get("title") or "Unknown",
            "duration": int(data.get("duration") or 0),
            "thumbnail": data.get("thumbnail"),
            "thumb": data.get("thumbnail"),
            "url": data.get("webpage_url") or url,
            "link": data.get("webpage_url") or url,
            "channel": (
                data.get("channel")
                or data.get("uploader")
                or ""
            ),
        }

    async def title(self, url: str) -> Optional[str]:
        data = await self.details(url)

        if not data:
            return None

        return data["title"]

    async def duration(self, url: str) -> int:
        data = await self.details(url)

        if not data:
            return 0

        return data["duration"]

    async def thumbnail(self, url: str) -> Optional[str]:
        data = await self.details(url)

        if not data:
            return None

        return data["thumbnail"]

    async def get_related_videos(
        self,
        video_id: str,
        limit: int = 10,
        exclude_ids: Optional[Union[List[str], set]] = None,
    ) -> List[Dict[str, Any]]:

        excluded = set(str(x) for x in (exclude_ids or []))
        excluded.add(str(video_id))

        info = await self.details(
            f"https://www.youtube.com/watch?v={video_id}"
        )

        if not info:
            return []

        query = info.get("title")

        if not query:
            return []

        results = await self.search(
            query,
            limit=max(limit + 15, 25),
        )

        videos = []

        for result in results:
            result_url = (
                result.get("link")
                or result.get("url")
                or ""
            )

            result_id = (
                result.get("id")
                or self.extract_video_id(result_url)
            )

            if not result_id:
                continue

            if result_id in excluded:
                continue

            excluded.add(result_id)

            video_title = (
                result.get("title")
                or "Unknown"
            )

            duration_text = (
                result.get("duration")
                or "0:00"
            )

            thumb = (
                result.get("thumbnails", [{}])[0].get("url")
                if result.get("thumbnails")
                else f"https://i.ytimg.com/vi/{result_id}/hqdefault.jpg"
            )

            videos.append(
                {
                    "id": result_id,
                    "vidid": result_id,
                    "title": video_title,
                    "duration": duration_text,
                    "thumbnail": thumb,
                    "thumb": thumb,
                    "url": (
                        f"https://www.youtube.com/watch?v={result_id}"
                    ),
                    "link": (
                        f"https://www.youtube.com/watch?v={result_id}"
                    ),
                }
            )

            if len(videos) >= limit:
                break

        return videos

    async def autoplay(
        self,
        videoid: str,
        title: str = "",
        max_duration: Optional[int] = None,
        exclude_ids: Optional[Union[List[str], set]] = None,
        exclude_titles: Optional[
            Union[List[str], set]
        ] = None,
    ) -> Optional[Dict[str, Any]]:

        excluded_ids = set(
            str(x)
            for x in (exclude_ids or [])
            if x
        )

        if videoid:
            excluded_ids.add(str(videoid))

        excluded_titles = {
            str(x).strip().lower()
            for x in (exclude_titles or [])
            if x
        }

        queries = []

        if title:
            queries.append(title)

        if videoid:
            try:
                current = await self.details(
                    f"https://www.youtube.com/watch?v={videoid}"
                )

                if current and current.get("title"):
                    current_title = current["title"]

                    if current_title not in queries:
                        queries.append(current_title)

            except Exception:
                pass

        for query in queries:
            results = await self.search(
                query,
                limit=30,
            )

            for result in results:
                link = (
                    result.get("link")
                    or result.get("url")
                    or ""
                )

                vidid = (
                    result.get("id")
                    or self.extract_video_id(link)
                )

                if not vidid:
                    continue

                if str(vidid) in excluded_ids:
                    continue

                result_title = (
                    result.get("title")
                    or ""
                )

                if (
                    result_title.strip().lower()
                    in excluded_titles
                ):
                    continue

                details = await self.details(
                    f"https://www.youtube.com/watch?v={vidid}"
                )

                if not details:
                    continue

                duration_sec = int(
                    details.get("duration") or 0
                )

                if (
                    max_duration
                    and duration_sec > int(max_duration)
                ):
                    continue

                excluded_ids.add(str(vidid))

                return {
                    "title": (
                        details.get("title")
                        or result_title
                        or "Unknown"
                    ),
                    "link": (
                        details.get("url")
                        or f"https://www.youtube.com/watch?v={vidid}"
                    ),
                    "url": (
                        details.get("url")
                        or f"https://www.youtube.com/watch?v={vidid}"
                    ),
                    "vidid": vidid,
                    "id": vidid,
                    "duration_sec": duration_sec,
                    "duration_min": (
                        f"{duration_sec // 60}:"
                        f"{duration_sec % 60:02d}"
                    ),
                    "thumb": (
                        details.get("thumbnail")
                        or f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg"
                    ),
                    "thumbnail": (
                        details.get("thumbnail")
                        or f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg"
                    ),
                }

        return None

    async def playlist(
        self,
        url: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:

        opts = {
            "extract_flat": True,
            "skip_download": True,
        }

        data = await self._yt_dlp_extract(
            url,
            opts,
        )

        if not data:
            return []

        output = []

        for entry in (data.get("entries") or [])[:limit]:
            if not entry:
                continue

            video_id = entry.get("id")

            if not video_id:
                continue

            video_url = (
                entry.get("url")
                or f"https://www.youtube.com/watch?v={video_id}"
            )

            output.append(
                {
                    "id": video_id,
                    "vidid": video_id,
                    "title": (
                        entry.get("title")
                        or "Unknown"
                    ),
                    "duration": int(
                        entry.get("duration") or 0
                    ),
                    "thumbnail": (
                        f"https://i.ytimg.com/vi/"
                        f"{video_id}/hqdefault.jpg"
                    ),
                    "thumb": (
                        f"https://i.ytimg.com/vi/"
                        f"{video_id}/hqdefault.jpg"
                    ),
                    "url": video_url,
                    "link": video_url,
                }
            )

        return output

    async def stream_url(
        self,
        url: str,
        video: bool = False,
    ) -> Optional[str]:

        options = {
            "format": (
                "best[height<=720]/best"
                if video
                else "bestaudio/best"
            ),
        }

        data = await self._yt_dlp_extract(
            url,
            options,
        )

        if not data:
            return None

        if data.get("url"):
            return data["url"]

        for fmt in reversed(
            data.get("formats") or []
        ):
            if fmt.get("url"):
                return fmt["url"]

        return None

    async def download_song(
        self,
        videoid: str,
        path: str = "downloads",
    ) -> Optional[str]:

        os.makedirs(path, exist_ok=True)

        url = (
            videoid
            if videoid.startswith("http")
            else f"https://www.youtube.com/watch?v={videoid}"
        )

        output = os.path.join(
            path,
            "%(id)s.%(ext)s",
        )

        options = dict(self.ydl_base_opts)

        options.update(
            {
                "format": "bestaudio/best",
                "outtmpl": output,
            }
        )

        def download():
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(
                    url,
                    download=True,
                )

                filename = ydl.prepare_filename(info)

                if os.path.exists(filename):
                    return filename

                video_id = info.get("id")

                for name in os.listdir(path):
                    if name.startswith(
                        str(video_id)
                    ):
                        return os.path.join(
                            path,
                            name,
                        )

                return filename

        try:
            return await asyncio.to_thread(
                download
            )

        except Exception as error:
            print(f"Audio download error: {error}")
            return None

    async def download_video(
        self,
        videoid: str,
        path: str = "downloads",
    ) -> Optional[str]:

        os.makedirs(path, exist_ok=True)

        url = (
            videoid
            if videoid.startswith("http")
            else f"https://www.youtube.com/watch?v={videoid}"
        )

        output = os.path.join(
            path,
            "%(id)s.%(ext)s",
        )

        options = dict(self.ydl_base_opts)

        options.update(
            {
                "format": (
                    "bestvideo[height<=720]+"
                    "bestaudio/best[height<=720]/best"
                ),
                "outtmpl": output,
            }
        )

        def download():
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(
                    url,
                    download=True,
                )

                return ydl.prepare_filename(info)

        try:
            return await asyncio.to_thread(
                download
            )

        except Exception as error:
            print(f"Video download error: {error}")
            return None

    async def formats(
        self,
        url: str,
    ) -> List[Dict[str, Any]]:

        data = await self._yt_dlp_extract(
            url,
            {
                "skip_download": True,
            },
        )

        if not data:
            return []

        return data.get("formats") or []


YouTube = YouTubeAPI()
