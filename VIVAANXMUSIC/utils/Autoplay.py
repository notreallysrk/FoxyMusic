# ===========================================================
# AUTOPLAY HELPER - FIXED
# ===========================================================

import asyncio
import glob
import os
import random

import yt_dlp

try:
    from py_yt import VideosSearch
except ImportError:
    from youtubesearchpython import VideosSearch


_HISTORY_LIMIT = 50
_played_history: dict[int, list[str]] = {}


# ===========================================================
# HISTORY
# ===========================================================

def remember_played(chat_id: int, vidid: str):
    """Current played song ko history mein save kare."""
    if not chat_id or not vidid:
        return

    vidid = str(vidid).strip()

    if not vidid:
        return

    history = _played_history.setdefault(chat_id, [])

    if vidid in history:
        history.remove(vidid)

    history.append(vidid)

    if len(history) > _HISTORY_LIMIT:
        del history[:-_HISTORY_LIMIT]


def get_history(chat_id: int) -> list[str]:
    return _played_history.get(chat_id, [])


def clear_history(chat_id: int):
    _played_history.pop(chat_id, None)


# ===========================================================
# COOKIE
# ===========================================================

def _cookie_file():
    possible_folders = [
        os.path.join(os.getcwd(), "VIVAANXMUSIC", "assets"),
        os.path.join(os.getcwd(), "ShiviMusic", "assets"),
        os.path.join(os.getcwd(), "assets"),
    ]

    for folder in possible_folders:
        if not os.path.isdir(folder):
            continue

        files = []

        for pattern in ("*.txt", "*.cookies", "*.cookie"):
            files.extend(glob.glob(os.path.join(folder, pattern)))

        if files:
            return random.choice(files)

    return None


# ===========================================================
# VIDEO ID EXTRACTOR
# ===========================================================

def _extract_video_id(video):
    if not isinstance(video, dict):
        return None

    vidid = (
        video.get("id")
        or video.get("videoId")
        or video.get("video_id")
    )

    if not vidid:
        return None

    return str(vidid)


# ===========================================================
# NORMAL SEARCH CANDIDATES
# ===========================================================

def _extract_candidates(
    results,
    chat_id: int,
    skip_history: bool = False,
):
    candidates = []

    played = set()

    if not skip_history:
        played = set(get_history(chat_id))

    for video in results or []:

        if not isinstance(video, dict):
            continue

        vidid = _extract_video_id(video)

        title = (
            video.get("title")
            or video.get("name")
        )

        link = (
            video.get("link")
            or video.get("url")
        )

        if not link and vidid:
            link = f"https://www.youtube.com/watch?v={vidid}"

        duration = (
            video.get("duration")
            or video.get("duration_min")
            or "0:00"
        )

        if not vidid or not title or not link:
            continue

        if vidid in played:
            continue

        if str(duration).lower() in (
            "none",
            "live",
            "live now",
            "upcoming",
        ):
            continue

        thumbs = video.get("thumbnails") or []

        thumb = None

        if thumbs:

            first_thumb = thumbs[0]

            if isinstance(first_thumb, dict):
                thumb = first_thumb.get("url")

            elif isinstance(first_thumb, str):
                thumb = first_thumb

        if not thumb:
            thumb = (
                f"https://i.ytimg.com/vi/"
                f"{vidid}/hqdefault.jpg"
            )

        if thumb:
            thumb = thumb.split("?")[0]

        candidates.append(
            {
                "vidid": vidid,
                "id": vidid,
                "title": str(title),
                "link": str(link),
                "duration_min": str(duration),
                "duration": str(duration),
                "thumb": thumb,
                "thumbnail": thumb,
            }
        )

    return candidates


# ===========================================================
# YOUTUBE MIX
# ===========================================================

def _fetch_mix_sync(
    video_id: str,
    limit: int = 30,
):
    if not video_id:
        return []

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "playlistend": limit,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    cookiefile = _cookie_file()

    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    urls = [
        f"https://www.youtube.com/watch?v={video_id}&list=RD{video_id}",
        f"https://www.youtube.com/playlist?list=RD{video_id}",
    ]

    for url in urls:

        try:

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:

                info = ydl.extract_info(
                    url,
                    download=False,
                )

            entries = (
                (info or {}).get("entries")
                or []
            )

            entries = [
                entry
                for entry in entries
                if entry
            ]

            if entries:
                return entries

        except Exception as error:
            print(
                f"[AUTOPLAY MIX ERROR] "
                f"{type(error).__name__}: {error}"
            )

    return []


# ===========================================================
# MIX CANDIDATES
# ===========================================================

