import asyncio
import random
from typing import Dict, List, Union

from VIVAANXMUSIC import userbot
from VIVAANXMUSIC.core.mongo import mongodb


authdb = mongodb.adminauth
authuserdb = mongodb.authuser
autoenddb = mongodb.autoend
autodeletedb = mongodb.autodelete
autoplaydb = mongodb.autoplay
assdb = mongodb.assistants
blacklist_chatdb = mongodb.blacklistChat
blockeddb = mongodb.blockedusers
chatsdb = mongodb.chats
channeldb = mongodb.cplaymode
countdb = mongodb.upcount
gbansdb = mongodb.gban
langdb = mongodb.language
messagevaultdb = mongodb.messagevault
onoffdb = mongodb.onoffper
playmodedb = mongodb.playmode
playtypedb = mongodb.playtypedb
skipdb = mongodb.skipmode
sudoersdb = mongodb.sudoers
usersdb = mongodb.tgusersdb
vcnotifydb = mongodb.vcnotify


active = []
activevideo = []
assistantdict = {}
autoend = {}
autodelete = {}
autoplay = {}
count = {}
channelconnect = {}
langm = {}
loop = {}
maintenance = []
nonadmin = {}
pause = {}
playmode = {}
playtype = {}
skipmode = {}
mute = {}
vcnotify = {}


ASSISTANT_WAIT_TIMEOUT = 30
ASSISTANT_WAIT_INTERVAL = 0.5


async def _available_assistants() -> list[int]:
    from VIVAANXMUSIC.core.userbot import assistants

    if assistants:
        return list(assistants)

    deadline = asyncio.get_running_loop().time() + ASSISTANT_WAIT_TIMEOUT

    while (
        not assistants
        and asyncio.get_running_loop().time() < deadline
    ):
        await asyncio.sleep(ASSISTANT_WAIT_INTERVAL)

    if not assistants:
        raise RuntimeError(
            "No active assistant client is available. "
            "Check STRING_SESSION values and assistant startup logs."
        )

    return list(assistants)


async def get_assistant_number(chat_id: int):
    return assistantdict.get(chat_id)


async def get_client(assistant: int):
    assistant = int(assistant)

    clients = {
        1: userbot.one,
        2: userbot.two,
        3: userbot.three,
        4: userbot.four,
        5: userbot.five,
    }

    return clients.get(assistant)


async def set_assistant_new(chat_id, number):
    number = int(number)

    assistantdict[chat_id] = number

    await assdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"assistant": number}},
        upsert=True,
    )


async def set_assistant(chat_id):
    assistants = await _available_assistants()

    ran_assistant = random.choice(assistants)

    assistantdict[chat_id] = ran_assistant

    await assdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"assistant": ran_assistant}},
        upsert=True,
    )

    return await get_client(ran_assistant)


async def get_assistant(chat_id: int):
    assistants = await _available_assistants()

    assistant = assistantdict.get(chat_id)

    if assistant is None:
        dbassistant = await assdb.find_one(
            {"chat_id": chat_id}
        )

        if not dbassistant:
            return await set_assistant(chat_id)

        got_assis = dbassistant.get("assistant")

        if got_assis in assistants:
            assistantdict[chat_id] = got_assis
            return await get_client(got_assis)

        return await set_assistant(chat_id)

    if assistant in assistants:
        return await get_client(assistant)

    return await set_assistant(chat_id)


async def set_calls_assistant(chat_id):
    assistants = await _available_assistants()

    ran_assistant = random.choice(assistants)

    assistantdict[chat_id] = ran_assistant

    await assdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"assistant": ran_assistant}},
        upsert=True,
    )

    return ran_assistant


