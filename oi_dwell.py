"""The memory the desk never had.

WHY THIS EXISTS. Measured 2026-08-24: the desk published 1,807 state
transitions in one session -- 1,126 on `deployable` alone, median life
ELEVEN SECONDS, one chain snapshot. Meanwhile the CE/PE OI divergence ran
one way for four hours (+1.7M at 09:17 -> +88.7M at 13:20 while spot fell
24299 -> 24150) and nothing said so, because `gear`, `conviction` and
`deployable` are each recomputed from the instantaneous snapshot with no
memory. A four-hour build rendered as ~1,800 flickers, and the operator
read the screen all day and was told nothing.

TWO PIECES, DELIBERATELY SEPARATE:

  `Gate`      generic hysteresis. A new value must be seen CONFIRM
              consecutive times before it replaces the held one. Applies to
              any field; knows nothing about options.

  `direction` the OI read the desk was missing entirely: signed
              (put - call) OI-change divergence, dead-zoned and
              volume-gated, then run through a Gate.

THE VOLUME GATE IS NOT OPTIONAL. In the first ~20 minutes the day's
cumulative oi_chg base is tiny, so the ratio is violent noise: replaying
2026-08-24 without it, SENSEX called BULLISH at 09:19 (+4.4 favourable,
+560.6 adverse) and took 18 minutes to correct. MIN_BASE suppresses a
direction until there is enough OI behind it to mean something.

TUNE, DO NOT TRUST. CONFIRM/DEAD/MIN_BASE are calibration knobs measured
against three sessions (2026-08-20/21/24), not derived constants. Re-run
`python oi_dwell.py replay <chain.jsonl>` after any change; the sweep in
`replay` prints what each setting would have done.
"""

CONFIRM = 12          # consecutive disagreeing snapshots before a flip wins
DEAD = 0.15           # |strength| under this is NEUTRAL, not a direction
MIN_BASE = 5_000_000  # max(|call dOI|,|put dOI|) before direction may arm


def strength(strikes):
    """Signed OI-change divergence over a chain snapshot's strikes.

    (put - call) / max(|call|, |put|)  -- positive = puts building = BULLISH,
    matching `chain_metrics.oi_flow`'s `strength` exactly, so the two can
    never disagree about sign. Returns (strength, base); `base` is the
    magnitude the volume gate reads.
    """
    ce = sum((s.get("ce", {}).get("oi_chg") or 0) for s in strikes)
    pe = sum((s.get("pe", {}).get("oi_chg") or 0) for s in strikes)
    base = max(abs(ce), abs(pe))
    return ((pe - ce) / base if base else 0.0), base


HOLD = "__hold__"     # "no candidate this tick" -- NOT a value
_UNSET = object()     # "nothing acquired yet" -- NOT None, which is a value


def direction(strikes, min_base=MIN_BASE, dead=DEAD):
    """The instantaneous read, or HOLD when there is not enough OI to have one.

    HOLD IS NOT None, AND THE DISTINCTION IS LIVE. `deployable` uses None to
    mean "stand aside", which is a real state the gate must be able to move
    TO. "no opinion this tick" is a different thing entirely, and folding the
    two together would make a desk that goes deployable once and can never
    stand aside again.
    """
    s, base = strength(strikes)
    if base < min_base:
        return HOLD, s, base
    return ("BULLISH" if s > dead else
            "BEARISH" if s < -dead else "NEUTRAL"), s, base


class Gate:
    """Hysteresis for one field. `update` returns the value to PUBLISH.

    A `None` reading is not a candidate -- it means "no opinion this
    snapshot", which must never displace a held state, or the gate would
    reset every time the chain hiccuped.
    """

    def __init__(self, confirm=CONFIRM, initial=_UNSET):
        self.confirm = confirm
        self.held = initial
        self._pending = _UNSET
        self._n = 0

    def update(self, reading):
        if reading == HOLD:
            return None if self.held is _UNSET else self.held
        if self.held is _UNSET:
            # FIRST acquisition is immediate. Hysteresis exists to stop
            # flip-FLOPPING; there is nothing yet to flop away from, and
            # making the desk blank for CONFIRM snapshots after every
            # routine bounce would be a new failure, not a fix.
            self.held = reading
            return self.held
        if reading == self.held:
            self._pending, self._n = _UNSET, 0
            return self.held
        if reading == self._pending:
            self._n += 1
        else:
            self._pending, self._n = reading, 1
        if self._n >= self.confirm:
            self.held, self._pending, self._n = reading, _UNSET, 0
        return self.held


