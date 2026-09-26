# Rev d's §D tables, generated from expr/revd/*.json (after rev d's run) into expr/revd/tables_d.md.
# The prose around them is written by hand after reading these. Counts and rows only; no word crossed with an outcome.
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
J = lambda p: json.load(open(os.path.join(HERE, p), encoding="utf-8"))
S, Sc, E, G = J("revd/stability.json"), J("revc/stability.json"), J("revd/entries.json"), J("revd/grid.json")
RF, MV, SEL = J("revd/refusals.json"), J("revd/moved_from_revc.json"), J("revd/seller_0924.json")
T = "{:,}".format
g = lambda tb, k: tb.get(k, 0)
out = []
P = out.append

# D.1 per index-day
P("### D.1 table\n")
P("| index-day | dir | BUY (count · ref) | LEANS BUY (count · ref; of which ties) | EITHER | LEANS SELL (count · ref) | SELL (count · ref) | STAND ASIDE (both · led) | changes · BUY↔SELL · buy-side↔sell-side | median run |")
P("|---|---|---|---|---|---|---|---|---|---|")
for r in S["per_index_day"]:
    if r["cad"] != "3m":
        continue
    tb = r["tab"]
    b = (g(tb, "BUY·count·"), g(tb, "BUY·refusal·"))
    lbt = g(tb, "LEANS BUY·refusal·tie")
    lb = (g(tb, "LEANS BUY·count·"), g(tb, "LEANS BUY·refusal·") + lbt)
    ls = (g(tb, "LEANS SELL·count·"), g(tb, "LEANS SELL·refusal·") + g(tb, "LEANS SELL·refusal·tie"))
    ss = (g(tb, "SELL·count·"), g(tb, "SELL·refusal·"))
    sa = (g(tb, "STAND ASIDE·refusal·both"), g(tb, "STAND ASIDE·refusal·led"))
    day = r["day"] if r["d"] == "UP" else ""
    P(f"| {day} | {r['d']} | {sum(b)} ({b[0]} · {b[1]}) | {sum(lb)} ({lb[0]} · {lb[1]}; {lbt}) | {g(tb, 'EITHER·count·')} "
      f"| {sum(ls)} ({ls[0]} · {ls[1]}) | {sum(ss)} ({ss[0]} · {ss[1]}) | {sum(sa)} ({sa[0]} · {sa[1]}) "
      f"| {r['changes']} · {r['strong_flips']} · {r['side_flips']} | {r['median_run_min']:g} min |")
t3, t1, c3, c1 = S["totals"]["3m"], S["totals"]["1m"], Sc["totals"]["3m"], Sc["totals"]["1m"]
P("\ntotals 3m words " + json.dumps(t3["words"]) + "\ntab " + json.dumps(t3["tab"], ensure_ascii=False))
P("totals 1m words " + json.dumps(t1["words"]) + "\ntab " + json.dumps(t1["tab"], ensure_ascii=False))
P("rev c 3m words " + json.dumps(c3["words"]))
P("\nmoved from rev c (3m closes): " + json.dumps(MV, ensure_ascii=False) + f" total {sum(MV.values())}")
P("\nrefusals per close: " + json.dumps(RF["refusals"]) + f" of {RF['N_closes']}")
P("behind refusal words: " + json.dumps(RF["behind_refusal_words"], ensure_ascii=False))

# D.2
P("\n### D.2 table\n")
P("| | read every minute | **read at the 3-minute close (registered)** | rev c at the 3-minute close |")
P("|---|---|---|---|")
def lean(t):
    w = t["words"]; dirn = sum(w.get(k, 0) for k in ("BUY", "LEANS BUY", "LEANS SELL", "SELL"))
    return f"{T(w.get('LEANS BUY', 0) + w.get('LEANS SELL', 0))} of {T(dirn)}"
P(f"| reads | {T(t1['reads'])} | {T(t3['reads'])} | {T(c3['reads'])} |")
P(f"| word changes, of transitions | {T(t1['changes'])} of {T(t1['trans'])} | **{T(t3['changes'])} of {T(t3['trans'])}** | {T(c3['changes'])} of {T(c3['trans'])} |")
P(f"| median life of a word | {t1['median_run_min']:g} minutes | **{t3['median_run_min']:g} minutes** | {c3['median_run_min']:g} minutes |")
P(f"| runs that last a single read | {T(t1['runs_of_one'])} of {T(t1['runs'])} | **{T(t3['runs_of_one'])} of {T(t3['runs'])}** | {T(c3['runs_of_one'])} of {T(c3['runs'])} |")
P(f"| direct BUY ↔ SELL flips | {t1['strong_flips']} | **{t3['strong_flips']}** | {c3['strong_flips']} |")
P(f"| buy-side ↔ sell-side flips | {t1['side_flips']} | **{t3['side_flips']}** | {c3['side_flips']} |")
P(f"| directional words that are LEANS | {lean(t1)} | **{lean(t3)}** | {lean(c3)} |")

