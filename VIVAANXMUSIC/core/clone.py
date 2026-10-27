"""Clone bot manager for FoxyMusic.

Clones run as separate Pyrogram bot clients while sharing this process's
music/playback services and MongoDB. Telegram webhooks are cleared because
this application is a worker-style Pyrogram polling bot.
"""
import asyncio
import copy
import inspect
import re
import time
from contextvars import ContextVar
from functools import wraps
from types import MethodType

import aiohttp
from pyrogram import Client

from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from VIVAANXMUSIC.core.mongo import mongodb
from VIVAANXMUSIC.logging import LOGGER

MAX_CLONES_PER_USER = 5
TOKEN_RE = re.compile(r"^[0-9]{5,15}:[A-Za-z0-9_-]{30,60}$")
ACTIVE_CLONE = ContextVar("foxy_active_clone_client", default=None)
CLONE_CLIENTS = {}  # token -> Client
CLONE_META = {}     # token -> {owner_id, username, bot_id}
_ROUTING_INSTALLED = False
_ROUTED_METHODS = (
    "send_message", "send_photo", "send_video", "send_audio", "send_voice",
    "send_document", "send_animation", "send_sticker", "send_video_note",
    "send_media_group", "edit_message_text", "edit_message_caption",
    "edit_message_media", "edit_message_reply_markup", "delete_messages",
    "delete_messages", "delete_user_history", "get_chat", "get_chat_member",
    "get_chat_members", "get_chat_member_count", "get_users", "get_me",
    "get_messages", "get_chat_history", "get_file", "download_media",
    "ban_chat_member", "unban_chat_member", "restrict_chat_member",
    "promote_chat_member", "export_chat_invite_link", "leave_chat",
    "join_chat", "pin_chat_message", "unpin_chat_message",
    "set_chat_title", "set_chat_description", "set_chat_photo",
    "delete_chat_photo", "answer_callback_query", "send_chat_action",
    "get_chat_event_log", "get_discussion_replies", "copy_message",
    "forward_messages", "set_bot_commands", "get_bot_commands",
    "send_location", "send_contact", "send_poll", "stop_poll", "invoke",
)


def install_app_routing(app):
    """Route legacy global `app.*` API calls to the bot handling this update."""
    global _ROUTING_INSTALLED
    if _ROUTING_INSTALLED:
        return
    for name in _ROUTED_METHODS:
        original = getattr(app, name, None)
        if original is None or not callable(original):
            continue

        if inspect.isasyncgenfunction(original):
            def make_generator(method_name, fallback):
                async def routed(self, *args, **kwargs):
                    child = ACTIVE_CLONE.get()
                    target = getattr(child, method_name, None) if child else None
                    if target:
                        async for item in target(*args, **kwargs):
                            yield item
                    else:
                        async for item in fallback(*args, **kwargs):
                            yield item
                routed.__name__ = method_name
                routed.__qualname__ = method_name
                return routed
            setattr(app, name, MethodType(make_generator(name, original), app))
        elif inspect.iscoroutinefunction(original):
            def make_async(method_name, fallback):
                @wraps(fallback)
                async def routed(self, *args, **kwargs):
                    child = ACTIVE_CLONE.get()
                    target = getattr(child, method_name, None) if child else None
                    if target:
                        return await target(*args, **kwargs)
                    return await fallback(*args, **kwargs)
                return routed
            setattr(app, name, MethodType(make_async(name, original), app))
    _ROUTING_INSTALLED = True


def _copy_handlers(source, target):
    """Copy each registered handler while adding a per-update clone context."""
    for group, handlers in source.dispatcher.groups.items():
        for original in list(handlers):
            handler = copy.copy(original)
            callback = original.callback

            @wraps(callback)
            async def routed_callback(client, *args, __callback=callback, **kwargs):
                token = ACTIVE_CLONE.set(client)
                try:
                    return await __callback(client, *args, **kwargs)
                finally:
                    ACTIVE_CLONE.reset(token)

            handler.callback = routed_callback
            target.add_handler(handler, group)


async def _telegram_call(token, method, payload=None):
    timeout = aiohttp.ClientTimeout(total=12)
    url = f"https://api.telegram.org/bot{token}/{method}"
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload or {}) as response:
            data = await response.json(content_type=None)
            if response.status != 200 or not data.get("ok"):
                description = data.get("description", f"HTTP {response.status}")
                raise RuntimeError(description)
            return data.get("result")


def _collection():
    return mongodb.clone_bots


async def _make_client(app, token):
    install_app_routing(app)
    child = Client(
        name=f"foxy_clone_{token.split(':', 1)[0]}",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=token,
        in_memory=True,
        workers=16,
        max_concurrent_transmissions=4,
    )
    _copy_handlers(app, child)
    return child


