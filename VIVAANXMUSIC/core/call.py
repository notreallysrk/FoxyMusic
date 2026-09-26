import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Union

from ntgcalls import TelegramServerError
from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.errors import ChatAdminRequired, ChatSendPlainForbidden, ChatWriteForbidden, Forbidden
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw.functions.channels import GetFullChannel
from pyrogram.raw.functions.messages import GetFullChat
from pyrogram.raw.types import PeerUser, UpdateGroupCallParticipants
from pyrogram.types import InlineKeyboardMarkup
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import NoActiveGroupCall
from pytgcalls.types import AudioQuality, ChatUpdate, MediaStream, StreamEnded, Update, VideoQuality

import config
from strings import get_string
from VIVAANXMUSIC import LOGGER, YouTube, app
from VIVAANXMUSIC.misc import db
from VIVAANXMUSIC.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_autoplay,
    get_lang,
    get_loop,
    get_vcnotify,
    group_assistant,
    is_autoend,
    is_music_playing,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
    set_vcnotify,
)
from VIVAANXMUSIC.utils.exceptions import AssistantErr
from VIVAANXMUSIC.utils.formatters import check_duration, seconds_to_min, speed_converter
from VIVAANXMUSIC.utils.inline.play import stream_markup
from VIVAANXMUSIC.security import build_subprocess_env
from VIVAANXMUSIC.utils.stream.autoclear import auto_clean
from VIVAANXMUSIC.utils.stream.autodelete import (
    delete_queue_message,
    remember_player_message,
)
from VIVAANXMUSIC.utils.stream.cards import schedule_stream_card
from VIVAANXMUSIC.utils.stream.precache import schedule_youtube_precache_for_chat
from VIVAANXMUSIC.utils.errors import capture_internal_err, send_large_error
from VIVAANXMUSIC.utils.autoplay import (
    fetch_autoplay_track,
    remember_played,
)

autoend = {}
counter = {}
playback_watchdogs = {}
playback_watchdog_tokens = {}
playback_recovery_attempts = {}
vc_join_monitors = {}
vc_join_snapshots = {}
vc_join_targets = {}
vc_join_call_map = {}
vc_join_event_cache = {}
vc_join_notice_cache = {}

PLAYBACK_WATCHDOG_GRACE_SECONDS = 20
PLAYBACK_WATCHDOG_RECHECK_SECONDS = 30
PLAYBACK_EARLY_END_GRACE_SECONDS = 25
PLAYBACK_EARLY_END_MAX_RECOVERIES = 1


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _cancel_playback_watchdog(chat_id: int) -> None:
    playback_watchdog_tokens[chat_id] = playback_watchdog_tokens.get(chat_id, 0) + 1
    task = playback_watchdogs.pop(chat_id, None)
    if not task or task.done():
        return
    try:
        current = asyncio.current_task()
    except RuntimeError:
        current = None
    if task is not current:
        task.cancel()


class _SilentMystic:
    async def edit_text(self, *args, **kwargs):
        return None

    async def delete(self, *args, **kwargs):
        return None


def validate_stream_path(path: str) -> str:
    if path is None or (isinstance(path, str) and not path.strip()):
        raise AssistantErr("Unable to prepare stream source. Please try again.")
    return path


def dynamic_media_stream(path: str, video: bool = False, ffmpeg_params: str = None) -> MediaStream:
    path = validate_stream_path(path)
    return MediaStream(
        audio_path=path,
        media_path=path,
        audio_parameters=AudioQuality.MEDIUM if video else AudioQuality.STUDIO,
        video_parameters=VideoQuality.HD_720p if video else VideoQuality.SD_360p,
        video_flags=(MediaStream.Flags.AUTO_DETECT if video else MediaStream.Flags.IGNORE),
        ffmpeg_parameters=ffmpeg_params,
    )


def is_groupcall_invalid(err: Exception) -> bool:
    return type(err).__name__ == "GroupcallInvalid" or "GROUPCALL_INVALID" in str(err)


def is_too_many_open_files(err: Exception) -> bool:
    return getattr(err, "errno", None) == 24 or "too many open files" in str(err).lower()


async def _clear_(chat_id: int) -> None:
    _cancel_playback_watchdog(chat_id)
    playback_recovery_attempts.pop(chat_id, None)
    popped = db.pop(chat_id, None)
    if isinstance(popped, list):
        for item in popped:
            await auto_clean(item)
    elif popped:
        await auto_clean(popped)
    db[chat_id] = []
    for call_id, info in list(vc_join_call_map.items()):
        if info.get("chat_id") == chat_id:
            vc_join_call_map.pop(call_id, None)
    task = vc_join_monitors.pop(chat_id, None)
    if task and not task.done():
        task.cancel()
    vc_join_snapshots.pop(chat_id, None)
    vc_join_targets.pop(chat_id, None)
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)
    await set_loop(chat_id, 0)


