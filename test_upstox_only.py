"""Nothing on the Upstox path may depend on a Dhan file.

The switch itself is covered by test_broker_switch. This file covers the two
places that read or wrote `.dhan_token` REGARDLESS of the switch -- both found
on 2026-08-06 while checking whether the desktop launcher would come up on
Upstox:

  * `live._token()` opened `.dhan_token` unconditionally, so deleting a file
    the Upstox path never transmits would have killed the whole tape with a
    FileNotFoundError naming a broker it was not running on.
  * POST `/api/token` validated a Dhan JWT and wrote `.dhan_token` while the
    running tape and chain read `.upstox_token` -- an "accepted" that changed
    nothing the operator could see.

No token here is real: the Dhan-path test writes a placeholder into pytest's
tmp_path, never into the repo.
"""

import inspect
import json

import pytest

import live
import server
import upstox_chain


def _down_feed(last_error):
    """A source whose socket is down, with whatever the feed did or did not
    record. Built with __new__ so no websocket is created."""
    src = upstox_chain.UpstoxChainSource.__new__(upstox_chain.UpstoxChainSource)
    src.resolved = {"NIFTY": {"idx_key": "k", "meta": {}}}
    src.feed = type("_F", (), {"connected": False,
                               "last_error": last_error})()
    return src


def test_a_down_feed_with_no_recorded_error_still_gives_a_reason():
    """`last_error` is None before the first connect finishes, and the raw
    f-string printed "upstox feed down: None" -- an absence with no reason.
    On 2026-08-06 NIFTY showed that None while BANKNIFTY and SENSEX carried
    the real 401, so the watched index was the one hiding the cause."""
    with pytest.raises(RuntimeError) as e:
        _down_feed(None).poll({"under_sym": "NIFTY"}, "2026-08-07", None)
    msg = str(e.value)
    assert "None" not in msg
    assert "upstox_auth.py" in msg          # names the thing that fixes it


def test_a_real_feed_error_is_passed_through_untouched():
    """The fallback must not swallow a cause that WAS recorded."""
    with pytest.raises(RuntimeError) as e:
        _down_feed("WebSocketBadStatusException: Handshake status 401").poll(
            {"under_sym": "NIFTY"}, "2026-08-07", None)
    assert "401" in str(e.value)


def _broker(monkeypatch, value):
    """Select the broker for one test. `None` means "leave it unset", which
    is the shipped default and must stay Dhan."""
    if value is None:
        monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
    else:
        monkeypatch.setenv("TAPEMAP_BROKER", value)


# ---- live._token() ---------------------------------------------------------

def test_the_tape_needs_no_dhan_token_on_upstox(tmp_path, monkeypatch):
    """Run from a directory with no `.dhan_token` at all. On Upstox that is
    not an error, because the value is never sent anywhere."""
    monkeypatch.chdir(tmp_path)
    _broker(monkeypatch, "upstox")
    assert live._token() == ""


def test_the_tape_still_reads_the_dhan_token_on_dhan(tmp_path, monkeypatch):
    """The fix must not quietly disarm the path it was not aimed at."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".dhan_token").write_text(
        "  eyJtest.token.value  \n", encoding="utf-8")
    _broker(monkeypatch, None)                    # unset == dhan
    assert live._token() == "eyJtest.token.value"


def test_a_missing_dhan_token_still_fails_loudly_on_dhan(tmp_path, monkeypatch):
    """Returning "" for everyone would have been the easy fix, and it would
    have turned a real Dhan misconfiguration into a silently empty chart."""
    monkeypatch.chdir(tmp_path)
    _broker(monkeypatch, None)
    with pytest.raises(FileNotFoundError):
        live._token()


# ---- POST /api/token -------------------------------------------------------

def test_the_token_button_refuses_upstox_before_writing_anything():
    """Ordering, not just presence. A refusal placed after the write would
    still leave a Dhan file on disk and a poller reload behind it."""
    src = inspect.getsource(server.Handler.do_POST)
    refuse = src.index('_broker() == "upstox"')
    write = src.index("write_text")
    assert refuse < write, "the Upstox refusal must come before the write"


def test_the_refusal_names_what_actually_re_auths():
    """HANDOFF section 9: an absence gets a reason. "rejected" with no next
    step sends the operator to the Dhan dashboard at 09:15, which is exactly
    the wrong place."""
    assert "upstox_auth.py" in inspect.getsource(server.Handler.do_POST)


# ---- GET /api/health -------------------------------------------------------

class _Cap:
    """A Handler with the socket machinery removed.

    `__init__` is skipped and `_json` captures instead of writing, so routing
    can be exercised without binding a port or owning a real request.
    """

    def __init__(self, path, payloads=None):
        self.path = path
        self.payloads = payloads or {}
        self.chains = None
        self.poller = None
        self.sent = None

    def _json(self, body, code=200):
        self.sent = json.loads(body.decode())


def _get(path, payloads=None):
    cap = _Cap(path, payloads)
    server.Handler.do_GET(cap)
    return cap.sent


def test_health_reports_the_broker_actually_in_force(monkeypatch):
    monkeypatch.setenv("TAPEMAP_BROKER", "upstox")
    out = _get("/api/health", payloads={"NIFTY": {}, "SENSEX": {}})
    assert out["ok"] is True
    assert out["broker"] == "upstox"
    assert out["indices"] == ["NIFTY", "SENSEX"]
    assert isinstance(out["started_at"], float)


def test_health_says_dhan_when_nothing_selected_it(monkeypatch):
    """It must report what is TRUE, not what the launcher intended -- the
    launcher's whole check depends on this being able to say "dhan"."""
    monkeypatch.delenv("TAPEMAP_BROKER", raising=False)
    assert _get("/api/health")["broker"] == "dhan"


def test_only_one_server_may_hold_the_port():
    """Python's HTTPServer sets allow_reuse_address = 1, and on Windows that
    lets a second process TAKE a port the first is listening on. Two servers
    came up 2s apart on 2026-08-06 and the loser kept an Upstox socket."""
    assert server._Server.allow_reuse_address is False


def test_the_port_is_claimed_before_the_chain_poller_starts():
    """The ordering IS the fix. Both lines present in the wrong order is
    exactly the bug: the poller opened a websocket, and only then did the
    process find out it had lost the port -- and it kept the socket."""
    src = inspect.getsource(server.main)
    assert src.index("_Server((") < src.index("_start_chain(mock_chain")


def test_health_answers_with_no_tape_at_all(monkeypatch):
    """The point of the route. Both callers need an answer precisely when the
    tape has nothing: the launcher before deciding to reuse port 8765, and the
    banner before deciding whether "unreachable" is the truth."""
    monkeypatch.setenv("TAPEMAP_BROKER", "upstox")
    out = _get("/api/health", payloads={})
    assert out["ok"] is True
    assert out["indices"] == []
