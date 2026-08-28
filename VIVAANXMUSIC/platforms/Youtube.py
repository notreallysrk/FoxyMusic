import asyncio
import os
import random
import re
from typing import Union
from urllib.parse import parse_qs, urlparse

import aiohttp
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import Playlist


# =========================================================
# CONFIG
# =========================================================

API_URL = os.environ.get(
    "SHRUTI_API_URL",
    "https://friendmiss-5d49e780ee8d.herokuapp.com",
).rstrip("/")

API_KEY = os.environ.get(
    "SHRUTI_API_KEY",
    "",
)

DOWNLOAD_DIR = "downloads"

DOWNLOAD_CHUNK_SIZE = 1024 * 1024
AUDIO_DOWNLOAD_TIMEOUT = 300
VIDEO_DOWNLOAD_TIMEOUT = 600

HTTP_TIMEOUT = 45


# =========================================================
# HELPERS
# =========================================================

def time_to_seconds(value):
    if not value:
        return 0

    try:
        total = 0
        for part in str(value).split(":"):
            total = total * 60 + int(part)
        return total
    except (ValueError, TypeError):
        return 0


def _video_id(link: str) -> str:
    if not link:
        return ""

    link = str(link).strip()

    if re.fullmatch(r"[\w-]{6,}", link):
        return link

    try:
        parsed = urlparse(link)
        host = (parsed.netloc or "").lower()

        if "youtu.be" in host:
            video_id = parsed.path.strip("/").split("/")[0]
            if re.fullmatch(r"[\w-]{6,}", video_id):
                return video_id

        if (
            "youtube.com" in host
            or "youtube-nocookie.com" in host
        ):
            query = parse_qs(parsed.query)

            if query.get("v"):
                video_id = query["v"][0]
                if re.fullmatch(r"[\w-]{6,}", video_id):
                    return video_id

            parts = [
                part
                for part in parsed.path.split("/")
                if part
            ]

            if len(parts) >= 2 and parts[0] in {
                "shorts",
                "embed",
                "live",
                "v",
            }:
                video_id = parts[1]
                if re.fullmatch(r"[\w-]{6,}", video_id):
                    return video_id

    except Exception:
        pass

    patterns = [
        r"youtu\.be/([\w-]{6,})",
        r"youtube\.com/watch\?[^#]*v=([\w-]{6,})",
        r"youtube\.com/shorts/([\w-]{6,})",
        r"youtube\.com/embed/([\w-]{6,})",
        r"youtube\.com/live/([\w-]{6,})",
    ]

    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return match.group(1)

    return ""


def _clean_youtube_url(link: str) -> str:
    if not link:
        return ""

    video_id = _video_id(link)

    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"

    return str(link).strip()


def _duration_text(seconds: int) -> str:
    try:
        seconds = int(seconds or 0)

        if seconds <= 0:
            return "00:00"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"

        return f"{minutes}:{secs:02d}"

    except Exception:
        return "00:00"


def _normalize_title(value: str) -> str:
    value = str(value or "").lower().strip()

    value = re.sub(
        r"\([^)]*\)|\[[^]]*\]",
        " ",
        value,
    )

    value = re.sub(
        r"\b("
        r"official|video|audio|lyrics|lyric|full|song|music|"
        r"hd|4k|remastered|version|visualizer|mv|"
        r"fullvideo|status"
        r")\b",
        " ",
        value,
    )

    return re.sub(
        r"[^a-z0-9]+",
        "",
        value,
    )


def _title_words(value: str):
    value = str(value or "").lower()

    value = re.sub(
        r"\([^)]*\)|\[[^]]*\]",
        " ",
        value,
    )

    words = re.findall(
        r"[a-z0-9]+",
        value,
    )

    return {
        word
        for word in words
        if len(word) >= 4
        and word not in {
            "official",
            "video",
            "audio",
            "lyrics",
            "music",
            "song",
        }
    }


# =========================================================
# YT-DLP OPTIONS
# =========================================================

def _ydl_opts():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "ignoreerrors": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 3,
        "concurrent_fragment_downloads": 4,
        "geo_bypass": True,
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android_vr",
                    "android",
                    "ios",
                    "mweb",
                    "web",
                ],
            },
        },
    }


async def _extract_info(
    link: str,
    download=False,
    opts=None,
):
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


# =========================================================
# SEARCH
# =========================================================

async def _search_youtube(query: str, limit: int = 10):
    def run():
        options = _ydl_opts()

        options.update({
            "extract_flat": True,
            "ignoreerrors": True,
        })

        with yt_dlp.YoutubeDL(options) as ydl:
            data = ydl.extract_info(
                f"ytsearch{limit}:{query}",
                download=False,
            )

            entries = (
                data.get("entries")
                if data
                else []
            ) or []

            return [
                entry
                for entry in entries
                if entry
            ]

    try:
        return await asyncio.to_thread(run)
    except Exception:
        return []


