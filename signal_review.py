"""Did the day's signals play out? A descriptive post-mortem over one session.

    python signal_review.py [NIFTY|BANKNIFTY|SENSEX] [port]

Reads a running server's /api/data (read-only, writes nothing anywhere) and
scores every event that carried a direction against what the futures did next.

METHOD, stated up front so the numbers can be argued with rather than trusted:

  * Direction per event uses the SAME rules the UI uses -- ui-v2/src/data.ts
    `evDir`, replicated in ev_dir() below. Keep the two in step: if evDir
    changes, this file is wrong until it changes too.
  * An event the engine gave NO direction is not scored. It is listed
    separately and never counted as a miss.
  * Entry is the CLOSE of the bar the event is stamped on -- the earliest bar
    a reader could have acted on. This is deliberately pessimistic: the event
    fires because of what that bar did, so that bar's move is already spent.
  * Forward move at +5 / +15 / +30 minutes, SIGNED BY THE CALLED DIRECTION.
    Positive means price went the way the signal pointed.
  * MFE / MAE over the following 30 minutes: the best and the worst it got, in
    the signalled direction. A signal can be "right" at +30m and still have
    been unholdable in between; MAE is the only place that shows.
  * Horizons past the session's last bar do not exist. Those events are marked
    PARTIAL and excluded from the horizon they cannot fill -- never zero-filled.
  * The UNCONDITIONAL forward move over every bar is printed as the control.
    Without it a positive average means nothing: on a day that trends +67 pts,
    a random long "wins" too.
  * Events are grouped by CLAIM STRENGTH, the same call/risk/lean split the UI
    uses for its direction chip (ui-v2/src/trade/hinglish.ts CLAIM). A warning
    ("squeeze risk building") and a read ("bull trap sprung") should not be
    scored as though they had made the same promise.

WHAT THIS CANNOT TELL YOU. One session is an anecdote. Events cluster -- a
single minute can carry three of them -- so they are not independent samples.
Entry at bar close with a fixed 30-minute exit is not a trading rule. It scores
FUTURES, not option premium, so theta and IV are absent. Treat any number here
as a question worth asking of the ~55 cached days in data/backtest/, never as
an answer.
"""
import datetime
import json
import sys
import urllib.request

HORIZONS = (5, 15, 30)
MFE_WINDOW = 30

# Where --json writes when no path is given. The Trade tab's callout reads this
# snapshot as a static import, so the UI still computes nothing about the
# market -- it renders a number this script measured, on the date it says.
DEFAULT_JSON = "ui-v2/src/trade/signalScore.json"

# The two sentences the snapshot carries with it, lifted VERBATIM from this
# module's own docstring so the file and its export can never drift into
# claiming different things. Every surface that renders a number from the
# snapshot must render these beside it.
DISCLOSURE = ("One session. Events cluster, so these are not independent "
              "samples. Futures, not premium. No costs. Treat as a question, "
              "not an answer.")
METHOD = ("Entry at bar close with a fixed 30-minute exit is not a trading "
          "rule. This scores SIGNAL QUALITY, never expectancy.")

# Claim strength, mirroring ui-v2/src/trade/hinglish.ts CLAIM. Taken from each
# kind's own emit text in engine.py: a read, a warning, or a positional tilt.
CALL = {"ABSORPTION", "CLIMAX", "IGNITION", "DIVERGENCE", "TRAP-SPRUNG",
        "SPRING", "SPRING-FAIL", "BAND-REVERSAL", "BAND-BREAK"}
RISK = {"SQUEEZE-RISK", "TRAP-SETTING", "TRAP", "ARMED"}
LEAN = {"CAMPAIGN", "BUYER-BUILD", "GAMMA-PIN", "OI-PEAK-LAG", "PRESS",
        "WALL-MIGRATION", "ROLE-FLIP", "CARRY"}


def ev_dir(e):
    """Port of ui-v2/src/data.ts evDir. Returns -1, 0 or +1."""
    k = e.get("kind")
    m = str(e.get("msg", "")).upper()
    s = (e.get("data") or {}).get("side")
    if k == "BAND-REVERSAL":
        return -1 if "+2" in m else 1 if "-2" in m else 0
    if k in ("TRAP-SPRUNG", "TRAP-SETTING"):
        return -1 if "BULL" in m else 1 if "BEAR" in m else 0
    if k in ("PRESS", "CAMPAIGN", "BUYER-BUILD"):
        return 1 if "BULLISH" in m else -1 if "BEARISH" in m else 0
    if k == "OI-PEAK-LAG":
        return 1 if "UPWARD" in m else -1 if "DOWNWARD" in m else 0
    if k == "SQUEEZE-RISK":
        return 1 if "UPSIDE" in m else -1 if "DOWNSIDE" in m else 0
    if k == "DIVERGENCE":
        return -1 if "HIGH" in m else 1 if "LOW" in m else 0
    if k == "IGNITION":
        return 1 if m.startswith("UP") or "UP:" in m else -1
    if k in ("ARMED", "SPRING", "WALL-MIGRATION", "ROLE-FLIP"):
        return 1 if s == "UP" else -1 if s == "DN" else 0
    if k == "ABSORPTION":
        return 1 if "SELLERS HITTING" in m else -1 if "BUYERS HITTING" in m else 0
    if k == "GAMMA-PIN":
        return 1 if m.startswith("FLOOR") else -1 if m.startswith("CEILING") else 0
    return 0


