"""Scratch, descriptive: VALIDATE rev 2a's outcome -- first passage on 1-min highs/lows to the STATIC
target (Room's target, leaving walls removed) or the STATIC L, 30 finished minutes after the check."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "nifty_1m_2026-09-25.json"))); ix = {r[1]: r for r in rows}
def mm(t): h, m = t.split(':'); return int(h) * 60 + int(m)
def hm(n): return f"{n // 60:02d}:{n % 60:02d}"
def fp(t, d, T, L):
    for n in range(mm(t) + 1, min(mm(t) + 30, mm('15:29')) + 1):
        r = ix[hm(n)]; hi, lo = r[3], r[4]
        tgt = (lo <= T) if d < 0 else (hi >= T); stp = (hi >= L) if d < 0 else (lo <= L)
        if tgt and stp: return 'same minute', hm(n)
        if tgt: return 'target', hm(n)
        if stp: return 'stop', hm(n)
    return 'neither', None
for name, t, d, T, L in [('09:35 PE', "09:35", -1, 23100.0, 23121.6), ('09:43 PE', "09:43", -1, 23030.0, 23121.6),
                         ('14:12 PE', "14:12", -1, 23100.0, 23121.6), ('12:00 CE', "12:00", 1, 23100.0, 23075.2),
                         ('12:04 PE', "12:04", -1, 23030.0, 23091.6)]:
    c = ix[t][5]
    print(name, 'close', c, 'target', T, round(abs(c - T), 2), 'line', L, round(abs(c - L), 2), '->', fp(t, d, T, L))
