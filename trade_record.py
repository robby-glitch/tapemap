# tapemap/trade_record.py
"""trade_record.py -- the marked trade's record beyond {idx, k, side, role, t0, p0, qty, exit_t}: her thesis, the lots by
role, her lamp acknowledgements, re-plans and tags (Mary's Validate spec, C:/Users/kaam/Downloads/validate-tab-spec.md
§2.2, §2.3, §6, §7, as adapted 2026-10-05: lamps AUTO with a click to acknowledge, lot roles yes, no order path).

THE SCHEMA (backward compatible: a trade without these keys reads as before, and as ONE CORE lot):
  thesis  {why (<=120), t1, t2, inval, src: {t1, t2, inval: 'engine'|'her'}, locked_at}
  roles   [{id, role: CORE|BANKER|ADD, lots, entry_px, entry_t, add_stop?, exit_px?, exit_t?, exit_reason?, exit_note?}]
  acks    [{t, lamp, from, to}]
  replan  [{t, t1, t2}]            -- targets only, never the invalidation
  tags    ['FEAR_EXIT', 'FLIP', 'AMBER_EXIT', 'COOLDOWN', 'PREM_PEEK', ...]
RECORDS, NEVER ORDERS: an exit here is what she did on her broker, written down. Recording more lots than a role holds is
refused. When every lot is out, the trade's own exit_t is set, so the hold engine freezes at her exit as before.
Pure over the trade dict (the server holds the lock and saves the day)."""
from __future__ import annotations

from typing import List, Optional, Tuple

ROLES = ("CORE", "BANKER", "ADD")
REASONS = ("TARGET_1", "TARGET_2", "RED", "STOPPED", "FEAR_EXIT", "STALL", "MANUAL")
LAMPS = ("zone", "flow", "oi", "vpin")
STATES = ("G", "A", "R", "X")
MAX_ADDS = 3
OPS = ("thesis", "role_add", "role_exit", "ack", "replan", "peek")


