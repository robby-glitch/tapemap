"""tools/telegram_setup.py -- connect TapeMap's Telegram alerts to her chat, once (spec 2026-10-25-message-window-telegram §4).

    1. In Telegram, send /start to her bot (Telegram keeps it for getUpdates about 24 hours).
    2. python tools/telegram_setup.py

Reads the token from telegr/bot.txt (telegram_out.token), asks getUpdates for the newest PRIVATE chat that wrote to the
bot, writes its id to telegr/chat.txt (git-ignored, as bot.txt) and sends "TapeMap connected ✓" there. The token is never
printed, logged or written anywhere else. Outbound only: the bot is never asked to read commands later.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import telegram_out  # noqa: E402

UPDATES_TIMEOUT = telegram_out.TIMEOUT_S


def latest_private(updates):
    """The newest private chat in a getUpdates reply -> (chat id, first name), or None."""
    best = None
    for u in (updates or {}).get("result") or ():
        ch = ((u.get("message") or u.get("edited_message") or {}).get("chat")) or {}
        if ch.get("type") == "private" and ch.get("id") is not None and (best is None or u.get("update_id", 0) > best[0]):
            best = (u.get("update_id", 0), str(ch["id"]), ch.get("first_name") or "")
    return best[1:] if best else None


def main():
    tok = telegram_out.token()
    if not tok:
        print("telegr/bot.txt has no bot-token line -- nothing done.")
        return 1
    try:
        req = urllib.request.Request(telegram_out.API.format(tok, "getUpdates"))
        with telegram_out._open(req, timeout=UPDATES_TIMEOUT) as r:
            got = json.loads(r.read().decode("utf-8") or "{}")
    except Exception as e:  # noqa: BLE001 -- said plainly, the token scrubbed
        print("Telegram did not answer: " + telegram_out.scrub(f"{type(e).__name__}: {e}"))
        return 1
    hit = latest_private(got)
    if not hit:
        print("No private chat has written to the bot lately. Send /start to the bot in Telegram, then run this again.")
        return 1
    chat_id, who = hit
    os.makedirs(telegram_out.DIR, exist_ok=True)
    with open(os.path.join(telegram_out.DIR, "chat.txt"), "w", encoding="utf-8") as f:
        f.write(chat_id + "\n")
    if not telegram_out.send(tok, chat_id, "TapeMap connected ✓"):
        print(f"Saved the chat ({who or 'private chat'}) to telegr/chat.txt, but the test message did not go through "
              "(the reason is above). Run this again.")
        return 1
    print(f"Saved the chat ({who or 'private chat'}) to telegr/chat.txt. Sent: TapeMap connected ✓")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