async def group_assistant(self, chat_id: int):
    assistants = await _available_assistants()

    assistant = assistantdict.get(chat_id)

    if assistant is None:
        dbassistant = await assdb.find_one(
            {"chat_id": chat_id}
        )

        if not dbassistant:
            assis = await set_calls_assistant(chat_id)
        else:
            assis = dbassistant.get("assistant")

            if assis in assistants:
                assistantdict[chat_id] = assis
            else:
                assis = await set_calls_assistant(chat_id)
    else:
        if assistant in assistants:
            assis = assistant
        else:
            assis = await set_calls_assistant(chat_id)

    clients = {
        1: self.one,
        2: self.two,
        3: self.three,
        4: self.four,
        5: self.five,
    }

    return clients.get(int(assis))


async def is_skipmode(chat_id: int) -> bool:
    mode = skipmode.get(chat_id)

    if mode is None:
        user = await skipdb.find_one(
            {"chat_id": chat_id}
        )

        if not user:
            skipmode[chat_id] = True
            return True

        skipmode[chat_id] = False
        return False

    return bool(mode)


async def skip_on(chat_id: int):
    skipmode[chat_id] = True

    user = await skipdb.find_one(
        {"chat_id": chat_id}
    )

    if user:
        return await skipdb.delete_one(
            {"chat_id": chat_id}
        )


async def skip_off(chat_id: int):
    skipmode[chat_id] = False

    user = await skipdb.find_one(
        {"chat_id": chat_id}
    )

    if not user:
        return await skipdb.insert_one(
            {"chat_id": chat_id}
        )


async def get_upvote_count(chat_id: int) -> int:
    mode = count.get(chat_id)

    if mode is None:
        data = await countdb.find_one(
            {"chat_id": chat_id}
        )

        if not data:
            count[chat_id] = 5
            return 5

        count[chat_id] = data["mode"]
        return data["mode"]

    return mode


async def set_upvotes(chat_id: int, mode: int):
    count[chat_id] = mode

    await countdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"mode": mode}},
        upsert=True,
    )


# =========================================================
# AUTOPLAY
# =========================================================

async def get_autoplay(chat_id: int) -> bool:
    """
    Get autoplay status.
    Default: False
    """

    mode = autoplay.get(chat_id)

    if mode is None:
        data = await autoplaydb.find_one(
            {"chat_id": chat_id}
        )

        if not data:
            autoplay[chat_id] = False
            return False

        mode = bool(data.get("mode", False))
        autoplay[chat_id] = mode

        return mode

    return bool(mode)


async def set_autoplay(chat_id: int, mode: bool):
    """
    Enable or disable autoplay.
    """

    enabled = bool(mode)

    autoplay[chat_id] = enabled

    await autoplaydb.update_one(
        {"chat_id": chat_id},
        {"$set": {"mode": enabled}},
        upsert=True,
    )


# OLD FUNCTION COMPATIBILITY
# Many AloneMusic / QueenMusic call.py files use these names.

async def is_autoplay_on(chat_id: int) -> bool:
    return await get_autoplay(chat_id)


async def autoplay_on(chat_id: int):
    await set_autoplay(chat_id, True)


async def autoplay_off(chat_id: int):
    await set_autoplay(chat_id, False)


async def get_autodelete(chat_id: int) -> bool:
    mode = autodelete.get(chat_id)

    if mode is None:
        data = await autodeletedb.find_one(
            {"chat_id": chat_id}
        )

        if not data:
            autodelete[chat_id] = False
            return False

        mode = bool(data.get("mode", False))
        autodelete[chat_id] = mode

        return mode

    return bool(mode)


async def set_autodelete(chat_id: int, mode: bool):
    enabled = bool(mode)

    autodelete[chat_id] = enabled

    await autodeletedb.update_one(
        {"chat_id": chat_id},
        {"$set": {"mode": enabled}},
        upsert=True,
    )


async def get_vcnotify(chat_id: int) -> bool:
    mode = vcnotify.get(chat_id)

    if mode is None:
        data = await vcnotifydb.find_one(
            {"chat_id": chat_id}
        )

        if not data:
            vcnotify[chat_id] = False
            return False

        mode = bool(data.get("mode", False))
        vcnotify[chat_id] = mode

        return mode

    return bool(mode)


