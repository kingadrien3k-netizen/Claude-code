"""Read-only Twitch chat over IRC. Uses an anonymous login, so no token is needed."""
from __future__ import annotations

import asyncio
import logging
import random
import re
import ssl

log = logging.getLogger("clipbot.chat")

HOST, PORT = "irc.chat.twitch.tv", 6697
PRIVMSG = re.compile(r"^(?:@\S+ )?:(\w+)!\S+ PRIVMSG #(\w+) :(.*)$")


async def read_chat(channels: list[str], on_message) -> None:
    """Calls on_message(channel, user, text) forever; reconnects on drops."""
    backoff = 1
    while True:
        try:
            reader, writer = await asyncio.open_connection(HOST, PORT, ssl=ssl.create_default_context())
            nick = f"justinfan{random.randint(10000, 99999)}"
            writer.write(f"PASS SCHMOOPIIE\r\nNICK {nick}\r\n".encode())
            for ch in channels:
                writer.write(f"JOIN #{ch}\r\n".encode())
            await writer.drain()
            log.info("connected to chat: %s", ", ".join(channels))
            backoff = 1
            while True:
                raw = await asyncio.wait_for(reader.readline(), timeout=360)
                if not raw:
                    raise ConnectionError("chat connection closed")
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if line.startswith("PING"):
                    writer.write(line.replace("PING", "PONG", 1).encode() + b"\r\n")
                    await writer.drain()
                    continue
                m = PRIVMSG.match(line)
                if m:
                    on_message(m.group(2).lower(), m.group(1), m.group(3))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - keep the bot alive
            log.warning("chat error (%s); reconnecting in %ss", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
