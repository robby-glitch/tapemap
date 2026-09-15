"""trader.py -- the paper desk: the tool trading itself, both sides, 2 lots.

WHAT THIS IS. The judge the operator asked for: a paper book the stack runs
on its own readings, managing positions as it sees fit, logging every
decision AND every refusal, so that after enough sessions the record -- not
anyone's memory -- says whether the readings deserve real capital. PAPER
FOREVER: this module simulates fills against quotes we already receive
(quoting.py), talks to no broker, and must never learn how (CLAUDE.md rule
10 binds it doubly). Deployment of real capital is the operator's decision
alone, made OUTSIDE this code.

BOTH SIDES, BY DESIGN. The operator's correction, recorded: the desk is not
a seller. It sells when hedging damps (PIN), buys the forced flow when it
runs (CASCADE -- the short-covering scalp), goes directional after a
liquidity grab (the war map's BREAK->RUN), and sells the crest after a
squeeze exhausts. Four strategies, two long, two short, every entry carrying
its rule-9 sentence: WHO is forced, and WHY. No sentence, no trade.

    SELL_PIN        maker  short the wings beyond the expected move in PIN
    BUY_CASCADE     taker  long the trapped side's option while it covers
    DIR_AFTER_GRAB  taker  long the break direction when a dwell resolves
                           BREAK->RUN with a named target
    SELL_CREST      maker  short the side that just finished covering, into
                           its extraction-inflated premium

RISK BEFORE SIGNALS (the whole point of book.py):
    - no new risk when the book's forced_ratio < FORCED_MIN -- if the
      declared stress would force us, we are the crowd and the answer is no
    - one position per (strategy, index); MAX_OPEN concurrent overall
    - a day loss beyond DAY_LOSS_CAP flattens the book and closes the day
    - no entries after NO_ENTRY_AFTER; everything squares off by SQUARE_OFF
      (intraday only, like the operator)
    - every one of these refusals is LOGGED with its reason -- the decision
      journal scores the trades not taken too

SINGLE-LEG POSITIONS ONLY, deliberately: a strangle is two positions. Each
leg's P&L, margin and attribution stay separately readable, partial fills
cannot strand a half-structure, and the margin model prices each naked short
conservatively (no pairing discount) -- errors lean cautious.

THE FILL MODEL'S HONESTY TRAVELS WITH THE RESULTS: maker fills assume front
of queue at ~10s sampling, so maker P&L here is an UPPER BOUND (quoting.py's
docstring); any review of this book must repeat that sentence.

KILL CONDITION (declared at birth): if after ~30 paper sessions the
attribution shows the strategy set doing no better than the flat book --
the S5 skip -- the brain is rewritten or deleted, not tuned. The paper book
exists to earn or lose TRUST, never to gate the operator, and its numbers
are accounting, not a promise: no figure here is ever an expectancy claim.

Disk (this module only, senses.py precedent, all fail-soft, market-hours
gated):
    data/paper_desk/state.json          the whole book + quotes, rewritten
    data/paper_desk/trades.jsonl        one line per fill, append-only
    data/paper_desk/decisions_<day>.jsonl   entries/exits/refusals/posts
"""

from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

import book as book_mod
import desk as desk_mod
import hedge as hedge_mod
import quoting
import surface as surface_mod
from gamma import theta_day as bs_theta_day
from gamma import vega as bs_vega

# --- the [I] layer, every number declared -----------------------------------
PAPER_CAPITAL = 25_00_000.0   # Rs 25L behind a 2-lot test book
PAPER_LOTS = 2                # the operator's 2-3 lot test range, low end
MAX_OPEN = 2                  # concurrent positions across all indices
FORCED_MIN = 1.5              # forced_ratio below this -> no new risk
DAY_LOSS_CAP = 25_000.0       # rupees; beyond it the book flattens for the day
NO_ENTRY_AFTER = (15, 0)      # IST
SQUARE_OFF = (15, 18)         # IST
SCALP_TARGET = 0.25           # long scalps: +25% of entry premium
SCALP_STOP = -0.15            # ...or -15%, evaluated on marks, no resting stop
SHORT_DECAY_TARGET = 0.40     # shorts: close when premium has decayed 40%
SHORT_STOP = -0.50            # ...and cut when the premium has moved HALF the
                              # credit AGAINST the book. Shorts had a target and
                              # NO stop until 2026-08-25 -- the leg with unbounded
                              # loss was the one left unstopped. Measured 08-24:
                              # P7 (SELL_CREST BANKNIFTY 57700PE x60 @153.55) ran
                              # to 357.55 and was closed only by the 15:18 clock,
                              # Rs -12,240 against +5,502 from the other twelve
                              # trips combined; frac reached -1.33. DAY_LOSS_CAP
                              # could not save it -- the winners masked it, so the
                              # aggregate never breached the cap.  [M]
CASCADE_MIN = 2               # snapshots a CASCADE must SURVIVE before its ending
                              # may arm SELL_CREST. Measured 08-24: 23 of 23
                              # cascade spells lasted exactly ONE snapshot, so the
                              # arm fired on every flicker -- each blink "ending a
                              # cascade" and inviting a short. At 2 this suppresses
                              # all 23, which is the point: there was no real
                              # cascade that day.  [M]
CREST_TTL = 8                 # snapshots a crest offer rests before it dies
CASCADE_COOL = 3              # consecutive non-CASCADE snapshots before a
                              # cascade scalp is declared over  [I]

DIR_ = os.path.join("data", "paper_desk")
STATE = os.path.join(DIR_, "state.json")
TRADES = os.path.join(DIR_, "trades.jsonl")

MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)


def day_decisions_path(day: Optional[str] = None) -> str:
    day = day or datetime.now().strftime("%Y-%m-%d")
    return os.path.join(DIR_, f"decisions_{day}.jsonl")


def market_hours(now: Optional[datetime] = None) -> bool:
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False
    return MARKET_OPEN <= (now.hour, now.minute) <= MARKET_CLOSE


