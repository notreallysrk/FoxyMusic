"""
Autoplay helper - fixed for VIVAANXMUSIC.

Primary:
    YouTube Mix / Radio playlist (RD + videoID)

Fallback:
    YouTube title search

Features:
    - Per-chat history prevents repeat songs.
    - Mix extraction retries on temporary errors.
    - Search fallback if Mix fails.
    - Returns ALL candidates so call.py can try each one.
    - History resets only when all available candidates are exhausted.
    - No autoplay track-count limit.
"""

import asyncio
import glob
import os
import random

import yt_dlp
from youtubesearchpython import VideosSearch

from VIVAANXMUSIC.logging import LOGGER


_HISTORY_LIMIT = 50
_played_history: dict[int, list[str]] = {}


# ===========================================================
# LOGGER
# ===========================================================

def _logger():
    try:
        return LOGGER(__name__)
    except Exception:
        import logging
        return logging.getLogger(__name__)


# ===========================================================
# HISTORY
# ===========================================================

def remember_played(chat_id: int, vidid: str):
    """Save a played/autoplayed video ID in per-chat history."""

    if not chat_id or not vidid:
        return

    vidid = str(vidid).strip()

    if not vidid:
        return

    hist = _played_history.setdefault(chat_id, [])

    if vidid in hist:
        hist.remove(vidid)

    hist.append(vidid)

    if len(hist) > _HISTORY_LIMIT:
        del hist[:-_HISTORY_LIMIT]


def _history(chat_id: int) -> list[str]:
    return _played_history.get(chat_id, [])


def clear_history(chat_id: int):
    """Clear autoplay history for a chat."""
    _played_history.pop(chat_id, None)


# ===========================================================
# COOKIE
# ===========================================================

def _cookie_file():
    """
    Find cookies files.

    Supports:
        VIVAANXMUSIC/assets
        SWAGGYMUSIC/assets
        ShiviMusic/assets
        assets
    """

    folders = [
        os.path.join(os.getcwd(), "VIVAANXMUSIC", "assets"),
        os.path.join(os.getcwd(), "SWAGGYMUSIC", "assets"),
        os.path.join(os.getcwd(), "ShiviMusic", "assets"),
        os.path.join(os.getcwd(), "assets"),
    ]

    files = []

    for folder in folders:

        if not os.path.isdir(folder):
            continue

        files.extend(
            glob.glob(os.path.join(folder, "*.txt"))
        )

        files.extend(
            glob.glob(os.path.join(folder, "*.cookies"))
        )

        files.extend(
            glob.glob(os.path.join(folder, "*.cookie"))
        )

    if not files:
        return None

    return random.choice(files)


# ===========================================================
# MIX EXTRACTION
# ===========================================================

def _fetch_mix_sync(
    video_id: str,
    limit: int = 30,
) -> list:

    if not video_id:
        return []

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "playlistend": limit,
        "no_warnings": True,
        "ignoreerrors": True,
        "noplaylist": False,
    }

    cookiefile = _cookie_file()

    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    urls = [
        (
            "https://www.youtube.com/"
            f"watch?v={video_id}&list=RD{video_id}"
        ),
        (
            "https://www.youtube.com/"
            f"playlist?list=RD{video_id}"
        ),
    ]

    last_error = None

    for url in urls:

        try:

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

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

            last_error = error

    if last_error:
        raise last_error

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
        played = set(
            _history(chat_id)
        )

    seen = set()

    for entry in entries or []:

        if not entry:
            continue

        if not isinstance(entry, dict):
            continue

        vidid = (
            entry.get("id")
            or entry.get("video_id")
            or entry.get("videoId")
        )

        title = (
            entry.get("title")
            or entry.get("fulltitle")
        )

        if not vidid or not title:
            continue

        vidid = str(vidid).strip()

        if not vidid:
            continue

        # Duplicate Mix entries avoid karo.
        if vidid in seen:
            continue

        seen.add(vidid)

        # Current/already played song avoid karo.
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

            duration_min = "0:00"

        link = (
            entry.get("webpage_url")
            or entry.get("url")
        )

        if (
            not link
            or not str(link).startswith("http")
        ):

            link = (
                "https://www.youtube.com/"
                f"watch?v={vidid}"
            )

        thumb = (
            entry.get("thumbnail")
            or entry.get("thumbnail_url")
            or (
                "https://i.ytimg.com/vi/"
                f"{vidid}/hqdefault.jpg"
            )
        )

        candidate = {
            "id": vidid,
            "vidid": vidid,
            "title": str(title),
            "link": str(link),
            "duration": duration_min,
            "duration_min": duration_min,
            "thumb": thumb,
            "thumbnail": thumb,
        }

        candidates.append(
            candidate
        )

    return candidates


# ===========================================================
# FETCH YOUTUBE MIX
# ===========================================================

