"""One-off patch: add the better-trade panel (BETTER-RULES.md) to scratch/page.html and build_page.py."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "page.html")
s = open(p, encoding="utf-8").read()
assert "#bt{" not in s, "already patched"

css = """
/* ---------------- the better-trade panel (BETTER-RULES.md) ---------------- */
#bt{position:fixed;top:64px;right:424px;width:372px;background:var(--panel);border:1px solid #d6d3cc;border-radius:8px;
    box-shadow:0 6px 24px rgba(40,36,30,.12);z-index:9;font-size:12.5px;overflow:hidden}
#bt .bh{display:flex;align-items:center;gap:8px;padding:6px 8px 6px 10px;background:#fbfaf7;border-bottom:1px solid var(--line);color:var(--mute);font-size:12px}
#bt .bh b{color:var(--ink)} #bt .bh .one{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--ink)}
#bt .bh button{padding:0 7px;font-size:13px;line-height:20px}
#bt .dr{font-size:10.5px;padding:0 6px;border:1px solid var(--line);border-radius:8px}
#bt.min .bb{display:none}
#bt .ck{padding:8px 12px;font-size:13.5px;border-bottom:1px solid var(--line)}
#bt .ck.AGAINST,#bt .ck.BROKEN{background:#fdecea;color:#8c1d17} #bt .ck.AGREES{background:var(--hold-bg);color:var(--hold)}
#bt .ck.UNCLEAR,#bt .ck.COULD{background:var(--blind-bg);color:var(--blind)}
#bt .ln{padding:6px 12px;border-bottom:1px solid #f0eee9}
#bt .ln .k{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);display:block}
#bt .ln .w{font-weight:700} #bt .ln .f{color:var(--mute);font-size:11.5px;display:block}
#bt .ix{display:grid;grid-template-columns:78px 1fr;gap:2px 8px;padding:6px 12px;border-bottom:1px solid #f0eee9}
#bt .ix .n{font-weight:600} #bt .ix .d{font-size:12px} #bt .ix .d.cl{font-weight:700}
#bt .ft{padding:5px 12px 7px;color:var(--faint);font-size:11px}
</style>"""
s = s.replace("</style>", css, 1)

html = """<div id="bt" class="min">
  <div class="bh"><b>Better trade</b><span class="dr">DRAFT</span><span class="one" id="btone"></span><button id="btt" title="open / collapse">+</button></div>
  <div class="bb" id="btb"></div>
</div>

