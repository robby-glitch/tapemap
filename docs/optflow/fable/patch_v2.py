"""Derives mockup-v2.tpl.html from mockup.tpl.html (Round 2: expression cells, 9 strikes, firm labels, 12 px, no %,
Float 440 mode) and teaches make_mockup.py the template name. Run from this folder once; kept for the record."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(HERE, "mockup.tpl.html"), encoding="utf-8").read()


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, b)


rep('<title>Option flow × OI · 3 Nov 2026</title>', '<title>Option flow × OI v2 · 3 Nov 2026</title>')
rep('.chip { background:var(--chip); border-radius:999px; padding:2px 9px; font-size:12.5px; white-space:nowrap; }',
    '.chip { background:var(--chip); border-radius:999px; padding:2px 9px; font-size:12.5px; white-space:nowrap; }\n'
    '  .expr { display:grid; grid-template-columns:auto 1fr; gap:2px 10px; font-size:13px; margin-top:6px; }\n'
    '  .expr b { color:var(--mute); font-weight:600; }')
rep('.next { font-size:12px;', '.next { font-size:12.5px;')
rep('.lhead { display:grid; grid-template-columns: 1fr 86px 1fr; font-size:11.5px;', '.lhead { display:grid; grid-template-columns: 1fr 96px 1fr; font-size:12px;')
rep('.row { display:grid; grid-template-columns: 1fr 86px 1fr; align-items:center; height:34px;', '.row { display:grid; grid-template-columns: 1fr 96px 1fr; align-items:center; height:36px;')
rep('.k small { display:block; font-weight:400; color:var(--mute); font-size:10.5px; letter-spacing:.2px; }', '.k small { display:block; font-weight:400; color:var(--mute); font-size:12px; letter-spacing:.2px; }')
rep('.lab { font-size:11px;', '.lab { font-size:12px;')
rep('.press::after { content:"▶"; position:absolute; font-size:9px;', '.press::after { content:"▶"; position:absolute; font-size:12px;')
rep('.spot span { position:absolute; left:50%; transform:translate(-50%,-55%); background:var(--spot); color:#fff; font-size:11px;', '.spot span { position:absolute; left:50%; transform:translate(-50%,-55%); background:var(--spot); color:#fff; font-size:12px;')
rep('.legend { display:flex; gap:12px; flex-wrap:wrap; font-size:11.5px;', '.legend { display:flex; gap:12px; flex-wrap:wrap; font-size:12px;')
rep('.cell { border:1px solid var(--line); border-radius:6px; padding:4px 2px; text-align:center; font-size:11px; line-height:1.2; }', '.cell { border:1px solid var(--line); border-radius:6px; padding:4px 2px; text-align:center; font-size:12px; line-height:1.2; }')
rep('.log td { font-size:12px; }', '.log td { font-size:12.5px; }')
rep('.health { font-size:12px;', '.health { font-size:12.5px;')
rep('kbd { font:11px monospace;', 'kbd { font:12px monospace;')
rep('.lab.off { color:var(--mute); }',
    '.lab.off { color:var(--mute); }\n  .lab.soft { color:var(--mute); }\n'
    '  body.float .grid { grid-template-columns: 440px; }\n  body.float .stack > .panel:not(.keep) { display:none; }\n'
    '  body.float .answer { max-width:440px; grid-template-columns:1fr; }\n  body.float .jarvis { text-align:left; }\n'
    '  body.float .row { height:30px; }\n  body.float .legend { display:none; }\n  body.float .nums span:nth-child(n+4) { display:none; }')
rep('<button class="ctl" id="hind">what came next: off</button>', '<button class="ctl" id="hind">what came next: off</button>\n  <button class="ctl" id="mode">Float 440</button>')
rep('    <div class="word" id="word">—</div>\n    <div class="chips" id="chips"></div>',
    '    <div class="word" id="word">—</div>\n    <div class="chips" id="chips"></div>\n    <div class="expr" id="expr"></div>')
rep('    <div class="panel">\n      <h2>Pichle 30 min · the word every 3-min close · fut change</h2>',
    '    <div class="panel keep">\n      <h2>Pichle 30 min · the word every 3-min close · fut change</h2>')
rep('<div class="panel health" id="health"></div>', '<div class="panel health keep" id="health"></div>')
rep('  function d() { return DAY[idx]; }', '''  var floatMode = false;
  function expression(w, cap, fl) {
    var ck = cap && cap.top ? fmt(cap.top[0]) + "s" : "the cap", fk = fl && fl.top ? fmt(fl.top[0]) + "s" : "the floor";
    switch (w) {
      case "UP FUEL": return ["CE · fuel = call writers " + (cap && cap.w === "COVER" ? "covering " : "not pressing ") + ck, fl && fl.w === "WRITE" ? "sell PE · put writers pressing " + fk + " behind you" : "sell PE only with a wall behind · floor " + fk + ": " + (fl ? EN[fl.w] : "?")];
      case "LID BREAKING": return ["CE · the cap " + ck + " is being bought back", "no fresh CE sale here · wait for the floor"];
      case "FLOOR UP": return ["no fuel yet · floor rising, cap quiet", "sell PE · writers with you at " + fk];
      case "UP BUYERS": return ["CE · buyers chasing, writers posting (fades more)", "sell PE only with a wall behind · writers posting, not pressing"];
      case "DOWN FUEL": return ["PE · fuel = put writers " + (fl && fl.w === "COVER" ? "covering " : "not pressing ") + fk, cap && cap.w === "WRITE" ? "sell CE · call writers pressing " + ck + " behind you" : "sell CE only with a wall behind · cap " + ck + ": " + (cap ? EN[cap.w] : "?")];
      case "LID": return ["no fresh CE under the lid " + ck, "sell CE at " + ck + " · writers with you"];
      case "FLOOR BREAKING": return ["PE · the floor " + fk + " is being bought back", "no fresh PE sale here · wait for the cap"];
      case "DOWN BUYERS": return ["PE · buyers chasing, writers posting (fades more)", "sell CE only with a wall behind"];
      case "PIN": return ["no trade · both sides writing " + fk + "–" + ck, "the seller's afternoon · both sides writing " + fk + "–" + ck];
      case "SQUEEZE": return ["direction not clear · both walls breaking", "refused · never sell into a squeeze"];
      case "BUYERS OUT": return ["no trade · buyers leaving both sides (theta)", "nothing to defend · premium bleeding"];
      case "OI?": return ["could not check · chain stale", "refused · a writer does not sell a wall she cannot see"];
      default: return ["no read", "no read"];
    }
  }
  function d() { return DAY[idx]; }''')
rep('    $("chips").innerHTML = ch;', '''    $("chips").innerHTML = ch;
    var ex = expression(w, cap, fl);
    $("expr").innerHTML = "<b>for a buyer</b><span>" + ex[0] + "</span><b>for a seller</b><span>" + ex[1] + "</span>";''')
rep('    var ks = []; for (var k = atm + 6 * step; k >= atm - 6 * step; k -= step) ks.push(k);',
    '    var n = floatMode ? 2 : 4, ks = []; for (var k = atm + n * step; k >= atm - n * step; k -= step) ks.push(k);')
rep('        var q = kidx(k, sd), oi = q >= 0 ? x.oi[q][i] : null, who = q >= 0 ? x.who[i][q] : null, doi = q >= 0 ? x.doi[i][q] : null, big = q >= 0 ? x.bigc[i][q] : 0;',
    '        var q = kidx(k, sd), oi = q >= 0 ? x.oi[q][i] : null, who = q >= 0 ? x.who[i][q] : null, doi = q >= 0 ? x.doi[i][q] : null, big = q >= 0 ? x.bigc[i][q] : 0, firm = q >= 0 && x.firm[i] ? x.firm[i][q] : 0;')
rep('''        if (q < 0) inner = '<span class="lab off">no footprint</span><div class="track"></div>';
        else if (oi == null) inner = '<span class="lab off">OI?</span><div class="track"></div>';''',
    '''        if (q < 0 || oi == null) inner = '<span class="lab"></span><div class="track"></div>';''')
rep('''          var lab = act ? "<b>" + HI[who] + " " + L(doi) + "</b>" : (who === "M" && doi != null && Math.abs(doi) >= x.oi_move ? "dono taraf " + L(doi) : "");
          if (big) lab += (lab ? " · " : "") + "BADA " + klots(big, x);
          if (lab && role === "ITM") lab += " <small>ITM</small>";''',
    '''          var lab = act ? (firm ? "<b>" + HI[who] + " " + L(doi) + "</b>" : HI[who] + "? " + L(doi)) : "";
          if (big && act) lab += " · BADA " + klots(big, x).replace(" lots", "");
          if (lab && role === "ITM") lab += " · ITM";''')
rep('''          var label = '<span class="lab' + (act ? "" : " off") + '">' + lab + "</span>";''',
    '''          var label = '<span class="lab' + (act && firm ? "" : " soft") + '">' + lab + "</span>";''')
rep('    var rowH = 34, topK = ks[0];', '    var rowH = floatMode ? 30 : 36, topK = ks[0];')
rep('''      if (r >= 1.25) rows.push({ k: ks, built: built, who: "writers", avg: lp[1], now: lp[0], pct: Math.round((r - 1) * 100), sev: r });
      else if (r <= 0.75) rows.push({ k: ks, built: built, who: "buyers", avg: lp[1], now: lp[0], pct: Math.round((1 - r) * 100), sev: 1 / r });''',
    '''      if (r >= 1.25) rows.push({ k: ks, built: built, who: "writers", avg: lp[1], now: lp[0] });
      else if (r <= 0.75) rows.push({ k: ks, built: built, who: "buyers", avg: lp[1], now: lp[0] });''')
rep('''    if (!rows.length) { $("trap").innerHTML = '<tr><td class="empty">no one under water by 25 % yet (OI built today ≥ ' + L(4 * x.oi_move, 1) + ")</td></tr>"; return; }''',
    '''    if (!rows.length) { $("trap").innerHTML = '<tr><td class="empty">no one under water by a quarter of their price yet (OI built today ≥ ' + L(4 * x.oi_move, 1).replace("+", "") + ")</td></tr>"; return; }''')
rep('''      return "<tr><td><b>" + fmt(r.k[0]) + " " + r.k[1] + "</b></td><td>" + r.who + " " + L(r.built, 0) + "</td><td>" + (r.who === "writers" ? "wrote" : "paid") + " ~" + r.avg.toFixed(1) + " → now " + r.now.toFixed(1) + "</td><td class='ans " + (r.who === "writers" ? "dn" : "g") + "'>" + (r.who === "writers" ? "phanse " + r.pct + "%" : "doobe " + r.pct + "%") + "</td><td class='t'>" + fuel + "</td></tr>";''',
    '''      var ag = r.who === "writers" ? r.now - r.avg : r.avg - r.now;
      return "<tr><td><b>" + fmt(r.k[0]) + " " + r.k[1] + "</b></td><td>" + r.who + " " + L(r.built, 0) + "</td><td>" + (r.who === "writers" ? "wrote" : "paid") + " ~" + r.avg.toFixed(1) + " → now " + r.now.toFixed(1) + "</td><td class='ans " + (r.who === "writers" ? "dn" : "g") + "'>" + (r.who === "writers" ? "phanse" : "doobe") + " " + ag.toFixed(1) + " against them</td><td class='t'>" + fuel + "</td></tr>";''')
rep("<h2>Phanse hue · who is under water (OI built today vs the day's avg price)</h2>",
    "<h2>Phanse hue · who is under water (OI built today vs the day's avg price, in premium points)</h2>")
rep('  $("bN").addEventListener("click", function () {',
    '''  $("mode").addEventListener("click", function () { floatMode = !floatMode; document.body.classList.toggle("float", floatMode); $("mode").textContent = floatMode ? "Page" : "Float 440"; $("mode").classList.toggle("on", floatMode); lastI = -1; render(); });
  $("bN").addEventListener("click", function () {''')
rep('      <span>last 3 min · <kbd>←</kbd> <kbd>→</kbd> <kbd>space</kbd></span>',
    '      <span>faint = label not firm (OI lag) · last 3 min · <kbd>←</kbd> <kbd>→</kbd> <kbd>space</kbd></span>')
open(os.path.join(HERE, "mockup-v2.tpl.html"), "w", encoding="utf-8").write(s)
m = open(os.path.join(HERE, "make_mockup.py"), encoding="utf-8").read()
if "sys.argv" not in m:
    m = m.replace('tpl = open(os.path.join(HERE, "mockup.tpl.html"), encoding="utf-8").read()',
                  'import sys\nname = sys.argv[1] if len(sys.argv) > 1 else "mockup"          # mockup | mockup-v2\n'
                  'tpl = open(os.path.join(HERE, name + ".tpl.html"), encoding="utf-8").read()')
    m = m.replace('p = os.path.join(HERE, "mockup.html")', 'p = os.path.join(HERE, name + ".html")')
    open(os.path.join(HERE, "make_mockup.py"), "w", encoding="utf-8").write(m)
print("v2 template written")