def _append(path: str, row: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return True
    except Exception:
        return False


def _by_k(doc: dict) -> Dict[tuple, dict]:
    out = {}
    for s in doc.get("strikes") or []:
        k = s.get("k")
        if k is None:
            continue
        for right, side in (("CE", "ce"), ("PE", "pe")):
            leg = s.get(side)
            if leg:
                out[(float(k), right)] = leg
    return out


def _atm_strike(doc: dict) -> Optional[float]:
    spot, ks = doc.get("spot"), [s.get("k") for s in doc.get("strikes") or []]
    ks = [k for k in ks if k is not None]
    if spot is None or not ks:
        return None
    return float(min(ks, key=lambda k: abs(k - spot)))


def _secs(ts: Optional[str]) -> Optional[int]:
    """"HH:MM:SS" -> seconds of day. None when unparseable, never 0."""
    try:
        h, m, s = (int(x) for x in (ts or "").split(":")[:3])
    except (ValueError, TypeError):
        return None
    return h * 3600 + m * 60 + s


def _vwap(rows: List[dict]) -> tuple:
    """(price, qty) across partial fills, QUANTITY-WEIGHTED.

    A plain mean would misprice a position filled 10 lots at 100 and 1 lot at
    200 as 150 -- the arithmetic that makes a losing trade look flat.
    """
    q = sum(abs(r.get("qty") or 0) for r in rows)
    if not q:
        return (None, 0)
    return (sum((r.get("px") or 0.0) * abs(r.get("qty") or 0)
                for r in rows) / q, q)


def pair_trades(rows: List[dict],
                why_by: Optional[Dict[tuple, dict]] = None) -> List[dict]:
    """Trade-log rows -> one round trip per pid. Pure; the caller reads files.

    THE LOG IS THE RECORD, not `state.json`. `closed_today` came off the
    in-memory book, which a restart truncates to whatever the state file kept
    -- on 2026-08-25 that was 20 rows against 62 real round trips in
    `trades.jsonl`. Same durability asymmetry the day-state work fixed for the
    drag trace, biting a screen the operator actually reads.

    `why_by` is an optional {(idx, strategy, entry_ts): {...}} recovered from
    the decisions log, used ONLY for rows written before the trade row carried
    its own why. A recovered why is tagged as such -- it is a join on three
    fields, not an identity, and must not pass as the durable article.

    A position with opens and no closes is still OPEN: it is returned with
    null exit fields rather than dropped, because a screen that silently omits
    the running trade is how a book gets misread.
    """
    by_pid: Dict[str, List[dict]] = {}
    for r in rows:
        by_pid.setdefault(r.get("pid"), []).append(r)
    out = []
    for pid, rs in by_pid.items():
        opens = [r for r in rs if r.get("kind") == "open"]
        closes = [r for r in rs if r.get("kind") == "close"]
        if not pid or not opens:
            continue
        o_px, o_qty = _vwap(opens)
        c_px, _c_qty = _vwap(closes) if closes else (None, 0)
        first, last = opens[0], (closes[-1] if closes else None)
        side = first.get("side")
        sgn = 1 if side == "BUY" else -1
        realized = (round(sgn * (c_px - o_px) * o_qty, 2)
                    if (c_px is not None and o_px is not None) else None)
        a, b = _secs(first.get("ts")), _secs((last or {}).get("ts"))
        why = first.get("forced_why")
        who = first.get("forced_who")
        src = "trade row" if (why or who) else None
        if src is None and why_by:
            rec = why_by.get((first.get("idx"), first.get("strategy"),
                              first.get("ts"))) or {}
            if rec:
                why, who = rec.get("forced_why"), rec.get("forced_who")
                src = "decisions-log join [I] on idx+strategy+timestamp"
        out.append({
            "pid": pid, "idx": first.get("idx"),
            "strategy": first.get("strategy"),
            "instrument": (f"{first.get('strike'):.0f}{first.get('right')}"
                           if first.get("strike") is not None
                           else first.get("right")),
            "strike": first.get("strike"), "right": first.get("right"),
            "side": side, "qty": o_qty,
            "entry_ts": first.get("ts"), "entry_px": (round(o_px, 2)
                                                      if o_px is not None
                                                      else None),
            "exit_ts": (last or {}).get("ts"),
            "exit_px": round(c_px, 2) if c_px is not None else None,
            "hold_s": (b - a) if (a is not None and b is not None) else None,
            "realized": realized,
            "state": "CLOSED" if closes else "OPEN",
            "mode": first.get("mode"),
            "exit_mode": (last or {}).get("mode"),
            "partial_fills": len(opens) + len(closes) > 2,
            "why": why, "forced_who": who, "why_src": src,
            "why_missing": None if src else
                           ("not durably logged for this trade: the trade row "
                            "predates 2026-08-26, when the rule-9 sentence "
                            "began travelling with it, and no decisions row "
                            "matched on idx+strategy+timestamp"),
        })
    out.sort(key=lambda t: (t["entry_ts"] or ""))
    return out


def day_accounting(trades: List[dict], key: str) -> Dict[str, dict]:
    """Net rupees and COUNTS per `key`. Never a rate -- house rule 4.

    `net` sums only trades that actually closed; `open` counts the rest rather
    than letting a running position read as a zero-P&L one.
    """
    out: Dict[str, dict] = {}
    for t in trades:
        k = t.get(key) or "?"
        d = out.setdefault(k, {"net": 0.0, "trades": 0, "open": 0})
        if t.get("realized") is None:
            d["open"] += 1
        else:
            d["net"] += t["realized"]
            d["trades"] += 1
    for d in out.values():
        d["net"] = round(d["net"], 2)
    return out


class Trader:
    """The whole paper desk. Feed on_chain at chain pace; read state()."""

    def __init__(self, state_path: Optional[str] = None,
                 trades_path: Optional[str] = None,
                 decisions_path: Optional[str] = None,
                 capital: float = PAPER_CAPITAL):
        # Module constants read at CALL time, not def time, so a --mock-chain
        # server that redirects them (server._isolate_mock_writers) cannot
        # write fixture trades into the live forward record -- the 2026-08-24
        # replay leak, which cost the paper desk its clean day 1.
        self.state_path = state_path or STATE
        self.trades_path = trades_path or TRADES
        self.decisions_path = decisions_path   # None -> per-day file
        self.book = book_mod.Book(capital)
        self.quoter = quoting.Quoter()
        self.decisions = deque(maxlen=80)      # in-memory tail for the API
        self.day: Optional[str] = None
        self.realized_at_day_start = 0.0
        self.day_stopped = False
        self._last_gear: Dict[str, str] = {}
        self._last_drain_side: Dict[str, Optional[str]] = {}
        self._casc_run: Dict[str, int] = {}        # idx -> consecutive CASCADE
        self._last_casc_len: Dict[str, int] = {}   # idx -> length of the run that
                                                   # just ended; read on the
                                                   # transition snapshot itself
        self._no_casc: Dict[str, int] = {}     # idx -> consecutive non-CASCADE
        self._marks: Dict[str, dict] = {}      # idx -> last mark context
        # THE SHORT-VARIANCE HEDGER (hedge.py). Its inventory is deliberately
        # NOT in self.book: hedge positions there would move book.risk() ->
        # forced_ratio -> the FORCED_MIN entry gate, i.e. a shadow module
        # steering the live paper desk. It reads net delta and never writes it.
        self.hedge = hedge_mod.HedgeBook()
        self._hedge_daily_written: Dict[str, str] = {}   # idx -> day written
        self._load()

    # -- persistence ---------------------------------------------------------
    def _load(self):
        try:
            with open(self.state_path, encoding="utf-8") as f:
                d = json.load(f)
            self.book = book_mod.Book.from_dict(d.get("book") or {})
            self.day = d.get("day")
            self.realized_at_day_start = d.get("realized_at_day_start", 0.0)
            self.day_stopped = d.get("day_stopped", False)
            # Absent on a state.json written before the hedger existed, which
            # must read as "no hedge inventory", never as a crash.
            self.hedge = hedge_mod.HedgeBook.from_dict(d.get("hedge") or {})
            self._hedge_daily_written = d.get("hedge_daily_written") or {}
        except Exception:
            pass                                # fresh book is the default

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
            tmp = self.state_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"book": self.book.to_dict(), "day": self.day,
                           "realized_at_day_start": self.realized_at_day_start,
                           "day_stopped": self.day_stopped,
                           "hedge": self.hedge.to_dict(),
                           "hedge_daily_written": self._hedge_daily_written}, f)
            os.replace(tmp, self.state_path)
        except Exception:
            pass                                # never stall the loop for disk

    def _log(self, kind: str, idx: str, strategy: str, detail: str,
             now: Optional[datetime] = None, pid: Optional[str] = None,
             **evidence):
        # `pid` added 2026-08-26. Without it the decisions log carried the WHY
        # (the rule-9 sentence) and the trades log carried the POSITION, and
        # nothing joined them -- so "why did it take this trade" was
        # unanswerable per trade the moment the process restarted. See
        # `_open_from_fill`, which now also stamps the why onto the trade row
        # itself so one file answers it.
        row = {"ts": (now or datetime.now()).isoformat(timespec="seconds"),
               "kind": kind, "idx": idx, "strategy": strategy,
               "pid": pid,
               "detail": detail, "evidence": evidence}
        self.decisions.append(row)
        if market_hours(now):
            _append(self.decisions_path
                    or day_decisions_path((now or datetime.now())
                                          .strftime("%Y-%m-%d")), row)

    # -- helpers -------------------------------------------------------------
    def _entry_ctx(self, leg_quote: dict, doc: dict) -> dict:
        """iv0/delta0/vega0 for attribution, honest Nones when absent."""
        iv, delta = leg_quote.get("iv"), leg_quote.get("delta")
        vega0 = None
        try:
            if iv and doc.get("expiry") and doc.get("spot"):
                T = surface_mod.years_to_expiry(doc["expiry"])
                k = leg_quote.get("_k")
                if T and T > 0 and k:
                    vega0 = bs_vega(doc["spot"], k, iv, T)
        except Exception:
            vega0 = None
        return {"iv0": iv, "delta0": delta, "vega0": vega0}

    def _open_from_fill(self, f: quoting.Fill, doc: dict,
                        now: Optional[datetime]):
        ctx = f.context
        q = dict(_by_k(doc).get((f.strike, f.right)) or {})
        q["_k"] = f.strike
        ec = self._entry_ctx(q, doc)
        leg = book_mod.PaperLeg(strike=f.strike, right=f.right, side=f.side,
                                qty=f.qty, entry_px=f.px, entry_ts=f.ts,
                                mode=f.mode, **ec)
        p = self.book.open(idx=f.idx, strategy=f.strategy, lots=PAPER_LOTS,
                           legs=[leg], ts=f.ts, spot0=doc.get("spot"),
                           forced_who=ctx.get("forced_who", ""),
                           forced_why=ctx.get("forced_why", ""),
                           gear=ctx.get("gear", ""),
                           policy=ctx.get("policy", {}))
        p.day = (now or datetime.now()).strftime("%Y-%m-%d")
        # THE WHY TRAVELS WITH THE TRADE, from 2026-08-26. It used to live only
        # in decisions_<day>.jsonl, which carries no pid -- so the rule-9
        # sentence and the position it justified sat in two files with no join
        # key, and "kya liya kb kyu liya" could not be answered per trade from
        # the durable record. Three fields on the row the position already
        # writes is the whole fix.
        _append(self.trades_path, {"day": p.day, "ts": f.ts,
                                   "pid": p.pid, "idx": f.idx,
                                   "strategy": f.strategy, "kind": "open",
                                   "side": f.side, "strike": f.strike,
                                   "right": f.right, "px": f.px,
                                   "qty": f.qty, "mode": f.mode,
                                   "forced_who": ctx.get("forced_who"),
                                   "forced_why": ctx.get("forced_why"),
                                   "gear": ctx.get("gear")})
        self._log("entry", f.idx, f.strategy,
                  f"{f.side} {f.strike:.0f}{f.right} x{f.qty} @ {f.px} "
                  f"[{f.mode}] -- forced: {ctx.get('forced_who', '?')}",
                  now=now, pid=p.pid, forced_why=ctx.get("forced_why"),
                  gear=ctx.get("gear"))
        return p

    def _close(self, p, by_k: Dict[tuple, dict], ts: str, why: str,
               now: Optional[datetime]):
        fills = {}
        for i, leg in enumerate(p.legs):
            # exits cross: urgency is the point of an exit
            side = "SELL" if leg.side == "BUY" else "BUY"
            q = by_k.get((leg.strike, leg.right)) or {}
            px = q.get("bid") if side == "SELL" else q.get("ask")
            if not px:
                px, src = book_mod.mark_px(q)
                if px is None:
                    self._log("exit", p.idx, p.strategy,
                              f"{p.pid}: cannot close, no quote on "
                              f"{leg.strike:.0f}{leg.right}; will retry",
                              now=now)
                    return False
            fills[i] = (px, "taker")
        realized = self.book.close(p, fills, ts)
        for i, leg in enumerate(p.legs):
            _append(self.trades_path, {"day": p.day, "ts": ts,
                                       "pid": p.pid, "idx": p.idx,
                                       "strategy": p.strategy, "kind": "close",
                                       "side": ("SELL" if leg.side == "BUY"
                                                else "BUY"),
                                       "strike": leg.strike,
                                       "right": leg.right,
                                       "px": fills[i][0], "qty": leg.qty,
                                       "mode": "taker"})
        self._log("exit", p.idx, p.strategy,
                  f"{p.pid} closed: {why} -- realized Rs {realized:,.0f}",
                  now=now, pid=p.pid, realized=realized, exit_why=why)
        return True

    # -- the short-variance hedger (hedge.py) --------------------------------
    def _hedge(self, idx: str, marks: List[dict], spot: Optional[float],
               lot: int, ts: str, now: datetime) -> None:
        """Rebalance the PAPER futures hedge against the option book's delta.

        SHADOW: writes only hedge.py's own inventory and its own ledger; never
        touches self.book, so `forced_ratio` and the entry gate cannot move.
        PAPER: house rule 10 -- there is no order path from here.
        """
        day = now.strftime("%Y-%m-%d")

        # A PARTIAL delta is not a delta. If any leg's greeks did not arrive,
        # net_delta is a smaller number than the truth (book.mark_position's
        # `delta_why` names the legs), and sizing a futures trade against it
        # would hedge the wrong amount in a confidently wrong direction.
        missing = [w for m in marks for w in (m.get("delta_why") or [])]
        if missing:
            self._hedge_log(day, ts, idx,
                            f"delta incomplete, refusing to hedge: "
                            f"{'; '.join(missing[:3])}", None, now)
            return
        if spot is None or not lot:
            self._hedge_log(day, ts, idx,
                            "no spot or lot size; a hedge cannot be priced "
                            "or sized", None, now)
            return

        opt_delta_lots = sum(m["net_delta"] for m in marks) / float(lot)
        held = self.hedge.leg(idx).lots
        p = hedge_mod.plan(opt_delta_lots, held)
        if p is None:
            return

        # THE BRAKE. Stop, and say so ONCE per index per day -- loudly in the
        # decisions log and permanently in /api/paperdesk, never silently.
        if self.hedge.braked(idx):
            if not self.hedge.brake_logged.get(idx):
                self.hedge.brake_logged[idx] = True
                self._log("refusal", idx, "DELTA_HEDGE",
                          f"BRAKE: {self.hedge.used(idx)} hedges already today "
                          f"(max {hedge_mod.MAX_HEDGES_DAY}) -- hedging STOPS "
                          f"for {idx}. Net delta {p['residual_before']} lots "
                          f"is now RUNNING UNHEDGED.", now=now)
                self._hedge_log(day, ts, idx,
                                f"brake hit: {self.hedge.used(idx)} of "
                                f"{hedge_mod.MAX_HEDGES_DAY} used; delta runs "
                                f"unhedged from here",
                                p["residual_before"], now)
            return

        f = self.hedge.apply(idx, p["side"], p["lots"], lot, spot, ts,
                             p["residual_before"], p["residual_after"])
        row = hedge_mod.fill_row(
            f, day, spot,
            f"|delta| {abs(p['residual_before'])} lots reached the "
            f"{p['band']}-lot band; {p['side']} {p['lots']} lot(s) returns it "
            f"to {p['residual_after']}")
        if market_hours(now):
            _append(hedge_mod.ledger_path(day), row)
        self._log("hedge", idx, "DELTA_HEDGE",
                  f"{p['side']} {p['lots']} {idx} FUT x{f.qty} @ {f.px} "
                  f"[PAPER] -- delta {p['residual_before']} -> "
                  f"{p['residual_after']} lots", now=now,
                  hedge_realized=f.realized,
                  used=self.hedge.used(idx), max=hedge_mod.MAX_HEDGES_DAY)

    def _hedge_eod(self, idx: str, marks: List[dict], spot: Optional[float],
                   lot: int, ts: str, now: datetime) -> None:
        """Summarise the session, then FLATTEN the paper hedge.

        Flattening is not optional. The paper desk squares off its options at
        15:18; a hedge left on would stop being a hedge at that instant and
        become an outright overnight futures position -- the exact naked
        directional risk this module exists to remove. The flatten does NOT
        consume a brake slot: the brake caps rebalancing, and refusing to close
        a position because a counter is full would be the worst possible
        reading of a risk limit.
        """
        self._hedge_daily(idx, marks, now)
        held = self.hedge.leg(idx).lots
        if not held or spot is None or not lot:
            return
        side = "SELL" if held > 0 else "BUY"
        f = self.hedge.apply(idx, side, int(abs(held)), lot, spot, ts,
                             held, 0.0)
        self.hedge.hedges_today[idx] = max(0, self.hedge.used(idx) - 1)
        day = now.strftime("%Y-%m-%d")
        if market_hours(now):
            _append(hedge_mod.ledger_path(day),
                    hedge_mod.fill_row(f, day, spot,
                                       "EOD flatten -- a hedge held past the "
                                       "options it hedges is an outright "
                                       "overnight futures position"))
        self._log("hedge", idx, "DELTA_HEDGE",
                  f"EOD flatten: {side} {abs(held):.0f} {idx} FUT @ {f.px} "
                  f"[PAPER] -- realized Rs {f.realized:,.0f}", now=now,
                  hedge_realized=f.realized)

    def _hedge_log(self, day: str, ts: str, idx: str, why: str,
                   delta_lots: Optional[float], now: datetime) -> None:
        """A hedge NOT taken. Rate-limited to one row per (idx, reason) per day
        so a missing-greek snapshot repeating every 10s cannot bury the ledger
        -- but the FIRST one is always written."""
        key = f"{idx}|{why[:40]}"
        if self._hedge_daily_written.get(key) == day:
            return
        self._hedge_daily_written[key] = day
        if market_hours(now):
            _append(hedge_mod.ledger_path(day),
                    hedge_mod.refusal_row(day, ts, idx, why, delta_lots,
                                          self.hedge.used(idx)))

    def _hedge_daily(self, idx: str, marks: List[dict], now: datetime) -> None:
        """The session summary for one index, written once at square-off."""
        day = now.strftime("%Y-%m-%d")
        if self._hedge_daily_written.get(f"daily|{idx}") == day:
            return
        self._hedge_daily_written[f"daily|{idx}"] = day
        att = [m.get("attribution") for m in marks]
        theta = (sum(a["theta_gamma_resid"] for a in att)
                 if att and all(a for a in att) else None)
        ctx = self._marks.get(idx) or {}
        mk = ctx.get("mark") or {}
        lot = ctx.get("lot_size") or 0
        nd = mk.get("net_delta")
        gap = hedge_mod.gap_exposure(nd, mk.get("net_gamma"),
                                     ctx.get("expected_move"))
        row = hedge_mod.daily_row(
            day, idx, theta, self.hedge.realized_total(idx),
            self.hedge.used(idx), gap,
            (nd / float(lot)) if (nd is not None and lot) else None)
        if market_hours(now):
            _append(hedge_mod.ledger_path(day), row)

    def day_pnl(self, marks: List[dict]) -> float:
        open_u = sum(m.get("unrealized") or 0.0 for m in marks)
        return (self.book.realized_total - self.realized_at_day_start) + open_u

    # -- the tick ------------------------------------------------------------
    def on_chain(self, idx: str, doc: dict, view, chain_read: Optional[dict],
                 warmap_state: Optional[dict],
                 now: Optional[datetime] = None) -> None:
        now = now or datetime.now()
        today = now.strftime("%Y-%m-%d")
        if self.day != today:
            self.day = today
            self.realized_at_day_start = self.book.realized_total
            self.day_stopped = False
            # Hedge COUNTERS reset; hedge INVENTORY does not (roll_day says
            # why). The paper desk squares off at 15:18 so there is normally
            # nothing carried, but a leftover must keep its basis, not be
            # silently re-based at the next open.
            self.hedge.roll_day(today)
        ts = doc.get("ts") or now.strftime("%H:%M:%S")
        by_k = _by_k(doc)
        spot = doc.get("spot")
        reg = desk_mod.regime_from_chain(doc)
        lot = desk_mod.lot_size_from_chain(doc.get("strikes")) \
            or desk_mod.LOT_SIZE.get(idx, desk_mod.DEFAULT_LOT_SIZE)
        gear = getattr(view, "gear", None) or "UNKNOWN"
        conv = getattr(view, "conviction", None) or "NONE"
        bias = getattr(view, "bias", None) or "UNKNOWN"
        cr = chain_read or {}

        # CASCADE IS DEFINITIONALLY A ONE-SNAPSHOT STATE, so "is the cascade
        # over" cannot be read off a single tick. `drain` is true only while
        # the trapped side's WINDOWED flow sits in the top decile
        # (chainside.DRAIN_P = 0.90), which about one snapshot in ten can
        # satisfy. Measured 2026-08-24, the paper desk's first live morning:
        # 23 of 23 CASCADE spells lasted exactly one 10s snapshot, so every
        # BUY_CASCADE was closed by the next tick's UNKNOWN -- seven round
        # trips, median hold 10s, and the strategy could never once express
        # its own thesis. The exit now needs CASCADE_COOL consecutive quiet
        # snapshots, which leaves the position's target/stop doing the work
        # a scalp's exit should.
        if gear == "CASCADE":
            self._casc_run[idx] = self._casc_run.get(idx, 0) + 1
        elif self._casc_run.get(idx, 0):
            self._last_casc_len[idx] = self._casc_run[idx]
            self._casc_run[idx] = 0
        self._no_casc[idx] = 0 if gear == "CASCADE"             else self._no_casc.get(idx, 0) + 1

        # 1) maker fills first -- a resting quote that got crossed is a
        # position regardless of what this snapshot's readings now say
        for f in self.quoter.on_quotes(idx, by_k, ts):
            self._open_from_fill(f, doc, now)

        # mark context for risk + exits
        marks = [self.book.mark_position(p, by_k, spot)
                 for p in self.book.open_positions() if p.idx == idx]
        agg_delta = sum(m["net_delta"] for m in marks)
        agg_gamma = sum(m["net_gamma"] for m in marks)
        self._marks[idx] = {"spot": spot, "lot_size": lot,
                            "expected_move": reg.expected_move,
                            "mark": {"net_delta": agg_delta,
                                     "net_gamma": agg_gamma}}
        risk = self.book.risk(self._marks)
        dpnl = self.day_pnl(marks)

        # 2) the day-loss circuit breaker: flatten, stop, say so
        if not self.day_stopped and dpnl < -DAY_LOSS_CAP:
            self.day_stopped = True
            self._log("refusal", idx, "DAY_STOP",
                      f"day P&L Rs {dpnl:,.0f} beyond the Rs "
                      f"{DAY_LOSS_CAP:,.0f} cap -- flattening, done for "
                      f"the day", now=now)
        eod = (now.hour, now.minute) >= SQUARE_OFF
        if eod or self.day_stopped:
            self.quoter.cancel(lambda q: q.idx == idx)
            # The hedge summary is taken BEFORE the square-off, on the book as
            # it actually stood at the close -- that is the exposure a holder
            # would carry overnight. Afterwards everything is flat and the gap
            # number would read zero for a reason that has nothing to do with
            # hedging.
            self._hedge_eod(idx, marks, spot, lot, ts, now)
            for p in [p for p in self.book.open_positions() if p.idx == idx]:
                self._close(p, by_k, ts,
                            "EOD square-off" if eod else "day-loss stop", now)
            self._save()
            return
        # The hedger sits BELOW the square-off branch on purpose: at EOD the
        # book is being flattened, and rebalancing a delta that is about to
        # become zero would burn brake slots and book round trips against
        # positions that no longer exist.
        self._hedge(idx, marks, spot, lot, ts, now)

        # 3) exits, policy vs marks + regime state. Strategies closed on
        # THIS snapshot are barred from re-entering on it: a scalp that
        # takes its +25% while its trigger is still true would otherwise
        # buy straight back at a worse price in the same breath -- churn
        # wearing a signal's clothes.
        closed_now = set()

        def _c(p, why):
            if self._close(p, by_k, ts, why, now):
                closed_now.add(p.strategy)

        seq = (warmap_state or {}).get("sequence") or {}
        for p in [p for p in self.book.open_positions() if p.idx == idx]:
            m = next((x for x in marks if x["pid"] == p.pid), None)
            if m is None:
                continue
            entry_prem = sum(l.entry_px * l.qty for l in p.legs)
            frac = (m["unrealized"] / entry_prem) if entry_prem else None
            pol = p.policy or {}
            longish = all(l.side == "BUY" for l in p.legs)
            if longish and frac is not None:
                if frac >= pol.get("target", SCALP_TARGET):
                    _c(p, f"target +{frac:.0%}")
                    continue
                if frac <= pol.get("stop", SCALP_STOP):
                    _c(p, f"cut {frac:.0%}")
                    continue
            if not longish and frac is not None:
                # short: unrealized turns positive as the premium decays
                if frac >= pol.get("decay_target", SHORT_DECAY_TARGET):
                    _c(p, f"decay target +{frac:.0%}")
                    continue
                # ...and negative as it inflates. SYMMETRIC WITH THE LONG
                # branch above, deliberately: a short's loss is unbounded, so
                # of the two this is the branch that must not be missing.
                if frac <= pol.get("stop", SHORT_STOP):
                    _c(p, f"cut {frac:.0%}")
                    continue
            if p.strategy == "SELL_PIN" and gear == "CASCADE":
                _c(p, "gear left PIN for CASCADE -- shorts do not argue "
                      "with a cascade")
                continue
            if p.strategy == "BUY_CASCADE"                     and self._no_casc.get(idx, 0) >= CASCADE_COOL:
                _c(p, f"cascade over: {CASCADE_COOL} snapshots with no "
                      f"top-decile drain; the scalp rides forced flow only "
                      f"while it flows")
                continue
            if p.strategy == "DIR_AFTER_GRAB":
                key = (p.policy or {}).get("seq_key")
                st = seq.get(key, {}).get("state") if key else None
                if st is not None and st == "IDLE":
                    _c(p, "the run resolved (HIT or FAILED); the thesis "
                          "is spent either way")
                    continue

        # 4) entries -- both sides, every block logged as a refusal
        if (now.hour, now.minute) >= NO_ENTRY_AFTER:
            return self._save()

        def blocked(strategy: str) -> Optional[str]:
            if self.day_stopped:
                return "day-loss stop is on"
            # the DUPE check outranks MAX_OPEN: when both apply, "already
            # holding" is the reason a reader can act on
            if any(p.strategy == strategy and p.idx == idx
                   for p in self.book.open_positions()):
                return "already holding this strategy on this index"
            if strategy in closed_now:
                return "closed this snapshot; no same-tick re-entry"
            if len(self.book.open_positions()) >= MAX_OPEN:
                return f"MAX_OPEN {MAX_OPEN} reached"
            fr = risk.get("forced_ratio")
            if fr is not None and fr < FORCED_MIN:
                return (f"forced_ratio {fr} < {FORCED_MIN}: the stress "
                        f"would force us -- rule 5, no new risk")
            return None

        atm = _atm_strike(doc)
        units = PAPER_LOTS * lot

        # SELL_PIN: wings beyond the expected move, posted at the ask
        if gear == "PIN" and reg.expected_move and spot and atm:
            why_not = blocked("SELL_PIN")
            has_quote = any(q.strategy == "SELL_PIN" and q.idx == idx
                            for q in self.quoter.resting)
            if why_not:
                self._log("refusal", idx, "SELL_PIN", why_not, now=now)
            elif not has_quote:
                for right, k_target in (("CE", spot + reg.expected_move),
                                        ("PE", spot - reg.expected_move)):
                    ks = [k for (k, r) in by_k if r == right]
                    beyond = ([k for k in ks if k >= k_target]
                              if right == "CE"
                              else [k for k in ks if k <= k_target])
                    if not beyond:
                        self._log("refusal", idx, "SELL_PIN",
                                  f"no {right} strike beyond the expected "
                                  f"move on the subscribed chain", now=now)
                        continue
                    k = min(beyond) if right == "CE" else max(beyond)
                    q = by_k.get((k, right)) or {}
                    if not q.get("ask"):
                        self._log("refusal", idx, "SELL_PIN",
                                  f"{k:.0f}{right}: no ask to join", now=now)
                        continue
                    self.quoter.post(idx, k, right, "SELL", q["ask"], units,
                                     "SELL_PIN", ts, context={
                        "forced_who": "option buyers holding through PIN",
                        "forced_why": "hedging damps the move they paid "
                                      "for; the drag record is their bill",
                        "gear": gear,
                        "policy": {"decay_target": SHORT_DECAY_TARGET}})
                    self._log("post", idx, "SELL_PIN",
                              f"offer {k:.0f}{right} x{units} @ {q['ask']} "
                              f"(join ask, beyond EM)", now=now)

        # BUY_CASCADE: the short-covering scalp, taken
        if gear == "CASCADE" and conv == "FORCED" and bias in ("BULL", "BEAR") \
                and atm:
            right = "CE" if bias == "BULL" else "PE"
            why_not = blocked("BUY_CASCADE")
            if why_not:
                self._log("refusal", idx, "BUY_CASCADE", why_not, now=now)
            else:
                f, wn = self.quoter.take(idx, atm, right, "BUY", units,
                                         "BUY_CASCADE", by_k, ts, context={
                    "forced_who": f"trapped {cr.get('trapped_side', '?')} "
                                  f"writers ({cr.get('worst_leg', '?')})",
                    "forced_why": f"drain rank {cr.get('drain_rank')} -- "
                                  f"covering is not optional",
                    "gear": gear,
                    "policy": {"target": SCALP_TARGET, "stop": SCALP_STOP}})
                if f:
                    self._open_from_fill(f, doc, now)
                else:
                    self._log("refusal", idx, "BUY_CASCADE", wn, now=now)

        # DIR_AFTER_GRAB: a dwell resolved BREAK->RUN with a named target
        for ev in (warmap_state or {}).get("seq_fired") or []:
            if ev.get("to") != "RUN" or not ev.get("target"):
                continue
            up = ev.get("target", {}).get("px", 0) > (spot or 0)
            right = "CE" if up else "PE"
            why_not = blocked("DIR_AFTER_GRAB")
            if why_not:
                self._log("refusal", idx, "DIR_AFTER_GRAB", why_not, now=now)
                continue
            if not atm:
                continue
            key = f"{ev.get('level')}@{ev.get('px'):.1f}"
            f, wn = self.quoter.take(idx, atm, right, "BUY", units,
                                     "DIR_AFTER_GRAB", by_k, ts, context={
                "forced_who": f"stops beyond {ev.get('level')} "
                              f"{ev.get('px')}",
                "forced_why": "liquidity grab resolved into a run with a "
                              "named target; stops feed it [I]",
                "gear": gear,
                "policy": {"target": SCALP_TARGET, "stop": SCALP_STOP,
                           "seq_key": key}})
            if f:
                self._open_from_fill(f, doc, now)
            else:
                self._log("refusal", idx, "DIR_AFTER_GRAB", wn, now=now)

        # SELL_CREST: the cascade just ended; offer the inflated side
        prev_gear = self._last_gear.get(idx)
        # A cascade that lasted ONE snapshot never happened; its "ending" is
        # the detector blinking, not flow exhausting. Neutering prev_gear here
        # rather than adding a clause below keeps the arm condition one
        # expression, and the refusal path identical. See CASCADE_MIN.
        if self._last_casc_len.get(idx, 0) < CASCADE_MIN:
            prev_gear = None
        if prev_gear == "CASCADE" and gear != "CASCADE" \
                and self._last_drain_side.get(idx) and atm:
            side_r = self._last_drain_side[idx].upper()  # the side that covered
            why_not = blocked("SELL_CREST")
            if why_not:
                self._log("refusal", idx, "SELL_CREST", why_not, now=now)
            else:
                ks = sorted(k for (k, r) in by_k if r == side_r)
                otm = ([k for k in ks if k > (spot or 0)] if side_r == "CE"
                       else [k for k in reversed(ks) if k < (spot or 0)])
                if otm:
                    k = otm[0]
                    q = by_k.get((k, side_r)) or {}
                    if q.get("ask"):
                        self.quoter.post(idx, k, side_r, "SELL", q["ask"],
                                         units, "SELL_CREST", ts,
                                         ttl=CREST_TTL, context={
                            "forced_who": "the crowd that just bought back",
                            "forced_why": "post-squeeze premium is "
                                          "extraction, not information; it "
                                          "decays when the last forced "
                                          "buyer is done",
                            "gear": gear,
                            "policy": {"decay_target": SHORT_DECAY_TARGET}})
                        self._log("post", idx, "SELL_CREST",
                                  f"offer {k:.0f}{side_r} x{units} @ "
                                  f"{q['ask']} into the crest "
                                  f"(ttl {CREST_TTL} snaps)", now=now)
        if cr.get("drain"):
            self._last_drain_side[idx] = cr.get("trapped_side")
        self._last_gear[idx] = gear
        self._save()

    # -- the review surface --------------------------------------------------
    def state(self, docs_by_idx: Optional[Dict[str, dict]] = None) -> dict:
        marks = []
        for p in self.book.open_positions():
            doc = (docs_by_idx or {}).get(p.idx) or {}
            marks.append(self.book.mark_position(p, _by_k(doc),
                                                 doc.get("spot")))
        return {
            "paper": True,
            "note": ("PAPER ONLY -- no order path exists or ever will; "
                     "maker P&L is an UPPER bound (front-of-queue fill "
                     "model at ~10s sampling); deployment is the "
                     "operator's decision, made outside this code"),
            "capital": self.book.capital,
            "lots": PAPER_LOTS,
            "realized_total": round(self.book.realized_total, 2),
            "day_pnl": round(self.day_pnl(marks), 2),
            "day_stopped": self.day_stopped,
            "open": [pd for pd in self.book.to_dict()["positions"]
                     if pd["state"] == "OPEN"],
            "marks": marks,
            "risk": self.book.risk(self._marks),
            "quotes": self.quoter.state(),
            "decisions": list(self.decisions),
            "closed_today": [
                {"pid": p.pid, "idx": p.idx, "strategy": p.strategy,
                 "realized": p.realized, "opened": p.opened_ts,
                 "closed": p.closed_ts, "forced_who": p.forced_who}
                for p in self.book.positions
                if p.state == "CLOSED" and p.day == self.day][-20:],
            "hedge": self._hedge_state(marks),
            "theta_day_est": self._theta_day(docs_by_idx or {}),
            "margin_shift": self._margin_shift(docs_by_idx or {}),
            **self._day_from_log(),
        }

    # -- the day, read back from the LOG rather than from memory -------------
    def _day_from_log(self) -> dict:
        """`day_trades` + `day_refusals`, built from the durable files.

        THE POINT: `closed_today` above comes off the in-memory book, so a
        restart truncates it to whatever `state.json` held -- 20 rows against
        62 real round trips on 2026-08-25. The log has all of them, so the
        screen reads the log. Same fix as the drag day trace, same reason.

        WHICH DAY: the latest session PRESENT IN THE LOG, not the calendar
        date. The operator reviews after the close, often past midnight; a
        calendar read would blank the screen at 00:00 for the session she is
        still looking at. The day served is always published so there is no
        ambiguity about what is on screen.
        """
        rows = []
        try:
            with open(self.trades_path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue          # a torn last line costs one row
        except OSError:
            return {"day_trades": None, "day_refusals": None,
                    "day_trades_why": (f"could not read {self.trades_path} -- "
                                       f"the paper desk may not have traded "
                                       f"yet")}
        days = [r.get("day") for r in rows if r.get("day")]
        if not days:
            return {"day_trades": [], "day_refusals": [],
                    "day_trades_why": "the trade log holds no dated rows yet"}
        day = max(days)
        todays = [r for r in rows if r.get("day") == day]
        trades = pair_trades(todays, self._why_from_decisions(day))
        return {
            "day": day,
            "day_is_calendar_today": day == datetime.now().strftime("%Y-%m-%d"),
            "day_trades": trades,
            "day_trades_why": None,
            "day_trades_note": ("built from data/paper_desk/trades.jsonl, the "
                                "durable record -- unlike `closed_today`, "
                                "which is the in-memory tail and is truncated "
                                "by a restart. Partial fills are averaged "
                                "quantity-weighted."),
            "by_index": day_accounting(trades, "idx"),
            "by_strategy": day_accounting(trades, "strategy"),
            "accounting_note": ("net rupees and counts only. No hit rate, win "
                                "rate or expectancy is computed here or "
                                "anywhere -- house rule 4; the verdict is the "
                                "operator's, against a bar she states first."),
            "day_refusals": self._refusals(day),
        }

    def _why_from_decisions(self, day: str) -> Dict[tuple, dict]:
        """Recover the rule-9 sentence for trades written before it travelled
        on the trade row. Keyed (idx, strategy, HH:MM:SS).

        A JOIN, NOT AN IDENTITY -- the decisions log has no pid (that was the
        defect), so this matches on three fields and every recovered why is
        tagged `why_src` accordingly. New trades do not need it.
        """
        out: Dict[tuple, dict] = {}
        for r in self._decisions_rows(day):
            if r.get("kind") != "entry":
                continue
            ts = (r.get("ts") or "")[11:19]
            ev = r.get("evidence") or {}
            detail = r.get("detail") or ""
            who = detail.split("forced:", 1)[-1].strip() if "forced:" in detail \
                else None
            out[(r.get("idx"), r.get("strategy"), ts)] = {
                "forced_why": ev.get("forced_why"), "forced_who": who}
        return out

    def _decisions_rows(self, day: str) -> List[dict]:
        path = self.decisions_path or day_decisions_path(day)
        out = []
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
        except OSError:
            return []
        return out

    def _refusals(self, day: str) -> List[dict]:
        """Every trade NOT taken, with its reason. The refusals are half the
        record: a desk that only shows what it did cannot be judged on what it
        declined."""
        return [{"ts": r.get("ts"), "idx": r.get("idx"),
                 "strategy": r.get("strategy"), "pid": r.get("pid"),
                 "why": r.get("detail"), "evidence": r.get("evidence") or {}}
                for r in self._decisions_rows(day)
                if r.get("kind") == "refusal"]

    # -- the two numbers the DESK screen asks for -----------------------------
    def _theta_day(self, docs: Dict[str, dict]) -> dict:
        """One calendar day of decay on the open book, in rupees. [I].

        WHY A SECOND THETA NUMBER EXISTS. `book.mark_position`'s attribution
        publishes `theta_gamma_resid`, which is a RESIDUAL -- everything
        delta x dS and vega x dIV failed to explain, so theta and gamma
        (and every higher-order term) arrive fused. That is the honest
        decomposition of what ACTUALLY happened, and it cannot answer the
        forward question the screen asks: *ek din nikal jaye = +Rs Z*.

        This is that forward question, and it is a MODEL number, not a
        measurement: per-leg Black-76 theta at the current mark's IV, summed,
        signed by side. Long options lose it, short options collect it.

        Every input that is missing REMOVES a leg from the sum and is named in
        `why` -- a partial theta reported as though it were the whole book's
        would understate income exactly when a leg is unquoted, which is
        exactly when it matters.
        """
        total, legs, why = 0.0, 0, []
        for p in self.book.open_positions():
            doc = docs.get(p.idx) or {}
            by_k = _by_k(doc)
            spot, expiry = doc.get("spot"), doc.get("expiry")
            if spot is None or not expiry:
                why.append(f"{p.pid}: no spot/expiry this snapshot")
                continue
            try:
                T = surface_mod.years_to_expiry(expiry)
            except Exception:
                T = None
            if not T or T <= 0:
                why.append(f"{p.pid}: expiry {expiry} gives no time value")
                continue
            for l in p.legs:
                if l.right == "FUT":
                    continue           # a future has no time value to decay
                q = by_k.get((l.strike, l.right)) or {}
                iv = q.get("iv")
                if not iv:
                    why.append(f"{l.strike:.0f}{l.right}: no IV to price theta")
                    continue
                td = bs_theta_day(spot, l.strike, iv, T,
                                  "C" if l.right == "CE" else "P")
                total += book_mod._sgn(l.side) * td * l.qty
                legs += 1
        return {
            "rupees": round(total, 2) if legs else None,
            "legs": legs,
            "why": why or None,
            "no_legs_why": None if legs else
                           ("nothing priceable: the book is empty, or no leg "
                            "had both a live IV and a positive time to "
                            "expiry"),
            "tag": "I",
            "method": ("per-leg Black-76 theta at the snapshot's own IV, "
                       "signed by side, divided by 365 CALENDAR days "
                       "(gamma.DAYS_PER_YEAR -- the basis T is built on, and "
                       "a Friday short really does collect three days by "
                       "Monday). A MODEL number: distinct from marks' "
                       "theta_gamma_resid, which is a measured residual with "
                       "gamma fused into it. Uses the INDEX as the forward, "
                       "the same substitution the rest of this book makes."),
        }

    def _margin_shift(self, docs: Dict[str, dict]) -> dict:
        """Margin recomputed at spot +/-1% and +/-2%. [I], same model.

        The survival table's "free margin" row used to assume margin is a
        CONSTANT while spot moves. It is not: `desk._naked_margin` is a
        percentage of NOTIONAL, so a short book's margin grows as the index
        does -- the crowd doctrine's whole mechanism (rule 5), where the hunt
        kills through margin rather than opinion. Recomputed here with the
        SAME [I] model rather than a second one that could disagree.

        ponytail: shifts spot only, not IV -- a real SPAN run would raise both
        together and this understates the squeeze. Add a vol shift when the
        forward record shows the gap mattering.
        """
        out, why = {}, []
        base_total = 0.0
        shifts = (-0.02, -0.01, 0.01, 0.02)
        totals = {f"{s:+.0%}": 0.0 for s in shifts}
        priced = 0
        for p in self.book.open_positions():
            doc = docs.get(p.idx) or {}
            spot = doc.get("spot")
            lot = (desk_mod.lot_size_from_chain(doc.get("strikes"))
                   or desk_mod.LOT_SIZE.get(p.idx, desk_mod.DEFAULT_LOT_SIZE))
            if spot is None:
                why.append(f"{p.pid}: no spot; notional unknowable")
                continue
            m0, _n = self.book.margin_position(p, spot, lot)
            if m0 is None:
                why.append(f"{p.pid}: margin not priceable")
                continue
            base_total += m0
            priced += 1
            for s in shifts:
                m, _ = self.book.margin_position(p, spot * (1.0 + s), lot)
                totals[f"{s:+.0%}"] += (m if m is not None else m0)
        return {
            "base": round(base_total, 0) if priced else None,
            "at": {k: round(v, 0) for k, v in totals.items()} if priced
                  else None,
            "positions_priced": priced,
            "why": why or None,
            "no_base_why": None if priced else
                           ("no open position could be priced -- an empty "
                            "book, or no spot this snapshot"),
            "tag": "I",
            "model": desk_mod._NAKED_MODEL_NOTE,
            "note": ("spot is shifted; IV is NOT. A real SPAN run raises both "
                     "together, so these are a FLOOR on the squeeze."),
        }

    def _hedge_state(self, marks: List[dict]) -> dict:
        """The short-variance review surface. SHADOW: describes, decides
        nothing. No rate, no win count -- house rule 4."""
        per = {}
        for idx, ctx in (self._marks or {}).items():
            mk = ctx.get("mark") or {}
            lot = ctx.get("lot_size") or 0
            nd = mk.get("net_delta")
            im = [m for m in marks if m.get("idx") == idx]
            missing = [w for m in im for w in (m.get("delta_why") or [])]
            opt_lots = (nd / float(lot)) if (nd is not None and lot) else None
            held = self.hedge.leg(idx).lots
            att = [m.get("attribution") for m in im]
            theta = (sum(a["theta_gamma_resid"] for a in att)
                     if att and all(a for a in att) else None)
            per[idx] = {
                "option_delta_lots": (None if opt_lots is None
                                      else round(opt_lots, 3)),
                # A partial delta is not a delta: say so rather than publish a
                # smaller number that looks complete.
                "delta_why": (None if not missing else
                              "net delta is PARTIAL (" + "; ".join(missing[:3])
                              + ") -- hedging is refused while it is"),
                "hedge_lots": held,
                "net_delta_lots": (None if opt_lots is None
                                   else round(opt_lots + held, 3)),
                "band_lots": hedge_mod.BAND_LOTS,
                "hedges_used": self.hedge.used(idx),
                "hedges_max": hedge_mod.MAX_HEDGES_DAY,
                "brake_hit": self.hedge.braked(idx),
                "brake_why": ("hedging STOPPED for today -- delta from here "
                              "runs UNHEDGED"
                              if self.hedge.braked(idx) else None),
                "hedge_cost_today": round(self.hedge.realized_total(idx), 2),
                "theta_collected": (None if theta is None
                                    else round(theta, 2)),
                "net_variance": (None if theta is None else
                                 round(theta + self.hedge.realized_total(idx),
                                       2)),
                "gap_exposure": hedge_mod.gap_exposure(
                    nd, mk.get("net_gamma"), ctx.get("expected_move")),
            }
        return {
            "paper": True, "shadow": True, "tag": "I",
            "indices": per,
            "fills_today": self.hedge.fills[-40:],
            "cumulative_hedge_cost": round(self.hedge.realized_total(), 2),
            "ledger": hedge_mod.ledger_path(self.day or ""),
            "note": ("PAPER futures against a PAPER option book -- no order "
                     "path exists or ever will. Fills assume no spread paid "
                     "and use the INDEX in place of the future (carry cancels "
                     "on a round trip; only carry drift is unmodelled), so "
                     "hedge cost is a LOWER bound and net_variance an UPPER "
                     "one. theta_collected bundles theta + gamma + "
                     "higher-order -- it is not isolated decay."),
        }
