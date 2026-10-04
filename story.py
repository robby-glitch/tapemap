# tapemap/story.py
"""story.py -- the decoder's one sentence (Fable, docs/reader/FABLE-DECODER-DESIGN-2026-10-04.md §2.6), for the panel and
the DESK.

ONE DEFINITION. The events are the GoCharting extension's (orderflow-desk src/engine/decoder.js), posted with every tape
as `tape["decoder"]` (schema v1: id, kind, t, p, side, lots, trades, at, oi{state,doi,net,step}, quad, split, state,
chip, chips, en). This module READS their fields and never re-derives an event, a threshold or a state: if the page
says BAAKI, the sentence says confirm pending. What it adds is only what the page cannot know on its own bar -- where
price is NOW against an open print -- and the count of prints still open.

Pure, stdlib only, no I/O, no clock. Every number in the sentence is the event's own [M] (lots, price, trades, OI on the
bar) or the futures price now [M]; the direction words (naye / held / trapped) are [I] and the object says so in `tag`.
"""
from __future__ import annotations

from typing import Optional

KINDS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7")
_EMPTY = {"sentence": None, "sentence_why": "no decoder event yet", "chips": [], "event": None, "asof": None,
          "open_prints": 0, "tag": {"M": ["lots", "p", "trades", "oi.doi", "fut"], "I": ["state", "quad", "split"]}}


def _px(p: float) -> str:
    return f"{round(p):,}"


def compose(dec: Optional[dict], fut: Optional[float] = None) -> dict:
    """The sentence for the event that matters most now: the newest print still waiting for its exit (an open level),
    else the newest event the page drew (shown). None, with its reason, when the page sent no decoder or nothing yet."""
    out = dict(_EMPTY)
    if not isinstance(dec, dict):
        return {**out, "sentence_why": "the extension sent no decoder (it predates 0.4.0)"}
    if dec.get("v") != 1:
        return {**out, "sentence_why": f"decoder schema {dec.get('v')!r} is not the one this server reads (1)"}
    evs = [e for e in dec.get("events") or [] if isinstance(e, dict) and e.get("kind") in KINDS and e.get("en")]
    open_prints = [e for e in evs if e["kind"] == "E1" and e.get("state") == "BAAKI"]
    shown = [e for e in evs if e.get("shown")]
    top = (sorted(open_prints, key=lambda e: e.get("t") or 0) or sorted(shown, key=lambda e: e.get("t") or 0) or [None])[-1]
    if top is None:
        return {**out, "sentence_why": "no decoder event yet today" if not evs else "no event at her ring or a level yet"}
    s = top["en"]
    if top["kind"] == "E1" and top.get("state") == "BAAKI" and fut is not None and top.get("p") is not None:
        d = round(float(fut) - float(top["p"]), 1)
        s += f"; price now {abs(d):g} pts {'above' if d > 0 else 'below' if d < 0 else 'at'} his price"
    others = [e for e in open_prints if e is not top]
    if others:
        s += "; also open: " + ", ".join(f"{'buyer' if e.get('side', 0) > 0 else 'seller'} {_px(e['p'])}" for e in others[-2:])
    return {**out, "sentence": s, "sentence_why": None, "chips": list(top.get("chips") or [top.get("chip")])[:3],
            "event": {"id": top.get("id"), "kind": top["kind"], "state": top.get("state"), "t": top.get("t"), "p": top.get("p"), "side": top.get("side")},
            "asof": top.get("time"), "open_prints": len(open_prints)}