class Call:
    def __init__(self):
        self.userbot1 = Client("VivaanXAssis1", config.API_ID, config.API_HASH, session_string=config.STRING1) if config.STRING1 else None
        self.one = PyTgCalls(self.userbot1) if self.userbot1 else None
        self.userbot2 = Client("VivaanXAssis2", config.API_ID, config.API_HASH, session_string=config.STRING2) if config.STRING2 else None
        self.two = PyTgCalls(self.userbot2) if self.userbot2 else None
        self.userbot3 = Client("VivaanXAssis3", config.API_ID, config.API_HASH, session_string=config.STRING3) if config.STRING3 else None
        self.three = PyTgCalls(self.userbot3) if self.userbot3 else None
        self.userbot4 = Client("VivaanXAssis4", config.API_ID, config.API_HASH, session_string=config.STRING4) if config.STRING4 else None
        self.four = PyTgCalls(self.userbot4) if self.userbot4 else None
        self.userbot5 = Client("VivaanXAssis5", config.API_ID, config.API_HASH, session_string=config.STRING5) if config.STRING5 else None
        self.five = PyTgCalls(self.userbot5) if self.userbot5 else None
        self.active_calls: set[int] = set()
        self._stream_locks: dict[int, asyncio.Lock] = {}

    def _get_stream_lock(self, chat_id: int) -> asyncio.Lock:
        lock = self._stream_locks.get(chat_id)
        if lock is None:
            lock = asyncio.Lock()
            self._stream_locks[chat_id] = lock
        return lock

    @staticmethod
    def _track_signature(track: dict) -> tuple:
        return (str(track.get("file") or ""), str(track.get("vidid") or ""), str(track.get("streamtype") or ""), str(track.get("speed_path") or ""), str(track.get("speed") or ""), str(track.get("seconds") or ""))

    def _watchable_track(self, chat_id: int):
        queue = db.get(chat_id)
        if not queue or not isinstance(queue[0], dict):
            return None
        track = queue[0]
        seconds = _safe_int(track.get("seconds"), 0)
        if seconds <= 0 or str(track.get("file") or "").startswith("live_"):
            return None
        return track, seconds, _safe_int(track.get("played"), 0)

    def _schedule_playback_watchdog(self, client, chat_id: int, *, initial_delay: int = 0) -> None:
        _cancel_playback_watchdog(chat_id)
        token = playback_watchdog_tokens.get(chat_id, 0) + 1
        playback_watchdog_tokens[chat_id] = token

        async def watchdog() -> None:
            try:
                if initial_delay > 0:
                    await asyncio.sleep(initial_delay)
                current = self._watchable_track(chat_id)
                if not current:
                    return
                initial_track, _, _ = current
                signature = self._track_signature(initial_track)
                while playback_watchdog_tokens.get(chat_id) == token:
                    current = self._watchable_track(chat_id)
                    if not current:
                        return
                    track, seconds, played = current
                    if self._track_signature(track) != signature or chat_id not in self.active_calls:
                        return
                    if not await is_music_playing(chat_id):
                        await asyncio.sleep(PLAYBACK_WATCHDOG_RECHECK_SECONDS)
                        continue
                    remaining = max(seconds - played, 0)
                    await asyncio.sleep(max(PLAYBACK_WATCHDOG_RECHECK_SECONDS, remaining + PLAYBACK_WATCHDOG_GRACE_SECONDS))
                    current = self._watchable_track(chat_id)
                    if not current:
                        return
                    track, seconds, played = current
                    if self._track_signature(track) != signature or chat_id not in self.active_calls:
                        return
                    if not await is_music_playing(chat_id):
                        continue
                    if played < seconds:
                        continue
                    LOGGER(__name__).warning("Playback watchdog advancing stuck stream | chat_id=%s | title=%s", chat_id, track.get("title") or "Unknown Title")
                    await self.play(client, chat_id)
                    return
            except asyncio.CancelledError:
                raise
            except Exception as err:
                LOGGER(__name__).warning("Playback watchdog failed | chat_id=%s | reason=%s", chat_id, err)
            finally:
                if playback_watchdogs.get(chat_id) is asyncio.current_task():
                    playback_watchdogs.pop(chat_id, None)

        playback_watchdogs[chat_id] = asyncio.create_task(watchdog())

    def _register_early_end_recovery(self, chat_id: int, signature: tuple) -> bool:
        previous_signature, attempts = playback_recovery_attempts.get(chat_id, (None, 0))
        if previous_signature != signature:
            attempts = 0
        if attempts >= PLAYBACK_EARLY_END_MAX_RECOVERIES:
            return False
        playback_recovery_attempts[chat_id] = (signature, attempts + 1)
        return True

    async def _recover_early_stream_end(self, client, chat_id: int) -> bool:
        current = self._watchable_track(chat_id)
        if not current:
            return False
        track, seconds, played = current
        if seconds - played <= PLAYBACK_EARLY_END_GRACE_SECONDS:
            return False
        signature = self._track_signature(track)
        if not self._register_early_end_recovery(chat_id, signature):
            return False
        queued = str(track.get("file") or "")
        streamtype = track.get("streamtype") or "audio"
        video = str(streamtype) == "video"
        title = str(track.get("title") or "Unknown Title")
        videoid = str(track.get("vidid") or "").strip()
        source_path = queued
        if queued.startswith("vid_"):
            if not videoid or videoid in {"telegram", "soundcloud"}:
                return False
            source_path, _, _ = await self._download_youtube_queue_source(videoid, title, _SilentMystic(), streamtype, modes=("local", "stream"))
        elif queued.startswith("index_") or queued == "index_url":
            source_path = videoid
        elif queued.startswith("live_"):
            return False
        if not source_path:
            return False
        seek_to = max(played, 0)
        duration = track.get("dur") or seconds_to_min(seconds)
        stream = dynamic_media_stream(source_path, video=video, ffmpeg_params=f"-ss {seconds_to_min(seek_to)} -to {duration}")
        await self._play_stream(client, chat_id, stream)
        if db.get(chat_id) and isinstance(db[chat_id][0], dict):
            db[chat_id][0]["played"] = seek_to
        self._schedule_playback_watchdog(client, chat_id)
        return True

    async def _resolve_vc_call_id(self, chat_id: int) -> int | None:
        try:
            chat = await app.get_chat(chat_id)
            if chat.type in {ChatType.SUPERGROUP, ChatType.CHANNEL, ChatType.FORUM}:
                full = await app.invoke(GetFullChannel(channel=await app.resolve_peer(chat_id)))
            else:
                full = await app.invoke(GetFullChat(chat_id=abs(int(chat_id))))
            call = getattr(getattr(full, "full_chat", None), "call", None)
            return int(call.id) if call else None
        except Exception:
            return None

    @staticmethod
    def _extract_user_id_from_peer(peer) -> int | None:
        return int(peer.user_id) if isinstance(peer, PeerUser) else None

    @staticmethod
    def _remember_join_event(call_id: int, user_id: int, date: int, source: int) -> bool:
        now = time.monotonic()
        for key, stamp in list(vc_join_event_cache.items()):
            if now - stamp > 30:
                vc_join_event_cache.pop(key, None)
        key = (call_id, user_id, date, source, "join")
        if key in vc_join_event_cache:
            return False
        vc_join_event_cache[key] = now
        return True

    @staticmethod
    def _remember_join_notice(notify_chat_id: int, user_id: int, date: int, source: int) -> bool:
        now = time.monotonic()
        for key, stamp in list(vc_join_notice_cache.items()):
            if now - stamp > 60:
                vc_join_notice_cache.pop(key, None)
        key = (notify_chat_id, user_id, date, source)
        if key in vc_join_notice_cache:
            return False
        vc_join_notice_cache[key] = now
        return True

    async def _fetch_vc_participant_ids(self, chat_id: int) -> set[int]:
        assistant = await group_assistant(self, chat_id)
        participants = await assistant.get_participants(chat_id)
        return {int(p.user_id) for p in participants if getattr(p, "user_id", None)}

    async def _send_vc_join_notice(self, notify_chat_id: int, user_id: int, date: int = 0, source: int = 0) -> None:
        if not self._remember_join_notice(notify_chat_id, user_id, date, source):
            return
        try:
            user = await app.get_users(user_id)
            name = " ".join(part for part in [user.first_name, user.last_name] if part).strip() or user.username or "Unknown User"
            username = f" (@{user.username})" if user.username else ""
        except Exception:
            name, username = "Unknown User", ""
        try:
            await app.send_message(notify_chat_id, f"Joined VC\nName: {name}{username}\nUser ID: <code>{user_id}</code>")
        except (ChatWriteForbidden, ChatSendPlainForbidden, Forbidden):
            try:
                await set_vcnotify(notify_chat_id, False)
            except Exception:
                pass

    async def _handle_group_call_participants_update(self, update: UpdateGroupCallParticipants) -> None:
        call_id = int(update.call.id)
        mapping = vc_join_call_map.get(call_id)
        if not mapping or not await get_vcnotify(mapping["notify_chat_id"]):
            return
        snapshot = vc_join_snapshots.setdefault(mapping["chat_id"], set())
        for participant in update.participants:
            user_id = self._extract_user_id_from_peer(getattr(participant, "peer", None))
            if not user_id:
                continue
            if getattr(participant, "left", False):
                snapshot.discard(user_id)
                continue
            if not getattr(participant, "just_joined", False) or user_id in snapshot:
                continue
            if not self._remember_join_event(call_id, user_id, int(getattr(participant, "date", 0) or 0), int(getattr(participant, "source", 0) or 0)):
                continue
            snapshot.add(user_id)
            await self._send_vc_join_notice(mapping["notify_chat_id"], user_id, int(getattr(participant, "date", 0) or 0), int(getattr(participant, "source", 0) or 0))

    async def _vc_join_monitor_loop(self, chat_id: int, notify_chat_id: int) -> None:
        try:
            while True:
                if not await get_vcnotify(notify_chat_id):
                    vc_join_snapshots.pop(chat_id, None)
                    await asyncio.sleep(1)
                    continue
                try:
                    current_ids = await self._fetch_vc_participant_ids(chat_id)
                except Exception:
                    await asyncio.sleep(1)
                    continue
                previous_ids = vc_join_snapshots.get(chat_id)
                if previous_ids is None:
                    vc_join_snapshots[chat_id] = current_ids
                else:
                    for user_id in current_ids - previous_ids:
                        try:
                            await self._send_vc_join_notice(notify_chat_id, user_id)
                        except Exception:
                            continue
                    vc_join_snapshots[chat_id] = current_ids
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        finally:
            if vc_join_monitors.get(chat_id) is asyncio.current_task():
                vc_join_monitors.pop(chat_id, None)

    async def maybe_start_vc_join_notifier(self, chat_id: int, notify_chat_id: int) -> bool:
        if not await get_vcnotify(notify_chat_id):
            return False
        call_id = await self._resolve_vc_call_id(chat_id)
        vc_join_targets[chat_id] = notify_chat_id
        if call_id:
            vc_join_call_map[call_id] = {"chat_id": chat_id, "notify_chat_id": notify_chat_id}
        if chat_id not in vc_join_snapshots:
            try:
                vc_join_snapshots[chat_id] = await self._fetch_vc_participant_ids(chat_id)
            except Exception:
                vc_join_snapshots[chat_id] = set()
        existing = vc_join_monitors.get(chat_id)
        if not existing or existing.done():
            vc_join_monitors[chat_id] = asyncio.create_task(self._vc_join_monitor_loop(chat_id, notify_chat_id))
        return True

    async def stop_vc_join_notifier(self, chat_id: int) -> None:
        task = vc_join_monitors.pop(chat_id, None)
        if task and not task.done():
            task.cancel()
        vc_join_snapshots.pop(chat_id, None)
        vc_join_targets.pop(chat_id, None)
        for call_id, info in list(vc_join_call_map.items()):
            if info.get("chat_id") == chat_id:
                vc_join_call_map.pop(call_id, None)

    async def _play_stream(self, assistant: PyTgCalls, chat_id: int, stream: MediaStream) -> None:
        """Play a stream with short Telegram/NTgCalls recovery retries.

        TelegramServerError is often transient.  The old code immediately
        raised it, which made the bot show the generic Telegram server error
        even when the voice chat became usable a moment later.
        """
        async with self._get_stream_lock(chat_id):
            last_error = None
            for attempt in range(4):
                try:
                    await assistant.play(chat_id, stream)
                    return
                except TelegramServerError as err:
                    last_error = err
                    LOGGER(__name__).warning(
                        "Telegram server error while starting stream | chat=%s | attempt=%s/4 | type=%s | repr=%r",
                        chat_id,
                        attempt + 1,
                        type(err).__name__,
                        err,
                    )
                    if attempt >= 3:
                        raise
                    # Reset a possibly stale VC state before retrying.
                    # Replaying the exact same NTgCalls state can otherwise
                    # reproduce TelegramServerError on every attempt.
                    try:
                        await assistant.leave_call(chat_id)
                    except Exception:
                        pass
                    await asyncio.sleep(1.0 + (attempt * 1.5))
                except OSError as err:
                    if err.errno != 24 or attempt >= 2:
                        raise
                    last_error = err
                    await asyncio.sleep(1)
                except Exception as err:
                    if not (is_groupcall_invalid(err) or is_too_many_open_files(err)) or attempt >= 2:
                        raise
                    last_error = err
                    await asyncio.sleep(1)
            if last_error:
                raise last_error

    @capture_internal_err
    async def pause_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        await assistant.pause(chat_id)
        _cancel_playback_watchdog(chat_id)

    @capture_internal_err
    async def resume_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        await assistant.resume(chat_id)
        self._schedule_playback_watchdog(assistant, chat_id)

    @capture_internal_err
    async def mute_stream(self, chat_id: int) -> None:
        await (await group_assistant(self, chat_id)).mute(chat_id)

    @capture_internal_err
    async def unmute_stream(self, chat_id: int) -> None:
        await (await group_assistant(self, chat_id)).unmute(chat_id)

    @capture_internal_err
    async def stop_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        await self.stop_vc_join_notifier(chat_id)
        await _clear_(chat_id)
        if chat_id not in self.active_calls:
            return
        try:
            await assistant.leave_call(chat_id)
        except Exception:
            pass
        finally:
            self.active_calls.discard(chat_id)

    @capture_internal_err
    async def force_stop_stream(self, chat_id: int) -> None:
        assistant = await group_assistant(self, chat_id)
        await self.stop_vc_join_notifier(chat_id)
        try:
            check = db.get(chat_id)
            if check:
                popped = check.pop(0)
                if popped:
                    await auto_clean(popped)
        except (IndexError, KeyError):
            pass
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)
        await _clear_(chat_id)
        if chat_id not in self.active_calls:
            return
        try:
            await assistant.leave_call(chat_id)
        except Exception:
            pass
        finally:
            self.active_calls.discard(chat_id)

    @capture_internal_err
    async def skip_stream(self, chat_id: int, link: str, video: Union[bool, str] = None, image: Union[bool, str] = None) -> None:
        assistant = await group_assistant(self, chat_id)
        await self._play_stream(assistant, chat_id, dynamic_media_stream(link, video=bool(video)))
        self._schedule_playback_watchdog(assistant, chat_id)

    @capture_internal_err
    async def vc_users(self, chat_id: int) -> list:
        participants = await (await group_assistant(self, chat_id)).get_participants(chat_id)
        return [p.user_id for p in participants if not p.is_muted]

    @capture_internal_err
    async def seek_stream(self, chat_id: int, file_path: str, to_seek: str, duration: str, mode: str) -> None:
        assistant = await group_assistant(self, chat_id)
        stream = dynamic_media_stream(file_path, video=(mode == "video"), ffmpeg_params=f"-ss {to_seek} -to {duration}")
        await self._play_stream(assistant, chat_id, stream)
        self._schedule_playback_watchdog(assistant, chat_id, initial_delay=1)

    @capture_internal_err
    async def speedup_stream(self, chat_id: int, file_path: str, speed: float, playing: list) -> None:
        if not isinstance(playing, list) or not playing or not isinstance(playing[0], dict):
            raise AssistantErr("Invalid stream info for speedup.")
        assistant = await group_assistant(self, chat_id)
        base = os.path.basename(file_path)
        chatdir = os.path.join("playback", str(speed))
        os.makedirs(chatdir, exist_ok=True)
        out = os.path.join(chatdir, base)
        if not os.path.exists(out):
            vs = str(2.0 / float(speed))
            proc = await asyncio.create_subprocess_exec("ffmpeg", "-i", file_path, "-filter:v", f"setpts={vs}*PTS", "-filter:a", f"atempo={speed}", out, stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=build_subprocess_env())
            await proc.communicate()
        dur = int(await asyncio.get_event_loop().run_in_executor(None, check_duration, out))
        played, con_seconds = speed_converter(playing[0]["played"], speed)
        duration_min = seconds_to_min(dur)
        stream = dynamic_media_stream(out, video=(playing[0]["streamtype"] == "video"), ffmpeg_params=f"-ss {played} -to {duration_min}")
        if chat_id in db and db[chat_id] and db[chat_id][0].get("file") == file_path:
            await self._play_stream(assistant, chat_id, stream)
        else:
            raise AssistantErr("Stream mismatch during speedup.")
        db[chat_id][0].update({"played": con_seconds, "dur": duration_min, "seconds": dur, "speed_path": out, "speed": speed, "old_dur": db[chat_id][0].get("dur"), "old_second": db[chat_id][0].get("seconds")})
        self._schedule_playback_watchdog(assistant, chat_id)

    @capture_internal_err
    async def stream_call(self, link: str) -> None:
        assistant = await group_assistant(self, config.LOGGER_ID)
        try:
            await self._play_stream(assistant, config.LOGGER_ID, MediaStream(link))
            await asyncio.sleep(8)
        finally:
            try:
                await assistant.leave_call(config.LOGGER_ID)
            except Exception:
                pass

    @capture_internal_err
    async def join_call(self, chat_id: int, original_chat_id: int, link: str, video: Union[bool, str] = None, image: Union[bool, str] = None) -> None:
        assistant = await group_assistant(self, chat_id)
        _ = get_string(await get_lang(chat_id))
        try:
            await self._play_stream(assistant, chat_id, dynamic_media_stream(link, video=bool(video)))
        except (NoActiveGroupCall, ChatAdminRequired):
            raise AssistantErr(_["call_8"])
        except TelegramServerError:
            # _play_stream already retries transient Telegram/NTgCalls
            # failures.  If all retries fail, return the existing friendly
            # message instead of leaking the raw exception.
            raise AssistantErr(_["call_10"])
        except Exception as e:
            if is_groupcall_invalid(e):
                raise AssistantErr(_["call_8"])
            if is_too_many_open_files(e):
                raise AssistantErr("Server open-file limit reached. Please try again in a few seconds.")
            raise AssistantErr(f"ᴜɴᴀʙʟᴇ ᴛᴏ ᴊᴏɪɴ ᴛʜᴇ ɢʀᴏᴜᴘ ᴄᴀʟʟ.\nRᴇᴀsᴏɴ: {e}")
        self.active_calls.add(chat_id)
        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)
        await self.maybe_start_vc_join_notifier(chat_id, original_chat_id)
        self._schedule_playback_watchdog(assistant, chat_id, initial_delay=2)
        if await is_autoend():
            counter[chat_id] = {}
            if len(await assistant.get_participants(chat_id)) == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    async def _enqueue_autoplay_track(self, chat_id: int, finished_track: dict) -> bool:
        if not finished_track:
            return False
        try:
            if not await get_autoplay(chat_id):
                return False
        except Exception:
            return False
        queued_file = str(finished_track.get("file") or "")
        if queued_file.startswith("live_") or queued_file == "index_url":
            return False
        videoid = str(finished_track.get("vidid") or "").strip()
        if not videoid or videoid in {"telegram", "soundcloud"}:
            return False
        title = str(finished_track.get("title") or "").strip()
        try:
            remember_played(chat_id, videoid)
            recommendation = await fetch_autoplay_track(chat_id, title, videoid)
        except Exception as err:
            LOGGER(__name__).warning("Autoplay lookup failed | chat=%s | video=%s | error=%s", chat_id, videoid, err)
            return False
        if not recommendation:
            return False
        try:
            new_vidid = str(recommendation.get("vidid") or "").strip()
            new_title = str(recommendation.get("title") or "").strip()
            if not new_vidid or not new_title or new_vidid == videoid:
                return False
            duration_min = str(recommendation.get("duration_min") or "0:00")
            duration_sec = recommendation.get("duration_sec")
            if not duration_sec:
                try:
                    parts = duration_min.strip().split(":")
                    if len(parts) == 2:
                        duration_sec = int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        duration_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    else:
                        duration_sec = 0
                except Exception:
                    duration_sec = 0
            try:
                duration_sec = int(duration_sec or 0)
            except (TypeError, ValueError):
                duration_sec = 0
            db.setdefault(chat_id, []).append({
                "title": new_title.title(),
                "dur": duration_min,
                "streamtype": finished_track.get("streamtype", "audio"),
                "by": "Autoplay",
                "user_id": 0,
                "chat_id": finished_track.get("chat_id", chat_id),
                "file": f"vid_{new_vidid}",
                "vidid": new_vidid,
                "seconds": duration_sec,
                "played": 0,
            })
            remember_played(chat_id, new_vidid)
            LOGGER(__name__).info("Autoplay track added | chat=%s | old=%s | new=%s | title=%s", chat_id, videoid, new_vidid, new_title)
            return True
        except Exception as err:
            LOGGER(__name__).warning("Autoplay queue add failed | chat=%s | error=%s", chat_id, err)
            return False

    async def _stop_if_queue_empty(self, client, chat_id: int, finished_track=None, allow_autoplay: bool = True) -> bool:
        if db.get(chat_id):
            return False
        if allow_autoplay and finished_track:
            try:
                if await self._enqueue_autoplay_track(chat_id, finished_track):
                    return False
            except Exception as err:
                LOGGER(__name__).warning("Autoplay enqueue exception | chat=%s | error=%s", chat_id, err)
        await _clear_(chat_id)
        if chat_id in self.active_calls:
            try:
                await client.leave_call(chat_id)
            except NoActiveGroupCall:
                pass
            except Exception:
                pass
            finally:
                self.active_calls.discard(chat_id)
        return True

    async def _discard_unplayable_queue_head(self, client, chat_id: int, reason: str) -> bool:
        queue = db.get(chat_id)
        dropped = None
        if queue:
            try:
                dropped = queue.pop(0)
            except IndexError:
                pass
        if dropped:
            try:
                await auto_clean(dropped)
            except Exception:
                pass
        LOGGER(__name__).warning("Skipping unplayable queued track | chat=%s | track=%s | reason=%s", chat_id, (dropped or {}).get("vidid") or (dropped or {}).get("title") or "unknown", reason)
        return await self._stop_if_queue_empty(client, chat_id, dropped, allow_autoplay=True)

    async def _download_youtube_queue_source(self, videoid: str, title: str, mystic, streamtype, modes=("local", "stream")):
        """Resolve a fresh YouTube source for queued playback.

        The configured API is preferred. Direct extraction is only an optional
        secondary path when explicitly requested by the caller.
        """
        is_video = str(streamtype) == "video"
        # API is the primary YouTube source. This intentionally avoids direct
        # yt-dlp extraction so YouTube's "Sign in to confirm you're not a bot"
        # message never becomes part of normal playback.
        for mode in modes:
            if mode == "local":
                try:
                    file_path, direct = await YouTube.download(
                        videoid, mystic, video=is_video, videoid=True, title=title
                    )
                except Exception as err:
                    LOGGER(__name__).warning("YouTube API source failed for %s: %s", videoid, err)
                    continue
                if file_path:
                    return file_path, direct, "api"
            elif mode == "stream":
                try:
                    direct_url = await YouTube.stream_url(videoid, videoid=True)
                except Exception:
                    direct_url = None
                if direct_url:
                    return direct_url, True, "direct"
        return None, False, "missing"

        return None, False, "missing"



    @capture_internal_err
    async def play(self, client, chat_id: int) -> None:
        _cancel_playback_watchdog(chat_id)
        check = db.get(chat_id)
        popped = None
        loop = await get_loop(chat_id)
        try:
            if loop == 0:
                popped = check.pop(0)
            else:
                loop -= 1
                await set_loop(chat_id, loop)
            if popped:
                await auto_clean(popped)
            if await self._stop_if_queue_empty(client, chat_id, popped, allow_autoplay=True):
                return
        except Exception:
            try:
                await _clear_(chat_id)
                return await client.leave_call(chat_id)
            except Exception:
                return
        while True:
            check = db.get(chat_id)
            if not check:
                await self._stop_if_queue_empty(client, chat_id, allow_autoplay=False)
                return
            current = check[0]
            if not isinstance(current, dict):
                if await self._discard_unplayable_queue_head(client, chat_id, "malformed queue item"):
                    return
                continue
            queued = current.get("file")
            _ = get_string(await get_lang(chat_id))
            title = str(current.get("title") or "Unknown Title").title()
            user = current.get("by") or "Unknown"
            requester_id = current.get("user_id")
            original_chat_id = current.get("chat_id", chat_id)
            streamtype = current.get("streamtype") or "audio"
            videoid = current.get("vidid")
            if videoid and str(videoid) not in {"telegram", "soundcloud"}:
                remember_played(chat_id, str(videoid))
            current["played"] = 0
            await delete_queue_message(chat_id, current)
            exis = current.get("old_dur")
            if exis:
                current["dur"] = exis
                current["seconds"] = current.get("old_second", 0)
                current["speed_path"] = None
                current["speed"] = 1.0
            video = str(streamtype) == "video"
            if not queued or not isinstance(queued, str):
                if await self._discard_unplayable_queue_head(client, chat_id, "missing queued stream path"):
                    return
                continue
            if "live_" in queued:
                try:
                    n, link = await YouTube.video(videoid, True)
                except Exception:
                    n, link = 0, None
                if n == 0 or not link:
                    if await self._discard_unplayable_queue_head(client, chat_id, "live stream URL was unavailable"):
                        return
                    continue
                try:
                    await self._play_stream(client, chat_id, dynamic_media_stream(link, video=video))
                except Exception:
                    return await app.send_message(original_chat_id, text=_["call_6"])
                self._schedule_playback_watchdog(client, chat_id)
                button = stream_markup(_, chat_id)
                schedule_stream_card(chat_id=chat_id, original_chat_id=original_chat_id, videoid=videoid, user_id=requester_id, caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{videoid}", title[:23], current.get("dur"), user), button=button, markup="tg")
                return
            elif "vid_" in queued:
                mystic = await app.send_message(original_chat_id, _["call_7"])
                file_path, direct, source_mode = await self._download_youtube_queue_source(videoid, title, mystic, streamtype)
                if not file_path:
                    try:
                        await mystic.edit_text(_["call_6"], disable_web_page_preview=True)
                    except Exception:
                        pass
                    if await self._discard_unplayable_queue_head(client, chat_id, "YouTube download returned no playable stream path"):
                        return
                    continue
                try:
                    await self._play_stream(client, chat_id, dynamic_media_stream(file_path, video=video))
                except Exception:
                    fallback_path, _, _ = await self._download_youtube_queue_source(videoid, title, mystic, streamtype, modes=("stream",))
                    if not fallback_path:
                        if await self._discard_unplayable_queue_head(client, chat_id, "fallback YouTube download returned no playable stream path"):
                            return
                        continue
                    try:
                        await self._play_stream(client, chat_id, dynamic_media_stream(fallback_path, video=video))
                    except Exception:
                        if await self._discard_unplayable_queue_head(client, chat_id, "YouTube stream playback failed"):
                            return
                        continue
                self._schedule_playback_watchdog(client, chat_id)
                button = stream_markup(_, chat_id)
                try:
                    await mystic.delete()
                except Exception:
                    pass
                schedule_youtube_precache_for_chat(chat_id)
                schedule_stream_card(chat_id=chat_id, original_chat_id=original_chat_id, videoid=videoid, user_id=requester_id, caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{videoid}", title[:23], current.get("dur"), user), button=button, markup="stream")
                return
            elif "index_" in queued:
                if not videoid:
                    if await self._discard_unplayable_queue_head(client, chat_id, "index stream URL was missing"):
                        return
                    continue
                try:
                    await self._play_stream(client, chat_id, dynamic_media_stream(videoid, video=video))
                except Exception:
                    return await app.send_message(original_chat_id, text=_["call_6"])
                self._schedule_playback_watchdog(client, chat_id)
                button = stream_markup(_, chat_id)
                run = await app.send_photo(chat_id=original_chat_id, photo=config.STREAM_IMG_URL, caption=_["stream_2"].format(user), reply_markup=InlineKeyboardMarkup(button))
                current["mystic"] = run
                remember_player_message(chat_id, run)
                current["markup"] = "tg"
                return
            else:
                source = queued
                # Old queue entries may contain an expired YouTube CDN URL.
                # Refresh them by video ID before giving up.
                if videoid and str(videoid) not in {"telegram", "soundcloud"} and (
                    "youtube.com" in str(queued) or "googlevideo.com" in str(queued)
                ):
                    try:
                        source = await asyncio.wait_for(
                            YouTube.stream_url(str(videoid), videoid=True),
                            timeout=5,
                        ) or queued
                    except Exception:
                        source = queued
                try:
                    await self._play_stream(client, chat_id, dynamic_media_stream(source, video=video))
                except Exception:
                    return await app.send_message(original_chat_id, text=_["call_6"])
                self._schedule_playback_watchdog(client, chat_id)
                if videoid == "telegram":
                    button = stream_markup(_, chat_id)
                    run = await app.send_photo(chat_id=original_chat_id, photo=config.TELEGRAM_AUDIO_URL if str(streamtype) == "audio" else config.TELEGRAM_VIDEO_URL, caption=_["stream_1"].format(config.SUPPORT_CHAT, title[:23], current.get("dur"), user), reply_markup=InlineKeyboardMarkup(button))
                    current["mystic"] = run
                    remember_player_message(chat_id, run)
                    current["markup"] = "tg"
                elif videoid == "soundcloud":
                    button = stream_markup(_, chat_id)
                    run = await app.send_photo(chat_id=original_chat_id, photo=config.SOUNCLOUD_IMG_URL, caption=_["stream_1"].format(config.SUPPORT_CHAT, title[:23], current.get("dur"), user), reply_markup=InlineKeyboardMarkup(button))
                    current["mystic"] = run
                    remember_player_message(chat_id, run)
                    current["markup"] = "tg"
                else:
                    button = stream_markup(_, chat_id)
                    schedule_stream_card(chat_id=chat_id, original_chat_id=original_chat_id, videoid=videoid, user_id=requester_id, caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{videoid}", title[:23], current.get("dur"), user), button=button, markup="stream")
                return

    async def start(self) -> None:
        LOGGER(__name__).info("Starting PyTgCalls Clients...")
        if config.STRING1:
            await self.one.start()
        if config.STRING2:
            await self.two.start()
        if config.STRING3:
            await self.three.start()
        if config.STRING4:
            await self.four.start()
        if config.STRING5:
            await self.five.start()

    @capture_internal_err
    async def ping(self) -> str:
        pings = []
        if config.STRING1: pings.append(self.one.ping)
        if config.STRING2: pings.append(self.two.ping)
        if config.STRING3: pings.append(self.three.ping)
        if config.STRING4: pings.append(self.four.ping)
        if config.STRING5: pings.append(self.five.ping)
        return str(round(sum(pings) / len(pings), 3)) if pings else "0.0"

    @capture_internal_err
    async def decorators(self) -> None:
        assistants = list(filter(None, [self.one, self.two, self.three, self.four, self.five]))
        raw_clients = list(filter(None, [app, self.userbot1, self.userbot2, self.userbot3, self.userbot4, self.userbot5]))
        CRITICAL = ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT | ChatUpdate.Status.DISCARDED_CALL | ChatUpdate.Status.BUSY_CALL

        async def unified_update_handler(client, update: Update) -> None:
            try:
                if isinstance(update, ChatUpdate):
                    if (update.status & ChatUpdate.Status.LEFT_CALL) or (update.status & CRITICAL):
                        await self.stop_stream(update.chat_id)
                        return
                elif isinstance(update, StreamEnded):
                    if update.stream_type == StreamEnded.Type.AUDIO:
                        assistant = await group_assistant(self, update.chat_id)
                        if await self._recover_early_stream_end(assistant, update.chat_id):
                            return
                        await self.play(assistant, update.chat_id)
            except AssistantErr as err:
                LOGGER(__name__).warning("Stream update skipped for chat %s: %s", getattr(update, "chat_id", "unknown"), err)
            except Exception:
                import sys, traceback
                exc_type, exc_obj, exc_tb = sys.exc_info()
                full_trace = "".join(traceback.format_exception(exc_type, exc_obj, exc_tb))
                caption = f"🚨 <b>Stream Update Error</b>\n📍 <b>Update Type:</b> <code>{type(update).__name__}</code>\n📍 <b>Error Type:</b> <code>{exc_type.__name__}</code>"
                filename = f"update_error_{getattr(update, 'chat_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                await send_large_error(full_trace, caption, filename)

        async def raw_group_call_handler(client, update, users, chats) -> None:
            try:
                if isinstance(update, UpdateGroupCallParticipants):
                    await self._handle_group_call_participants_update(update)
            except (ChatWriteForbidden, ChatSendPlainForbidden, Forbidden) as err:
                LOGGER(__name__).warning("VC notify update ignored: %s", err)
            except Exception:
                import sys, traceback
                exc_type, exc_obj, exc_tb = sys.exc_info()
                full_trace = "".join(traceback.format_exception(exc_type, exc_obj, exc_tb))
                caption = f"VC Notify Error\nUpdate Type: {type(update).__name__}\nError Type: {exc_type.__name__}"
                filename = f"vc_notify_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                await send_large_error(full_trace, caption, filename)

        for assistant in assistants:
            assistant.on_update()(unified_update_handler)
        for raw_client in raw_clients:
            raw_client.add_handler(RawUpdateHandler(raw_group_call_handler), group=99)


JARVIS = Call()
        
