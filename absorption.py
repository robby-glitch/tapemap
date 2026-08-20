"""absorption.py -- operator object #3b: a level that ate more than it showed.

WHAT IT ANSWERS. `sweep.py` sees the book being taken. This sees the book
REFUSING to be taken -- size resting at a price, being hit repeatedly, and
still being there. That is the pre-condition signature of the Aug-19 cascade:
14:19-14:29, roughly 20K of aggressive selling into 24,095-24,105 and the
price would not make a new low. Somebody was under the market eating every
hit. Ten minutes later the trapped inventory above detonated.

NOT THE SAME AS `engine.ABSORPTION`, WHICH ALREADY EXISTS. That one is a BAR
read -- volume rank > 0.95 with range rank < 0.55, "extreme effort, no
result" -- inferred from a candle after it closes, and it lives in the engine
event stream that scored -0.1/-6.2 against a +4.1 do-nothing control and is
default OFF. This one is a BOOK read, and it does not infer: it proves
replenishment by arithmetic, and it can say so while the level is still being
defended rather than after the bar prints. Different resolution, different
evidence, and this module claims nothing about the other one's verdict.

THE ARITHMETIC, WHICH IS THE ONLY REASON TO TRUST THIS. On a limit book a
trade happens when an aggressor meets resting size, AT the resting order's
price. So while the best bid and the best ask both stand still, every trade in
that window happened at exactly one of those two prices -- there is nowhere
else for it to go. Therefore:

    traded across the window  >  the most that was ever DISPLAYED there
        =>  the size at the touch was replenished. At least once.

That is a proof, not a heuristic, and it is why `ratio` is meaningful rather
than suggestive. A `ratio` of 3 means the touch was rebuilt about three times
over while nobody could move it.

WINDOW. A window opens when the touch (both best prices) is stable and closes
the moment either moves -- because once the touch moves, trades can occur at
prices this module was not watching and the proof above stops holding. A gap
in the feed also closes it: `vtt` unknown means the volume term is unknown,
and an absorption number built on a guessed denominator is worse than none.

WHAT IT DELIBERATELY DOES NOT SAY: **which side absorbed.** Total volume
cannot be split into buyer- and seller-initiated from a snapshot; that needs
per-side aggressor data, which is exactly what the Dhan footprint carried and
this feed does not. Reporting "buyers absorbed" here would be the
interpretation layer wearing a measurement's clothes. Both touch prices are
emitted; a caller that has an aggression source can attribute the side, and
that attribution is its `[I]`, not this module's.

**THE PROOF LEAKS WHEN THE TOUCH IS ABNORMALLY WIDE, SO `spread` IS EMITTED.**
Measured live 2026-08-20 11:04: a FUT window reported bid 24268.0 / ask
24275.0 -- seven points, where that contract normally shows one or two -- with
585 traded across it. If the quoted touch is that wide, trades almost
certainly happened at prices INSIDE it, and "there is nowhere else for it to
go" stops being true; the volume then gets credited to two prices it never
touched. A stale or transiently thin frame produces exactly this. So the
spread travels with every event and a consumer should distrust any window
whose spread is wide for that instrument. No cutoff is applied here, because
"wide for that instrument" is a percentile against its own session -- the
consumer's `[I]`, not this module's.

Other limits, all the snapshot's fault:
  * `shown` is DISPLAYED size. An iceberg rests larger, so `ratio` is a floor
    on how much was hidden, never an estimate of it.
  * Sub-snapshot flickers of the touch are invisible; a window that looks
    stable may have moved and come back, which would over-attribute volume to
    these two prices. Faster frames narrow this; nothing removes it.
  * `MIN_FRAMES` exists so a single quiet interval cannot be called a defence.
    It is a floor on evidence, not a tuned sensitivity.

Pure computation, stdlib only, no I/O. Emits measurements `[M]`.
Forward-logged from day one; gates nothing until its line earns it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

# Two frames is the least that can show a touch HOLDING rather than merely
# existing. A definition of evidence, not a sensitivity knob.
MIN_FRAMES = 2


@dataclass
class Absorption:
    """One stretch where the touch held while volume kept arriving."""
    t_from: str
    t_to: str
    bid_px: float
    ask_px: float
    absorbed: float            # volume traded while the touch stood still
    shown: float               # most that was ever displayed at those prices
    ratio: float               # absorbed / shown -- times the book was rebuilt
    spread: float              # ask_px - bid_px; READ THIS, see the docstring
    frames: int                # snapshots the touch survived
    tag: str = "M"


def _touch(ladder: Optional[dict]):
    """(best bid, best ask, displayed size across both), or None."""
    if not ladder:
        return None
    bid, ask = ladder.get("bid") or [], ladder.get("ask") or []
    if not bid or not ask:
        return None
    return bid[0]["price"], ask[0]["price"], bid[0]["qty"] + ask[0]["qty"]


class AbsorptionDetector:
    """Feed it snapshots; it reports each stretch where the touch was defended.

    One per instrument. The event arrives when the touch FINALLY BREAKS, which
    is the honest moment -- until then the stretch is still growing and any
    number reported would be a running total presented as a finished one.
    Read `pending()` if a live panel needs the in-progress figure, and label it
    as in progress.
    """

    def __init__(self):
        self._px = None            # (bid, ask) currently being defended
        self._t0 = None
        self._t = None
        self._vtt0 = None
        self._vtt = None
        self._shown = 0.0
        self._frames = 0
        self.events: List[Absorption] = []

    # ---- internals ----------------------------------------------------
    def _close(self) -> Optional[Absorption]:
        """End the current window and emit it, if it proved anything."""
        ev = self._build()
        self._px = self._t0 = self._t = self._vtt0 = self._vtt = None
        self._shown, self._frames = 0.0, 0
        if ev:
            self.events.append(ev)
        return ev

    def _build(self) -> Optional[Absorption]:
        if self._px is None or self._frames < MIN_FRAMES:
            return None
        if self._vtt0 is None or self._vtt is None or self._shown <= 0:
            return None
        absorbed = self._vtt - self._vtt0
        if absorbed <= self._shown:          # nothing had to be replenished
            return None
        return Absorption(t_from=self._t0, t_to=self._t,
                          bid_px=self._px[0], ask_px=self._px[1],
                          absorbed=absorbed, shown=self._shown,
                          ratio=round(absorbed / self._shown, 2),
                          spread=round(self._px[1] - self._px[0], 4),
                          frames=self._frames)

    # ---- feed ---------------------------------------------------------
    def on_snapshot(self, t: str, ladder: Optional[dict],
                    vtt: Optional[float] = None) -> Optional[Absorption]:
        """One snapshot in; the finished absorption, if this one ended it.

        A missing book or a missing `vtt` closes the window rather than being
        skipped: the proof depends on watching an unbroken run of frames, and
        stitching across a hole would credit these two prices with volume that
        may have traded anywhere.
        """
        now = _touch(ladder)
        if now is None or vtt is None:
            return self._close()

        bid, ask, shown = now
        if self._px != (bid, ask):
            ev = self._close()                       # the touch moved
            self._px, self._t0, self._t = (bid, ask), t, t
            self._vtt0 = self._vtt = vtt
            self._shown, self._frames = shown, 1
            return ev

        self._t, self._vtt = t, vtt
        self._shown = max(self._shown, shown)
        self._frames += 1
        return None

    def pending(self) -> Optional[Absorption]:
        """The window still in progress, or None. Label it as in progress --
        it is a running total and it will keep growing."""
        return self._build()