async def _fetch_mix_candidates(
    chat_id: int,
    seed_vidid: str,
) -> list:

    if not seed_vidid:
        return []

    logger = _logger()

    loop = asyncio.get_running_loop()

    last_error = None
    last_entries = []

    for attempt in range(2):

        try:

            entries = await loop.run_in_executor(
                None,
                _fetch_mix_sync,
                seed_vidid,
                30,
            )

            last_entries = entries or []

            candidates = (
                _extract_mix_candidates(
                    last_entries,
                    chat_id,
                    skip_history=False,
                )
            )

            if candidates:
                return candidates

            # Mix mila, lekin sab songs history mein hain.
            # History reset karke same Mix ko dobara use karo.
            if last_entries:

                logger.info(
                    f"[AUTOPLAY MIX] "
                    f"history exhausted for chat {chat_id}, "
                    f"resetting history"
                )

                clear_history(chat_id)

                candidates = (
                    _extract_mix_candidates(
                        last_entries,
                        chat_id,
                        skip_history=True,
                    )
                )

                if candidates:
                    return candidates

            # Empty Mix par retry.
            if attempt == 0:

                logger.warning(
                    f"[AUTOPLAY MIX] empty Mix for "
                    f"{seed_vidid}, retrying"
                )

                await asyncio.sleep(1)

                continue

            return []

        except Exception as error:

            last_error = error

            logger.warning(
                f"[AUTOPLAY MIX] attempt "
                f"{attempt + 1}/2 failed for "
                f"{seed_vidid}: "
                f"{type(error).__name__}: {error}"
            )

            if attempt == 0:
                await asyncio.sleep(1)

    if last_error:

        logger.warning(
            f"[AUTOPLAY MIX] giving up for "
            f"{seed_vidid}: "
            f"{type(last_error).__name__}"
        )

    return []


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
        played = set(
            _history(chat_id)
        )

    seen = set()

    for video in results or []:

        if not isinstance(video, dict):
            continue

        vidid = (
            video.get("id")
            or video.get("videoId")
            or video.get("video_id")
        )

        title = (
            video.get("title")
            or video.get("name")
        )

        link = (
            video.get("link")
            or video.get("url")
        )

        duration = (
            video.get("duration")
            or video.get("duration_min")
        )

        if not vidid or not title:
            continue

        vidid = str(vidid).strip()

        if not vidid:
            continue

        if vidid in seen:
            continue

        seen.add(vidid)

        if vidid in played:
            continue

        # Live/upcoming autoplay mein avoid.
        if isinstance(duration, str):

            if duration.lower() in {
                "live",
                "live now",
                "upcoming",
            }:
                continue

        if not duration:
            duration = "0:00"

        if not link:

            link = (
                "https://www.youtube.com/"
                f"watch?v={vidid}"
            )

        thumbs = (
            video.get("thumbnails")
            or []
        )

        thumb = None

        if thumbs:

            first_thumb = thumbs[0]

            if isinstance(
                first_thumb,
                dict,
            ):

                thumb = (
                    first_thumb.get("url")
                )

            elif isinstance(
                first_thumb,
                str,
            ):

                thumb = first_thumb

        if not thumb:

            thumb = (
                "https://i.ytimg.com/vi/"
                f"{vidid}/hqdefault.jpg"
            )

        if thumb:
            thumb = thumb.split("?")[0]

        candidate = {
            "id": vidid,
            "vidid": vidid,
            "title": str(title),
            "link": str(link),
            "duration": str(duration),
            "duration_min": str(duration),
            "thumb": thumb,
            "thumbnail": thumb,
        }

        candidates.append(
            candidate
        )

    return candidates


# ===========================================================
# SEARCH FALLBACK
# ===========================================================

async def _fetch_search_candidates(
    chat_id: int,
    seed_title: str,
) -> list:

    if not seed_title:
        return []

    logger = _logger()

    try:

        search = VideosSearch(
            str(seed_title),
            limit=30,
        )

        data = await search.next()

        results = (
            data.get("result", [])
            if isinstance(data, dict)
            else []
        )

    except Exception as error:

        logger.warning(
            f"[AUTOPLAY SEARCH] failed for "
            f"'{seed_title}': "
            f"{type(error).__name__}: {error}"
        )

        return []

    candidates = _extract_candidates(
        results,
        chat_id,
        skip_history=False,
    )

    if candidates:
        return candidates

    # Search results hain, lekin history mein sab aa chuke hain.
    if results:

        clear_history(chat_id)

        candidates = _extract_candidates(
            results,
            chat_id,
            skip_history=True,
        )

    return candidates


# ===========================================================
# MAIN AUTOPLAY FUNCTION
# ===========================================================

async def fetch_autoplay_track(
    chat_id: int,
    seed_title: str,
    seed_vidid: str = None,
) -> list:
    """
    Return ALL available autoplay candidates.

    Primary:
        YouTube Mix / Radio

    Fallback:
        YouTube title search

    call.py ko returned list ke har candidate ko try karna
    chahiye. Download fail ho to next candidate try karo.
    """

    logger = _logger()

    # -------------------------------------------------------
    # PRIMARY: YouTube Mix
    # -------------------------------------------------------

    if seed_vidid:

        candidates = (
            await _fetch_mix_candidates(
                chat_id,
                str(seed_vidid),
            )
        )

        if candidates:

            random.shuffle(
                candidates
            )

            return candidates

        logger.info(
            f"[AUTOPLAY] Mix empty for "
            f"{seed_vidid}; using search fallback"
        )

    # -------------------------------------------------------
    # FALLBACK: Title Search
    # -------------------------------------------------------

    if not seed_title:
        return []

    candidates = (
        await _fetch_search_candidates(
            chat_id,
            seed_title,
        )
    )

    if candidates:

        random.shuffle(
            candidates
        )

    return candidates


# ===========================================================
# BACKWARD COMPATIBILITY
# ===========================================================

async def fetch_autoplay_track_one(
    chat_id: int,
    seed_title: str,
    seed_vidid: str = None,
):
    """
    Old code compatibility.

    Returns:
        dict -> one track
        None -> no candidate
    """

    candidates = await fetch_autoplay_track(
        chat_id,
        seed_title,
        seed_vidid,
    )

    if not candidates:
        return None

    return candidates[0]


async def get_autoplay_track(
    chat_id: int,
    seed_title: str,
    seed_vidid: str = None,
):
    """
    Alias for old call.py versions.
    """

    return await fetch_autoplay_track_one(
        chat_id,
        seed_title,
        seed_vidid,
    )


def clear_autoplay_history(
    chat_id: int,
):
    clear_history(chat_id)
