"""tools/jarvis_review.py -- THE EVENING SHEET (Jarvis v3 Task 4): what Jarvis said today and her trades against it, read
from the day's files into data/jarvis/review_<day>.md. Counts only: never a rate, a % or a verdict. An input that is absent
is named on its own line, never read as a zero. Writes only that one file.

Inputs (DIR = data/jarvis): call_<day>.jsonl (the CALL LOG, written by the server), pause_<day>.jsonl (tools/pause_log.py),
cmd_<day>.jsonl (the command grammar's record), and her marks (day_state's hold_trades).

Run by eod_capture.bat after pause_log.py; re-runnable any time (it rewrites the day's sheet):
    python tools/jarvis_review.py [YYYY-MM-DD]          default: today, IST
"""
import datetime
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import day_state  # noqa: E402

DIR = os.path.join(HERE, "data", "jarvis")
CC = "could not check — "
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
TRUE_MIN = 45   # [I] a PALAT? episode "came true" when a PALAT row follows within 45 min of its first row: the CALL LOG
                # contract's window, the same 45 min as the leg's pause outcome (legs.HORIZON)


def _rows(path):
    """A JSONL file's dict rows in order; None when the file is absent (absent is not empty). A torn line is skipped."""
    if not os.path.exists(path):
        return None
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if isinstance(r, dict):
                out.append(r)
    return out


def _m(t):
    return int(t[:2]) * 60 + int(t[3:5])


def _count(c):
    if isinstance(c, dict) and c.get("with") is not None and c.get("against") is not None:
        return f"WITH {c['with']} · AGAINST {c['against']}"
    return "count not logged"


def _at(rows, t):
    """The call row standing at clock t (HH:MM[:SS]): the last row at or before its minute, else None."""
    return next((r for r in reversed(rows) if r["t"] <= t[:5]), None)


def _word_lines(idx, rows):
    seq = []
    for r in rows:
        w = r.get("word") or "no word"
        if not seq or seq[-1][1] != w:
            seq.append((r["t"], w))
    ends = [t for t, _ in seq[1:]]
    held = [_m(b) - _m(a) for (a, _), b in zip(seq, ends)] + [_m(rows[-1]["t"]) - _m(seq[-1][0]) + 1]
    return [f"{idx} · word changes: {len(seq) - 1}",
            " → ".join(f"{t} {w} ({h} min)" for (t, w), h in zip(seq, held))]


def _palat_line(idx, rows):
    def word(r):
        return str(r.get("word") or "")
    eps = [i for i, r in enumerate(rows) if word(r).startswith("PALAT?") and not (i and word(rows[i - 1]).startswith("PALAT?"))]
    true = sum(any(word(r).startswith("PALAT") and not word(r).startswith("PALAT?")
                   and 0 < _m(r["t"]) - _m(rows[i]["t"]) <= TRUE_MIN for r in rows[i:]) for i in eps)
    return f"{idx} · PALAT? said {len(eps)}× · came true {true}×"


def _blind_line(idx, rows):
    spans, cur = [], None
    for r in rows:
        if r.get("blind"):
            if cur:
                cur[1] = r["t"]
            else:
                cur = [r["t"], r["t"]]
                spans.append(cur)
        else:
            cur = None
    n = sum(1 for r in rows if r.get("blind"))
    return f"{idx} · blind {n} min" + ("".join(f" · {a}" if a == b else f" · {a}–{b}" for a, b in spans))


def _trade_line(tr, rows):
    """One mark: side, entry, the word at entry and its count, the word at exit, fut points her way (the call rows' fut)."""
    p0, t0, ex = tr.get("p0"), str(tr.get("t0") or ""), tr.get("exit_t")
    s = (f"{tr.get('idx')} {tr.get('k'):g} {tr.get('side')} {tr.get('role')} "
         + (f"@{p0:g}" if p0 is not None else "entry price not marked") + f" · in {t0} ")
    a = _at(rows, t0)
    s += f"{a.get('word')} ({_count(a.get('count'))})" if a else f"{CC}no call row by {t0[:5]}"
    if not ex:
        return s + " · no exit marked"
    b = _at(rows, str(ex))
    s += f" · out {ex} " + (str(b.get("word")) if b else f"{CC}no call row by {str(ex)[:5]}")
    fa, fb = a and a.get("fut"), b and b.get("fut")
    if not isinstance(fa, (int, float)) or not isinstance(fb, (int, float)):
        return s + f" · fut points {CC}no fut in the call rows"
    d = 1 if (tr.get("side"), tr.get("role")) in (("CE", "long"), ("PE", "short")) else -1
    return s + f" · fut {fa:,.1f}f → {fb:,.1f}f · " + f"{d * (fb - fa):+.1f}".replace("-", "−") + " pts her way"


