import asyncio
import logging

from telethon import TelegramClient, events
from telethon.sessions import StringSession

import config
from filter import matches, matched_keywords
from notifier import send_notification
from sheets import load_channels, load_keywords, write_row

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

def build_link(channel: str, message_id: int) -> str:
    return f"https://t.me/{channel}/{message_id}"


KEYWORDS_RELOAD_INTERVAL = 1800  # seconds


async def main():
    logger.info("Starting monitor...")

    channels = await asyncio.to_thread(load_channels)
    include_kw, exclude_kw = await asyncio.to_thread(load_keywords)

    logger.info(f"Channels: {channels}")
    logger.info(f"Include: {include_kw}")
    logger.info(f"Exclude: {exclude_kw}")

    state = {"include": include_kw, "exclude": exclude_kw}

    async def reload_keywords_loop():
        while True:
            await asyncio.sleep(KEYWORDS_RELOAD_INTERVAL)
            try:
                new_include, new_exclude = await asyncio.to_thread(load_keywords)
                state["include"] = new_include
                state["exclude"] = new_exclude
                logger.info(f"Keywords reloaded: include={len(new_include)}, exclude={len(new_exclude)}")
            except Exception as e:
                logger.error(f"Failed to reload keywords: {e}")

    session = StringSession(config.SESSION_STRING) if config.SESSION_STRING else "monitor_session"

    client = TelegramClient(
        session,
        config.TG_API_ID,
        config.TG_API_HASH,
    )

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        message = event.message
        text = message.text or message.caption or ""

        logger.info(f"Raw text from @{(await event.get_chat()).username}: {text[:300]}")

        if not matches(text, state["include"], state["exclude"]):
            return

        chat = await event.get_chat()
        channel = chat.username or str(chat.id)

        keywords = matched_keywords(text, state["include"])
        link = build_link(channel, message.id)

        logger.info(f"Match in @{channel}: {keywords}")

        await asyncio.gather(
            asyncio.to_thread(write_row, channel, keywords, text, link),
            send_notification(channel, keywords, text, link),
        )

    await client.start()

    # Validate channels — skip ones that don't exist
    valid_channels = []
    for ch in channels:
        try:
            await client.get_input_entity(ch)
            valid_channels.append(ch)
        except ValueError:
            logger.warning(f"Channel not found, skipping: {ch}")

    client.remove_event_handler(handler)
    client.add_event_handler(handler, events.NewMessage(chats=valid_channels))

    logger.info(f"Monitoring {len(valid_channels)}/{len(channels)} channels")
    logger.info("Telethon connected. Waiting for messages...")
    asyncio.create_task(reload_keywords_loop())
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
