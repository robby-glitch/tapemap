"""Noise floor of OI change: option chain at ATM +/- 2 (per strike-leg and per side summed) and futures OI (book),
per 5 / 15 / 30 min, by slot and day kind. DESCRIPTIVE ONLY. Run: python -B pr_oi.py > pr_oi_out.txt
Units: option OI in lakh units ("L", the app's unit: read.lakh); futures OI in lots and % of OI."""
import sys, json, glob, gzip, os
import numpy as np
sys.dont_write_bytecode = True
D = 'C:/Users/kaam/Desktop/operator mode/tapemap/data/'
sys.path.insert(0, 'C:/Users/kaam/Desktop/operator mode/tapemap/tools')
import rank_build as rb   # read-only helpers (_first_row, _surface_expiry)

LOT = {'NIFTY': 65, 'BANKNIFTY': 30, 'SENSEX': 20}
M0, M1 = 558, 930
SL = lambda m: (m - 555) // 30   # noqa: E731


def rows(p):
    op = gzip.open if p.endswith('.gz') else open
    out = []
    with op(p, 'rt', encoding='utf-8') as f:
        for l in f:
            try:
                out.append(json.loads(l))
            except ValueError:
                pass
    return out


def kind(idx, day):
    ex = (rb._first_row(D + f'chain/chain_{idx}_{day}.jsonl') or {}).get('expiry') or rb._surface_expiry(D[:-1], idx, day)
    bk = rb._first_row(D + f'book/book_{idx}_{day}.jsonl') or {}
    if bk.get('expiry') and str(bk['expiry'])[:10] == day or day == '2026-09-30' and idx != 'SENSEX':
        return 'ROLL'
    return 'EXPIRY' if ex and str(ex)[:10] == day else 'NORMAL'


def chain_minutes(idx, day):
    """{minute: (spot, {k: (ce, pe)})} from the last chain row at or before each minute (<= 60 s old)."""
    f = glob.glob(D + f'chain/chain_{idx}_{day}.jsonl*')
    R = [r for r in rows(f[0]) if r.get('strikes') and 'sec' in r]
    if len(R) < 1900 or R[0]['sec'] > 33300 + 7 * 60:
        return None, None
    out, j = {}, 0
    for m in range(M0, M1):
        while j + 1 < len(R) and R[j + 1]['sec'] <= m * 60 + 59:
            j += 1
        r = R[j]
        if r['sec'] > m * 60 + 59 or m * 60 + 59 - r['sec'] > 60:
            continue
        out[m] = (r['spot'], {s['k']: ((s.get('ce') or {}).get('oi'), (s.get('pe') or {}).get('oi')) for s in R[j]['strikes']})
    ks = sorted({s['k'] for s in R[0]['strikes']})
    return out, ks[1] - ks[0]


def q(x, ps=(10, 50, 90)):
    x = np.asarray([v for v in x if v is not None and not np.isnan(v)])
    return [round(float(np.percentile(x, p)), 2) for p in ps] if len(x) else None