async def set_vcnotify(chat_id: int, mode: bool):
    enabled = bool(mode)

    vcnotify[chat_id] = enabled

    await vcnotifydb.update_one(
        {"chat_id": chat_id},
        {"$set": {"mode": enabled}},
        upsert=True,
    )


async def get_vault_message(code: str):
    return await messagevaultdb.find_one(
        {"code": code}
    )


async def save_vault_message(code: str, data: dict):
    data = dict(data)
    data["code"] = code

    await messagevaultdb.update_one(
        {"code": code},
        {"$set": data},
        upsert=True,
    )


async def delete_vault_message(code: str):
    await messagevaultdb.delete_one(
        {"code": code}
    )


async def is_autoend() -> bool:
    chat_id = 1234

    user = await autoenddb.find_one(
        {"chat_id": chat_id}
    )

    return bool(user)


async def autoend_on():
    chat_id = 1234

    user = await autoenddb.find_one(
        {"chat_id": chat_id}
    )

    if not user:
        await autoenddb.insert_one(
            {"chat_id": chat_id}
        )


async def autoend_off():
    chat_id = 1234

    await autoenddb.delete_one(
        {"chat_id": chat_id}
    )


async def get_loop(chat_id: int) -> int:
    return loop.get(chat_id, 0)


async def set_loop(chat_id: int, mode: int):
    loop[chat_id] = int(mode)


async def get_cmode(chat_id: int):
    mode = channelconnect.get(chat_id)

    if mode is None:
        data = await channeldb.find_one(
            {"chat_id": chat_id}
        )

        if not data:
            return None

        mode = data.get("mode")
        channelconnect[chat_id] = mode

    return mode


async def set_cmode(chat_id: int, mode: int):
    channelconnect[chat_id] = mode

    await channeldb.update_one(
        {"chat_id": chat_id},
        {"$set": {"mode": mode}},
        upsert=True,
    )


async def get_playtype(chat_id: int) -> str:
    mode = playtype.get(chat_id)

    if mode is None:
        data = await playtypedb.find_one(
            {"chat_id": chat_id}
        )

        if not data:
            playtype[chat_id] = "Everyone"
            return "Everyone"

        mode = data.get("mode", "Everyone")
        playtype[chat_id] = mode

    return mode


async def set_playtype(chat_id: int, mode: str):
    playtype[chat_id] = mode

    await playtypedb.update_one(
        {"chat_id": chat_id},
        {"$set": {"mode": mode}},
        upsert=True,
    )


async def get_playmode(chat_id: int) -> str:
    mode = playmode.get(chat_id)

    if mode is None:
        data = await playmodedb.find_one(
            {"chat_id": chat_id}
        )

        if not data:
            playmode[chat_id] = "Direct"
            return "Direct"

        mode = data.get("mode", "Direct")
        playmode[chat_id] = mode

    return mode


async def set_playmode(chat_id: int, mode: str):
    playmode[chat_id] = mode

    await playmodedb.update_one(
        {"chat_id": chat_id},
        {"$set": {"mode": mode}},
        upsert=True,
    )


async def get_lang(chat_id: int) -> str:
    mode = langm.get(chat_id)

    if mode is None:
        data = await langdb.find_one(
            {"chat_id": chat_id}
        )

        if not data:
            langm[chat_id] = "en"
            return "en"

        mode = data.get("lang", "en")
        langm[chat_id] = mode

    return mode


async def set_lang(chat_id: int, lang: str):
    langm[chat_id] = lang

    await langdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"lang": lang}},
        upsert=True,
    )


async def is_music_playing(chat_id: int) -> bool:
    return bool(pause.get(chat_id, False))


async def music_on(chat_id: int):
    pause[chat_id] = True


async def music_off(chat_id: int):
    pause[chat_id] = False


async def is_muted(chat_id: int) -> bool:
    return bool(mute.get(chat_id, False))


async def mute_on(chat_id: int):
    mute[chat_id] = True


async def mute_off(chat_id: int):
    mute[chat_id] = False


async def get_active_chats() -> list:
    return active


async def is_active_chat(chat_id: int) -> bool:
    return chat_id in active


