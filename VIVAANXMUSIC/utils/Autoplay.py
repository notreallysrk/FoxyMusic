import asyncio
from collections import defaultdict, deque

from VIVAANXMUSIC import YouTube

_played_tracks = defaultdict(lambda: deque(maxlen=50))


def remember_played(chat_id: int, videoid: str):
    videoid = str(videoid or "").strip()
    if not videoid:
        return
    history = _played_tracks[int(chat_id)]
    try:
        history.remove(videoid)
    except ValueError:
        pass
    history.append(videoid)


def get_played_tracks(chat_id: int):
    return set(_played_tracks.get(int(chat_id), []))


async def fetch_autoplay_track(chat_id: int, seed_title: str, seed_vidid: str = None, max_duration=None):
    """Return a different, not-recently-played YouTube track."""
    chat_id = int(chat_id)
    seed_vidid = str(seed_vidid or "").strip()
    seed_title = str(seed_title or "").strip() or seed_vidid

    if seed_vidid:
        remember_played(chat_id, seed_vidid)
    if not seed_title:
        return None

    played = get_played_tracks(chat_id)
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
                )
            except TypeError:
                track = await YouTube.autoplay(seed_vidid, query, max_duration=max_duration)
            except Exception:
                track = None

            if not track:
                break

            vidid = str(track.get("vidid") or "").strip()
            if vidid and vidid != seed_vidid and vidid not in played:
                remember_played(chat_id, vidid)
                return track

            if vidid:
                played.add(vidid)
            else:
                break

    return None


def clear_autoplay_history(chat_id: int):
    _played_tracks.pop(int(chat_id), None)
    
