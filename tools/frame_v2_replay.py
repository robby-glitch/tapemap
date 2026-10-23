"""tools/frame_v2_replay.py -- the extension v2's frame keys as the server would have answered at a time, from files.

    python tools/frame_v2_replay.py --idx NIFTY --day 2026-10-12 --at 10:30 [--out f.json]
    python tools/frame_v2_replay.py --idx NIFTY --day 2026-10-12 --times 09:40,10:25,11:00 [--out f.json]

-> {day, at, read, read_why, plan, plan_why, writers, ux_flow, rank_ref_id, rank_ref}; with --times one object keyed
by "HH:MM". The server's own path (server._v2_parts) on v2feed.Day of the recorded day, frame_v2.cut to T and the
Upstox 5-min bars closed by T, so nothing after T is seen. rank_ref = data/rank/rank_ref_<idx>_<day>.json (days <
day), built in memory and written there when missing. `expr` (the hold window's live word) is null in a replay.
Read-only apart from that one file.
"""
import argparse
import datetime
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(TOOLS)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLS)
os.chdir(HERE)                                    # tape_log / ux_log read data/tape/ relative to tapemap/

import rank_build  # noqa: E402
import server      # noqa: E402
import ux_log      # noqa: E402
import v2feed      # noqa: E402


def sec_of(hhmm):
    h, m = hhmm.split(":")[:2]
    return int(h) * 3600 + int(m) * 60


def ms_at(day, sec):
    d = datetime.datetime.fromisoformat(day).replace(tzinfo=v2feed.IST)
    return int((d + datetime.timedelta(seconds=sec)).timestamp() * 1000)


def rank_ref(idx, day, write=True):
    p = rank_build.path_for(os.path.join(rank_build.DATA, "rank"), idx, day)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    ref = rank_build.build(idx, day)
    if write:
        rank_build.write(ref, os.path.dirname(p))
    return ref


def replay(idx, day, times, ref=None):
    """{"HH:MM": the frame keys at that time} for one recorded day."""
    ref = ref if ref is not None else rank_ref(idx, day)
    D = v2feed.Day(day, v2feed.DATA)
    D.refresh()
    s = D.idx[idx]
    ux_all = ux_log.read_bars(day, idx)
    out = {}
    for hhmm in times:
        T, ms = sec_of(hhmm), ms_at(day, sec_of(hhmm))
        ux = [b for b in ux_all if isinstance(b.get("t"), (int, float)) and b["t"] + 300000 <= ms]
        parts = server._v2_parts(idx, day, s, T, ms, ux, ref)
        out[hhmm] = dict({"day": day, "at": hhmm}, **parts, rank_ref_id=ref.get("id"), rank_ref=ref)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--idx", default="NIFTY")
    ap.add_argument("--day", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--at")
    g.add_argument("--times")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    times = [a.at] if a.at else [t.strip() for t in a.times.split(",") if t.strip()]
    res = replay(a.idx, a.day, times)
    doc = res[a.at] if a.at else res
    text = json.dumps(doc, ensure_ascii=False, default=str, indent=1)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(a.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