<script>/*BETTER*/</script>
"""
s = s.replace("<script>/*VERDICT*/</script>", html + "<script>/*VERDICT*/</script>", 1)

ctl = ('      <label title="RULES 9.6: positioning alone no longer folds; needs CVD / prints against, or the line (implies 9.4)">'
       '<input type="checkbox" class="var" value="merged"> 9.6 merged (in-sample)</label>')
assert ctl in s
s = s.replace(ctl, ctl + """
      <label title="BETTER-RULES 11.1: the day word from the price rows, OI counted as a fact"><input type="checkbox" id="btprice"> B-11.1 price-led day word</label>
      <label title="show the better-trade read on its own, as when she is flat"><input type="checkbox" id="btflat"> I am flat</label>""")

js = r"""
// ---------------------------------------------------------------- the better-trade panel
let btOpen = null;
function daysOf(day) { return { NIFTY: DAYS[`NIFTY_${day}`], BANKNIFTY: DAYS[`BANKNIFTY_${day}`], SENSEX: DAYS[`SENSEX_${day}`] }; }
function paintBT(v) {
  const flat = $("#btflat").checked, t = cur.t, V = $("#btprice").checked ? { price: true } : null;
  const R = BT.read(daysOf(t.day), v.t, flat ? null : { idx: t.idx, side: t.side, role: t.role }, V);
  const entryFold = !flat && cur.reads[0] && cur.reads[0].word === "FOLD";
  let ck = "", cw = "", one;
  if (!flat) {
    const c = R.check || { word: "COULD NOT CHECK", why: "" };
    cw = entryFold ? "BROKEN" : c.word.split(" ")[0];
    ck = `<div class="ck ${cw}">${entryFold ? `<b>You entered into a broken setup.</b> The window read FOLD at your entry minute (${esc(cur.reads[0].line)}). ` : ""}<b>Your trade vs today: ${esc(c.word)}.</b> ${esc(c.why)}</div>`;
    one = entryFold ? "you entered into a broken setup" : c.word === "AGAINST" ? "your trade is against today's read"
        : c.word === "AGREES" ? "your trade agrees with today's read" : "today is not clear on your index";
  } else one = R.best ? `best: ${R.best.text}` : "no trade is clean right now";
  const rows = R.reads.map((r) => `<span class="n">${r.idx}</span><span class="d${R.cleanest.idx === r.idx ? " cl" : ""}">${r.blind ? esc(r.blind)
      : `${esc(r.word)}${r.changing ? " (changing)" : ""} · ${esc(r.side.text)}${r.day !== "NEITHER" ? ` · ${r.for.length} for · ${r.against.length} against` : ""}`}</span>`).join("");
  const mine = R.reads.find((r) => r.idx === t.idx) || R.reads[0];
  const facts = (r) => r.blind ? "" : [...r.for.map((x) => "● " + x), ...r.against.map((x) => "✕ " + x), ...r.cant.map((x) => "? " + x)].map(esc).join("<br>");
  const cl = R.reads.find((r) => r.idx === R.cleanest.idx);
  $("#btb").innerHTML = ck +
    `<div class="ix">${rows}</div>` +
    `<div class="ln"><span class="k">the day, ${esc(mine.idx)}</span>${mine.blind ? esc(mine.blind) : `<span class="w">${esc(mine.word)}</span> — ${esc(mine.why)}<span class="f">${facts(mine)}</span>`}</div>` +
    `<div class="ln"><span class="k">cleanest index</span><span class="w">${esc(R.cleanest.text)}</span>${cl && cl.idx !== mine.idx ? `<span class="f">${facts(cl)}</span>` : ""}` +
    `${cl && cl.idx === "BANKNIFTY" ? `<span class="f">context: BANKNIFTY trends and inverts reversion tests (research §3); the fade gate caps it at soft</span>` : ""}</div>` +
    `<div class="ln"><span class="k">the engine's trade, ${esc(mine.idx)}</span>${esc(mine.engine ? mine.engine.text : "—")}</div>` +
    `<div class="ln"><span class="k">best · second best</span><span class="w">${esc(R.bestText)}</span><span class="f">second: ${esc(R.secondText)}</span></div>` +
    `<div class="ft">counts of facts, never odds · advisory · no size, no strike, no price · ${V ? "B-11.1 proposal ON (post-data)" : "the draft as written before replay"} · [I] REGIME / STRONG / CVD · [M] fronts, folds, premium</div>`;
  $("#btone").textContent = one;
  const auto = !flat && (cw === "AGAINST" || cw === "BROKEN");
  const open = btOpen == null ? (flat || auto) : btOpen;
  $("#bt").classList.toggle("min", !open); $("#btt").textContent = open ? "–" : "+";
}
"""
marker = "// ---------------------------------------------------------------- the page around it"
assert marker in s
s = s.replace(marker, js + "\n" + marker, 1)

a = """  const v = cur.reads[cur.i];
  paint(v, playing);"""
assert a in s
s = s.replace(a, a + """
  try { paintBT(v); } catch (e) { $("#btb").textContent = "could not check — " + e.message; }""")
a = "  cur = { t, d, reads, i: 0, variants };"
assert a in s
s = s.replace(a, a + " btOpen = null;")
a = '  $("#bplay").onclick = play;'
assert a in s
s = s.replace(a, a + """
  $("#btt").onclick = () => { btOpen = $("#bt").classList.contains("min"); if (cur) seek(cur.i); };
  for (const id of ["#btprice", "#btflat"]) $(id).addEventListener("change", () => { btOpen = null; if (cur) seek(cur.i); });""")
open(p, "w", encoding="utf-8").write(s)

p = os.path.join(HERE, "build_page.py")
b = open(p, encoding="utf-8").read()
if "better.js" not in b:
    b = b.replace('js = open(os.path.join(HERE, "..", "verdict.js"), encoding="utf-8").read()',
                  'js = open(os.path.join(HERE, "..", "verdict.js"), encoding="utf-8").read()\n'
                  'bt = open(os.path.join(HERE, "..", "better.js"), encoding="utf-8").read()')
    b = b.replace('page = page.replace("<script>/*VERDICT*/</script>", "<script>\\n" + js + "\\n</script>")',
                  'page = page.replace("<script>/*VERDICT*/</script>", "<script>\\n" + js + "\\n</script>")\n'
                  'page = page.replace("<script>/*BETTER*/</script>", "<script>\\n" + bt + "\\n</script>")')
    assert "better.js" in b and "/*BETTER*/" in b
    open(p, "w", encoding="utf-8").write(b)
print("patched")