async def start_clone(app, token, owner_id=None, persist=False):
    """Validate and start a clone. Never log or return its token."""
    if not TOKEN_RE.fullmatch(token):
        raise ValueError("Invalid Telegram bot token format.")
    existing = CLONE_CLIENTS.get(token)
    if existing and existing.is_connected:
        return await existing.get_me()

    # This target uses Pyrogram polling, not an HTTP webhook server. Remove a
    # previously configured webhook so Telegram permits getUpdates polling.
    await _telegram_call(token, "deleteWebhook", {"drop_pending_updates": False})
    child = await _make_client(app, token)
    try:
        await child.start()
        me = await child.get_me()
        if not me.is_bot:
            raise ValueError("The supplied token does not belong to a bot.")
        CLONE_CLIENTS[token] = child
        CLONE_META[token] = {
            "owner_id": int(owner_id or OWNER_ID),
            "username": me.username or str(me.id),
            "bot_id": me.id,
        }
        try:
            from pyrogram.types import BotCommand
            await child.set_bot_commands([
                BotCommand("start", "Start the bot"),
                BotCommand("help", "Open help menu"),
                BotCommand("play", "Play music in voice chat"),
                BotCommand("queue", "Show current queue"),
                BotCommand("pause", "Pause playback"),
                BotCommand("resume", "Resume playback"),
                BotCommand("skip", "Skip current song"),
                BotCommand("stop", "Stop playback"),
                BotCommand("clone", "Start your own clone bot"),
                BotCommand("unclone", "Remove your clone bot"),
            ])
        except Exception as exc:
            LOGGER(__name__).warning("Could not set clone command menu: %s", type(exc).__name__)

        if persist:
            await _collection().update_one(
                {"_id": token},
                {"$set": {
                    "bot_id": me.id,
                    "username": me.username or str(me.id),
                    "owner_id": int(owner_id or OWNER_ID),
                }, "$setOnInsert": {"created_at": int(time.time())}},
                upsert=True,
            )
        LOGGER(__name__).info("Clone bot started: @%s (token hidden)", me.username or me.id)
        return me
    except Exception:
        CLONE_CLIENTS.pop(token, None)
        CLONE_META.pop(token, None)
        try:
            if child.is_connected:
                await child.stop()
        except Exception:
            pass
        raise


async def stop_clone(token, delete_record=True):
    # Remove the persistent record first, so a database failure cannot leave
    # a stopped clone that unexpectedly comes back on the next restart.
    if delete_record:
        await _collection().delete_one({"_id": token})
    child = CLONE_CLIENTS.pop(token, None)
    meta = CLONE_META.pop(token, {})
    if child:
        try:
            if child.is_connected:
                await child.stop()
        except Exception as exc:
            LOGGER(__name__).warning(
                "Clone stop failed for bot id %s: %s",
                meta.get("bot_id"), type(exc).__name__,
            )
    try:
        await _telegram_call(token, "deleteWebhook", {"drop_pending_updates": False})
    except Exception:
        pass


async def restore_clones(app):
    install_app_routing(app)
    try:
        cursor = _collection().find({})
        records = await cursor.to_list(length=None)
    except Exception as exc:
        LOGGER(__name__).error("Could not load saved clones from MongoDB: %s", type(exc).__name__)
        return
    for record in records:
        token = record.get("_id")
        if not isinstance(token, str) or not TOKEN_RE.fullmatch(token):
            LOGGER(__name__).warning("Skipping malformed clone record in MongoDB.")
            continue
        try:
            await start_clone(app, token, record.get("owner_id"), persist=False)
            await asyncio.sleep(0.2)
        except Exception as exc:
            LOGGER(__name__).error(
                "Could not restore clone bot id %s: %s",
                record.get("bot_id", "unknown"), type(exc).__name__,
            )


async def restart_all_clones(app):
    try:
        records = await _collection().find({}).to_list(length=None)
    except Exception:
        return 0, 0
    ok = failed = 0
    for record in records:
        token = record.get("_id")
        if not isinstance(token, str) or not TOKEN_RE.fullmatch(token):
            failed += 1
            continue
        await stop_clone(token, delete_record=False)
        try:
            await start_clone(app, token, record.get("owner_id"), persist=False)
            ok += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.2)
    return ok, failed


async def shutdown_clones():
    """Stop in-memory clone clients without deleting their MongoDB records."""
    for token, child in list(CLONE_CLIENTS.items()):
        try:
            if child.is_connected:
                await child.stop()
        except Exception as exc:
            LOGGER(__name__).warning(
                "Clone shutdown failed for bot id %s: %s",
                CLONE_META.get(token, {}).get("bot_id", "unknown"),
                type(exc).__name__,
            )
        finally:
            CLONE_CLIENTS.pop(token, None)
            CLONE_META.pop(token, None)
