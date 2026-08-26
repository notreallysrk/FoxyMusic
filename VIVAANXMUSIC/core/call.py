import asyncio
import os
from datetime import datetime, timedelta

from ntgcalls import TelegramServerError
from pyrogram import Client
from pyrogram.errors import ChatAdminRequired
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import NoActiveGroupCall
from pytgcalls.types import AudioQuality, ChatUpdate, MediaStream, StreamEnded, VideoQuality

import config
from strings import get_string
from VIVAANXMUSIC import LOGGER, YouTube, app
from VIVAANXMUSIC.misc import db
from VIVAANXMUSIC.utils.database import (
    add_active_chat, add_active_video_chat, get_autoplay, get_lang, get_loop,
    group_assistant, is_autoend, music_on, remove_active_chat,
    remove_active_video_chat, set_loop,
)
from VIVAANXMUSIC.utils.exceptions import AssistantErr
from VIVAANXMUSIC.utils.formatters import check_duration, seconds_to_min, speed_converter
from VIVAANXMUSIC.utils.inline.play import stream_markup
from VIVAANXMUSIC.security import build_subprocess_env
from VIVAANXMUSIC.utils.stream.autoclear import auto_clean
from VIVAANXMUSIC.utils.stream.autodelete import delete_queue_message, remember_player_message
from VIVAANXMUSIC.utils.stream.cards import schedule_stream_card
from VIVAANXMUSIC.utils.stream.precache import schedule_youtube_precache_for_chat
from VIVAANXMUSIC.utils.errors import capture_internal_err
from VIVAANXMUSIC.utils.Autoplay import fetch_autoplay_track, remember_played

autoend, counter = {}, {}
playback_watchdogs, playback_tokens = {}, {}

def media(path, video=False, params=None):
    if not path:
        raise AssistantErr("Unable to prepare stream source.")
    return MediaStream(
        audio_path=path, media_path=path,
        audio_parameters=AudioQuality.MEDIUM if video else AudioQuality.STUDIO,
        video_parameters=VideoQuality.HD_720p if video else VideoQuality.SD_360p,
        video_flags=MediaStream.Flags.AUTO_DETECT if video else MediaStream.Flags.IGNORE,
        ffmpeg_parameters=params,
    )

async def clear(chat_id):
    task = playback_watchdogs.pop(chat_id, None)
    if task and not task.done():
        task.cancel()
    playback_tokens[chat_id] = playback_tokens.get(chat_id, 0) + 1
    for item in db.pop(chat_id, []):
        await auto_clean(item)
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)
    await set_loop(chat_id, 0)

