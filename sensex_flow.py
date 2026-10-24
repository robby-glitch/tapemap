"""sensex_flow.py -- SENSEX reads NIFTY's order flow: HOLD v2 Amendment 3 and the in-trade FLOW read (the Python half of
docs/hold/SENSEX-NIFTY-FLOW-PREREG.md, sha256 9e2831b5..., SIGNED 2026-10-25 "sign without 5", research-findings §1q;
Validate rev 3.1 is engine.js R31). Her
words: "i dont consider sensex oderflow i take nifty oder flow and trade in sensex ... but i consider its oi". For a SENSEX
trade every ORDER-FLOW read is NIFTY futures', labelled NIFTY; every OI read stays SENSEX's own. A NIFTY read that cannot
be made is "could not check — NIFTY flow not read (why)": never SENSEX's, never a zero.

ON since her signature (§9); False would restore rev 3 / §1m exactly (no caller enters here then). Pure: no I/O, no clock."""
from __future__ import annotations

import hold2

ON = True                        # §9: signed 2026-10-25
FROM = "2026-10-25"              # the signing day: forward HOLD v2 SENSEX rows from it are push_src NIFTY
SHA8, SRC = "9e2831b5", "NIFTY"            # the signed text (§9)
SIDE = {"BUYERS": 1, "SELLERS": -1}


def on(idx):
    return ON and idx == "SENSEX"


def _sec(hms):
    p = [int(x) for x in str(hms).split(":")[:3]] + [0, 0]
    return p[0] * 3600 + p[1] * 60 + p[2]


# ---- §1.2 HOLD v2 Amendment 3: NIFTY's push moves the SENSEX line, in SENSEX prices ----------------------------------

def translate(npush, sx_bars5):
    """NIFTY's pushes (hold2.pushes on NIFTY's own bars, ranked on NIFTY's own history) as SENSEX line moves: each keeps
    its slot, time, close and direction; its origin becomes o, the open of SENSEX's own 5-min bar of the same slot, and
    U = max(sigma of SENSEX's 5-min bars at that bar (hold2.sigmas: market.js vwapSeries, as §1m), 0.1 % of o). A slot
    with no SENSEX bar is skipped. -> (pushes in hold2.pushes' shape with src "NIFTY" and the NIFTY bar kept as n_*, the
    skipped NIFTY pushes)"""
    by = {b["s"]: (b, sg) for b, sg in zip(sx_bars5 or (), hold2.sigmas(sx_bars5 or ()))}
    out, skip = [], []
    for p in npush or ():
        b, sg = by.get(p["s"], (None, 0.0))
        if b is None or b.get("o") is None:
            skip.append(p)
            continue
        out.append(dict(p, origin=b["o"], c=b["c"], U=max(sg, hold2.U_MIN * b["o"]), src=SRC,
                        n_origin=p["origin"], n_c=p["c"], n_U=p["U"], n_src=p.get("src")))
    return out, skip


def line(npush, nwhy, sx_bars5):
    """The SENSEX line's pushes -> (translated, None, skipped), or (None, why, []) when NIFTY's cannot be read: the trail
    is then inactive and says why; it never reads SENSEX's own."""
    if npush is None:
        return None, f"push ? — could not check: NIFTY flow not read ({nwhy or hold2.NO_REF})", []
    P, skip = translate(npush, sx_bars5)
    return P, None, skip


def stamp(h2, skip, t0, now_m):
    """HOLD v2's block for a SENSEX trade (display): push_src NIFTY, its push named NIFTY, and each NIFTY push of her
    direction closed since her entry that had no SENSEX bar: "NIFTY push hh:mm · SENSEX bar ?"."""
    if not (h2 or {}).get("ok"):
        return h2
    h, m = (int(x) for x in str(t0).split(":")[:2])
    sk = [f"NIFTY push {p['t']} · SENSEX bar ?" for p in skip or () if p["d"] == h2.get("d") and h * 60 + m + 1 < p["close"] <= now_m]
    for k in ("text", "why", "why_short"):
        if isinstance(h2.get(k), str):
            h2[k] = h2[k].replace("PUSH ", "NIFTY PUSH ")
    if sk and h2.get("text"):
        h2["text"] += " · " + " · ".join(sk)
    h2["push_src"] = SRC
    return h2


