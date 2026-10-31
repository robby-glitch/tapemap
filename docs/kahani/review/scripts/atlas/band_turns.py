"""Band turns (her ask, 31 Oct): every band signal the server logged live 21-30 Oct (data/confluence_log.jsonl) -- the
zone triggers with and without the full CONFLUENCE entry (zone + OI + flow, §1i) and FADE-D (§1n) -- traced on the
futures minutes after it. Under §1k terms: the registered rules are frozen and NOT re-scored here (no R, no bar);
this prints paths in points and sigma, counts only, never a rate. Run after the frames are cached (atlas_build.py +
the SENSEX / BANKNIFTY forward days)."""
import json
import os
import statistics
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5))
A = os.path.join(tempfile.gettempdir(), "jarvis_atlas", "frames")
STALL_MIN, NEW_U = 6, 0.25                    # legs.py's own pause: 6 min with no new extreme of 0.25U


def m2i(s):
    return int(s[:2]) * 60 + int(s[3:5])


def hm(m):
    return f"{m // 60:02d}:{m % 60:02d}"


FR = {}


def frame(idx, day):
    k = (idx, day)
    if k not in FR:
        p = os.path.join(A, f"{idx}_{day}.json")
        FR[k] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    return FR[k]


def trace(d, close, s, E=None):
    """The path after a signal whose bar closed at `close` (HH:MM), direction s (+1 buy / -1 sell)."""
    M = [m2i(t) for t in d["mins"]]
    c = m2i(close)
    i0 = next((i for i, m in enumerate(M) if m >= c - 1), None)          # the bar's last minute
    if i0 is None or M[i0] > c + 2:
        return None
    E = E if E is not None else d["fut"][i0]
    sd = d["sd"][i0] or None
    if not sd:
        return None
    U = max(sd, 0.001 * E)
    end = next((j for j in range(i0, len(M)) if M[j] - M[i0] > 60 or d["mins"][j] >= "15:20"), len(M) - 1)
    best, best_t, last_new, stall, first = 0.0, M[i0], M[i0], None, None
    mae, vw_t = 0.0, None
    for j in range(i0 + 1, end + 1):
        fav = s * ((d["fhi"][j] if s > 0 else d["flo"][j]) - E)
        adv = s * (E - (d["flo"][j] if s > 0 else d["fhi"][j]))
        mae = max(mae, adv)
        if first is None and (fav >= sd or adv >= sd):
            first = "+1σ" if fav >= sd and not adv >= sd else "−1σ" if adv >= sd and not fav >= sd else "both"
        if vw_t is None and s * (d["fut"][j] - d["vwap"][j]) >= 0:
            vw_t = M[j] - M[i0]
        if fav >= best + NEW_U * U or (best == 0 and fav > 0 and fav >= NEW_U * U):
            best, best_t, last_new = fav, M[j], M[j]
        if stall is None and best > 0 and M[j] - last_new >= STALL_MIN:
            fl = d.get("flow") or d.get("delta") or []
            w = [fl[k] for k in range(max(0, j - 2), j + 1) if k < len(fl) and fl[k] is not None]
            stall = {"t": d["mins"][j], "after": M[j] - M[i0], "pts": round(best, 1),
                     "delta_with": None if not w else (s * sum(w) > 0), "j": j}
    mfe = best
    out = {"E": E, "sd": round(sd, 1), "mfe": round(mfe, 1), "mae": round(mae, 1), "mfe_sd": round(mfe / sd, 2),
           "mae_sd": round(mae / sd, 2), "first": first or "neither", "vwap_min": vw_t, "mfe_min": best_t - M[i0],
           "stall": stall}
    if stall:                                     # after the first stall: did it go on (a real new extreme)?
        more = max(s * ((d["fhi"][j] if s > 0 else d["flo"][j]) - E) for j in range(stall["j"], end + 1))
        back = max(s * (E - (d["flo"][j] if s > 0 else d["fhi"][j])) for j in range(stall["j"], end + 1))
        stall["went_on"] = round(more - stall["pts"], 1)
        stall["then_back_to_E"] = back >= 0
        del stall["j"]
    return out


