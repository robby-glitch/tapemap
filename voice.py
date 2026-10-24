"""voice.py -- THE ONE VOICE in a trade (NOTEPAD A52; Mary 2026-10-24, "build it"). Mid-trade the fold engine's word,
HOLD v2's line, PULLBACK / GAVE UP, the W-BLEED gauge and ZONE ALONE all spoke at once. This folds them into ONE state
per open marked trade, the highest that is active:

  EXIT     the fold engine says FOLD, or HOLD v2's line is hit / 15:20 -- whichever came FIRST, named
  WARN     PAST GIVE-UP, HOLD v2's front gave up (until the line trails or locks after it), GAVE UP
           (docs/validate2/fable/DESIGN.md §5.4), W-BLEED (>= 10 % off the peak with >= 15 updates, §5.5), ZONE ALONE
           (§5.3) -- the FIRST that triggered, with its number
  TIGHTEN  HOLD v2's line moved her way, or its breakeven lock engaged: an event, shown 60 s
  HOLD     nothing above

DISPLAY ONLY. It reads the engine's reply and HOLD v2's block and writes neither; both rules keep running exactly as
registered (fold.py rev 6, §1m). When they disagree the more cautious state shows. `seq` moves only when the state
changes: the faces sound on it, never on a repeat. Pure apart from `mem` (the caller's dict per trade: a restart starts
it again at the first look, and a trigger with no time of its own is then dated from that look, `seen` says which) and
`prem_at` (the engine's own chain interpolation, [I])."""
from __future__ import annotations

import re

ORDER = ("HOLD", "TIGHTEN", "WARN", "EXIT")
TIGHTEN_MS = 60000
BLEED_OFF, BLEED_N = 0.10, 15          # §5.5: amber at >= 10 % off the peak with >= 15 updates (fold.OI_NOISE_N)
WITH_WORDS = (("O", None), ("F", "flow saath"), ("Z", "zone peeche"), ("V", "VPIN saath"))   # OI first: her method


def _sec(hms):
    p = [int(x) for x in str(hms).split(":")[:3]] + [0, 0]
    return p[0] * 3600 + p[1] * 60 + p[2]


def _at(base, hms):
    """'HH:MM[:SS]' on the view's day -> epoch ms, or None."""
    return None if not hms else base + _sec(hms) * 1000


def _hm(base, t):
    s = (t - base) // 1000
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}"


def _n(x):
    return "?" if x is None else f"{x:,.0f}"


def _commas(s):
    return re.sub(r"\b(\d{5,})(\.\d+)?\b", lambda m: f"{float(m.group(0)):,.0f}", str(s))


def _L(x):
    return "?" if x is None else f"{x / 1e5:.1f}L"


def bleed(W):
    """The W-BLEED gauge (§5.5) on the engine's wall behind her: on, or not."""
    return bool(W) and (W.get("off") or 0) >= BLEED_OFF and (W.get("upd") or 0) >= BLEED_N


def _triggers(rep, h2, base, d, W):
    """Every active rule as (state, key, t ms or None, reason, src). t None: no time of its own (dated at first sight)."""
    v = rep["view"]
    words = [w for w in rep.get("words") or () if not w.get("after_exit")]
    head, clause = str(v.get("headline") or ""), v.get("clause") or ""
    out = []
    fw = next((w for w in words if str(w.get("headline") or "").startswith("FOLD")), None)
    if fw or head.startswith("FOLD"):
        h = str((fw or {}).get("headline") or head)
        what = _commas(re.sub(r"^FOLD\s*·?\s*|\s*·\s*\d{1,2}:\d{2}(:\d{2})?$", "", h)) or "fold"
        out.append(("EXIT", "FOLD", _at(base, (fw or {}).get("t")), f"FOLD — {what} (fold engine)", "fold engine"))
    if (h2 or {}).get("ok"):
        how, x = str(h2.get("how") or ""), h2.get("v2_exit") or {}
        if how.startswith("line_") or how == "mark":      # the line alone: it keeps trailing past a gave-up, and is her stop
            out.append(("EXIT", "V2", _at(base, h2.get("touched_t") or "15:20"),
                        "15:20 — din khatam (HOLD v2)" if how == "mark" else f"stop hit {_n(h2.get('line_fut'))}f (HOLD v2)",
                        "HOLD v2"))
        # its front gave up: WARN, never EXIT. §1m.12: v2 never changes her window's word, and in-sample (28 rows) its
        # gave-up cut winners as often as it saved losers (her 21 Oct PE: 11:07, then +5R). Answered once the line trails
        # her way again or the lock engages after it.
        g = h2.get("gave_up_t")
        if g and not any(a and a > g for a in [m.get("at") for m in h2.get("moves") or ()] + [h2.get("lock_t")]):
            px = f" @ {_n(x.get('px'))}f" if x.get("how") == "gave_up" else ""
            out.append(("WARN", "V2GU", _at(base, g), f"{'CE' if d < 0 else 'PE'} front gave up{px} · line "
                        f"{_n(h2.get('line_fut'))}f (HOLD v2)", "HOLD v2"))
    if head.startswith("PAST GIVE-UP"):
        t0 = None
        for w in words:                                    # the start of the latest run of PAST GIVE-UP words
            t0 = (t0 or w.get("t")) if str(w.get("headline") or "").startswith("PAST GIVE-UP") else None
        out.append(("WARN", "PGU", _at(base, t0), "PAST GIVE-UP — " + _commas(" · ".join(clause.split(" · ")[:2]) or "give-up crossed"),
                    "fold engine"))
    fut, E = v.get("fut"), v.get("E")
    ev = v.get("oi_event")
    if W and fut is not None and E is not None and d * (fut - E) < 0 and (ev or bleed(W)):
        off = f"−{100 * W['off']:.1f}% off its {_L(W.get('peak'))} peak" if W.get("off") is not None else "off its peak"
        out.append(("WARN", "GAVEUP", None, f"GAVE UP — {W.get('k')} {W.get('side')} writers {off} · fut {d * (fut - E):+.0f} vs entry",
                    "§5.4"))
    if bleed(W):
        out.append(("WARN", "BLEED", _at(base, W.get("bleed_t")),
                    f"W-BLEED — {W.get('k')} {W.get('side')} −{100 * W['off']:.1f}% off {_L(W.get('peak'))} peak · {W['upd']} upd", "§5.5"))
    ch, since = v.get("chips") or {}, v.get("chip_since") or {}
    if ch.get("Z") == "WITH" and ch.get("F") != "WITH" and ch.get("O") != "WITH":
        ts = [since.get(k) for k in ("Z", "F", "O") if since.get(k)]
        out.append(("WARN", "ZONE", _at(base, max(ts, key=_sec)) if ts else None,
                    f"ZONE ALONE — OI {str(ch.get('O') or '?').lower()} · flow {str(ch.get('F') or '?').lower()}", "§5.3"))
    return out


