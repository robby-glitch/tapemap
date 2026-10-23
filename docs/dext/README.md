# Dext record and the three-way parity (gate 3)

Gate 3 of the trader's plan to retire GoCharting. The Dext (Dhan) order-flow extension
(`C:\Users\kaam\Desktop\dext extension\dext-decoder\dext-decoder\`, v0.7.0) sends its charts' closed 1-minute candles
here. TapeMap records them, and every evening it checks them against Upstox and GoCharting. This is display and
recording only: no engine, frame, signal or log that TapeMap decides on reads `data/dext/`.

## The door: `POST /api/dext/candles`

* **Body:** `{inst: {EXCH, SEG, SEC_ID}, name, candles: [...], ohlc: [...]}`.
  * `candles` are Dext's getOrderFlow 1m candles in CONTRACTS, with `t` in epoch seconds:
    `t time high low buy_volume sell_volume neutral_volume total_volume delta cumulative_delta levels[price buy_volume
    sell_volume neutral_volume total_volume delta]`.
  * `ohlc` are getData rows: `t o h l c v oi`.
* **Reply:** `{ok, stored: {day: n}, last_t}`.
  * A refused payload gets a 400 with `{ok: false, why}` and nothing from it is stored.
  * A web page's Origin gets a 403. This is the hold doors' rule: only a `chrome-extension://` Origin, or no
    `Sec-Fetch-Site` header (as with curl), is let in.
* **Cheap by construction:** the door does no frame build and calls no engine.
  * Each day file is read once per process. After that, only the lines that differ are appended; it is never rewritten
    per request (the 2026-09-18 wedge).
  * A 1,500-candle history batch takes about 0.1 s.
* **Refused whole:** a body over 4 MB, more than 2,000 candles or rows, more than 1,000 levels in a candle, a `t` that is
  not a whole minute, a non-finite, negative or huge number, a malformed `time`, or an id-like or odd `name`.
  * Fields outside the lists above are dropped, never stored.

## The files: `data/dext/`

| file | what |
|---|---|
| `dext_<EXCH>-<SEC_ID>_<day>.jsonl` | one raw 1m candle per line (IST day of `t`). A re-sent minute: last copy wins on read |
| `dext_ohlc_<EXCH>-<SEC_ID>_<day>.jsonl` | getData rows, the same rule |
| `instruments.json` | `{"NSE-48704": {EXCH, SEG, SEC_ID, name, lot}}`. `lot` stays null until someone writes it in; a written lot is kept |
| `parity_<day>.json` | the evening report |

Readers: `dext_log.read_candles(key, day)` and `dext_log.read_ohlc(key, day)` return one row per `t`. Tests and a
`--mock-chain` run point `dext_log.DIR` elsewhere (`conftest.py`, `server._isolate_mock_writers`).

## The parity: `dext_parity.py [day]` and `GET /api/dext/parity?day=`

There are three sources for NIFTY futures:

* **D:** Dext, 1m folded into 5m bars anchored at 09:15 IST, in lots.
* **U:** Upstox, from `data/tape/ux_NIFTY_<day>.jsonl`.
* **G:** GoCharting, from `data/tape/tape_NIFTY_<day>.jsonl`.

`eod_capture.bat` runs it for today after the scoring line. It writes the report and one line to
`data/eod_capture.log`, and its exit code never changes the bat's. With nothing sent that day the line says
"could not check — no Dext candles today". The GET computes the same report on request and writes nothing.

### Rules

* **Same contract or no comparison.** Dext's NSE `SEC_ID` is Upstox's exchange token: `48704` = `NSE_FO|48704`, NIFTY
  OCT FUT.
  * GoCharting's NIFTY-I is the continuous near month, so it is compared only on days whose Upstox record is on Dext's
    contract.
  * On any other day the report names both contracts and compares nothing.
* **Lot:** read from `instruments.json`. If that is empty, it is the lot the Upstox dump gave the same exchange token.
  It is never assumed.
* **The 09:15 bar is excluded.** Dext and GoCharting fold the pre-open auction into it and Upstox does not. Its three
  volumes are reported on their own.
* **Dext's 15:30–15:39 minutes are excluded.** That is NSE's closing auction session, which only Dext carries. Their
  volume is reported on its own.
* **Bars:** every pairwise number is over the bars that all compared sources have. A bar one source lacks is named
  under `bars.missing`.

### The report

* **Volume and delta:** Σ volume and Σ delta for D, U and G; the bars whose volume agrees within 0.5 lot.
* **OI:** how many bar-end OI values are equal (Dext's comes from its getData rows).
* **Delta agreement:** same-sign delta bars and the per-bar delta correlation, for each pair.
* **Delta vs move:** each source's delta correlated with the bar's own close − open (Dext's from getData).
* **Footprint cells:** the median footprint cell overlap, D~U and D~G. Cells are 5-point rows centred on multiples of 5,
  with all volume at the price, and overlap is Σmin/Σmax per bar.
* **POC:** how often the heaviest row agrees.
* **Top cells:** the 5 heaviest single-price cells of the day for each source.

These are counts and ratios only. The report never names a winner or gives an accuracy verdict; the trader reads the
rows.

### Reproduced from the trader's manual run

These come from her export, same contract, 09:15 excluded. `test_dext.py` runs the fixture
`test/fixtures/dext_parity_NIFTY_2026-10-05.json.gz` through `dext_log.store` in 1,500-candle batches.

| day | bars | Σ vol D / U / G | ΣΔ D / U / G | same-sign D=U, D=G | cell overlap D~U, D~G |
|---|---|---|---|---|---|
| 30 Sep | 70 | 53,067 / 53,067 / 53,076 | −6,343 / −8,188 / −7,390 | 66/70, 49/70 | 0.90, 0.90 |
| 1 Oct | 74 | 83,694 / 83,689 / 83,674 | −1,570 / −5,998 / +14 | 64/74, 64/74 | 0.85, 0.84 |
| 5 Oct | 74 | 49,242 / 49,234 / 49,233 | −1,544 / −2,372 / −1,509 | 60/74, 62/74 | 0.90, 0.90 |

GoCharting's 30 Sep record lacks 11:05, 11:40, 13:35 and 13:40, so that day compares 70 bars.