rows = [json.loads(x) for x in open(os.path.join(ROOT, "data", "confluence_log.jsonl"), encoding="utf-8") if x.strip()]
T = []
for r in rows:
    d = frame(r["index"], r["day"])
    if d is None or r["setup"] not in ("FADE", "FADE-D"):
        continue
    s = 1 if r["side"] == "BUY" else -1
    if r["setup"] == "FADE":
        e = r.get("entry")
        close = e["close"] if e else hm(m2i(r["t"]) + 3)
        grp = "CONFLUENCE (zone+OI+flow)" if e else "zone touch, no confirmation"
        tr = trace(d, close, s, e["E"] if e else None)
    else:
        e = r.get("entry")
        if e:
            close, grp = e["t"], "FADE-D (cum delta + OI lead)"
        else:
            close, grp = (r.get("locs") or [{}])[0].get("close"), "FADE-D location, no confirmation"
        if not close:
            continue
        tr = trace(d, close, s, e["E"] if e else None)
    if tr:
        T.append({"grp": grp, "day": r["day"], "idx": r["index"], "side": r["side"], "t": close, "kind": r.get("kind"), **tr})

G = ["CONFLUENCE (zone+OI+flow)", "zone touch, no confirmation", "FADE-D (cum delta + OI lead)", "FADE-D location, no confirmation"]
med = lambda xs: round(statistics.median(xs), 2) if xs else None
print("== did the signal catch the turn? (next 60 min, futures; sigma = the band's at the signal) ==")
for g in G:
    X = [x for x in T if x["grp"] == g]
    if not X:
        continue
    print(f"{g} (n {len(X)}): +1σ first {sum(x['first'] == '+1σ' for x in X)} · −1σ first {sum(x['first'] == '−1σ' for x in X)}"
          f" · neither {sum(x['first'] == 'neither' for x in X)} · reached VWAP {sum(x['vwap_min'] is not None for x in X)}"
          f" · median best {med([x['mfe_sd'] for x in X])}σ · median worst {med([x['mae_sd'] for x in X])}σ")
print("\n== every confirmed entry ==")
for x in sorted([x for x in T if not x["grp"].endswith("confirmation")], key=lambda x: (x["day"], x["t"])):
    st = x["stall"]
    print(f"{x['day']} {x['idx']:<9} {x['grp'][:10]:<10} {x['side']:<4} {x['t']} E {x['E']:.0f} σ{x['sd']:.0f} | first {x['first']:<7}"
          f" best {x['mfe']:+.0f} ({x['mfe_sd']}σ) at +{x['mfe_min']}m · worst {x['mae']:.0f} ({x['mae_sd']}σ) · VWAP "
          f"{'+' + str(x['vwap_min']) + 'm' if x['vwap_min'] is not None else 'no'}"
          + (f" | stall +{st['after']}m at {st['pts']:+.0f}, delta {'with' if st['delta_with'] else 'against' if st['delta_with'] is False else '?'}"
             f", then went on {st['went_on']:+.0f}{' · came back to entry' if st['then_back_to_E'] else ''}" if st else " | no stall"))
print("\n== the first stall (6 min, no new extreme) as an exit, all band signals ==")
S = [x for x in T if x["stall"]]
for lbl, f in (("delta still WITH the trade at the stall", lambda x: x["stall"]["delta_with"] is True),
               ("delta AGAINST the trade at the stall", lambda x: x["stall"]["delta_with"] is False)):
    X = [x for x in S if f(x)]
    if X:
        print(f"{lbl} (n {len(X)}): went on ≥ +0.5σ more {sum(x['stall']['went_on'] >= 0.5 * x['sd'] for x in X)}"
              f" · came back to entry {sum(x['stall']['then_back_to_E'] for x in X)} · median stall at +{med([x['stall']['after'] for x in X])} min,"
              f" {med([x['stall']['pts'] / x['sd'] for x in X])}σ in · median more after it {med([x['stall']['went_on'] / x['sd'] for x in X])}σ")
print(f"signals that never got +0.25U before stalling or 60 min: {sum(1 for x in T if not x['stall'])} of {len(T)}")
print("\nwhere the best point was reached, minutes after the signal (all signals with a best > 0):",
      " ".join(str(x["mfe_min"]) for x in sorted(T, key=lambda x: x["mfe_min"]) if x["mfe"] > 0))
