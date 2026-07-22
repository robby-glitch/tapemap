"""Unit sanity for chain_metrics (plain asserts, no framework).

Run:  python test_chain_metrics.py
Covers the four checks from the plan: max pain on a symmetric chain = ATM,
GEX flip on a constructed profile, writer-score signs on scripted
OI/premium paths, and squeeze quiet-then-fires on the synthetic fixture.
"""

import json
from pathlib import Path

from chain_metrics import ChainState, max_pain, pcr

FIXTURE = Path(__file__).parent / "data" / "chain_sample.jsonl"


def _row(k, ce_oi, pe_oi, ce_ltp=50.0, pe_ltp=50.0, iv=0.12,
         ce_chg=0, pe_chg=0):
    def side(oi, ltp, chg):
        return {"ltp": ltp, "oi": oi, "oi_chg": chg, "iv": iv,
                "vol": 1000, "bid": ltp - 0.1, "ask": ltp + 0.1,
                "avg": None, "gamma": None, "delta": None}
    return {"k": k, "ce": side(ce_oi, ce_ltp, ce_chg),
            "pe": side(pe_oi, pe_ltp, pe_chg)}


def snap(sec, spot, strikes):
    return {"ts": f"{sec//3600:02d}:{sec%3600//60:02d}:{sec%60:02d}",
            "sec": sec, "spot": spot,
            "atm": min(strikes, key=lambda s: abs(s["k"] - spot))["k"],
            "strikes": strikes}


def test_max_pain_symmetric():
    # symmetric OI mountain centred on 24300 -> max pain must be 24300
    strikes = [_row(k, 1_000_000 - abs(k - 24300) * 800,
                    1_000_000 - abs(k - 24300) * 800)
               for k in range(24000, 24601, 100)]
    assert max_pain(strikes) == 24300, max_pain(strikes)
    p_oi, p_v = pcr(strikes)
    assert abs(p_oi - 1.0) < 1e-9
    print("PASS max_pain symmetric = ATM, PCR = 1")


def test_writer_score_signs():
    # strike A: OI rises while premium falls  -> writer-built, w > 0
    # strike B: OI rises while premium rises  -> buyer-built,  w < 0
    st = ChainState()
    prev = None
    for i in range(16):                      # 150s at 10s steps -> 2 buckets
        sec = 34000 + i * 10
        a_ltp = 60.0 - i * 0.6               # bleeding premium
        b_ltp = 60.0 + i * 0.6               # ripping premium
        strikes = [_row(24200, 500_000 + i * 20_000, 300_000, ce_ltp=a_ltp),
                   _row(24400, 500_000 + i * 20_000, 300_000, ce_ltp=b_ltp)]
        s = snap(sec, 24300.0, strikes)
        m = st.update(s, 0.004, prev)
        prev = s
    by_k = {r["k"]: r for r in m["per_strike"]}
    assert by_k[24200]["ce_w"] > 0.3, by_k[24200]
    assert by_k[24400]["ce_w"] < -0.3, by_k[24400]
    print(f"PASS writer signs: bleed->w={by_k[24200]['ce_w']}, "
          f"rip->w={by_k[24400]['ce_w']}")


def test_gex_flip_and_walls():
    # writer-built books both sides of spot (dealers long gamma at wings),
    # buyer-built ATM (dealers short) -> cumulative GEX must cross zero and
    # walls must sit on the heavy writer strikes.
    st = ChainState()
    prev = None
    for i in range(16):
        sec = 34000 + i * 10
        strikes = [
            _row(24100, 200_000, 900_000 + i * 30_000,
                 pe_ltp=40.0 - i * 0.5),                 # PE writers below
            _row(24300, 400_000 + i * 30_000, 400_000 + i * 30_000,
                 ce_ltp=80.0 + i * 0.7, pe_ltp=80.0 + i * 0.7),  # buyers ATM
            _row(24500, 900_000 + i * 30_000, 200_000,
                 ce_ltp=40.0 - i * 0.5),                 # CE writers above
        ]
        s = snap(sec, 24300.0, strikes)
        m = st.update(s, 0.004, prev)
        prev = s
    assert m["flip_px"] is not None, m
    assert m["wall_dn"] == 24100 and m["wall_up"] == 24500, m
    print(f"PASS gex flip={m['flip_px']:.0f} walls={m['wall_dn']}/{m['wall_up']}"
          f" regime={m['gex_regime']}")


def test_squeeze_on_fixture():
    snaps = [json.loads(x) for x in
             FIXTURE.read_text(encoding="utf-8").splitlines() if x.strip()]
    st = ChainState()
    prev = None
    calm_max, fire_max, fire_side = 0.0, 0.0, None
    for i, s in enumerate(snaps):
        m = st.update(s, s.get("T", 1e-3), prev)
        prev = s
        t_min = i * 5 / 60.0
        sc = m["squeeze"]["score"]
        if t_min < 25:
            calm_max = max(calm_max, sc)
        if 40 <= t_min <= 70 and sc > fire_max:
            fire_max, fire_side = sc, m["squeeze"]["side"]
    assert calm_max < 0.15, f"squeeze not quiet in calm phase: {calm_max}"
    assert fire_max >= 0.30, f"squeeze failed to fire in rally: {fire_max}"
    assert fire_side == "UP", fire_side
    print(f"PASS squeeze: calm max={calm_max:.2f}, "
          f"rally max={fire_max:.2f} side={fire_side}")


if __name__ == "__main__":
    test_max_pain_symmetric()
    test_writer_score_signs()
    test_gex_flip_and_walls()
    test_squeeze_on_fixture()
    print("ALL PASS")