def score(day):
    bars = [b for b in day["bars"] if b.get("fut")]
    idx = {b["t"]: i for i, b in enumerate(bars)}
    close = [b["fut"]["c"] for b in bars]
    high = [b["fut"]["h"] for b in bars]
    low = [b["fut"]["l"] for b in bars]
    scored, undirected = [], []
    for e in day["events"]:
        i = idx.get(e["t"])
        if i is None:
            continue
        d = ev_dir(e)
        if d == 0:
            undirected.append(e["kind"])
            continue
        row = {"t": e["t"], "kind": e["kind"], "dir": d, "px": close[i]}
        for h in HORIZONS:
            j = i + h
            row[f"f{h}"] = None if j >= len(close) else round(d * (close[j] - close[i]), 1)
        w = slice(i + 1, min(i + 1 + MFE_WINDOW, len(close)))
        hs, ls = high[w], low[w]
        if hs:
            row["mfe"] = round(d * ((max(hs) if d > 0 else min(ls)) - close[i]), 1)
            row["mae"] = round(d * ((min(ls) if d > 0 else max(hs)) - close[i]), 1)
        else:
            row["mfe"] = row["mae"] = None
        row["full"] = len(hs) == MFE_WINDOW
        scored.append(row)
    return bars, close, high, low, scored, undirected


def summary(sym, day, bars, close, scored):
    """The claim-strength table above, in machine-readable form.

    CLAIM LEVEL ONLY, and deliberately so. The per-kind table this script
    prints runs n=1-5 per kind on a single session; rendered on a card as
    "100% - 2/2" that reads as a measurement, and no amount of styling or
    small-print fixes it. A human reading the printed table has the rest of
    the table for context; a hover card has none. So the export carries the
    claim buckets (n~16-18) and the control, and nothing finer. Per-kind
    numbers stay something you read here, with your eyes, in context.

    The control is not optional. Without it a hit rate means nothing: on a day
    that trends +67 pts a random long "wins" too, so any surface showing
    `claim` must be able to show what doing nothing scored over the same bars.
    """
    def agg(rows):
        v = [r["f30"] for r in rows if r["f30"] is not None]
        if not v:
            return None
        return {"n": len(v), "hit": sum(1 for x in v if x > 0),
                "avg30": round(sum(v) / len(v), 1)}

    claim = {}
    for name, group in (("call", CALL), ("risk", RISK), ("lean", LEAN)):
        a = agg([r for r in scored if r["kind"] in group])
        if a:
            claim[name] = a

    # The unconditional +30m move over every bar -- computed the same way the
    # printed control is, so the report and the snapshot cannot disagree.
    mv = [close[i + 30] - close[i] for i in range(len(close) - 30)]
    control = ({"n": len(mv), "hit": sum(1 for x in mv if x > 0),
                "avg30": round(sum(mv) / len(mv), 1)} if mv else None)

    return {
        "generated": datetime.date.today().isoformat(),
        "session": day["day"],
        "index": sym,
        "bars": len(bars),
        "events": len(day["events"]),
        "scored": len(scored),
        "horizon_min": 30,
        "claim": claim,
        "control": control,
        "disclosure": DISCLOSURE,
        "method": METHOD,
    }


def parse_args(argv):
    """(sym, port, json_out) from the bare argument list.

    --json [path] may appear anywhere; everything else stays positional, so
    the existing `signal_review.py BANKNIFTY 8765` invocation keeps working
    exactly as it did. Its own function so that promise is testable rather
    than merely asserted in a comment.
    """
    argv = list(argv)
    json_out = None
    if "--json" in argv:
        i = argv.index("--json")
        tail = argv[i + 1:]
        # A path may follow --json. Anything starting with "-" is the next
        # flag, not a filename, so --json falls back to its default there.
        if tail and not tail[0].startswith("-"):
            json_out = tail[0]
            del argv[i:i + 2]
        else:
            json_out = DEFAULT_JSON
            del argv[i]
    sym = argv[0] if argv else "NIFTY"
    port = argv[1] if len(argv) > 1 else "8765"
    return sym, port, json_out