async def add_active_chat(chat_id: int):
    if chat_id not in active:
        active.append(chat_id)


async def remove_active_chat(chat_id: int):
    if chat_id in active:
        active.remove(chat_id)


async def get_active_video_chats() -> list:
    return activevideo


async def is_active_video_chat(chat_id: int) -> bool:
    return chat_id in activevideo


async def add_active_video_chat(chat_id: int):
    if chat_id not in activevideo:
        activevideo.append(chat_id)


async def remove_active_video_chat(chat_id: int):
    if chat_id in activevideo:
        activevideo.remove(chat_id)


async def check_nonadmin_chat(chat_id: int) -> bool:
    user = await authdb.find_one(
        {"chat_id": chat_id}
    )

    return bool(user)


async def is_nonadmin_chat(chat_id: int) -> bool:
    mode = nonadmin.get(chat_id)

    if mode is None:
        user = await authdb.find_one(
            {"chat_id": chat_id}
        )

        mode = bool(user)
        nonadmin[chat_id] = mode

    return bool(mode)


async def add_nonadmin_chat(chat_id: int):
    nonadmin[chat_id] = True

    if not await check_nonadmin_chat(chat_id):
        return await authdb.insert_one(
            {"chat_id": chat_id}
        )


async def remove_nonadmin_chat(chat_id: int):
    nonadmin[chat_id] = False

    if await check_nonadmin_chat(chat_id):
        return await authdb.delete_one(
            {"chat_id": chat_id}
        )


async def is_on_off(on_off: int) -> bool:
    data = await onoffdb.find_one(
        {"on_off": on_off}
    )

    return bool(data)


async def add_on(on_off: int):
    if not await is_on_off(on_off):
        return await onoffdb.insert_one(
            {"on_off": on_off}
        )


async def add_off(on_off: int):
    if await is_on_off(on_off):
        return await onoffdb.delete_one(
            {"on_off": on_off}
        )


async def is_maintenance():
    if not maintenance:
        get = await onoffdb.find_one(
            {"on_off": 1}
        )

        if not get:
            maintenance.clear()
            maintenance.append(2)
            return True

        maintenance.clear()
        maintenance.append(1)
        return False

    return 1 not in maintenance


async def maintenance_off():
    maintenance.clear()
    maintenance.append(2)

    if await is_on_off(1):
        return await onoffdb.delete_one(
            {"on_off": 1}
        )


async def maintenance_on():
    maintenance.clear()
    maintenance.append(1)

    if not await is_on_off(1):
        return await onoffdb.insert_one(
            {"on_off": 1}
        )


async def is_served_user(user_id: int) -> bool:
    user = await usersdb.find_one(
        {"user_id": user_id}
    )

    return bool(user)


async def get_served_users() -> list:
    users_list = []

    async for user in usersdb.find(
        {"user_id": {"$gt": 0}}
    ):
        users_list.append(user)

    return users_list


async def add_served_user(user_id: int):
    if not await is_served_user(user_id):
        return await usersdb.insert_one(
            {"user_id": user_id}
        )


async def remove_served_user(user_id: int):
    if await is_served_user(user_id):
        return await usersdb.delete_one(
            {"user_id": user_id}
        )


async def get_served_chats() -> list:
    chats_list = []

    async for chat in chatsdb.find(
        {"chat_id": {"$lt": 0}}
    ):
        chats_list.append(chat)

    return chats_list


async def is_served_chat(chat_id: int) -> bool:
    chat = await chatsdb.find_one(
        {"chat_id": chat_id}
    )

    return bool(chat)


async def add_served_chat(chat_id: int):
    if not await is_served_chat(chat_id):
        return await chatsdb.insert_one(
            {"chat_id": chat_id}
        )


async def remove_served_chat(chat_id: int):
    if await is_served_chat(chat_id):
        return await chatsdb.delete_one(
            {"chat_id": chat_id}
        )


