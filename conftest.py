# tapemap/conftest.py
"""Every test runs with the ladder record pointed at a temp dir.

THE LEAK (2026-09-19): server.do_POST now writes each posted bar to
tape_log.DIR (data/tape/, the live forward record). A pre-existing route
test that posts a toy doc without redirecting DIR wrote three toy rows into
the real record -- the same class of incident as the 2026-08-24 replay leak
(server._isolate_mock_writers). One autouse fixture, so no test can ever
reach data/tape/ by forgetting a monkeypatch; tests that set DIR themselves
still win, because their monkeypatch is applied after this one.

2026-09-28 (pro-tool P1-01): EVERY forward-record writer, the same way. The
fixture had three of them; a morning test run would have written a fake marked
trade into today's day_state and a FRAMETEST stick did land in data/ that day.
The list here and the one in server._isolate_mock_writers are the same list;
test_leak_guard.py asserts each path is under tmp_path.
"""
import pytest

import tape_log
import ux_log

# module attribute -> the tmp name (monkeypatch imports each module by name).
# Strings where the module holds a string, Paths where it holds a Path.
STR_PATHS = {"tape_log.DIR": "tape", "book_log.DIR": "book", "day_state.DIR": "day_state",
             "hold_log.DIR": "hold", "calls_log.DIR": "calls", "frame_log.DIR": "frame",
             "senses.DIR": "senses", "trigger_log.PATH": "trigger_log.jsonl",
             "confluence_log.PATH": "confluence_log.jsonl",   # §1i's forward log (confluence_log.py)
             "onesided.PATH": "onesided_log.jsonl",           # §1o's daily row (onesided.py)
             "server.DECODE_DIR": "decode",                   # N7: the DECODE block's forward log (server._decode_log)
             "server.MAP_DIR": "hold", "server.VOICE_DIR": "voice",   # the TRADE MAP's log (_map_log), the voice paths (_voice_path)
             "server.SHADOW_DIR": "hold",                     # holdshadow's log (_shadow_log): a toy trade wrote shadow_2026-09-30 on 23 Oct
             "sequence.DIR": "warmap", "desk_log.SURF_DIR": "surface", "desk_log.DESK_LOG_PATH": "desk_log.jsonl",
             "server.VPIN_LOG": "vpin_log.jsonl", "server.VPIN_BACKFILL_LOG": "vpin_backfill.jsonl",
             "server.VPIN_FAST_LOG": "vpin_fast.jsonl",
             "server.RANK_DIR": "rank",                        # the extension v2's rank_ref files (server._rank_ref)
             "chain_backfill.DIR": "chain_backfill",           # the 09:15 REST backfill on disk (pro-tool P2-06)
             "reader_live.DIR": "reader",                      # the shadow leg engine's log (docs/reader/8-shadow-build.md)
             "xindex_live.DIR": "xindex",                      # the shadow cross-index log (docs/reader/10-xindex-build.md)
             "sides_log.DIR": "sides",                         # the sides read's forward log (sides_log.py)
             "trap_log.DIR": "trap",                           # the trap layer's forward log (trap_log.py)
             "decoder_log.DIR": "decoder",                     # the decoder's forward log (decoder_log.py)
             "dext_log.DIR": "dext",                           # the Dext record, gate 3 (dext_log.py)
             "feed_health.LOG": "feed_log.jsonl",              # A17: server.py sets it at import; tests wrote 197 rows
             "server.VALIDATE_DIR": "validate",               # F12: Validate's press log (server._validate_press)
             "server.IMPORT_DIR": "receipts",                 # F13a: the tradebook import marks (server._receipts_import)
             "server.MSG_DIR": "messages",                    # A101: the message stream's record (server._msg_write)
             "server.HS_DIR": "raftaar",                      # A132: the handshake's forward log (server._hs_log)
             "telegram_out.DIR": "telegr",                    # A101: her token + chat id -- no test can read the real ones
             "jarvis.TAPE_DIR": "tape_fut1m",                 # P0 (30 Oct): the saved 1-min fut tape (jarvis.save_tape)
             "jarvis_log.DIR": "jarvis", "jarvis_cmd.DIR": "jarvis",   # Jarvis v3: the call log, the command log
             "jarvis_voice.DIR": "jarvis", "jarvis_voice.KEYS": "keys",   # Task 7: the voice log; no test reads her keys
             # the instrument dump cache: a stale cache would be RE-FETCHED and rewritten under data/
             "upstox_instruments.CACHE_FMT": "upstox_{}.json"}
PATH_PATHS = {"chain_live.CHAIN_DIR": "chain", "live.STICK_F": "stick_state.json",
              # the Dhan scrip-master cache (a fallback path, but it lives under data/ and a stale one is re-downloaded)
              "instruments.SCRIP_CACHE": "scrip_master.csv"}


@pytest.fixture(autouse=True)
def _tape_record_in_tmp(tmp_path, monkeypatch):
    for target, name in STR_PATHS.items():
        monkeypatch.setattr(target, str(tmp_path / name))
    for target, name in PATH_PATHS.items():
        monkeypatch.setattr(target, tmp_path / name)
    # C10 (25 Oct review): the shipped default is upstox; the suite keeps running on the mocked Dhan path it was written on,
    # whatever the shell has set. A test of the unset default delenv's it (test_broker_switch, test_upstox_only)
    monkeypatch.setenv("TAPEMAP_BROKER", "dhan")
    # Task 7: no voice thread outlives a test (it would write after this redirect is undone, into server._JVOICE too);
    # test_jarvis_voice.py restores the real one where it tests the hook
    monkeypatch.setattr("jarvis_voice.later", lambda store, key, fn: None)
    # the rev 6 event log (P2-02) is being written beside this; guarded until it lands
    try:
        import fold_log
        monkeypatch.setattr(fold_log, "DIR", str(tmp_path / "fold"))
    except ImportError:
        pass
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
    tape_log._seen_marks2.clear()
    ux_log._STATE.clear()
    import decoder_log
    decoder_log._SEEN.clear()
    decoder_log._MIN_SEEN.clear()
    decoder_log._EV_CACHE.clear()
    yield
    tape_log._seen_bars.clear()
    tape_log._seen_marks.clear()
    ux_log._STATE.clear()