def main():
    sym, port, json_out = parse_args(sys.argv[1:])
    url = f"http://127.0.0.1:{port}/api/data?idx={sym}"
    D = json.loads(urllib.request.urlopen(url, timeout=20).read())
    if not D.get("days"):
        print(f"no session for {sym}: {D.get('live_error')}")
        return
    day = D["days"][-1]
    bars, close, high, low, scored, undirected = score(day)
    if not scored:
        print(f"{sym} {day['day']}: no directional events")
        return

    # Written BEFORE the report so a snapshot survives a broken pipe, and only
    # once there is something to write -- a session with no directional events
    # produces no file rather than an empty-but-official-looking one.
    if json_out:
        snap = summary(sym, day, bars, close, scored)
        with open(json_out, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        buckets = " · ".join(
            "{} n={} hit {}/{}".format(k, c["n"], c["hit"], c["n"])
            for k, c in snap["claim"].items()) or "none"
        print(f"wrote {json_out} — session {snap['session']}, "
              f"{snap['scored']} directional events · {buckets}\n")

    print(f"{sym} · session {day['day']} · {len(bars)} bars · "
          f"{len(day['events'])} events · {len(scored)} carried a direction\n")
    print(f"{'time':>5} {'kind':<14} {'dir':>3} {'entry':>9} "
          f"{'+5m':>7} {'+15m':>7} {'+30m':>7} {'best':>7} {'worst':>7}")
    print("-" * 82)
    for r in scored:
        def f(v):
            return "    n/a" if v is None else f"{v:+7.1f}"
        print(f"{r['t']:>5} {r['kind']:<14} {'UP' if r['dir'] > 0 else 'DN':>3} "
              f"{r['px']:>9.1f} {f(r['f5'])} {f(r['f15'])} {f(r['f30'])} "
              f"{f(r['mfe'])} {f(r['mae'])}" + ("" if r["full"] else "   PARTIAL"))

    print("\nBy kind (points, signed by the called direction):")
    print(f"{'kind':<14} {'n':>3} {'+15m avg':>9} {'+15m hit':>9} "
          f"{'+30m avg':>9} {'+30m hit':>9} {'avg best':>9} {'avg worst':>9}")
    print("-" * 82)
    kinds = {}
    for r in scored:
        kinds.setdefault(r["kind"], []).append(r)
    for k in sorted(kinds):
        rs = kinds[k]

        def stat(key):
            v = [r[key] for r in rs if r[key] is not None]
            if not v:
                return None, None, 0
            return sum(v) / len(v), sum(1 for x in v if x > 0) / len(v), len(v)
        a15, h15, n15 = stat("f15")
        a30, h30, n30 = stat("f30")
        mfe = [r["mfe"] for r in rs if r["mfe"] is not None]
        mae = [r["mae"] for r in rs if r["mae"] is not None]

        def s(x, pct=False):
            if x is None:
                return "      n/a"
            return f"{x * 100:8.0f}%" if pct else f"{x:+9.1f}"
        note = f"   [{n15}/{n30} full]" if n15 < len(rs) or n30 < len(rs) else ""
        print(f"{k:<14} {len(rs):>3} {s(a15)} {s(h15, True)} {s(a30)} "
              f"{s(h30, True)} {s(sum(mfe) / len(mfe) if mfe else None)} "
              f"{s(sum(mae) / len(mae) if mae else None)}{note}")

    print("\nBy claim strength (what the kind actually promised):")
    for name, group in (("call  (a read)", CALL), ("risk  (a warning)", RISK),
                        ("lean  (positioning)", LEAN)):
        rs = [r for r in scored if r["kind"] in group and r["f30"] is not None]
        if not rs:
            continue
        v = [r["f30"] for r in rs]
        ups = [r["f30"] for r in rs if r["dir"] > 0]
        dns = [r["f30"] for r in rs if r["dir"] < 0]
        print(f"  {name:<20} n={len(rs):<3} +30m avg {sum(v) / len(v):+6.1f} pts, "
              f"hit {sum(1 for x in v if x > 0)}/{len(v)}"
              + (f" | UP n={len(ups)} {sum(ups) / len(ups):+.1f}" if ups else "")
              + (f" | DN n={len(dns)} {sum(dns) / len(dns):+.1f}" if dns else ""))

    print("\nControl — the same horizons over EVERY bar, no signal involved:")
    for h in (15, 30):
        mv = [close[i + h] - close[i] for i in range(len(close) - h)]
        up = sum(1 for x in mv if x > 0)
        print(f"  {h}m: a long averages {sum(mv) / len(mv):+.1f} pts "
              f"({up}/{len(mv)} = {up / len(mv):.0%} up), "
              f"a short averages {-sum(mv) / len(mv):+.1f}")
    print(f"  session: open {close[0]:.1f} close {close[-1]:.1f} "
          f"({close[-1] - close[0]:+.1f}), range {min(low):.1f}-{max(high):.1f}")

    und = {}
    for k in undirected:
        und[k] = und.get(k, 0) + 1
    print("\nNo direction called (not scored, not counted against anything):")
    print("  " + " · ".join(f"{k} x{v}" for k, v in sorted(und.items())))
    print("\nOne session. Events cluster, so these are not independent samples. "
          "Futures, not premium. No costs. Treat as a question, not an answer.")


if __name__ == "__main__":
    main()
