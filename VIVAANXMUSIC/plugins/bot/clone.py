import html

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import Message

import config
from VIVAANXMUSIC import app
from VIVAANXMUSIC.core.clone import (
    CLONE_CLIENTS,
    CLONE_META,
    MAX_CLONES_PER_USER,
    TOKEN_RE,
    restart_all_clones,
    start_clone,
    stop_clone,
)
from VIVAANXMUSIC.core.mongo import mongodb
from VIVAANXMUSIC.logging import LOGGER


def _escape(value):
    return html.escape(str(value or ""))


@app.on_message(filters.command("clone"))
async def clone_command(client, message: Message):
    if not message.from_user:
        return
    args = message.command[1:]
    if not args:
        return await message.reply_text(
            "🤖 <b>Make your own Foxy Music bot</b>\n\n"
            "1. Create a bot with @BotFather.\n"
            "2. Send <code>/clone YOUR_BOT_TOKEN</code> here in private.\n\n"
            "⚠️ A bot token is a password. Never share it or post it in a group."
        )

    token = args[0].strip()
    try:
        await message.delete()
    except Exception:
        pass

    if message.chat.type != ChatType.PRIVATE:
        return await message.reply_text(
            "🔒 Token was sent in a group. Treat it as leaked and revoke it via @BotFather."
        )
    if not TOKEN_RE.fullmatch(token):
        return await message.reply_text("❌ Invalid token format. Copy the full token from @BotFather.")
    if token == config.BOT_TOKEN:
        return await message.reply_text("😄 That is the main bot's token. Send your own bot token.")

    owner_id = message.from_user.id
    collection = mongodb.clone_bots
    try:
        existing = await collection.find_one({"_id": token})
    except Exception as exc:
        LOGGER(__name__).error("Clone database lookup failed: %s", type(exc).__name__)
        return await message.reply_text("💾 Database is unavailable right now. Please try again later.")

    if existing and existing.get("owner_id") not in (owner_id, config.OWNER_ID):
        return await message.reply_text("❌ This bot is already registered by another user.")
    if not existing and owner_id != config.OWNER_ID:
        try:
            count = await collection.count_documents({"owner_id": owner_id})
        except Exception:
            return await message.reply_text("💾 Could not check your clone limit. Please try again.")
        if count >= MAX_CLONES_PER_USER:
            return await message.reply_text(
                f"❌ You have reached the limit of {MAX_CLONES_PER_USER} clone bots."
            )

    status = await message.reply_text("⏳ Validating token and starting your clone...")
    try:
        me = await start_clone(app, token, owner_id=owner_id, persist=True)
    except Exception as exc:
        LOGGER(__name__).warning("Clone start failed: %s", type(exc).__name__)
        try:
            await status.edit_text(
                "❌ Clone could not start. Check that the token is correct and that the bot "
                "is not running elsewhere. Please try again after checking the server logs."
            )
        except Exception:
            pass
        return

    try:
        await status.edit_text(
            f"✅ <b>@{_escape(me.username or me.id)} is running!</b>\n\n"
            "Add it to your group, promote it as admin, and use <code>/play</code>.\n"
            "Remove it later with <code>/unclone TOKEN</code> in private chat."
        )
    except Exception:
        pass


@app.on_message(filters.command("unclone") & filters.private)
async def unclone_command(client, message: Message):
    if not message.from_user:
        return
    args = message.command[1:]
    if not args:
        return await message.reply_text("Usage: <code>/unclone TOKEN</code>")

    argument = args[0].strip()
    try:
        await message.delete()
    except Exception:
        pass

    try:
        collection = mongodb.clone_bots
        if TOKEN_RE.fullmatch(argument):
            record = await collection.find_one({"_id": argument})
            token = argument
        else:
            if message.from_user.id != config.OWNER_ID:
                return await message.reply_text("❌ Only the owner can remove a clone by username.")
            record = await collection.find_one({"username": argument.lstrip("@")})
            token = record.get("_id") if record else None
    except Exception as exc:
        LOGGER(__name__).error("Clone removal lookup failed: %s", type(exc).__name__)
        return await message.reply_text("💾 Could not access the clone database.")

    if not record or not token:
        return await message.reply_text("❌ Clone not found.")
    if message.from_user.id not in (record.get("owner_id"), config.OWNER_ID):
        return await message.reply_text("❌ You can only remove your own clone.")

    username = record.get("username") or record.get("bot_id") or "clone"
    try:
        await stop_clone(token, delete_record=True)
    except Exception as exc:
        LOGGER(__name__).error("Clone removal failed: %s", type(exc).__name__)
        return await message.reply_text("❌ Could not fully remove the clone. Check server logs.")
    await message.reply_text(f"🗑️ Clone <b>@{_escape(username)}</b> has been removed.")


@app.on_message(filters.command("clones") & filters.private)
async def clones_command(client, message: Message):
    if not message.from_user or message.from_user.id != config.OWNER_ID:
        return
    try:
        records = await mongodb.clone_bots.find({}).to_list(length=None)
    except Exception as exc:
        LOGGER(__name__).error("Clone listing failed: %s", type(exc).__name__)
        return await message.reply_text("💾 Could not read the clone list.")

    lines = [f"🤖 <b>{len(records)} registered clone(s)</b>"]
    for index, record in enumerate(records[:60], 1):
        username = _escape(record.get("username") or record.get("bot_id") or "unknown")
        owner_id = record.get("owner_id", "unknown")
        running = "🟢" if record.get("_id") in CLONE_CLIENTS else "🔴"
        lines.append(f"{index}. {running} @{username} — owner <code>{owner_id}</code>")
    if len(records) > 60:
        lines.append(f"…and {len(records) - 60} more")
    await message.reply_text("\n".join(lines))


@app.on_message(filters.command("resetclones") & filters.private)
async def resetclones_command(client, message: Message):
    if not message.from_user or message.from_user.id != config.OWNER_ID:
        return
    status = await message.reply_text("🔄 Restarting saved clone bots…")
    try:
        ok, failed = await restart_all_clones(app)
        await status.edit_text(f"✅ Clone reset finished.\nRunning: {ok}\nFailed: {failed}")
    except Exception as exc:
        LOGGER(__name__).error("Clone reset failed: %s", type(exc).__name__)
        await status.edit_text("❌ Clone reset failed. Check server logs.")