def sheet(day, data_dir=DIR):
    """The day's sheet as markdown."""
    calls, pauses, cmds = (_rows(os.path.join(data_dir, f"{k}_{day}.jsonl")) for k in ("call", "pause", "cmd"))
    marks, why_marks = None, f"no marks file (day_state day_{day}.json)"
    if os.path.exists(day_state.path_for(day)):
        st = day_state.load(day)                 # {} only when it did not read (a saved day always carries `day`)
        marks, why_marks = (st.get("hold_trades") or [], None) if st else (None, "the marks file did not read")
    by = {}
    for r in calls or ():
        if isinstance(r.get("t"), str) and len(r["t"]) >= 5:
            by.setdefault(r.get("idx") or "?", []).append(r)
    no_calls = [CC + "no call log"] if calls is None else [] if by else ["the call log has no rows (checked)"]

    L = [f"# Jarvis evening sheet · {day}", "", "Counts only, display only: never a rate. An absent input is named under"
         " Could not check, never read as a zero.", ""]

    def section(title, lines):
        L.extend([f"## {title}", ""] + [f"- {x}" for x in lines] + [""])

    section("The word", no_calls or [x for idx, rows in by.items() for x in _word_lines(idx, rows)])
    section("PALAT?", no_calls or [_palat_line(idx, rows) for idx, rows in by.items()])
    section("Blind", no_calls or [_blind_line(idx, rows) for idx, rows in by.items()])
    section("Her trades vs the word", [CC + why_marks] if marks is None else
            [_trade_line(t, by.get(t.get("idx")) or []) for t in marks] or ["no marks today (checked)"])
    if cmds is None:
        section("Watches", [CC + "no command log"])
    else:
        sets = [r for r in cmds if r.get("kind") == "watch" and r.get("ok")]
        hits = [r for r in cmds if r.get("kind") == "watch_hit"]
        section("Watches", [f"watches set {len(sets)} · hit {len(hits)}"]
                + [f"{str(r.get('t'))[:5]} set {r.get('text')}" for r in sets]
                + [f"{r.get('t')} hit " + (f"{r['px']:,.1f}{r.get('frame') or ''}" if isinstance(r.get("px"), (int, float))
                                          else "price not logged") + f" · id {r.get('id')}" for r in hits])
    if pauses is None:
        section("Pauses", [CC + "no pause log"])
    else:
        bad = [r for r in pauses if r.get("why")]
        n = Counter((r.get("after") or {}).get("outcome") for r in pauses if not r.get("why"))
        section("Pauses", ([f"pauses {sum(n.values())} · CONT {n['CONT']} · REV {n['REV']} · UNRESOLVED {n['UNRESOLVED']}"
                            f" · window open {n[None]}"] if n or not bad else [])
                + [f"{CC}{r.get('idx')}: {r['why']}" for r in bad])
    absent = [CC + w for v, w in ((calls, f"no call log (call_{day}.jsonl)"), (pauses, f"no pause log (pause_{day}.jsonl)"),
                                  (cmds, f"no command log (cmd_{day}.jsonl)"), (marks, why_marks)) if v is None]
    section("Could not check", absent or ["every input was on disk"])
    return "\n".join(L)


def run(day, data_dir=DIR):
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"review_{day}.md")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write(sheet(day, data_dir))
    os.replace(path + ".tmp", path)
    return path


if __name__ == "__main__":
    os.chdir(HERE)                                 # day_state.DIR is relative to the repo
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.datetime.now(IST).strftime("%Y-%m-%d")
    if not re.fullmatch(r"\d{4}-\d\d-\d\d", day):
        sys.exit("usage: python tools/jarvis_review.py [YYYY-MM-DD]")
    print(f"jarvis review: {run(day)}")
