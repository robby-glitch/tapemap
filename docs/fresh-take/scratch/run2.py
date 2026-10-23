from rules2 import *
import sys

idx, day = sys.argv[1], sys.argv[2]
step = int(sys.argv[3]) if len(sys.argv) > 3 else 15
d = Day(idx, day)
rl = ruler_for(idx, day)
print('ruler', rl)
for T in range(9*3600+20*60, 15*3600+1, step*60):
    r = read(d, T, rl)
    if r['regime'] == 'WAIT':
        print(fmt(T), 'WAIT')
        continue
    print(fmt(T), '%-8s %-2s %-8s%s F %.0f z %+.1f cr %s used %s | CE30 %+.0fL PE30 %+.0fL wr %s | d15 %+.0f fl15 %s dp15 %s | moved %s stop %s' % (
        r['regime'], {1: 'UP', -1: 'DN', 0: ''}[r['dir']], r['phase'], ' FLIP' if r['flip'] else '     ', r['F'], r['z'], r['cross'],
        ('%.2f' % r['used']) if r['used'] else '-', r['ce30']/1e5, r['pe30']/1e5, r['wr'], r['d15'], r['fl15'],
        ('%.0f' % r['dp15']) if r['dp15'] is not None else '-', ('%.2f' % r['moved30']) if 'moved30' in r else '-', r.get('stop')))