async def blacklisted_chats() -> list:
    chats_list = []

    async for chat in blacklist_chatdb.find(
        {"chat_id": {"$lt": 0}}
    ):
        chats_list.append(chat["chat_id"])

    return chats_list


async def blacklist_chat(chat_id: int) -> bool:
    if not await blacklist_chatdb.find_one(
        {"chat_id": chat_id}
    ):
        await blacklist_chatdb.insert_one(
            {"chat_id": chat_id}
        )
        return True

    return False


async def whitelist_chat(chat_id: int) -> bool:
    if await blacklist_chatdb.find_one(
        {"chat_id": chat_id}
    ):
        await blacklist_chatdb.delete_one(
            {"chat_id": chat_id}
        )
        return True

    return False


async def _get_authusers(
    chat_id: int
) -> Dict[str, int]:
    notes = await authuserdb.find_one(
        {"chat_id": chat_id}
    )

    if not notes:
        return {}

    return notes.get("notes", {})


async def get_authuser_names(
    chat_id: int
) -> List[str]:
    notes = await _get_authusers(chat_id)
    return list(notes.keys())


async def get_authuser(
    chat_id: int,
    name: str
) -> Union[bool, dict]:
    notes = await _get_authusers(chat_id)

    if name in notes:
        return notes[name]

    return False


async def save_authuser(
    chat_id: int,
    name: str,
    note: dict
):
    notes = await _get_authusers(chat_id)

    notes[name] = note

    await authuserdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"notes": notes}},
        upsert=True,
    )


async def delete_authuser(
    chat_id: int,
    name: str
) -> bool:
    notes = await _get_authusers(chat_id)

    if name not in notes:
        return False

    del notes[name]

    await authuserdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"notes": notes}},
        upsert=True,
    )

    return True


async def get_gbanned() -> list:
    results = []

    async for user in gbansdb.find(
        {"user_id": {"$gt": 0}}
    ):
        results.append(user["user_id"])

    return results


async def is_gbanned_user(
    user_id: int
) -> bool:
    user = await gbansdb.find_one(
        {"user_id": user_id}
    )

    return bool(user)


async def add_gban_user(user_id: int):
    if not await is_gbanned_user(user_id):
        return await gbansdb.insert_one(
            {"user_id": user_id}
        )


async def remove_gban_user(user_id: int):
    if await is_gbanned_user(user_id):
        return await gbansdb.delete_one(
            {"user_id": user_id}
        )


async def get_sudoers() -> list:
    sudoers = await sudoersdb.find_one(
        {"sudo": "sudo"}
    )

    if not sudoers:
        return []

    return sudoers.get("sudoers", [])


async def add_sudo(user_id: int) -> bool:
    sudoers = await get_sudoers()

    if user_id in sudoers:
        return False

    sudoers.append(user_id)

    await sudoersdb.update_one(
        {"sudo": "sudo"},
        {"$set": {"sudoers": sudoers}},
        upsert=True,
    )

    return True


async def remove_sudo(user_id: int) -> bool:
    sudoers = await get_sudoers()

    if user_id not in sudoers:
        return False

    sudoers.remove(user_id)

    await sudoersdb.update_one(
        {"sudo": "sudo"},
        {"$set": {"sudoers": sudoers}},
        upsert=True,
    )

    return True


async def get_banned_users() -> list:
    results = []

    async for user in blockeddb.find(
        {"user_id": {"$gt": 0}}
    ):
        results.append(user["user_id"])

    return results


async def get_banned_count() -> int:
    users = blockeddb.find(
        {"user_id": {"$gt": 0}}
    )

    users = await users.to_list(
        length=100000
    )

    return len(users)


async def is_banned_user(
    user_id: int
) -> bool:
    user = await blockeddb.find_one(
        {"user_id": user_id}
    )

    return bool(user)


async def add_banned_user(user_id: int):
    if not await is_banned_user(user_id):
        return await blockeddb.insert_one(
            {"user_id": user_id}
        )


async def remove_banned_user(user_id: int):
    if await is_banned_user(user_id):
        return await blockeddb.delete_one(
            {"user_id": user_id}
    )
    
