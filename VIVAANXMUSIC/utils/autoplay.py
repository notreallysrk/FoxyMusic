# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 🚀
#
# This source code is under MIT License 📜
# ===========================================================

import asyncio
import glob
import os
import random
import re

import yt_dlp
from py_yt import VideosSearch


# =========================================================
# PER-CHAT PLAY HISTORY
# =========================================================

_HISTORY_LIMIT = 50

_played_history: dict[int, list[str]] = {}
_played_titles: dict[int, list[str]] = {}


def _norm_title(value: str) -> str:
    value = str(value or "").lower()

    value = re.sub(
        r"\([^)]*\)|\[[^]]*\]",
        " ",
        value,
    )

    value = re.sub(
        r"\b("
        r"official|video|audio|lyrics|lyric|full|song|music|"
        r"hd|4k|remastered|version|visualizer|status"
        r")\b",
        " ",
        value,
    )

    return re.sub(
        r"[^a-z0-9]+",
        "",
        value,
    )


def remember_played(
    chat_id: int,
    vidid: str,
    title: str = "",
):
    chat_id = int(chat_id)

    vidid = str(vidid or "").strip()

    if vidid:
        hist = _played_history.setdefault(
            chat_id,
            [],
        )

        if vidid in hist:
            hist.remove(vidid)

        hist.append(vidid)

        if len(hist) > _HISTORY_LIMIT:
            del hist[
                : len(hist) - _HISTORY_LIMIT
            ]

    normalized = _norm_title(title)

    if normalized:
        titles = _played_titles.setdefault(
            chat_id,
            [],
        )

        if normalized in titles:
            titles.remove(normalized)

        titles.append(normalized)

        if len(titles) > _HISTORY_LIMIT:
            del titles[
                : len(titles) - _HISTORY_LIMIT
            ]


def _history(chat_id: int) -> list:
    return _played_history.get(
        int(chat_id),
        [],
    )


def _title_history(chat_id: int) -> list:
    return _played_titles.get(
        int(chat_id),
        [],
    )


def clear_history(chat_id: int):
    chat_id = int(chat_id)

    _played_history.pop(
        chat_id,
        None,
    )

    _played_titles.pop(
        chat_id,
        None,
    )


# =========================================================
# NORMAL YOUTUBE SEARCH CANDIDATES
# =========================================================

def _extract_candidates(
    results,
    chat_id: int,
    skip_history: bool,
):
    candidates = []

    played = (
        set()
        if skip_history
        else set(_history(chat_id))
    )

    played_titles = (
        set()
        if skip_history
        else set(_title_history(chat_id))
    )

    for video in results:
        if not video:
            continue

        vidid = str(
            video.get("id") or ""
        ).strip()

        title = str(
            video.get("title") or ""
        ).strip()

        link = video.get("link")
        duration = video.get("duration")

        if not (
            vidid
            and title
            and link
            and duration
        ):
            continue

        if vidid in played:
            continue

        normalized_title = _norm_title(title)

        if (
            normalized_title
            and normalized_title in played_titles
        ):
            continue

        thumbs = (
            video.get("thumbnails")
            or []
        )

        thumb = None

        if thumbs:
            thumb = (
                thumbs[0]
                .get("url", "")
                .split("?")[0]
            )

        candidates.append(
            {
                "vidid": vidid,
                "title": title,
                "link": link,
                "duration_min": duration,
                "thumb": thumb,
            }
        )

    return candidates


# =========================================================
# YOUTUBE MIX / RADIO PLAYLIST
# =========================================================

def _cookie_file():
    folder = os.path.join(
        os.getcwd(),
        "ShiviMusic",
        "assets",
    )

    txt_files = glob.glob(
        os.path.join(
            folder,
            "*.txt",
        )
    )

    if not txt_files:
        return None

    return random.choice(txt_files)


def _fetch_mix_sync(
    video_id: str,
    limit: int = 20,
) -> list:

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "playlistend": limit,
        "no_warnings": True,
    }

    cookiefile = _cookie_file()

    if cookiefile:
        ydl_opts[
            "cookiefile"
        ] = cookiefile

    url = (
        f"https://www.youtube.com/"
        f"watch?v={video_id}"
        f"&list=RD{video_id}"
    )

    with yt_dlp.YoutubeDL(
        ydl_opts
    ) as ydl:

        info = ydl.extract_info(
            url,
            download=False,
        )

    return (
        info or {}
    ).get(
        "entries"
    ) or []