GATED_FIELDS = ("conviction", "deployable", "oi_dir")
"""Fields the gate may hold. `gear` is DELIBERATELY ABSENT.

`trader.py` records CASCADE as "DEFINITIONALLY A ONE-SNAPSHOT STATE" -- the
drain it names sits in the top decile about one snapshot in ten, so a
12-snapshot confirmation would mean the desk could never report CASCADE at
all. Replaying 2026-08-24 with `gear` gated proved exactly that: 46 raw
NIFTY gear changes collapsed to ZERO, i.e. the field would have frozen on
its first reading for the whole session. Gear's flicker is its semantics,
and the consumers that care already damp it themselves (trader.py's
`_no_casc` / CASCADE_COOL). Conviction and deployable are the fields sold
to the operator as a readable answer, and those are the ones that must hold
still long enough to be read."""


class StateGate:
    """One Gate per (index, field). Drop-in filter over the desk's state dict.

    ADDITIVE BY DESIGN: it can only ever hold a field at a value the desk
    itself published earlier. It never invents a state, so the worst case is
    a stale-by-CONFIRM-snapshots reading, never a fabricated one.
    """

    def __init__(self, confirm=CONFIRM):
        self.confirm = confirm
        self._g = {}

    def held_for(self, idx, fields=GATED_FIELDS):
        """What this index is currently HOLDING, without advancing anything.

        The gate must be advanced exactly once per chain snapshot, and that
        happens in `_log_chain_pace`. Any other reader -- the /api/desk
        handler serving the screen, most of all -- has to PEEK, never
        `filter`: a browser polling at its own rate would otherwise feed the
        same Gate a second, differently-timed stream of readings and confirm
        flips at a cadence nobody chose. Returns only fields already
        acquired; a field the gate has not seen yet is absent, not None.
        """
        out = {}
        for field in fields:
            g = self._g.get((idx, field))
            if g is not None and g.held is not _UNSET:
                out[field] = g.held
        return out

    def filter(self, idx, state, fields=GATED_FIELDS):
        out = {}
        for field, value in state.items():
            if field not in fields:          # passes through untouched
                out[field] = value
                continue
            g = self._g.setdefault((idx, field), Gate(self.confirm))
            out[field] = g.update(value)
        return out


def demo():
    """Self-check: a spike must not flip the gate; a run must."""
    g = Gate(confirm=3, initial="A")
    assert g.update("B") == "A", "one disagreeing read must not flip"
    assert g.update("B") == "A"
    assert g.update("B") == "B", "confirm-th read must flip"
    g2 = Gate(confirm=3, initial="A")
    for r in ("B", "B", "C", "B", "B"):          # never 3 in a row
        assert g2.update(r) == "A", "interrupted run must not flip"
    g3 = Gate(confirm=2, initial="A")
    assert g3.update(HOLD) == "A", "HOLD must not displace a held state"

    # None is a VALUE ("stand aside"), reachable like any other
    g4 = Gate(confirm=2, initial="long_call")
    assert g4.update(None) == "long_call", "one None must not flip"
    assert g4.update(None) is None, "confirmed None must win -- stand aside"
    assert g4.update("long_put") is None, "and must then be defended"

    # first acquisition is immediate, and None can be the first value
    g5 = Gate(confirm=99)
    assert g5.update("PIN") == "PIN", "first reading adopts at once"
    g6 = Gate(confirm=99)
    assert g6.update(None) is None and g6.held is None

    # volume gate: a huge ratio on a tiny base is not a direction
    tiny = [{"ce": {"oi_chg": 10}, "pe": {"oi_chg": 900}}]
    assert direction(tiny)[0] == HOLD, "tiny base must not arm a direction"
    big = [{"ce": {"oi_chg": 60_000_000}, "pe": {"oi_chg": 5_000_000}}]
    assert direction(big)[0] == "BEARISH", "calls building = BEARISH"
    assert direction([])[0] == HOLD, "empty chain is HOLD, never a direction"

    sgp = StateGate(confirm=2)
    assert sgp.held_for("N") == {}, "nothing acquired yet -> empty, not None"
    sgp.filter("N", {"conviction": "FORCED"})
    assert sgp.held_for("N") == {"conviction": "FORCED"}
    before = dict(sgp._g[("N", "conviction")].__dict__)
    sgp.held_for("N"); sgp.held_for("N")
    assert sgp._g[("N", "conviction")].__dict__ == before, "peek must not advance"

    sg = StateGate(confirm=2)
    # gear is NOT gated -- it passes straight through, flicker and all
    assert sg.filter("N", {"gear": "PIN"})["gear"] == "PIN"
    assert sg.filter("N", {"gear": "UNKNOWN"})["gear"] == "UNKNOWN"
    # conviction IS gated
    assert sg.filter("N", {"conviction": "FORCED"})["conviction"] == "FORCED"
    assert sg.filter("N", {"conviction": "NONE"})["conviction"] == "FORCED"
    assert sg.filter("N", {"conviction": "NONE"})["conviction"] == "NONE"
    print("oi_dwell demo OK")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "replay":
        import replay_dwell
        replay_dwell.main(sys.argv[2:])
    else:
        demo()