def chain_study(idx):
    days = sorted({os.path.basename(p)[len(f'chain_{idx}_'):][:10] for p in glob.glob(D + f'chain/chain_{idx}_*.jsonl*')})
    leg = {W: {} for W in (5, 15, 30)}       # (kind, slot) -> [|dOI| per strike-leg, L]
    legpct = {W: {} for W in (5, 15, 30)}
    side = {W: {} for W in (15, 30)}         # (kind, part) -> [signed CE sum, PE sum, L]
    pers, acc_ratio, churn, used = {15: [], 30: []}, [], [], []
    for day in days:
        mins, step = chain_minutes(idx, day)
        if not mins:
            continue
        kd = kind(idx, day)
        used.append((day[5:], kd[0]))
        sums = {}
        for m, (spot, K) in mins.items():
            atm = round(spot / step) * step
            for W in (5, 15, 30):
                if m - W not in mins:
                    continue
                K0 = mins[m - W][1]
                tot = {0: 0.0, 1: 0.0}
                ok = True
                for k in (atm + step * n for n in range(-2, 3)):
                    a, b = K.get(k), K0.get(k)
                    for li in (0, 1):
                        if a is None or b is None or a[li] is None or b[li] is None:
                            ok = False
                            continue
                        d = (a[li] - b[li]) / 1e5
                        leg[W].setdefault((kd, SL(m)), []).append(abs(d))
                        if b[li] > 0:
                            legpct[W].setdefault((kd, SL(m)), []).append(abs(d) / (b[li] / 1e5) * 100)
                        tot[li] += d
                if W in side and ok:
                    part = 0 if m < 600 else 1 if m < 720 else 2 if m < 810 else 3
                    side[W].setdefault((kd, part), []).append((tot[0], tot[1]))
                    sums[(W, m)] = (tot[0], tot[1], atm)
        # persistence of the side sums: adjacent non-overlapping windows on the same ATM
        for W in (15, 30):
            for m in range(M0 + 2 * W, M1):
                a, b = sums.get((W, m)), sums.get((W, m - W))
                if a and b and a[2] == b[2]:
                    pers[W].append((a[0], b[0]))
                    pers[W].append((a[1], b[1]))
        # speed of the build: d15(t) - d15(t-15), against |d15|
        for m in range(M0 + 30, M1):
            a, b = sums.get((15, m)), sums.get((15, m - 15))
            if a and b and a[2] == b[2]:
                for li in (0, 1):
                    acc_ratio.append((a[li] - b[li], a[li]))
        # churn at ATM +/- 2 per 30 min: gross |minute changes| / |net|
        for m in range(M0 + 30, M1, 30):
            if m not in mins or m - 30 not in mins:
                continue
            atm = round(mins[m][0] / step) * step
            for k in (atm + step * n for n in range(-2, 3)):
                for li in (0, 1):
                    g, prev = 0.0, None
                    for mm in range(m - 30, m + 1):
                        x = mins.get(mm, (None, {}))[1].get(k)
                        v = x[li] if x else None
                        if v is not None and prev is not None:
                            g += abs(v - prev)
                        if v is not None:
                            prev = v
                    a, b = mins[m][1].get(k), mins[m - 30][1].get(k)
                    if a and b and a[li] is not None and b[li] is not None and g > 0:
                        churn.append(g / max(abs(a[li] - b[li]), 1))
    print(f'\n=== CHAIN {idx}: {len(used)} full chain days (kind: N normal / E expiry / R roll): {used}')
    for W in (5, 15, 30):
        print(f' |dOI| per strike-leg at ATM+/-2 over {W} min, lakh units, by 30-min slot: NORMAL p10/p50/p90 · EXPIRY p50/p90 · NORMAL % of the leg OI p50/p90')
        for s in range(13):
            n_, e_, p_ = leg[W].get(('NORMAL', s), []), leg[W].get(('EXPIRY', s), []), legpct[W].get(('NORMAL', s), [])
            print(f'   {(555 + 30 * s) // 60:02d}:{(555 + 30 * s) % 60:02d}  {q(n_)}  · {q(e_, (50, 90))}  · {q(p_, (50, 90))}%  (n {len(n_)})')
    for W in (15, 30):
        print(f' ATM+/-2 side sum over {W} min (signed, L): NORMAL by day-part CE p10/p50/p90 | PE p10/p50/p90')
        for part in range(4):
            v = side[W].get(('NORMAL', part), [])
            print(f'   part {part}: CE {q([x[0] for x in v])} | PE {q([x[1] for x in v])} (n {len(v)})')
    for W in (15, 30):
        a = np.array(pers[W])
        print(f' persistence: corr(side sum over {W} min, the previous {W} min, same ATM) = {np.corrcoef(a[:, 0], a[:, 1])[0, 1]:.2f}, '
              f'same sign {np.mean(np.sign(a[:, 0]) == np.sign(a[:, 1])):.2f} (n {len(a)})')
    a = np.array(acc_ratio)
    print(f' speed of build d15(t)-d15(t-15) vs |d15(t)|: median |speed| / median |d15| = '
          f'{np.median(np.abs(a[:, 0])) / np.median(np.abs(a[:, 1])):.2f}')
    print(f' churn per 30 min, gross |minute changes| / |net change| per strike-leg: p10/p50/p90 {q(churn)}')


def fut_study(idx):
    days = sorted({os.path.basename(p)[len(f'book_{idx}_'):][:10] for p in glob.glob(D + f'book/book_{idx}_*.jsonl*')})
    ch = {W: {} for W in (5, 15, 30)}
    pers = {15: [], 30: []}
    used = []
    for day in days:
        R = [r for r in rows(glob.glob(D + f'book/book_{idx}_{day}.jsonl*')[0]) if isinstance(r.get('t'), (int, float)) and r.get('oi')]
        sec = [int(r['t'] // 1000 + 19800) % 86400 for r in R]
        if len(R) < 15000 or sec[0] > 33300 + 7 * 60 or sec[-1] < 55000:
            continue
        kd = kind(idx, day)
        if kd == 'ROLL':
            continue
        used.append((day[5:], kd[0]))
        oi, j = {}, 0
        for m in range(M0, M1):
            while j + 1 < len(R) and sec[j + 1] <= m * 60 + 59:
                j += 1
            if sec[j] <= m * 60 + 59:
                oi[m] = R[j]['oi']
        for W in (5, 15, 30):
            for m in range(M0 + W, M1):
                if m in oi and m - W in oi:
                    d = (oi[m] - oi[m - W])
                    ch[W].setdefault((kd, SL(m)), []).append((d / LOT[idx], d / oi[m - W] * 100))
        for W in (15, 30):
            for m in range(M0 + 2 * W, M1):
                if all(x in oi for x in (m, m - W, m - 2 * W)):
                    pers[W].append((oi[m] - oi[m - W], oi[m - W] - oi[m - 2 * W]))
    print(f'\n=== FUTURES OI {idx} (book, ~1 update / {"160" if idx == "SENSEX" else "60"} s): {len(used)} full non-roll days {used}')
    for W in (5, 15, 30):
        print(f' |dOI| over {W} min by 30-min slot, NORMAL: lots p10/p50/p90 · % of OI p50/p90')
        for s in range(13):
            v = ch[W].get(('NORMAL', s), [])
            print(f'   {(555 + 30 * s) // 60:02d}:{(555 + 30 * s) % 60:02d}  {q([abs(x[0]) for x in v])} · {q([abs(x[1]) for x in v], (50, 90))}%  (n {len(v)})')
    for W in (15, 30):
        a = np.array(pers[W], dtype=float)
        print(f' persistence: corr(dOI over {W} min, previous {W} min) = {np.corrcoef(a[:, 0], a[:, 1])[0, 1]:.2f}, same sign {np.mean(np.sign(a[:, 0]) == np.sign(a[:, 1])):.2f} (n {len(a)})')


if __name__ == '__main__':
    for idx in ('NIFTY', 'BANKNIFTY', 'SENSEX'):
        chain_study(idx)
        fut_study(idx)
