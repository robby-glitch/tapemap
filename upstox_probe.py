"""Can Upstox replace Dhan as this tool's data source? One question at a time.

WHY THIS EXISTS. On 2026-08-05 the Dhan DATA API subscription lapsed (401 /
DH-902) and the whole tape went dark. Upstox's API is free for account
holders, so it is the obvious alternative -- but a migration is only worth
starting if Upstox can supply the ONE thing the analytics cannot be rebuilt
without.

That thing is **per-strike implied volatility**. Everything downstream --
gamma, dealer-signed GEX, the flip price, both walls, the whole ZONE READ --
is computed from IV per strike. Bars and OI are replaceable; IV is the hinge.
So this probe answers four questions and stops:

  1. does the token authenticate at all?
  2. can we resolve NIFTY's futures + option instrument keys?
  3. do intraday candles come back, and do they carry OPEN INTEREST?
  4. does the option chain carry IV per strike, and an OI CHANGE?

READ-ONLY. Writes nothing, and never prints the token. Put the access token in
`.upstox_token` (gitignored, same as `.dhan_token`) -- never on the command
line, because arguments land in shell history.

    python upstox_probe.py

A THROWAWAY probe, not part of the app. Delete it once the answer is recorded.
"""

import gzip
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

BASE = "https://api.upstox.com/v2"
INSTRUMENTS_URL = ("https://assets.upstox.com/market-quote/instruments/"
                   "exchange/NSE.json.gz")
TOKEN_FILE = ".upstox_token"


def _tok():
    try:
        t = open(TOKEN_FILE, encoding="utf-8").read().strip()
    except OSError:
        sys.exit(f"no {TOKEN_FILE} — paste the Upstox access token into that file")
    if not t:
        sys.exit(f"{TOKEN_FILE} is empty")
    return t


def _get(url, tok):
    """(status, parsed_or_text). Never raises -- a failure IS an answer here."""
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {tok}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:300]
    except Exception as e:                       # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def q1_auth(tok):
    """Informative, NOT a gate.

    Upstox's Analytics Token is read-only and scoped to Market Data + Streaming;
    Portfolio and Account/Funds are granted only when a static IP is configured.
    So /user/profile can legitimately refuse while market data works perfectly,
    and an earlier version of this probe exited there -- reporting a failure
    that said nothing about the question actually being asked.

    The real authentication test is [3]: if candles come back, the token works
    for everything this tool needs.
    """
    print("\n[1] does the token reach the account endpoints? (informational)")
    st, body = _get(f"{BASE}/user/profile", tok)
    if st == 200:
        print("    OK — HTTP 200 (profile readable)")
    else:
        print(f"    HTTP {st} — expected for an Analytics Token without a "
              f"static IP. Not a problem: this tool never reads the account.")
        print(f"    said: {str(body)[:160]}")


def q2_instruments():
    print("\n[2] can we resolve NIFTY futures and options?")
    try:
        with urllib.request.urlopen(INSTRUMENTS_URL, timeout=90) as r:
            raw = gzip.GzipFile(fileobj=io.BytesIO(r.read())).read()
        rows = json.loads(raw.decode())
    except Exception as e:                       # noqa: BLE001
        print(f"    FAIL — instrument dump unreadable: {type(e).__name__}: {e}")
        return None, None
    print(f"    instrument rows: {len(rows)}")

    def nifty(kinds):
        return [r for r in rows
                if r.get("segment") == "NSE_FO"
                and (r.get("name") or "").upper() == "NIFTY"
                and (r.get("instrument_type") or "").upper() in kinds]

    futs, opts = nifty(("FUT", "FUTIDX")), nifty(("CE", "PE"))
    print(f"    NIFTY futures rows: {len(futs)}   option rows: {len(opts)}")
    if not futs:
        print("    FAIL — no NIFTY futures found; the filter or the schema differs")
        return None, None
    futs.sort(key=lambda r: r.get("expiry") or 0)
    f = futs[0]
    exp = f.get("expiry")
    when = (datetime.fromtimestamp(exp / 1000).strftime("%Y-%m-%d")
            if isinstance(exp, (int, float)) else exp)
    print(f"    nearest future: {f.get('trading_symbol')} exp {when}")
    print(f"    instrument_key: {f.get('instrument_key')}")
    idx = next((r.get("instrument_key") for r in rows
                if (r.get("trading_symbol") or "") in ("Nifty 50", "NIFTY 50")
                and r.get("segment") == "NSE_INDEX"), "NSE_INDEX|Nifty 50")
    return f.get("instrument_key"), idx


def q3_candles(tok, fut_key):
    print("\n[3] do intraday candles come back, and do they carry OI?")
    if not fut_key:
        print("    SKIPPED — no futures key from [2]")
        return
    key = urllib.parse.quote(fut_key, safe="")
    st, body = _get(f"{BASE}/historical-candle/intraday/{key}/1minute", tok)
    if st != 200:
        print(f"    FAIL — HTTP {st}: {str(body)[:220]}")
        return
    candles = (body.get("data") or {}).get("candles") or []
    print(f"    OK — {len(candles)} one-minute candles")
    if candles:
        c = candles[0]
        print(f"    a candle has {len(c)} fields: {c}")
        # Dhan's shape is [ts, o, h, l, c, volume, open_interest]
        print("    carries OPEN INTEREST:",
              "YES (7th field)" if len(c) >= 7
              else "NO — OI would have to come from elsewhere")


def q4_chain(tok, idx_key):
    print("\n[4] THE HINGE — does the option chain carry IV per strike?")
    d = datetime.now()
    for _ in range(10):                          # next Thursday-ish expiry
        d += timedelta(days=1)
        if d.weekday() == 3:
            break
    exp = d.strftime("%Y-%m-%d")
    url = (f"{BASE}/option/chain?instrument_key="
           f"{urllib.parse.quote(idx_key, safe='')}&expiry_date={exp}")
    st, body = _get(url, tok)
    if st != 200:
        print(f"    FAIL — HTTP {st}: {str(body)[:220]}")
        print(f"    (tried expiry {exp}; a wrong expiry also 4xxs — retry with a real one)")
        return
    rows = body.get("data") or []
    print(f"    OK — {len(rows)} strikes for expiry {exp}")
    if not rows:
        return
    r = rows[len(rows) // 2]
    ce = r.get("call_options") or {}
    md, gk = ce.get("market_data") or {}, ce.get("option_greeks") or {}
    print(f"    strike {r.get('strike_price')} CE market_data keys: {sorted(md)[:6]}")
    print(f"                          option_greeks keys: {sorted(gk)}")
    iv = gk.get("iv")
    print(f"    IV present : {'YES' if iv is not None else 'NO'}  (value {iv})")
    print(f"    OI present : {'YES' if md.get('oi') is not None else 'NO'}  "
          f"(value {md.get('oi')})")
    prev = md.get("prev_oi")
    print(f"    prev_oi    : {'YES' if prev is not None else 'NO'} -> oi_chg is "
          f"{'derivable' if prev is not None else 'NOT direct; the poller must diff snapshots'}")
    print()
    print("    VERDICT:", "Upstox can drive the GEX stack." if iv is not None
          else "IV missing — gamma/GEX/flip/walls would need solving from "
               "premiums (gamma.implied_vol exists, but that is real work).")


def main():
    tok = _tok()
    print("Upstox probe — read-only. The token is never printed.")
    q1_auth(tok)
    fut_key, idx_key = q2_instruments()
    q3_candles(tok, fut_key)
    q4_chain(tok, idx_key)


if __name__ == "__main__":
    main()
