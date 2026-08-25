import re
from collections import defaultdict, deque

from VIVAANXMUSIC import YouTube


_played_tracks = defaultdict(lambda: deque(maxlen=50))
_played_titles = defaultdict(lambda: deque(maxlen=50))


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
        r"hd|4k|remastered|version|visualizer|"
        r"status|fullvideo|lvideo"
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
    videoid: str,
    title: str = "",
):
    chat_id = int(chat_id)

    videoid = str(videoid or "").strip()

    if videoid:
        history = _played_tracks[chat_id]

        try:
            history.remove(videoid)
        except ValueError:
            pass

        history.append(videoid)

    normalized = _norm_title(title)

    if normalized:
        titles = _played_titles[chat_id]

        try:
            titles.remove(normalized)
        except ValueError:
            pass

        titles.append(normalized)


def get_played_tracks(chat_id: int):
    return set(
        _played_tracks.get(
            int(chat_id),
            [],
        )
    )


def get_played_titles(chat_id: int):
    return set(
        _played_titles.get(
            int(chat_id),
            [],
        )
    )


def clear_autoplay_history(chat_id: int):
    chat_id = int(chat_id)

    _played_tracks.pop(
        chat_id,
        None,
    )

    _played_titles.pop(
        chat_id,
        None,
    )


def _detect_language(title: str) -> str:
    """
    Title se language/style guess.
    """

    text = str(title or "").lower()

    bhojpuri_words = [
        "bhojpuri",
        "khesari",
        "pawan singh",
        "nirahua",
        "dinesh lal",
        "bhojiwood",
    ]

    haryanvi_words = [
        "haryanvi",
        "haryana",
        "sapna",
        "masoom sharma",
        "gulzaar chhaniwala",
        "dada lakhmi",
    ]

    punjabi_words = [
        "punjabi",
        "punjabi song",
        "diljit",
        "sidhu moose",
        "ap dhillon",
        "karan aujla",
    ]

    english_words = [
        "english",
        "official music video",
        "taylor swift",
        "justin bieber",
        "ed sheeran",
        "the weeknd",
        "billie eilish",
    ]

    for word in bhojpuri_words:
        if word in text:
            return "bhojpuri"

    for word in haryanvi_words:
        if word in text:
            return "haryanvi"

    for word in punjabi_words:
        if word in text:
            return "punjabi"

    for word in english_words:
        if word in text:
            return "english"

    return "hindi"


async def fetch_autoplay_track(
    chat_id: int,
    seed_title: str,
    seed_vidid: str = None,
    max_duration=None,
):
    """
    Same language ke different songs:
    Hindi -> Hindi
    Punjabi -> Punjabi
    English -> English
    Haryanvi -> Haryanvi
    Bhojpuri -> Bhojpuri
    """

    chat_id = int(chat_id)

    seed_vidid = str(
        seed_vidid or ""
    ).strip()

    seed_title = str(
        seed_title or ""
    ).strip()

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

    seed_normalized = _norm_title(seed_title)

    if seed_normalized:
        played_titles.add(
            seed_normalized
        )

    # Current song ki language/style
    language = _detect_language(
        seed_title
    )

    # IMPORTANT:
    # Hindi song -> Hindi searches
    # Bhojpuri -> Bhojpuri searches
    # etc.
    queries = [
        f"latest {language} songs official audio",
        f"popular {language} songs official audio",
        f"trending {language} songs",
        f"best {language} songs",
        f"new {language} songs",
    ]

    for query in queries:

        for _ in range(3):

            try:
                track = await YouTube.autoplay(
                    seed_vidid,
                    query,
                    max_duration=max_duration,
                    exclude_ids=played_ids,
                    exclude_titles=played_titles,
                )

            except TypeError:
                track = await YouTube.autoplay(
                    seed_vidid,
                    query,
                    max_duration=max_duration,
                )

            except Exception:
                track = None

            if not track:
                break

            videoid = str(
                track.get("vidid") or ""
            ).strip()

            title = str(
                track.get("title") or ""
            ).strip()

            if not videoid:
                continue

            normalized_title = _norm_title(
                title
            )

            # Same/recent video reject
            if videoid in played_ids:
                continue

            # Same/recent title reject
            if (
                normalized_title
                and normalized_title
                in played_titles
            ):
                played_ids.add(videoid)
                continue

            # Save before returning
            remember_played(
                chat_id,
                videoid,
                title,
            )

            return track

    return None
