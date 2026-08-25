import re
from collections import defaultdict, deque

from VIVAANXMUSIC import YouTube


# Har chat ke recent played songs
_played_tracks = defaultdict(lambda: deque(maxlen=50))
_played_titles = defaultdict(lambda: deque(maxlen=50))


def _norm_title(value: str) -> str:
    """Compare titles safely."""
    value = str(value or "").lower().strip()

    # Remove bracket content
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value)

    # Remove common YouTube suffix words
    value = re.sub(
        r"\b("
        r"official|video|audio|lyrics|lyric|full|song|music|"
        r"hd|4k|remastered|version|visualizer|mv"
        r")\b",
        " ",
        value,
    )

    # Keep only comparable characters
    return re.sub(r"[^a-z0-9]+", "", value)


def _track_id(track):
    """Get YouTube video ID from different result formats."""
    if not isinstance(track, dict):
        return ""

    return str(
        track.get("vidid")
        or track.get("video_id")
        or track.get("id")
        or track.get("videoId")
        or ""
    ).strip()


def _track_title(track):
    """Get title safely."""
    if not isinstance(track, dict):
        return ""

    return str(
        track.get("title")
        or track.get("name")
        or track.get("track")
        or ""
    ).strip()


def remember_played(chat_id: int, videoid: str, title: str = ""):
    """Remember played track and normalized title."""
    chat_id = int(chat_id)
    videoid = str(videoid or "").strip()

    if videoid:
        history = _played_tracks[chat_id]

        try:
            history.remove(videoid)
        except ValueError:
            pass

        history.append(videoid)

    norm_title = _norm_title(title)

    if norm_title:
        titles = _played_titles[chat_id]

        try:
            titles.remove(norm_title)
        except ValueError:
            pass

        titles.append(norm_title)


def get_played_tracks(chat_id: int):
    return set(_played_tracks.get(int(chat_id), []))


def get_played_titles(chat_id: int):
    return set(_played_titles.get(int(chat_id), []))


def is_already_played(
    chat_id: int,
    videoid: str,
    title: str = "",
) -> bool:
    """Check both ID and title history."""
    chat_id = int(chat_id)

    videoid = str(videoid or "").strip()
    title = _norm_title(title)

    if videoid and videoid in _played_tracks.get(chat_id, []):
        return True

    if title and title in _played_titles.get(chat_id, []):
        return True

    return False


async def _get_autoplay_result(
    seed_vidid: str,
    query: str,
    max_duration,
    exclude_ids,
    exclude_titles,
):
    """
    Get autoplay result.
    First try advanced arguments.
    If Youtube.py does not support them, use fallback.
    """

    try:
        return await YouTube.autoplay(
            seed_vidid,
            query,
            max_duration=max_duration,
            exclude_ids=list(exclude_ids),
            exclude_titles=list(exclude_titles),
        )

    except TypeError:
        try:
            return await YouTube.autoplay(
                seed_vidid,
                query,
                max_duration=max_duration,
            )
        except TypeError:
            return await YouTube.autoplay(
                seed_vidid,
                query,
            )

    except Exception:
        return None


async def fetch_autoplay_track(
    chat_id: int,
    seed_title: str,
    seed_vidid: str = None,
    max_duration=None,
):
    """
    Find a different song.

    Important:
    - Current song excluded
    - Last 50 played IDs excluded
    - Last 50 normalized titles excluded
    - Repeated results are rejected
    """

    chat_id = int(chat_id)

    seed_vidid = str(seed_vidid or "").strip()
    seed_title = str(seed_title or "").strip()

    if not seed_title:
        seed_title = seed_vidid

    # Current song must be remembered immediately
    if seed_vidid:
        remember_played(
            chat_id,
            seed_vidid,
            seed_title,
        )

    if not seed_title:
        return None

    played_ids = get_played_tracks(chat_id)
    played_titles = get_played_titles(chat_id)

    # Explicitly exclude seed/current song
    if seed_vidid:
        played_ids.add(seed_vidid)

    seed_norm = _norm_title(seed_title)

    if seed_norm:
        played_titles.add(seed_norm)

    # Try related searches, but never accept same song
    queries = [
        seed_title,
        f"{seed_title} song",
        f"{seed_title} music",
        f"{seed_title} official audio",
        f"{seed_title} lyrics",
    ]

    # Prevent same result from being repeatedly returned
    attempted_ids = set()

    for query in queries:

        for _ in range(10):

            track = await _get_autoplay_result(
                seed_vidid=seed_vidid,
                query=query,
                max_duration=max_duration,
                exclude_ids=played_ids | attempted_ids,
                exclude_titles=played_titles,
            )

            if not track:
                break

            if not isinstance(track, dict):
                break

            vidid = _track_id(track)
            title = _track_title(track)
            norm_title = _norm_title(title)

            # Invalid result
            if not vidid:
                break

            # Mark result so API cannot give it again
            attempted_ids.add(vidid)

            # Never return current/seed video
            if seed_vidid and vidid == seed_vidid:
                continue

            # Never return recently played ID
            if vidid in played_ids:
                continue

            # Never return recent same title
            if norm_title and norm_title in played_titles:
                played_ids.add(vidid)
                continue

            # Extra duplicate safety
            if is_already_played(
                chat_id,
                vidid,
                title,
            ):
                played_ids.add(vidid)
                continue

            # Valid new track
            remember_played(
                chat_id,
                vidid,
                title,
            )

            return track

    return None


def clear_autoplay_history(chat_id: int):
    """Clear one chat's autoplay history."""
    chat_id = int(chat_id)

    _played_tracks.pop(chat_id, None)
    _played_titles.pop(chat_id, None)
