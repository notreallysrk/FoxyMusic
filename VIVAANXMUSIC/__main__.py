import asyncio
import importlib

from pyrogram import idle
from pyrogram.types import BotCommand
from pytgcalls.exceptions import NoActiveGroupCall

import config
from VIVAANXMUSIC import LOGGER, app, userbot
from VIVAANXMUSIC.core.call import JARVIS
from VIVAANXMUSIC.misc import sudo
from VIVAANXMUSIC.plugins import ALL_MODULES
from VIVAANXMUSIC.utils.database import get_banned_users, get_gbanned
from VIVAANXMUSIC.utils.lyrics import close_lyrics_http_client
from config import BANNED_USERS

BOT_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("help", "Open help menu"),
    BotCommand("play", "Play audio in voice chat"),
    BotCommand("vplay", "Play video in voice chat"),
    BotCommand("song", "Download a song"),
    BotCommand("spotify", "Download a Spotify track as audio"),
    BotCommand("apple", "Download an Apple Music track as audio"),
    BotCommand("lyrics", "Search and fetch song lyrics"),
    BotCommand("queue", "Show current queue"),
    BotCommand("player", "Open player controls"),
    BotCommand("autoplay", "Toggle similar-song autoplay"),
    BotCommand("autodelete", "Auto-delete player and queue notices"),
    BotCommand("vcnotify", "Toggle VC join notifications"),
    BotCommand("gpt", "Ask the AI assistant"),
    BotCommand("claude", "Ask Claude-style AI"),
    BotCommand("geminivision", "Analyze a replied image"),
    BotCommand("editimg", "Edit a replied image with AI"),
    BotCommand("getdraw", "Generate an AI image"),
    BotCommand("genvid", "Generate a short AI video"),
    BotCommand("upscale", "Enhance a replied image"),
    BotCommand("rmbg", "Remove image background"),
    BotCommand("weather", "Get weather info"),
    BotCommand("insta", "Download Instagram media"),
    BotCommand("youtube", "Download a YouTube link"),
    BotCommand("facebook", "Download Facebook media"),
    BotCommand("x", "Download X/Twitter media"),
    BotCommand("snap", "Download Snapchat media"),
    BotCommand("tiktok", "Download TikTok media"),
    BotCommand("movie", "Search movie info"),
    BotCommand("news", "Get latest topic news"),
    BotCommand("encrypt", "PM-only encrypt replied content"),
    BotCommand("decrypt", "PM-only one-time decrypt"),
    BotCommand("settings", "Open group settings"),
    BotCommand("ping", "Check bot status"),
    BotCommand("clone", "Start your own clone bot"),
    BotCommand("unclone", "Remove your clone bot"),
    BotCommand("clones", "List registered clone bots (owner)"),
    BotCommand("resetclones", "Restart saved clone bots (owner)"),
]


async def init():
    if (
        not config.STRING1
        and not config.STRING2
        and not config.STRING3
        and not config.STRING4
        and not config.STRING5
    ):
        LOGGER(__name__).error(
            "Assistant session not filled, please fill a Pyrogram session."
        )
        exit()

    await sudo()

    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except Exception:
        pass

    await app.start()
    await app.set_bot_commands(BOT_COMMANDS)
    await userbot.start()
    await JARVIS.start()

    try:
        await JARVIS.stream_call(
            "http://docs.evostream.com/sample_content/assets/sintel1m720p.mp4"
        )
    except NoActiveGroupCall:
        LOGGER("VIVAANXMUSIC").error(
            "Please turn on the voice chat of your log group/channel.\n\nBot stopped."
        )
        exit()
    except Exception:
        pass

    await JARVIS.decorators()
    for all_module in ALL_MODULES:
        importlib.import_module("VIVAANXMUSIC.plugins" + all_module)

    LOGGER("VIVAANXMUSIC.plugins").info("Modules loaded.")

    # Restore saved clone bots only after all plugin handlers have been loaded.
    from VIVAANXMUSIC.core.clone import restore_clones
    await restore_clones(app)
    LOGGER("FOXYMUSIC").info(
        "🦊 Foxy Music Robot Started Successfully..."
    )
    await idle()
    try:
        weather_plugin = importlib.import_module("VIVAANXMUSIC.plugins.Kishu.weather")
        await weather_plugin.close_weather_http_client()
    except Exception:
        pass
    try:
        song_plugin = importlib.import_module("VIVAANXMUSIC.plugins.tools.song")
        await song_plugin.close_song_http_client()
    except Exception:
        pass
    await close_lyrics_http_client()
    try:
        from VIVAANXMUSIC.core.clone import shutdown_clones
        await shutdown_clones()
    except Exception as exc:
        LOGGER("VIVAANXMUSIC").warning(f"Clone shutdown issue: {type(exc).__name__}")
    await app.stop()
    await userbot.stop()
    LOGGER("VIVAANXMUSIC").info("Stopping music bot...")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(init())