def _num(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if 0 < v < 1e7 else None


def direction(tr: dict) -> int:
    """+1: the trade wants the index up (long CE / short PE); -1 the other way."""
    return 1 if (tr.get("side") == "CE") == (tr.get("role") == "long") else -1


def roles(tr: dict) -> List[dict]:
    """Her lots by role. A trade marked without roles is one CORE of its qty (at least 1), closed with the trade."""
    if tr.get("roles"):
        return tr["roles"]
    return [{"id": "CORE", "role": "CORE", "lots": max(1, int(tr.get("qty") or 0) or 1), "entry_px": tr.get("p0"),
             "entry_t": tr.get("t0"), "exit_t": tr.get("exit_t"), "exit_reason": "MANUAL" if tr.get("exit_t") else None,
             "implied": True}]


def open_roles(tr: dict) -> List[dict]:
    return [r for r in roles(tr) if not r.get("exit_t")]


def thesis_from(doc: dict, now: str) -> Tuple[Optional[dict], Optional[str]]:
    """Her thesis off a mark / thesis body; values she did not give stay None for the engine to fill (src 'engine')."""
    th = doc.get("thesis")
    if th is None:
        return None, None
    if not isinstance(th, dict):
        return None, "thesis must be an object"
    why = str(th.get("why") or "").strip()
    if len(why) > 120:
        return None, "why is one line, at most 120 characters"
    out = {"why": why or None, "src": {}, "locked_at": now}
    for k in ("t1", "t2", "inval"):
        v = th.get(k)
        if v in (None, ""):
            out[k] = None
            continue
        if _num(v) is None:
            return None, f"{k} must be a price"
        out[k] = _num(v)
        # The slip says which values it prefilled from the engine; anything unlabelled is hers.
        out["src"][k] = "engine" if (th.get("src") or {}).get(k) == "engine" else "her"
    return out, None


def roles_from(doc: dict, tr: dict) -> Tuple[Optional[List[dict]], Optional[str]]:
    """The ladder off a mark: [{role, lots}] or {CORE: n, BANKER: n}. Entry price / time default to the mark's."""
    rs = doc.get("roles")
    if rs is None:
        return None, None
    if isinstance(rs, dict):
        rs = [{"role": k, "lots": v} for k, v in rs.items()]
    out, n = [], {}
    for r in rs if isinstance(rs, list) else []:
        role = str((r or {}).get("role") or "").upper()
        try:
            lots = int(r.get("lots") or 0)
        except (TypeError, ValueError):
            return None, "lots must be whole numbers"
        if role not in ROLES or not 0 < lots <= 50:
            return None, "each role is CORE, BANKER or ADD with 1-50 lots"
        n[role] = n.get(role, 0) + 1
        out.append({"id": f"{role}{n[role] if n[role] > 1 else ''}", "role": role, "lots": lots,
                    "entry_px": _num(r.get("entry_px")) or tr.get("p0"), "entry_t": r.get("entry_t") or tr.get("t0")})
    if not out:
        return None, "roles must list at least one lot"
    if sum(1 for r in out if r["role"] == "ADD") > MAX_ADDS:
        return None, f"at most {MAX_ADDS} ADD lots"
    return out, None


def _explicit(tr: dict) -> List[dict]:
    """The roles as a stored list (an implied single CORE becomes a real one the first time a role op touches it)."""
    return tr.get("roles") or [{k: v for k, v in r.items() if k != "implied"} for r in roles(tr)]


def _close_if_done(tr: dict, t: str, now_s: float):
    if tr.get("roles") and not open_roles(tr) and not tr.get("exit_t"):
        tr["exit_t"], tr["exit_at"] = max(r["exit_t"] for r in tr["roles"]), now_s


def apply(tr: dict, op: str, doc: dict, now: str, now_s: float, read: Optional[dict] = None) -> Optional[str]:
    """One record op on an open or closed trade, in place. -> None, or why it was refused. `read` is the last live
    validate read for this trade (validate.read), used to tag the exit (FEAR_EXIT / AMBER_EXIT) -- never to block it."""
    t = str(doc.get("t") or now)
    if op == "thesis":
        if tr.get("exit_t"):
            return "the trade is closed; the thesis was its contract"
        if (tr.get("thesis") or {}).get("locked_at") and (doc.get("thesis") or {}).get("inval") not in (None, "", (tr["thesis"] or {}).get("inval")):
            return "the invalidation is locked at entry; re-plan changes the targets only"
        th, why = thesis_from(doc, t)
        if why:
            return why
        old = tr.get("thesis") or {}
        tr["thesis"] = {**old, **{k: v for k, v in (th or {}).items() if v is not None and k != "src"},
                        "src": {**old.get("src", {}), **(th or {}).get("src", {})}, "locked_at": old.get("locked_at") or t}
        return None
    if op == "replan":
        t1, t2 = _num(doc.get("t1")), _num(doc.get("t2"))
        if "inval" in doc:
            return "re-plan changes the targets only, never the invalidation"
        if t1 is None and t2 is None:
            return "re-plan needs t1 or t2"
        th = tr.setdefault("thesis", {"why": None, "t1": None, "t2": None, "inval": None, "src": {}, "locked_at": t})
        tr.setdefault("replan", []).append({"t": t, "t1": t1, "t2": t2})
        for k, v in (("t1", t1), ("t2", t2)):
            if v is not None:
                th[k] = v
                th.setdefault("src", {})[k] = "her"
        return None
    if op == "ack":
        lamp, frm, to = str(doc.get("lamp") or "").lower(), doc.get("from"), doc.get("to")
        if lamp not in LAMPS or to not in STATES:
            return "ack needs lamp zone|flow|oi|vpin and to G|A|R|X"
        tr.setdefault("acks", []).append({"t": t, "lamp": lamp, "from": frm, "to": to})
        return None
    if op == "peek":                          # the premium % / given-back toggle: hers to use, logged
        tr.setdefault("peeks", []).append(t)
        tags = tr.setdefault("tags", [])
        if "PREM_PEEK" not in tags:
            tags.append("PREM_PEEK")
        return None
    if op == "role_add":
        if tr.get("exit_t"):
            return "the trade is closed"
        rs = _explicit(tr)
        adds = [r for r in rs if r["role"] == "ADD"]
        if sum(1 for r in adds if not r.get("exit_t")) >= MAX_ADDS:
            return f"at most {MAX_ADDS} ADD lots open"
        try:
            lots = int(doc.get("lots") or 1)
        except (TypeError, ValueError):
            return "lots must be a whole number"
        if not 0 < lots <= 50:
            return "lots must be 1-50"
        tr["roles"] = rs + [{"id": f"ADD{len(adds) + 1}", "role": "ADD", "lots": lots, "entry_px": _num(doc.get("entry_px")),
                             "entry_t": t, "add_stop": _num(doc.get("add_stop"))}]
        return None
    if op == "role_exit":
        rs = _explicit(tr)
        rid = str(doc.get("role_id") or "")
        r = next((x for x in rs if x["id"] == rid and not x.get("exit_t")), None)
        if r is None:
            return f"no open lot {rid or '(none named)'} on this trade"
        try:
            lots = int(doc.get("lots") or r["lots"])
        except (TypeError, ValueError):
            return "lots must be a whole number"
        if not 0 < lots <= r["lots"]:
            return f"{rid} holds {r['lots']} lot{'s' if r['lots'] != 1 else ''}; {lots} cannot be recorded out"
        reason = str(doc.get("exit_reason") or "MANUAL").upper()
        if reason not in REASONS:
            return "exit_reason must be one of " + ", ".join(REASONS)
        if lots < r["lots"]:                          # part of the role: the part that left is its own row
            r["lots"] -= lots
            r = dict(r, id=f"{rid}.{sum(1 for x in rs if x['id'].startswith(rid + '.')) + 1}", lots=lots)
            rs.append(r)
        r.update(exit_px=_num(doc.get("exit_px")), exit_t=t, exit_reason=reason,
                 **({"exit_note": str(doc.get("exit_note"))[:200]} if doc.get("exit_note") else {}))
        tr["roles"] = rs
        snap_exit(tr, read, r)
        tags = tr.setdefault("tags", [])
        for tag in exit_tags(reason, read):
            if tag not in tags:
                tags.append(tag)
        _close_if_done(tr, t, now_s)
        return None
    return "op must be one of " + ", ".join(OPS)


def snap_exit(tr: dict, read: Optional[dict], role: Optional[dict] = None):
    """The lamps and the reversal count at her exit (spec §7 lamp_state_at_exit / reversal_conditions_at_exit), on the
    trade (the receipts read it there) and on the role that left. Nothing written when there was no live read."""
    if not read or not read.get("lamps"):
        return
    lamps = {k: v.get("state") for k, v in read["lamps"].items()}
    rev = (read.get("reversal") or {}).get("met")
    tr["lamps_at_exit"], tr["reversal_at_exit"] = lamps, rev
    if role is not None:
        role["lamps_at_exit"], role["reversal_at_exit"] = lamps, rev


def exit_tags(reason: str, read: Optional[dict]) -> List[str]:
    """FEAR_EXIT: she said so (the friction dialog), or a green trade left before a third of her typical time with fewer
    than 2 reversal conditions met. AMBER_EXIT: a lot left while no lamp was red and one was amber (the spec: AMBER is a
    hold state). Tags describe; they never block."""
    out = ["FEAR_EXIT"] if reason == "FEAR_EXIT" else []
    if read and reason not in ("TARGET_1", "TARGET_2", "STOPPED"):
        tm, rv = read.get("timer") or {}, read.get("reversal") or {}
        if tm.get("fear_zone") and (rv.get("met") or 0) < 2 and "FEAR_EXIT" not in out:
            out.append("FEAR_EXIT")
        if (read.get("shadow") or {}).get("amber_no_exit"):
            out.append("AMBER_EXIT")
    return out


def entry_tags(new: dict, trades: List[dict], now_s: float) -> List[str]:
    """FLIP: the opposite direction within 60 s of an exit on the same index. COOLDOWN: inside 10 min of a STOPPED or RED
    exit. Warned and tagged, never refused (no order path, and she decides)."""
    tags = []
    for t in trades:
        if t is new or t.get("idx") != new.get("idx"):
            continue
        if t.get("exit_at") and now_s - t["exit_at"] <= 60 and direction(t) != direction(new):
            tags.append("FLIP")
        cut = [r for r in roles(t) if r.get("exit_reason") in ("STOPPED", "RED")]
        if cut and t.get("exit_at") and now_s - t["exit_at"] <= 600:
            tags.append("COOLDOWN")
    return sorted(set(tags))


def cooldown(trades: List[dict], idx: str, now_s: float) -> Tuple[Optional[dict], Optional[dict]]:
    """(cooldown, flip) for the FLAT face: 10 min after a STOPPED / RED exit; 60 s after any exit, with the direction a
    FLIP would take. Each {until (epoch s), left_s, why}."""
    cd = fl = None
    for t in trades:
        if t.get("idx") != idx or not t.get("exit_at"):
            continue
        cut = [r for r in roles(t) if r.get("exit_reason") in ("STOPPED", "RED")]
        if cut and now_s - t["exit_at"] < 600 and (cd is None or t["exit_at"] + 600 > cd["until"]):
            cd = {"until": t["exit_at"] + 600, "left_s": int(t["exit_at"] + 600 - now_s),
                  "why": f"{cut[-1]['exit_reason']} at {t['exit_t']} on {t['k']:g} {t['side']} — no new entry for 10 min unless a fresh ARM location"}
        if now_s - t["exit_at"] < 60 and (fl is None or t["exit_at"] + 60 > fl["until"]):
            fl = {"until": t["exit_at"] + 60, "left_s": int(t["exit_at"] + 60 - now_s), "from_d": direction(t),
                  "why": f"out of {t['k']:g} {t['side']} at {t['exit_t']} — the other side now is a FLIP"}
    return cd, fl