# D.4 entries
P("\n### D.4 words\n")
P("| # | entry (read · close read) | dir | **word (rev d)** | lead · b–s | refused | since · was | rev c word, if different | the sold leg (ATM): rev 5 B's first FOLD, seller pts |")
P("|---|---|---|---|---|---|---|---|---|")
cnt = {}
f5 = lambda v: f"{v[0]} r{v[1]} {v[2]:+g}" if v and v[0] else "no fold to 15:29"
for n, x in enumerate(E, 1):
    if "why" in x:
        P(f"| {n} | 09-21 13:59 NIFTY 23300CE | UP | **could not check** — never frozen | | | | | |")
        cnt["could not check"] = cnt.get("could not check", 0) + 1
        continue
    day, hhmm, idx, leg = x["id"].split(" ")
    base = x["word"].split(" · ")[0]
    for p_ in ("LEANS BUY", "LEANS SELL", "BUY", "SELL", "STAND ASIDE", "EITHER"):
        if base.startswith(p_):
            base = p_; break
    cnt[base] = cnt.get(base, 0) + 1
    lead = "—" if x["lead"] is None else x["lead"]
    ref = ", ".join(x["ref"]) or "—"
    sw = f"since {x['since']}" + (f" · was {x['was']}" if x["was"] else "")
    wc = "" if x["word_c"] == x["word"] else x["word_c"]
    o = x.get("other") or {}
    fold = f"{o['side']} {o['k']:g} (rev c sold {x['sell_c']:g}): {f5(o['rev5'])}" if o and x.get("sell_c") else (f"{o['side']} {o['k']:g}: {f5(o['rev5'])}" if o else "—")
    P(f"| {n} | {day} {x['read']} · {x['close_read']} {idx} {leg} | {x['d']} | **{x['word']}** | {lead} · {x['nb']}–{x['ns']} | {ref} | {sw} | {wc} | {fold} |")
P("\nentry word counts: " + json.dumps(cnt))

P("\n### D.4 R-multiples and the writer word\n")
P("| # | BUY leg R +30 | SELL leg (ATM) R +30 | G | index 30-min move vs d | sold leg to 14:59 · to 15:29 (seller pts) | writer word (rev d) · 30 min · to 15:29 |")
P("|---|---|---|---|---|---|---|")
for n, x in enumerate(E, 1):
    if "why" in x:
        P(f"| {n} | | | | | could not check | |"); continue
    rm, w, o = x.get("rmult") or {}, x.get("writer") or {}, x.get("other") or {}
    br = rm.get("buy", {}).get("r", rm.get("buy", {}).get("why", ""))
    sr = rm.get("sell", {}).get("r", rm.get("sell", {}).get("why", ""))
    G_ = rm.get("G", "—")
    mv = rm.get("move") or [None, None]
    mvs = f"{mv[0]:+g} {mv[1]}" if mv[0] is not None else "—"
    ww = w.get("word") or "—"
    extra = []
    if w.get("word_no_cnc_clause") and w["word_no_cnc_clause"] != w.get("word"):
        extra.append(f"was {w['word_no_cnc_clause']} without rev d's clause ({', '.join(w['cnc'])})")
    if w.get("line_beyond_strike"):
        extra.append("line beyond strike")
    P(f"| {n} | {br} | {sr} | {G_} | {mvs} | {o.get('at_1459', '—')} · {o.get('close', '—')} | {ww} · {w.get('out30', '—')} · {w.get('out1529', '—')}{' · ' + ' · '.join(extra) if extra else ''} |")

# D.6
P("\n### D.6 seller 09-24 (her strikes as CE sales), rev 5 B\n")
by = {}
for s in SEL:
    by.setdefault(s["k"], []).append(s)
P("| sold call (entries) | rev 5 B's first FOLD (as built, and under rev d) | at 14:59 [M] | at 15:29 [M] |")
P("|---|---|---|---|")
for k in sorted(by, reverse=True):
    ss_ = by[k]; r = ss_[0]["rev5"]
    P(f"| {k:,} ({', '.join(x['trade'].split(' ')[1] for x in ss_)}) | {r[0]} rule {r[1]}, {r[2]} | {ss_[0]['CE_1459']} | {ss_[0]['CE_1529']} |")
P("\ngrid legs: " + json.dumps(G["legs"]))

# D.7
P("\n### D.7 grid\n")
P("units " + str(G["units"]) + " words " + json.dumps(G["words"], ensure_ascii=False))
P("tab " + json.dumps(G["tab"], ensure_ascii=False))
P("scored G " + str(G["scored_G"]) + " notscored " + json.dumps(G["notscored"]) + "\ntab_scored " + json.dumps(G["tab_scored"], ensure_ascii=False))
P("writer " + json.dumps(G["writer"], ensure_ascii=False))
open(os.path.join(HERE, "revd", "tables_d.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