def _why(v, W):
    """HOLD's line 3: the two strongest WITH facts (OI first), else the engine's clause; blind says so."""
    head = str(v.get("headline") or "")
    if head.startswith("CAN'T CHECK"):
        return ["could not check — fold engine: " + (v.get("clause") or head)]
    ch, out = v.get("chips") or {}, []
    for k, word in WITH_WORDS:
        if ch.get(k) == "WITH":
            out.append(word or (f"{W.get('side')} {W.get('k')} writers building" if W else "OI saath"))
    return out[:2] or [v.get("clause") or "kuch saath nahi, kuch khilaaf nahi"]


def ladder(rep, h2, now_ms, mem, prem_at=None):
    """The voice for one open marked trade: {ok, state, seq, since, reason, src, l1, l2, l3, stop_*, lock_*, r_now, pnl,
    min, active, ...}, or {ok False, why}. `rep` is the /api/fold reply (ok, view, words, trade), `h2` HOLD v2's block
    (any shape: not ok is "no line"), `mem` this trade's dict, `prem_at(px)` -> (premium, why)."""
    v = (rep or {}).get("view") or {}
    d, t_v = v.get("d"), v.get("t")
    if not (rep or {}).get("ok") or v.get("headline") is None or d not in (1, -1) or t_v is None:
        why = str((rep or {}).get("why") or v.get("why") or "the engine has no read yet")
        return {"ok": False, "why": why if why.startswith("could not check") else "could not check — " + why}
    base = t_v - (((t_v // 1000) + 19800) % 86400) * 1000           # IST midnight of the view's day
    W = v.get("W") or None
    h2ok = bool((h2 or {}).get("ok"))
    trig = _triggers(rep, h2, base, d, W)
    seen = mem.setdefault("seen", {})
    for k in [k for k in seen if k not in {x[1] for x in trig}]:
        del seen[k]                                                  # cleared: a later return is a new trigger
    act = []
    for st, key, t, why, src in trig:
        seen.setdefault(key, now_ms)
        act.append({"state": st, "key": key, "t": t if t is not None else seen[key], "seen": t is None, "reason": why, "src": src})
    # TIGHTEN: a new HOLD v2 trail move or its lock, after the first look (her first look is the baseline, never an event)
    if h2ok:
        mv, lk = len(h2.get("moves") or ()), h2.get("lock_t")
        if "v2" in mem and (mv > mem["v2"][0] or (lk and not mem["v2"][1])):
            m = (h2.get("moves") or [{}])[-1]
            why = (f"BE lock ✓ {_n(h2.get('E'))}f (HOLD v2)" if lk and not mem["v2"][1] else
                   f"stop {_n(m.get('from'))}→{_n(m.get('to'))}f (HOLD v2 trail)")
            mem["tighten"] = (now_ms + TIGHTEN_MS, why, now_ms)
        mem["v2"] = (mv, lk)
    tg = mem.get("tighten")
    if tg and now_ms < tg[0]:
        act.append({"state": "TIGHTEN", "key": "TIGHT", "t": tg[2], "seen": False, "reason": tg[1], "src": "HOLD v2"})
    state = max((a["state"] for a in act), key=ORDER.index, default="HOLD")
    top = min((a for a in act if a["state"] == state), key=lambda a: a["t"], default=None)   # the first that triggered
    if mem.get("state") != state:
        mem["state"], mem["seq"], mem["at"] = state, mem.get("seq", 0) + 1, now_ms
    # the one stop: HOLD v2's line, else the engine's give-up G (her trade always has one or the other once read)
    G = (v.get("G") or {}).get("px")
    bix = (v.get("units") or {}).get("basis_ix")
    if h2ok and h2.get("line_fut") is not None:
        sf, ss, ssrc = h2["line_fut"], h2.get("line_spot"), "HOLD v2"
        sp, spw = prem_at(sf) if prem_at else (None, "could not check — no interpolation")
    else:
        sf, ssrc = G, "fold engine"
        ss = None if G is None or bix is None else round(G - bix, 1)
        sp, spw = (v.get("prem") or {}).get("at_G"), (v.get("prem") or {}).get("at_G_why")
    E, fut = v.get("E"), v.get("fut")
    line0 = (h2 or {}).get("line0") if h2ok else G
    risk = abs(line0 - E) if None not in (line0, E) and line0 != E else None
    r_now = None if risk is None or fut is None else round(d * (fut - E) / risk, 2)
    tr = rep.get("trade") or {}
    own = -1 if tr.get("side") == "SELL" else 1
    pn, p0 = (v.get("prem") or {}).get("now"), tr.get("p0")
    pnl = None if None in (pn, p0) else round(own * (pn - float(p0)), 1)
    mins = None if not tr.get("entry_t") else max(0, (t_v - _at(base, tr["entry_t"])) // 60000)
    lock_t = h2.get("lock_t") if h2ok else None
    lock_f = E if h2ok and E is not None else None
    lock_on = None if lock_f is None or risk is None else round(E + d * 2.0 * risk, 1)    # hold2.LOCK_R: MFE >= 2R
    side = f" {tr.get('ty') or ''}" + (" short" if own < 0 else "")
    l1 = (f"{'▲' if d > 0 else '▼'} {'?' if tr.get('k') is None else int(float(tr['k']))}{side} · {'?' if mins is None else mins} min · "
          f"{'?' if r_now is None else f'{r_now:+.1f}'}R ({'₹?' if pnl is None else f'₹{pnl:+.0f}'})")
    l2 = (f"stop {_n(sf)}f / {_n(ss)}s ≈ {'₹?' if sp is None else f'₹{sp:.0f}'}"
          + ("" if lock_f is None else f" · BE lock ✓ {lock_t}" if lock_t else      # where the lock ENGAGES (MFE 2R), not E
             "" if lock_on is None else f" · BE lock at {_n(lock_on)}f"))
    why = [top["reason"]] if top else _why(v, W)
    return {"ok": True, "state": state, "seq": mem["seq"], "since": _hm(base, mem["at"]) if mem["at"] >= base else None,
            "reason": top["reason"] if top else None, "src": top["src"] if top else None,
            "trig_t": _hm(base, top["t"]) if top else None, "seen": bool(top and top["seen"]),
            "l1": l1, "l2": l2, "l3": "why: " + " · ".join(why), "why": why,
            "stop_f": sf, "stop_s": ss, "stop_src": ssrc, "stop_prem": sp, "stop_prem_why": None if sp is not None else spw,
            "lock_f": lock_f, "lock_on_f": lock_on, "lock_t": lock_t, "r_now": r_now, "prem_now": pn, "pnl": pnl, "min": mins, "d": d,
            "active": [dict(a, t=_hm(base, a["t"])) for a in sorted(act, key=lambda a: (-ORDER.index(a["state"]), a["t"]))],
            "tag": "I", "note": "one voice, display only: the engine's word and HOLD v2 run as registered"}


def receipt(tr, prem, rows):
    """The post-trade receipt (A52 §4): her exit beside what the three shadow lines would have said, from their forward log
    rows (data/hold/shadow_<day>.jsonl, holdshadow.row) -- shown only after she is out."""
    by = {r.get("line"): r for r in rows or () if r.get("id") == tr.get("id")}
    parts = [f"you exited {str(tr.get('exit_t') or '?')[:5]} @ {'₹?' if prem is None else f'₹{prem:.0f}'}"]
    for ln in ("POP", "EFFORT", "CHOP"):
        r = by.get(ln) or {}
        sh = r.get("sh") or {}
        if r.get("how") in ("vwap", "pop", "effort", "mark") and sh.get("t"):
            parts.append(f"{ln} would say {sh['t']}" + ("" if sh.get("R") is None else f" ({sh['R']:+.1f}R)"))
        else:
            parts.append(f"{ln} {'?' if not r else '—'}")
    return {"ok": True, "text": " · ".join(parts), "n": len(by), "tag": "I",
            "why": None if by else "could not check — no shadow rows logged for this trade"}
