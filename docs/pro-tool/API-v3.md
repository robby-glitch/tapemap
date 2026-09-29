# API v3: the contract between the server, the new screens (ui-v2 `/pro.html`) and the GoCharting panel

Fixed by the supervisor on 2026-09-28 at 23:15 so that the server builder and the UI builders work in parallel.
- `fold.py` owns the reads.
- `server.py` serves them.
- The screens render them and compute nothing.

A real session never falls back to fixtures. If an endpoint is missing or down, the screen says
**"could not check — the engine is not answering (hh:mm:ss)"**.

## Reads

### `GET /api/fold?id=<trade_id>`: one marked trade, in-trade
Returns `{ok, id, trade, view, words, asof}`, or `{ok: false, why}`.
- **`trade`:** `{idx, k, ty: "CE"|"PE", side: "BUY"|"SELL", p0, entry_t, exit_t|null, qty}`, from `/api/hold/trades`.
- **`view`:** `fold.read`'s view (see `fixtures/fold_view_H2_slim.json` for real examples), trimmed to its last 12 `events`.
  - `headline`: HOLD / PAST GIVE-UP / FOLD / CAN'T CHECK.
  - `clause`: "behind you: … · against you: …".
  - `line2`: what takes her out, before it happens.
  - `rows{zone, flow, oi, vpin}`: each `{chip: WITH|AGAINST|QUIET|CAN'T CHECK, sentence}`.
  - `G`, `A`, `W`.
  - `prem{now, pct, peak, given_back, at_G, at_A, intrinsic, time, expiry_day}`.
  - `holes`.
  - `sound_id`: it changes only when a new FOLD is to sound, once.
  - `tag`.
- **`words`:** the headline history from `fold_log`, `[{t, headline, clause}]`. Logged words win.
- **After `exit_t`:** the view is frozen at the exit. The premium and P&L are **at her exit**, never at the latest price.

### `GET /api/fold/ifin?idx=NIFTY&k=<strike>&ty=CE|PE&side=BUY|SELL`: "IF YOU WERE IN", before entry
Returns `{ok, view}`: the same view for a hypothetical trade entered now at the live premium. It is logged as `ifin`, not as a trade.

### `GET /api/fold/flat?idx=NIFTY`: flat
Returns `{ok, next_fight: {above: {px, what, confirm}, below: {px, what, confirm}}, rows{zone, flow, oi, vpin}, day, asof}`.
- `what`: e.g. "22900 CE writers + trapped buyers 22910".
- `confirm`: e.g. "lifts followed by price and the 22900 CE shedding".
- `day`: one sentence for the day (R6).

### `GET /api/fold/record?day=YYYY-MM-DD`: after 15:30
Returns `{ok, trades: [{id, trade, words: [...], exit, best, peak_before_exit, given_back}]}`, as counts only and never rates.

## Writes (unchanged doors)

**`POST /api/hold/trades`** with `{op: mark | exit | reopen | unmark, idx, k, side, role, p0, t0, qty}`. This is the existing
door, and both screens use it.
- The ui-v2 page posts through the Vite proxy (same-origin).
- The extension posts through its service worker (`sw.js`), which P1-07 allows.

## The frame (GoCharting panel)
`POST /api/frame` (unchanged) returns the frame, **plus**:
- `fold`: `{trade: <marked trade or null>, view: <as above, or null>}`;
- `flat`: `<the flat read, when no trade is open>`.

The panel renders these. It computes nothing.