async def _search_single(query: str):
    results = await _search_youtube(query, 10)

    if results:
        return results[0]

    return None


# =========================================================
# OEMBED FALLBACK
# =========================================================

async def _oembed_info(video_id: str):
    if not video_id:
        return None

    url = (
        "https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch?v={video_id}"
        "&format=json"
    )

    timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)

    try:
        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/131.0 Safari/537.36"
                    ),
                },
            ) as response:

                if response.status != 200:
                    return None

                data = await response.json()

                return {
                    "id": video_id,
                    "title": data.get("title"),
                    "duration": 0,
                    "thumbnail": (
                        data.get("thumbnail_url")
                        or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                    ),
                }

    except Exception:
        return None


# =========================================================
# SHRUTI API DOWNLOADER
# =========================================================

async def _api_download(
    video_id: str,
    file_type: str,
    output_path: str,
    timeout_seconds: int,
) -> Union[str, None]:

    if not API_URL or not API_KEY or not video_id:
        return None

    tmp = output_path + ".part"

    try:
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        pass

    timeout = aiohttp.ClientTimeout(
        total=timeout_seconds,
        connect=30,
        sock_connect=30,
        sock_read=120,
    )

    connector = aiohttp.TCPConnector(
        limit=20,
        limit_per_host=10,
        ttl_dns_cache=300,
    )

    try:
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            read_bufsize=DOWNLOAD_CHUNK_SIZE,
        ) as session:

            async with session.get(
                f"{API_URL}/download",
                params={
                    "url": video_id,
                    "type": file_type,
                    "api_key": API_KEY,
                },
                allow_redirects=True,
            ) as resp:

                if resp.status != 200:
                    return None

                content_type = (
                    resp.headers.get(
                        "content-type",
                        "",
                    ).lower()
                )

                if (
                    "application/json" in content_type
                    or "text/html" in content_type
                    or "text/plain" in content_type
                ):
                    return None

                with open(tmp, "wb") as file:

                    async for chunk in resp.content.iter_chunked(
                        DOWNLOAD_CHUNK_SIZE
                    ):
                        if chunk:
                            file.write(chunk)

        if (
            os.path.exists(tmp)
            and os.path.getsize(tmp) > 1024
        ):
            os.replace(tmp, output_path)
            return output_path

    except Exception:
        pass

    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass

    return None


# =========================================================
# AUDIO DOWNLOAD
# =========================================================

async def download_song(link: str) -> Union[str, None]:

    url = _clean_youtube_url(link)
    vid = _video_id(url)

    if not vid:
        return None

    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True,
    )

    output = os.path.join(
        DOWNLOAD_DIR,
        f"{vid}.mp3",
    )

    cached = [
        output,
        os.path.join(DOWNLOAD_DIR, f"{vid}.m4a"),
        os.path.join(DOWNLOAD_DIR, f"{vid}.webm"),
        os.path.join(DOWNLOAD_DIR, f"{vid}.opus"),
    ]

    for path in cached:
        if (
            os.path.exists(path)
            and os.path.getsize(path) > 1024
        ):
            return path

    # API FIRST
    result = await _api_download(
        vid,
        "audio",
        output,
        AUDIO_DOWNLOAD_TIMEOUT,
    )

    if result:
        return result

    # YT-DLP FALLBACK
    try:
        def run():
            base = os.path.join(
                DOWNLOAD_DIR,
                vid,
            )

            opts = {
                "format": "bestaudio/best",
                "outtmpl": base + ".%(ext)s",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 5,
                "fragment_retries": 5,
                "socket_timeout": 30,
                "concurrent_fragment_downloads": 4,
                "extractor_args": {
                    "youtube": {
                        "player_client": [
                            "android_vr",
                            "android",
                            "ios",
                            "mweb",
                        ],
                    },
                },
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            for ext in [
                ".m4a",
                ".webm",
                ".opus",
                ".mp3",
                ".aac",
                ".mp4",
            ]:
                path = base + ext

                if (
                    os.path.exists(path)
                    and os.path.getsize(path) > 1024
                ):
                    return path

            return None

        return await asyncio.to_thread(run)

    except Exception:
        return None


# =========================================================
# VIDEO DOWNLOAD
# =========================================================

async def download_video(link: str) -> Union[str, None]:

    url = _clean_youtube_url(link)
    vid = _video_id(url)

    if not vid:
        return None

    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True,
    )

    output = os.path.join(
        DOWNLOAD_DIR,
        f"{vid}.mp4",
    )

    if (
        os.path.exists(output)
        and os.path.getsize(output) > 1024
    ):
        return output

    # API FIRST
    result = await _api_download(
        vid,
        "video",
        output,
        VIDEO_DOWNLOAD_TIMEOUT,
    )

    if result:
        return result

    # YT-DLP FALLBACK
    try:
        def run():

            opts = {
                "format": (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                    "best[ext=mp4]/"
                    "best"
                ),
                "merge_output_format": "mp4",
                "outtmpl": output,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "retries": 5,
                "fragment_retries": 5,
                "socket_timeout": 30,
                "concurrent_fragment_downloads": 4,
                "extractor_args": {
                    "youtube": {
                        "player_client": [
                            "android_vr",
                            "android",
                            "ios",
                            "mweb",
                        ],
                    },
                },
            }

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            candidates = [
                output,
                os.path.join(DOWNLOAD_DIR, f"{vid}.mkv"),
                os.path.join(DOWNLOAD_DIR, f"{vid}.webm"),
            ]

            for path in candidates:
                if (
                    os.path.exists(path)
                    and os.path.getsize(path) > 1024
                ):
                    return path

            return None

        return await asyncio.to_thread(run)

    except Exception:
        return None


