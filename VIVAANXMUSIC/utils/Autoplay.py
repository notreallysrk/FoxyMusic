import asyncio
from collections import defaultdict, deque
import re

from VIVAANXMUSIC import YouTube

_played_tracks = defaultdict(lambda: deque(maxlen=50))
_played_titles = defaultdict(lambda: deque(maxlen=50))


def _norm_title(value: str) -> str:
    value = str(value or "").lower()
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value)
    value = re.sub(r"\b(official|video|audio|lyrics|lyric|full|song|music|hd|4k)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", "", value)


def remember_played(chat_id: int, videoid: str, title: str = ""):
    videoid = str(videoid or "").strip()
    if not videoid:
        return
    history = _played_tracks[int(chat_id)]
    try:
        history.remove(videoid)
    except ValueError:
        pass
    history.append(videoid)
    norm = _norm_title(title)
    if norm:
        titles = _played_titles[int(chat_id)]
        try:
            titles.remove(norm)
        except ValueError:
            pass
        titles.append(norm)


def get_played_tracks(chat_id: int):
    return set(_played_tracks.get(int(chat_id), []))


async def fetch_autoplay_track(chat_id: int, seed_title: str, seed_vidid: str = None, max_duration=None):
    """Return a different, not-recently-played YouTube track."""
    chat_id = int(chat_id)
    seed_vidid = str(seed_vidid or "").strip()
    seed_title = str(seed_title or "").strip() or seed_vidid

    if seed_vidid:
        remember_played(chat_id, seed_vidid, seed_title)
    if not seed_title:
        return None

    played = get_played_tracks(chat_id)
    played_titles = set(_played_titles.get(chat_id, []))
    seed_norm = _norm_title(seed_title)
    if seed_norm:
        played_titles.add(seed_norm)
    queries = [
        seed_title,
        f"{seed_title} song",
        f"{seed_title} official audio",
        f"{seed_title} music",
    ]

    for query in queries:
        for _ in range(3):
            try:
                track = await YouTube.autoplay(
                    seed_vidid,
                    query,
                    max_duration=max_duration,
                    exclude_ids=played,
                    exclude_titles=played_titles,
                )
            except TypeError:
                track = await YouTube.autoplay(seed_vidid, query, max_duration=max_duration)
            except Exception:
                track = None

            if not track:
                break

            vidid = str(track.get("vidid") or "").strip()
            if vidid and vidid != seed_vidid and vidid not in played:
                candidate_title = _norm_title(track.get("title") or "")
                if candidate_title and candidate_title in played_titles:
                    played.add(vidid)
                    continue
                remember_played(chat_id, vidid, track.get("title") or "")
                return track

            if vidid:
                played.add(vidid)
            else:
                break

    return None


def clear_autoplay_history(chat_id: int):
    _played_tracks.pop(int(chat_id), None)
    _played_titles.pop(int(chat_id), None)
                               
