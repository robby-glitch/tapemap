"""tools/telegram_setup.py: the newest PRIVATE chat from getUpdates becomes telegr/chat.txt and hears "TapeMap connected ✓";
the token is never printed. A fake opener (no network), and conftest points telegram_out.DIR at tmp_path."""
import json
import os
import sys
import urllib.parse

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
import telegram_out as tg  # noqa: E402
import telegram_setup  # noqa: E402

FAKE = "4242" + ":" + "y" * 35        # token-shaped, made up here
UPD = {"ok": True, "result": [
    {"update_id": 5, "message": {"chat": {"id": -100, "type": "group", "title": "desk"}, "text": "/start"}},
    {"update_id": 7, "message": {"chat": {"id": 777, "type": "private", "first_name": "Mary"}, "text": "/start"}},
    {"update_id": 6, "message": {"chat": {"id": 555, "type": "private", "first_name": "Old"}, "text": "hi"}}]}


class _R:
    def __init__(self, body):
        self.b = json.dumps(body).encode()

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def _own_telegr(tmp_path, monkeypatch):
    """_bot() writes a FAKE bot.txt through tg.DIR: point it at tmp_path here, so it is safe even without conftest's
    STR_PATHS line and can never overwrite her real telegr/bot.txt."""
    monkeypatch.setattr(tg, "DIR", str(tmp_path / "telegr"))


def _bot():
    os.makedirs(tg.DIR, exist_ok=True)
    with open(os.path.join(tg.DIR, "bot.txt"), "w", encoding="utf-8") as f:
        f.write(f"key: {FAKE}\nbot: https://t.me/tapemap_x_bot\n")


def _fake(updates, sent):
    def fake(req, timeout=None):
        if req.data is None:                                    # GET getUpdates
            assert req.full_url.endswith("/getUpdates")
            return _R(updates)
        sent.append(urllib.parse.parse_qs(req.data.decode()))   # POST sendMessage
        return _R({"ok": True})
    return fake


def test_the_newest_private_chat_is_saved_and_told_connected_without_printing_the_token(monkeypatch, capsys):
    _bot()
    sent = []
    monkeypatch.setattr(tg, "_open", _fake(UPD, sent))
    assert telegram_setup.main() == 0
    with open(os.path.join(tg.DIR, "chat.txt"), encoding="utf-8") as f:
        assert f.read() == "777\n"
    assert sent == [{"chat_id": ["777"], "text": ["TapeMap connected ✓"], "disable_web_page_preview": ["true"]}]
    out = capsys.readouterr()
    assert "Mary" in out.out and FAKE not in out.out + out.err


def test_no_private_chat_writes_nothing_and_says_send_start(monkeypatch, capsys):
    _bot()
    sent = []
    monkeypatch.setattr(tg, "_open", _fake({"ok": True, "result": UPD["result"][:1]}, sent))
    assert telegram_setup.main() == 1
    assert not os.path.exists(os.path.join(tg.DIR, "chat.txt")) and sent == []
    assert "/start" in capsys.readouterr().out