def _extract_mix_candidates(
    entries,
    chat_id: int,
    skip_history: bool = False,
):
    candidates = []

    played = set()

    if not skip_history:
        played = set(get_history(chat_id))

    for entry in entries or []:

        if not entry:
            continue

        if not isinstance(entry, dict):
            continue

        vidid = _extract_video_id(entry)

        title = (
            entry.get("title")
            or entry.get("fulltitle")
        )

        if not vidid or not title:
            continue

        if vidid in played:
            continue

        duration = entry.get("duration")

        if isinstance(
            duration,
            (int, float),
        ):
            minutes, seconds = divmod(
                int(duration),
                60,
            )

            duration_min = (
                f"{minutes}:{seconds:02d}"
            )

        elif duration:
            duration_min = str(duration)

        else:
            # Unknown duration ko allow karo,
            # lekin Live entries ko nahi
            duration_min = "0:00"

        webpage_url = (
            entry.get("webpage_url")
            or entry.get("url")
        )

        if (
            not webpage_url
            or not str(webpage_url).startswith("http")
        ):
            webpage_url = (
                f"https://www.youtube.com/"
                f"watch?v={vidid}"
            )

        thumb = (
            entry.get("thumbnail")
            or entry.get("thumbnail_url")
            or f"https://i.ytimg.com/vi/"
               f"{vidid}/hqdefault.jpg"
        )

        candidates.append(
            {
                "vidid": vidid,
                "id": vidid,
                "title": str(title),
                "link": webpage_url,
                "duration_min": duration_min,
                "duration": duration_min,
                "thumb": thumb,
                "thumbnail": thumb,
            }
        )

    return candidates


# ===========================================================
# FETCH MIX
# ===========================================================

async def _fetch_mix_candidates(
    chat_id: int,
    seed_vidid: str,
):
    if not seed_vidid:
        return []

    loop = asyncio.get_running_loop()

    try:

        entries = await loop.run_in_executor(
            None,
            _fetch_mix_sync,
            seed_vidid,
            30,
        )

    except Exception as error:

        print(
            f"[AUTOPLAY MIX ERROR] "
            f"{type(error).__name__}: {error}"
        )

        return []

    candidates = _extract_mix_candidates(
        entries,
        chat_id,
        skip_history=False,
    )

    if candidates:
        return candidates

    # History ki wajah se sab songs skip hue hon
    # to history reset karke dobara candidates lo.
    if entries:

        clear_history(chat_id)

        candidates = _extract_mix_candidates(
            entries,
            chat_id,
            skip_history=True,
        )

    return candidates


# ===========================================================
# TEXT SEARCH FALLBACK
# ===========================================================

async def _search_fallback(
    chat_id: int,
    seed_title: str,
):
    if not seed_title:
        return None

    query = str(seed_title).strip()

    if not query:
        return None

    try:

        search = VideosSearch(
            query,
            limit=30,
        )

        data = await search.next()

        if isinstance(data, dict):
            results = data.get("result") or []
        else:
            results = []

    except Exception as error:

        print(
            f"[AUTOPLAY SEARCH ERROR] "
            f"{type(error).__name__}: {error}"
        )

        return None

    candidates = _extract_candidates(
        results,
        chat_id,
        skip_history=False,
    )

    if not candidates and results:

        clear_history(chat_id)

        candidates = _extract_candidates(
            results,
            chat_id,
            skip_history=True,
        )

    if not candidates:
        return None

    return random.choice(candidates)


# ===========================================================
# MAIN AUTOPLAY FUNCTION
# ===========================================================

async def fetch_autoplay_track(
    chat_id: int,
    seed_title: str,
    seed_vidid: str = None,
):
    """
    1. YouTube Mix / Radio try karta hai.
    2. Current song jaisi category ke songs leta hai.
    3. Played songs repeat nahi karta.
    4. Mix fail ho to title search fallback.
    5. History exhaust hone par reset karke autoplay continue karta hai.
    """

    # -------------------------------
    # FIRST: YouTube Mix
    # -------------------------------

    if seed_vidid:

        mix_candidates = (
            await _fetch_mix_candidates(
                chat_id,
                str(seed_vidid),
            )
        )

        if mix_candidates:

            track = random.choice(
                mix_candidates
            )

            return track

    # -------------------------------
    # SECOND: Title Search Fallback
    # -------------------------------

    return await _search_fallback(
        chat_id,
        seed_title,
    )


# ===========================================================
# COMPATIBILITY ALIASES
# ===========================================================

get_autoplay_track = fetch_autoplay_track


def clear_autoplay_history(
    chat_id: int,
):
    clear_history(chat_id)
