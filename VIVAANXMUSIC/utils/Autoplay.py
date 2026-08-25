import asyncio
from collections import defaultdict, deque

from VIVAANXMUSIC import YouTube


# Har chat ke last played video IDs
_played_tracks = defaultdict(lambda: deque(maxlen=30))


def remember_played(chat_id: int, videoid: str):
    """Remember played track so autoplay does not repeat it."""

    if not videoid:
        return

    videoid = str(videoid).strip()

    if not videoid:
        return

    history = _played_tracks[int(chat_id)]

    # Already exists to duplicate mat rakho
    try:
        history.remove(videoid)
    except ValueError:
        pass

    history.append(videoid)


def get_played_tracks(chat_id: int):
    return set(_played_tracks.get(int(chat_id), []))


async def fetch_autoplay_track(
    chat_id: int,
    seed_title: str,
    seed_vidid: str = None,
):
    """
    Get a NEW autoplay track.

    Current song, already played songs aur invalid tracks skip karega.
    """

    chat_id = int(chat_id)

    if seed_vidid:
        remember_played(chat_id, seed_vidid)

    played = get_played_tracks(chat_id)

    seed_title = str(seed_title or "").strip()
    seed_vidid = str(seed_vidid or "").strip()

    if not seed_title:
        seed_title = seed_vidid

    if not seed_title:
        return None

    # Multiple attempts with different queries
    queries = [
        seed_title,
        f"{seed_title} official audio",
        f"{seed_title} music",
    ]

    for query in queries:
        try:
            # YouTube.autoplay currently same-song filter karta hai.
            # Hum history bhi pass/validate karenge.
            track = await YouTube.autoplay(
                seed_vidid,
                query,
            )

            if (
                track
                and track.get("vidid")
                and track["vidid"] not in played
                and track["vidid"] != seed_vidid
            ):
                return track

        except Exception:
            continue

    # History clear karke ek baar retry
    # Lekin current song ko still repeat nahi karenge
    history = _played_tracks.get(chat_id)

    if history:
        history.clear()

    if seed_vidid:
        remember_played(chat_id, seed_vidid)

    try:
        track = await YouTube.autoplay(
            seed_vidid,
            seed_title,
        )

        if (
            track
            and track.get("vidid")
            and track["vidid"] != seed_vidid
        ):
            return track

    except Exception:
        pass

    return None


def clear_autoplay_history(chat_id: int):
    """Clear autoplay history when needed."""
    _played_tracks.pop(int(chat_id), None)