def push_src(idx, day):
    """A forward HOLD v2 row's stamp (tools/hold2_score.score): None while OFF (today's rows, unstamped); for SENSEX,
    "NIFTY" on or after the signing day FROM, "SENSEX-ux" before it (rows before the signature keep their source)."""
    if not on(idx):
        return None
    return SRC if FROM and day >= FROM else "SENSEX-ux"


# ---- §1.3 the in-trade FLOW read shown for a SENSEX trade ------------------------------------------------------------

def flow_chip(d, flat, ts=None):
    """The all-day NIFTY engine's flat FLOW row (fold.State.flat_view rows.flow: BUYERS / SELLERS / QUIET / CAN'T CHECK) in
    her direction d: BUYERS = WITH a trade wanting the future up, AGAINST one wanting it down; SELLERS the reverse; QUIET
    and CAN'T CHECK as they are. -> (chip, sentence "NIFTY flow: ..."). Not read, or not the trade's minute (`ts`, the
    view's "HH:MM:SS", within 60 s): CAN'T CHECK with why."""
    flat = flat or {}
    row = (flat.get("rows") or {}).get("flow") or {}
    why = None
    if not flat.get("ok"):
        why = flat.get("why") or "no NIFTY flat read"
    elif ts and flat.get("asof") and abs(_sec(flat["asof"]) - _sec(ts)) > 60:
        why = f"NIFTY read {flat['asof']}, trade {ts}"
    elif row.get("chip") not in ("BUYERS", "SELLERS", "QUIET", "CAN'T CHECK"):
        why = "no NIFTY flow row"
    if why:
        return "CAN'T CHECK", f"could not check — NIFTY flow not read ({why})"
    c = row["chip"]
    return (c if c not in SIDE else "WITH" if SIDE[c] == d else "AGAINST"), f"NIFTY flow: {row.get('sentence') or '—'}"


def flow_view(rep, flat, mem):
    """§1.3 on a COPY of the in-trade reply (server._in_trade, voice_path.run): view.chips.F / sentences.F / rows.flow
    become NIFTY's chip in her direction (flow_chip), chip_since.F the view time it took that value (`mem`: the caller's
    dict per trade), flow_src NIFTY on the view and the reply. The engine's state, word, G and acceptance are untouched; a
    frozen view (her exit) or a reply with no read passes through as it is."""
    v = (rep or {}).get("view") or {}
    if not (rep or {}).get("ok") or v.get("frozen") or v.get("headline") is None or v.get("d") not in (1, -1):
        return rep
    chip, sen = flow_chip(v["d"], flat, v.get("ts"))
    if (mem.get("F") or (None,))[0] != chip:
        mem["F"] = (chip, v.get("ts"))
    v = dict(v, chips=dict(v.get("chips") or {}, F=chip), sentences=dict(v.get("sentences") or {}, F=sen),
             rows=dict(v.get("rows") or {}, flow=dict(chip=chip, sentence=sen)),
             chip_since=dict(v.get("chip_since") or {}, F=mem["F"][1]), flow_src=SRC)
    return dict(rep, view=v, flow_src=SRC)


def relabel(vc):
    """The one voice's flow words name NIFTY ("NIFTY flow saath", "· NIFTY flow quiet"); voice.py is unchanged."""
    if not (vc or {}).get("ok"):
        return vc

    def f(s):
        return s.replace("flow saath", "NIFTY flow saath").replace(" · flow ", " · NIFTY flow ") if isinstance(s, str) else s
    vc["l3"], vc["reason"] = f(vc.get("l3")), f(vc.get("reason"))
    vc["why"] = [f(x) for x in vc.get("why") or ()]
    vc["active"] = [dict(a, reason=f(a.get("reason"))) for a in vc.get("active") or ()]
    return vc