class Call:
    def __init__(self):
        self.userbot1 = Client("VivaanXAssis1", config.API_ID, config.API_HASH, session_string=config.STRING1) if config.STRING1 else None
        self.userbot2 = Client("VivaanXAssis2", config.API_ID, config.API_HASH, session_string=config.STRING2) if config.STRING2 else None
        self.userbot3 = Client("VivaanXAssis3", config.API_ID, config.API_HASH, session_string=config.STRING3) if config.STRING3 else None
        self.userbot4 = Client("VivaanXAssis4", config.API_ID, config.API_HASH, session_string=config.STRING4) if config.STRING4 else None
        self.userbot5 = Client("VivaanXAssis5", config.API_ID, config.API_HASH, session_string=config.STRING5) if config.STRING5 else None
        self.one = PyTgCalls(self.userbot1) if self.userbot1 else None
        self.two = PyTgCalls(self.userbot2) if self.userbot2 else None
        self.three = PyTgCalls(self.userbot3) if self.userbot3 else None
        self.four = PyTgCalls(self.userbot4) if self.userbot4 else None
        self.five = PyTgCalls(self.userbot5) if self.userbot5 else None
        self.active_calls = set()
        self.locks, self.advance_locks = {}, {}

    def lock(self, chat_id):
        return self.locks.setdefault(chat_id, asyncio.Lock())

    def advance_lock(self, chat_id):
        return self.advance_locks.setdefault(chat_id, asyncio.Lock())

    async def _play(self, assistant, chat_id, stream):
        async with self.lock(chat_id):
            await assistant.play(chat_id, stream)

    def watchdog(self, assistant, chat_id):
        old = playback_watchdogs.pop(chat_id, None)
        if old and not old.done():
            old.cancel()
        token = playback_tokens.get(chat_id, 0) + 1
        playback_tokens[chat_id] = token
        async def run():
            try:
                q = db.get(chat_id)
                if not q: return
                sec = int(q[0].get("seconds") or 0)
                if sec <= 0 or str(q[0].get("file","")).startswith("live_"): return
                sig = (q[0].get("file"), q[0].get("vidid"))
                await asyncio.sleep(sec + 20)
                q = db.get(chat_id)
                if q and playback_tokens.get(chat_id) == token and (q[0].get("file"), q[0].get("vidid")) == sig:
                    await self.advance(assistant, chat_id)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                LOGGER(__name__).warning("Watchdog error: %s", e)
        playback_watchdogs[chat_id] = asyncio.create_task(run())

    async def source(self, videoid, title, mystic, streamtype):
        try:
            result = await YouTube.download(videoid, mystic, videoid=True, video=str(streamtype) == "video", title=title)
            if isinstance(result, (tuple, list)):
                return result[0] if result else None
            return result
        except Exception as e:
            LOGGER(__name__).warning("YouTube source error: %s", e)
            return None

    async def autoplay(self, chat_id, track):
        if not track or not await get_autoplay(chat_id):
            return False
        vid = str(track.get("vidid") or "")
        if not vid or vid in {"telegram", "soundcloud"} or str(track.get("file","")).startswith("live_"):
            return False
        try:
            remember_played(chat_id, vid, track.get("title",""))
            rec = await fetch_autoplay_track(chat_id, track.get("title",""), vid)
        except Exception as e:
            LOGGER(__name__).warning("Autoplay lookup failed: %s", e)
            return False
        if not rec or not rec.get("vidid") or str(rec["vidid"]) == vid:
            return False
        db.setdefault(chat_id, []).append({
            "title": str(rec.get("title") or "Autoplay").title(),
            "dur": rec.get("duration_min") or seconds_to_min(int(rec.get("duration_sec") or 0)),
            "streamtype": track.get("streamtype","audio"),
            "by": "Autoplay", "user_id": 0,
            "chat_id": track.get("chat_id", chat_id),
            "file": f"vid_{rec['vidid']}", "vidid": rec["vidid"],
            "seconds": int(rec.get("duration_sec") or 0), "played": 0,
        })
        return True

    async def advance(self, client, chat_id):
        async with self.advance_lock(chat_id):
            q = db.get(chat_id, [])
            if not q:
                return
            loop = await get_loop(chat_id)
            finished = q[0]
            if loop > 0:
                await set_loop(chat_id, loop - 1)
            else:
                finished = q.pop(0)
                await auto_clean(finished)
            if not db.get(chat_id):
                if not await self.autoplay(chat_id, finished):
                    await clear(chat_id)
                    try: await client.leave_call(chat_id)
                    except Exception: pass
                    self.active_calls.discard(chat_id)
                    return
            await self.play_current(client, chat_id)

    @capture_internal_err
    async def play(self, client, chat_id):
        await self.advance(client, chat_id)

    async def play_current(self, client, chat_id):
        while db.get(chat_id):
            t = db[chat_id][0]
            if not isinstance(t, dict):
                db[chat_id].pop(0); continue
            lang = await get_lang(chat_id)
            _ = get_string(lang)
            title = str(t.get("title") or "Unknown Title").title()
            vid = t.get("vidid")
            streamtype = t.get("streamtype","audio")
            video = streamtype == "video"
            t["played"] = 0
            if vid and str(vid) not in {"telegram","soundcloud"}:
                remember_played(chat_id, str(vid), title)
            await delete_queue_message(chat_id, t)
            try:
                queued = str(t.get("file") or "")
                if queued.startswith("live_"):
                    _, path = await YouTube.video(vid, True)
                elif queued.startswith("vid_"):
                    m = await app.send_message(t.get("chat_id",chat_id), _["call_7"])
                    path = await self.source(vid, title, m, streamtype)
                    try: await m.delete()
                    except Exception: pass
                elif queued.startswith("index_") or queued == "index_url":
                    path = vid
                else:
                    path = queued
                if not path:
                    raise AssistantErr("No playable source")
                await self._play(client, chat_id, media(path, video))
                self.active_calls.add(chat_id)
                self.watchdog(client, chat_id)
                button = stream_markup(_, chat_id)
                if vid in {"telegram","soundcloud"}:
                    photo = config.SOUNCLOUD_IMG_URL if vid == "soundcloud" else (config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL)
                    run = await app.send_photo(t.get("chat_id",chat_id), photo=photo,
                        caption=_["stream_1"].format(config.SUPPORT_CHAT,title[:23],t.get("dur"),t.get("by") or "Unknown"),
                        reply_markup=InlineKeyboardMarkup(button))
                    t["mystic"] = run
                    remember_player_message(chat_id, run)
                else:
                    if queued.startswith("vid_"):
                        schedule_youtube_precache_for_chat(chat_id)
                    schedule_stream_card(chat_id=chat_id, original_chat_id=t.get("chat_id",chat_id),
                        videoid=vid, user_id=t.get("user_id"),
                        caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{vid}",title[:23],t.get("dur"),t.get("by") or "Unknown"),
                        button=button, markup="stream")
                return
            except Exception as e:
                LOGGER(__name__).warning("Skipping unplayable track %s: %s", title, e)
                bad = db[chat_id].pop(0)
                await auto_clean(bad)

    @capture_internal_err
    async def join_call(self, chat_id, original_chat_id, link, video=None, image=None):
        assistant = await group_assistant(self, chat_id)
        _ = get_string(await get_lang(chat_id))
        try:
            await self._play(assistant, chat_id, media(link, bool(video)))
        except (NoActiveGroupCall, ChatAdminRequired):
            raise AssistantErr(_["call_8"])
        except TelegramServerError:
            raise AssistantErr(_["call_10"])
        self.active_calls.add(chat_id)
        await add_active_chat(chat_id); await music_on(chat_id)
        if video: await add_active_video_chat(chat_id)
        self.watchdog(assistant, chat_id)
        if await is_autoend():
            counter[chat_id] = {}
            autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    @capture_internal_err
    async def stop_stream(self, chat_id):
        assistant = await group_assistant(self, chat_id)
        await clear(chat_id)
        try: await assistant.leave_call(chat_id)
        except Exception: pass
        self.active_calls.discard(chat_id)

    @capture_internal_err
    async def force_stop_stream(self, chat_id):
        await self.stop_stream(chat_id)

    @capture_internal_err
    async def pause_stream(self, chat_id):
        a = await group_assistant(self, chat_id); await a.pause(chat_id)

    @capture_internal_err
    async def resume_stream(self, chat_id):
        a = await group_assistant(self, chat_id); await a.resume(chat_id); self.watchdog(a, chat_id)

    @capture_internal_err
    async def mute_stream(self, chat_id):
        await (await group_assistant(self, chat_id)).mute(chat_id)

    @capture_internal_err
    async def unmute_stream(self, chat_id):
        await (await group_assistant(self, chat_id)).unmute(chat_id)

    @capture_internal_err
    async def skip_stream(self, chat_id, link, video=None, image=None):
        a = await group_assistant(self, chat_id)
        await self._play(a, chat_id, media(link, bool(video)))
        self.watchdog(a, chat_id)

    @capture_internal_err
    async def vc_users(self, chat_id):
        return [p.user_id for p in await (await group_assistant(self, chat_id)).get_participants(chat_id) if not getattr(p,"is_muted",False)]

    @capture_internal_err
    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        a = await group_assistant(self, chat_id)
        await self._play(a, chat_id, media(file_path, mode == "video", f"-ss {to_seek} -to {duration}"))
        self.watchdog(a, chat_id)

    @capture_internal_err
    async def speedup_stream(self, chat_id, file_path, speed, playing):
        a = await group_assistant(self, chat_id)
        out = os.path.join("playback",str(speed),os.path.basename(file_path))
        os.makedirs(os.path.dirname(out),exist_ok=True)
        if not os.path.exists(out):
            p = await asyncio.create_subprocess_exec("ffmpeg","-i",file_path,"-filter:v",f"setpts={2.0/float(speed)}*PTS","-filter:a",f"atempo={speed}",out,
                stdin=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,env=build_subprocess_env())
            await p.communicate()
        dur = int(await asyncio.get_running_loop().run_in_executor(None,check_duration,out))
        played, converted = speed_converter(playing[0]["played"],speed)
        await self._play(a,chat_id,media(out,playing[0]["streamtype"]=="video",f"-ss {played} -to {seconds_to_min(dur)}"))
        db[chat_id][0].update({"played":converted,"dur":seconds_to_min(dur),"seconds":dur,"speed_path":out,"speed":speed})
        self.watchdog(a,chat_id)

    async def start(self):
        for x in [self.one,self.two,self.three,self.four,self.five]:
            if x: await x.start()

    @capture_internal_err
    async def ping(self):
        p = [x.ping for x in [self.one,self.two,self.three,self.four,self.five] if x]
        return str(round(sum(p)/len(p),3)) if p else "0.0"

    @capture_internal_err
    async def decorators(self):
        critical = (ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP |
                    ChatUpdate.Status.CLOSED_VOICE_CHAT | ChatUpdate.Status.DISCARDED_CALL |
                    ChatUpdate.Status.BUSY_CALL)
        async def handler(client, update):
            if isinstance(update, ChatUpdate):
                if (update.status & ChatUpdate.Status.LEFT_CALL) or (update.status & critical):
                    await self.stop_stream(update.chat_id)
            elif isinstance(update, StreamEnded):
                a = await group_assistant(self, update.chat_id)
                await self.advance(a, update.chat_id)
        for a in [x for x in [self.one,self.two,self.three,self.four,self.five] if x]:
            a.on_update()(handler)

JARVIS = Call()