# =========================================================
# YOUTUBE API CLASS
# =========================================================

class YouTubeAPI:

    def __init__(self):

        self.base = (
            "https://www.youtube.com/watch?v="
        )

        self.status = (
            "https://www.youtube.com/oembed?url="
        )

        self.listbase = (
            "https://youtube.com/playlist?list="
        )

    async def exists(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        if videoid:
            return bool(
                re.fullmatch(
                    r"[\w-]{6,}",
                    str(link),
                )
            )

        return bool(_video_id(link))

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

            entities = (
                message.entities
                or message.caption_entities
                or []
            )

            for entity in entities:

                if entity.type == MessageEntityType.URL:

                    found = text[
                        entity.offset:
                        entity.offset + entity.length
                    ]

                    if _video_id(found):
                        return found

                elif (
                    entity.type
                    == MessageEntityType.TEXT_LINK
                    and entity.url
                    and _video_id(entity.url)
                ):
                    return entity.url

        return None

    async def _get_info(
        self,
        url: str,
        search_query: str = None,
    ):

        # Search query
        if search_query:

            info = await _search_single(
                str(search_query).strip()
            )

            if info:
                return info

        # Direct extraction
        try:
            info = await _extract_info(url)

            if info and not info.get("entries"):
                return info

        except Exception:
            pass

        # Search exact video ID
        video_id = _video_id(url)

        if video_id:

            try:
                results = await _search_youtube(
                    video_id,
                    10,
                )

                for item in results:
                    if str(item.get("id")) == video_id:
                        return item

            except Exception:
                pass

            # Last metadata fallback
            return await _oembed_info(video_id)

        return None

    async def details(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        url = (
            self.base + str(link)
            if videoid
            else _clean_youtube_url(link)
        )

        is_direct = bool(
            videoid
            or _video_id(link)
        )

        info = await self._get_info(
            url,
            None if is_direct else str(link),
        )

        if not info:
            raise ValueError(
                "YouTube track details could not be fetched"
            )

        vidid = (
            str(info.get("id") or "")
            or _video_id(url)
        )

        title = (
            info.get("title")
            or "Unknown Title"
        )

        duration_sec = int(
            info.get("duration") or 0
        )

        thumbnail = (
            info.get("thumbnail")
            or f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg"
        )

        return (
            title,
            _duration_text(duration_sec),
            duration_sec,
            thumbnail,
            vidid,
        )

    async def title(
        self,
        link,
        videoid=None,
    ):
        return (
            await self.details(link, videoid)
        )[0]

    async def duration(
        self,
        link,
        videoid=None,
    ):
        return (
            await self.details(link, videoid)
        )[1]

    async def thumbnail(
        self,
        link,
        videoid=None,
    ):
        return (
            await self.details(link, videoid)
        )[3]

    async def track(
        self,
        link: str,
        videoid: Union[bool, str] = None,
    ):

        url = (
            self.base + str(link)
            if videoid
            else _clean_youtube_url(link)
        )

        is_direct = bool(
            videoid
            or _video_id(link)
        )

        info = await self._get_info(
            url,
            None if is_direct else str(link),
        )

        if not info:
            raise ValueError(
                "YouTube track details could not be fetched"
            )

        vidid = (
            str(info.get("id") or "")
            or _video_id(url)
        )

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

        thumbnail = (
            info.get("thumbnail")
            or f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg"
        )

        return {
            "title": title,
            "link": f"https://www.youtube.com/watch?v={vidid}",
            "vidid": vidid,
            "duration_min": _duration_text(duration_sec),
            "duration_sec": duration_sec,
            "thumb": thumbnail,
        }, vidid

    async def video(
        self,
        link: str,
        videoid=None,
    ):

        url = (
            self.base + str(link)
            if videoid
            else _clean_youtube_url(link)
        )

        try:

            file_path = await download_video(url)

            if file_path:
                return 1, file_path

            return 0, "Video download failed"

        except Exception as error:
            return 0, f"Video download error: {error}"

    async def playlist(
        self,
        link,
        limit,
        user_id,
        videoid=None,
    ):

        if videoid:
            link = self.listbase + str(link)

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

    async def autoplay(
        self,
        videoid: str,
        title: str = "",
        max_duration: Union[int, None] = None,
        exclude_ids=None,
        exclude_titles=None,
    ):

        query = str(title or "").strip()

        if not query:
            return None

        excluded_ids = {
            str(x).strip()
            for x in (exclude_ids or [])
            if str(x).strip()
        }

        if videoid:
            excluded_ids.add(str(videoid))

        excluded_titles = {
            _normalize_title(x)
            for x in (exclude_titles or [])
            if _normalize_title(x)
        }

        excluded_titles.add(
            _normalize_title(query)
        )

        search_queries = [
            f"{query} similar song",
            f"{query} song",
            f"{query} music",
            "latest hindi songs official audio",
            "popular hindi songs",
            "popular punjabi songs",
            "latest punjabi songs",
            "popular english songs",
            "latest english songs",
        ]

        random.shuffle(search_queries)

        candidates = []

        for search_query in search_queries:

            entries = await _search_youtube(
                search_query,
                20,
            )

            for entry in entries:

                vid = str(
                    entry.get("id") or ""
                ).strip()

                song_title = str(
                    entry.get("title") or ""
                ).strip()

                if not vid or not song_title:
                    continue

                if vid in excluded_ids:
                    continue

                normalized = _normalize_title(
                    song_title
                )

                if (
                    not normalized
                    or normalized in excluded_titles
                ):
                    continue

                duration = int(
                    entry.get("duration") or 0
                )

                if duration <= 0:
                    continue

                if (
                    max_duration
                    and duration > int(max_duration)
                ):
                    continue

                candidates.append({
                    "id": vid,
                    "title": song_title,
                    "duration": duration,
                    "thumbnail": (
                        entry.get("thumbnail")
                        or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                    ),
                })

                excluded_ids.add(vid)
                excluded_titles.add(normalized)

        if not candidates:
            return None

        selected = random.choice(
            candidates
        )

        return {
            "title": selected["title"],
            "link": (
                "https://www.youtube.com/watch?v="
                f"{selected['id']}"
            ),
            "vidid": selected["id"],
            "duration_sec": selected["duration"],
            "duration_min": _duration_text(
                selected["duration"]
            ),
            "thumb": selected["thumbnail"],
        }

    async def get_related_videos(
        self,
        videoid: str,
        title: str = "",
        max_duration=None,
        exclude_ids=None,
        exclude_titles=None,
    ):

        return await self.autoplay(
            videoid=videoid,
            title=title,
            max_duration=max_duration,
            exclude_ids=exclude_ids,
            exclude_titles=exclude_titles,
        )

    async def search(self, query: str):
        return await self.track(query)

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid=None,
    ):

        entries = await _search_youtube(
            link,
            10,
        )

        if not entries:
            raise ValueError(
                "YouTube result not found"
            )

        if query_type >= len(entries):
            raise IndexError(
                "YouTube search result not found"
            )

        result = entries[query_type]

        vidid = result.get("id")

        duration = int(
            result.get("duration") or 0
        )

        thumb = (
            result.get("thumbnail")
            or f"https://i.ytimg.com/vi/{vidid}/hqdefault.jpg"
        )

        return (
            result.get(
                "title",
                "Unknown Title",
            ),
            _duration_text(duration),
            thumb,
            vidid,
        )

    async def formats(
        self,
        link: str,
        videoid=None,
    ):

        url = (
            self.base + str(link)
            if videoid
            else _clean_youtube_url(link)
        )

        try:

            result = await _extract_info(url)

            if not result:
                return [], url

            formats = []

            for fmt in (
                result.get("formats")
                or []
            ):

                formats.append({
                    "format": fmt.get("format"),
                    "filesize": fmt.get("filesize"),
                    "format_id": fmt.get("format_id"),
                    "ext": fmt.get("ext"),
                    "format_note": fmt.get(
                        "format_note"
                    ),
                    "yturl": url,
                })

            return formats, url

        except Exception:
            return [], url

    async def download(
        self,
        link: str,
        mystic,
        video=None,
        videoid=None,
        songaudio=None,
        songvideo=None,
        format_id=None,
        title=None,
    ):

        url = (
            self.base + str(link)
            if videoid
            else _clean_youtube_url(link)
        )

        try:

            if video:
                file_path = await download_video(url)
            else:
                file_path = await download_song(url)

            if file_path:
                return file_path, True

            return None, False

        except Exception:
            return None, False


YouTube = YouTubeAPI()