def _extract_mix_candidates(
    entries,
    chat_id: int,
    skip_history: bool,
):
    candidates = []

    played = (
        set()
        if skip_history
        else set(_history(chat_id))
    )

    played_titles = (
        set()
        if skip_history
        else set(_title_history(chat_id))
    )

    for e in entries or []:
        if not e:
            continue

        vidid = str(
            e.get("id") or ""
        ).strip()

        title = str(
            e.get("title") or ""
        ).strip()

        if not (
            vidid
            and title
        ):
            continue

        if vidid in played:
            continue

        normalized_title = _norm_title(title)

        if (
            normalized_title
            and normalized_title
            in played_titles
        ):
            continue

        duration = e.get(
            "duration"
        )

        if isinstance(
            duration,
            (int, float),
        ):
            m, s = divmod(
                int(duration),
                60,
            )

            duration_min = (
                f"{m}:{s:02d}"
            )

        else:
            duration_min = (
                str(duration)
                if duration
                else "Live"
            )

        candidates.append(
            {
                "vidid": vidid,
                "title": title,
                "link": (
                    f"https://www.youtube.com/"
                    f"watch?v={vidid}"
                ),
                "duration_min": duration_min,
                "thumb": (
                    e.get("thumbnail")
                    or
                    f"https://i.ytimg.com/"
                    f"vi/{vidid}/hqdefault.jpg"
                ),
            }
        )

    return candidates


async def _fetch_mix_candidates(
    chat_id: int,
    seed_vidid: str,
) -> list:

    loop = asyncio.get_running_loop()

    try:
        entries = await loop.run_in_executor(
            None,
            _fetch_mix_sync,
            seed_vidid,
            20,
        )

    except Exception as e:
        print(
            f"[AUTOPLAY MIX ERROR] {e}"
        )

        return []

    return _extract_mix_candidates(
        entries,
        chat_id,
        skip_history=False,
    )


# =========================================================
# MAIN AUTOPLAY
# =========================================================

async def fetch_autoplay_track(
    chat_id: int,
    seed_title: str,
    seed_vidid: str = None,
):
    """
    Primary:
        YouTube Mix / Radio playlist.

    Fallback:
        Current song title search.

    Protection:
        Same recent video aur same title repeat
        nahi hoga.
    """

    chat_id = int(chat_id)

    seed_vidid = str(
        seed_vidid or ""
    ).strip()

    seed_title = str(
        seed_title or ""
    ).strip()

    # Current song ko history me save karo
    if seed_vidid:
        remember_played(
            chat_id,
            seed_vidid,
            seed_title,
        )

    # =====================================================
    # PRIMARY: YOUTUBE MIX
    # =====================================================

    if seed_vidid:
        mix_candidates = (
            await _fetch_mix_candidates(
                chat_id,
                seed_vidid,
            )
        )

        if mix_candidates:
            track = random.choice(
                mix_candidates
            )

            remember_played(
                chat_id,
                track.get("vidid"),
                track.get("title"),
            )

            return track

    # =====================================================
    # FALLBACK: TITLE SEARCH
    # =====================================================

    if not seed_title:
        return None

    queries = [
        seed_title,
        f"{seed_title} official audio",
        f"{seed_title} full song",
    ]

    for query in queries:

        try:
            search = VideosSearch(
                query,
                limit=20,
            )

            data = await search.next()

            results = (
                data.get(
                    "result",
                    [],
                )
                if isinstance(
                    data,
                    dict,
                )
                else []
            )

        except Exception as e:
            print(
                f"[AUTOPLAY SEARCH ERROR] {e}"
            )

            continue

        if not results:
            continue

        candidates = _extract_candidates(
            results,
            chat_id,
            skip_history=False,
        )

        if candidates:
            track = random.choice(
                candidates
            )

            remember_played(
                chat_id,
                track.get("vidid"),
                track.get("title"),
            )

            return track

    # =====================================================
    # LAST FALLBACK
    # =====================================================

    # History clear karke current search se koi song lo.
    # Isse autoplay completely stall nahi hoga.
    clear_history(chat_id)

    if seed_vidid:
        remember_played(
            chat_id,
            seed_vidid,
            seed_title,
        )

    try:
        search = VideosSearch(
            seed_title,
            limit=20,
        )

        data = await search.next()

        results = (
            data.get(
                "result",
                [],
            )
            if isinstance(
                data,
                dict,
            )
            else []
        )

        candidates = _extract_candidates(
            results,
            chat_id,
            skip_history=False,
        )

        if candidates:
            track = random.choice(
                candidates
            )

            remember_played(
                chat_id,
                track.get("vidid"),
                track.get("title"),
            )

            return track

    except Exception as e:
        print(
            f"[AUTOPLAY LAST FALLBACK ERROR] {e}"
        )

    return None


# ===========================================================
# ©️ 2025-26 All Rights Reserved by Purvi Bots (Im-Notcoder) 😎
# ===========================================================
