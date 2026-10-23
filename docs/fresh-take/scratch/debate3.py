"""Round 2 checks. Descriptive only: (2) touch vs first agreeing 1-min tick delta; (4) how often a 'first stop' EVENT fires.
No P&L, no outcomes."""
from frames_lib import *
import statistics, collections, bisect

def minute_delta(td, secs, t0, t1):
    i0 = bisect.bisect_left(secs, t0); i1 = bisect.bisect_left(secs, t1)
    sd = sum(x[1] for x in td[i0:i1]); v = sum(x[2] for x in td[i0:i1])
    return sd, v

lags = []; dists = []; at_touch_agree = 0; n = 0
detail = []
for idx in IDXS:
    for day in DAYS:
        if day == '2026-10-07': continue
        d, rl, recs = replay(idx, day)
        if not recs: continue
        td = tick_delta(d); secs = [x[0] for x in td]
        ks = sorted(recs)
        inside = True
        for T in ks:
            r = recs[T]
            if not r['ready']: continue
            z = r['z']
            if inside and abs(z) >= 1.0:
                inside = False
                dr = 1 if z > 0 else -1
                reg = r['shown']
                if reg[0] in ('TREND', 'LEAN') and reg[1] == dr:
                    n += 1
                    sg = r['sigma']
                    # delta in the last completed minute before T
                    sd, v = minute_delta(td, secs, T-60, T)
                    if v and sd*dr/v >= 0.03:
                        lag = 0; at_touch_agree += 1; Fa = r['F']
                    else:
                        lag = None
                        for k in range(1, 16):
                            sd, v = minute_delta(td, secs, T+60*(k-1), T+60*k)
                            if v and sd*dr/v >= 0.03:
                                lag = k; break
                        if lag is not None:
                            rr = recs.get(T+60*lag)
                            Fa = rr['F'] if rr else None
                    if lag is not None and Fa is not None:
                        lags.append(lag); dists.append((Fa - r['F'])*dr/sg)
                    else:
                        lags.append(99);
                    if idx == 'NIFTY' and day == '2026-10-08':
                        detail.append((fmt(T), 'z%+.2f' % z, 'F %.0f' % r['F'], 'lag', lag, 'sigma moved %.2f' % (dists[-1] if lag is not None and Fa is not None and lags[-1] != 99 else float('nan'))))
            elif not inside and abs(z) < 0.75:
                inside = True
print('1-sigma first-touch episodes inside an allowed side (shown TREND/LEAN with the touch):', n)
print('delta already agreeing in the minute before the touch:', at_touch_agree, '(%.0f%%)' % (100*at_touch_agree/n))
ok = [l for l in lags if l != 99]
print('first agreeing 1-min delta within 15 min: %d of %d' % (len(ok), n))
c = collections.Counter(min(l, 6) for l in ok)
print('lag minutes distribution (6 = 6+):', dict(sorted(c.items())))
print('median lag (those that came) %.1f min ; share within 2 min %.0f%%' % (statistics.median(ok), 100*sum(1 for l in ok if l <= 2)/len(ok)))
print('sigma moved in trade direction between touch and first agreeing delta: median %.2f, p25 %.2f, p75 %.2f ; share where price had already run further (>0): %.0f%%' % (
    statistics.median(dists), statistics.quantiles(dists, n=4)[0], statistics.quantiles(dists, n=4)[2], 100*sum(1 for x in dists if x > 0)/len(dists)))
print('8 Oct NIFTY episodes:')
for x in detail: print('  ', x)

# ---- point 4: event frequency
def onsets(flags, gap=30):
    out = []; last = -10**9
    for T, f in flags:
        if f and T - last >= gap*60:
            out.append(T); last = T
    return out

flip_ev = []; turn_ev = []; ep_ev = []
for idx in IDXS:
    for day in DAYS:
        if day == '2026-10-07': continue
        d, rl, recs = replay(idx, day)
        if not recs: continue
        ks = sorted(recs)
        flip_ev.append(len(onsets([(T, recs[T]['flip']) for T in ks])))
        turn_ev.append(len(onsets([(T, recs[T]['regime'] == 'TURN') for T in ks])))
        # once per trend/lean episode (shown state, same direction): first minute flip flag is on
        eps = 0; cur = None; fired = False
        for T in ks:
            sh = recs[T]['shown']
            k = sh[:2] if sh[0] in ('TREND', 'LEAN') else None
            if k != cur:
                cur = k; fired = False
            if cur and recs[T]['flip'] and not fired:
                eps += 1; fired = True
        ep_ev.append(eps)
print('EVENTS per index-day (33): flip-flag onsets (30-min refractory): median %s max %s ; TURN onsets median %s max %s ; first-stop once per trend/lean episode: median %s max %s' % (
    statistics.median(flip_ev), max(flip_ev), statistics.median(turn_ev), max(turn_ev), statistics.median(ep_ev), max(ep_ev)))
late = [(l, x) for l, x in zip(lags, dists) if 0 < l < 99]
xs = sorted(x for l, x in late)
print('NOT already agreeing at touch: %d episodes; lag median %.1f min; sigma moved toward trade direction while waiting: median %.2f, p25 %.2f, p75 %.2f, max %.2f; share price ran further (>0): %.0f%%' % (
    len(late), statistics.median(l for l, x in late), statistics.median(xs), statistics.quantiles(xs, n=4)[0], statistics.quantiles(xs, n=4)[2], max(xs), 100*sum(1 for x in xs if x > 0)/len(xs)))
