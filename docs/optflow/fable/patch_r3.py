"""Round 3 patches: (1) study.held() says its first word at a close, never mid-bar; (2) mockup-v2 gets both days
(days.json) with a day switch, and arrows only on FUEL words; (3) make_mockup.py embeds days.json for v2.
Run from this folder AFTER patch_v2.py:  python -I -X utf8 patch_r3.py"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for a, b in pairs:
        if b in s and a not in s:
            continue                       # already applied
        assert s.count(a) == 1, (path, a[:60], s.count(a))
        s = s.replace(a, b)
    open(path, "w", encoding="utf-8").write(s)


# 1. study.py: the first word at a close only
patch(os.path.join(HERE, "study.py"), [(
    '        elif w is None or w == "OI?":\n            w, ln, pend = cand, cl, None\n        elif (m - 555) % 3 == 2:',
    '        elif (w is None or w == "OI?") and (m - 555) % 3 == 2:   # the first word is said at a close, never mid-bar (R3)\n'
    '            w, ln, pend = cand, cl, None\n        elif w is None or w == "OI?":\n            pass\n        elif (m - 555) % 3 == 2:')])

# 2. mockup-v2.tpl.html (the output of patch_v2.py): two days, a day switch, FUEL-only arrows
T = os.path.join(HERE, "mockup-v2.tpl.html")
patch(T, [
    ('<script type="application/json" id="day">__DAY_JSON__</script>', '<script type="application/json" id="day">__DAYS_JSON__</script>'),
    ('  var DAY = JSON.parse(document.getElementById("day").textContent);',
     '  var DAYS = JSON.parse(document.getElementById("day").textContent), day = "2026-11-03", DAY = DAYS[day];'),
    ('<div class="seg"><button id="bN" class="on">NIFTY</button><button id="bS">SENSEX</button></div>',
     '<div class="seg"><button id="bN" class="on">NIFTY</button><button id="bS">SENSEX</button></div>\n'
     '  <div class="seg"><button id="d2">Mon 2 Nov</button><button id="d3" class="on">Tue 3 Nov</button></div>'),
    ('<span style="color:var(--mute)">Tue 3 Nov 2026 · NIFTY 03 NOV (expiry today) · SENSEX 05 NOV</span>',
     '<span style="color:var(--mute)" id="sub">Tue 3 Nov 2026 · NIFTY 03 NOV (expiry today) · SENSEX 05 NOV</span>'),
    ('  $("bN").addEventListener("click", function () {',
     '  function setDay(dd) { day = dd; DAY = DAYS[day]; $("d2").classList.toggle("on", dd === "2026-11-02"); $("d3").classList.toggle("on", dd === "2026-11-03");\n'
     '    $("sub").textContent = dd === "2026-11-02" ? "Mon 2 Nov 2026 · NIFTY 03 NOV (1 DTE) · SENSEX 05 NOV (3 DTE)" : "Tue 3 Nov 2026 · NIFTY 03 NOV (expiry today) · SENSEX 05 NOV";\n'
     '    $("rng").max = d().mins.length - 1; lastI = -1; go(Math.min(i, d().mins.length - 1)); }\n'
     '  $("d2").addEventListener("click", function () { setDay("2026-11-02"); });\n'
     '  $("d3").addEventListener("click", function () { setDay("2026-11-03"); });\n'
     '  $("bN").addEventListener("click", function () {'),
    ('"LID BREAKING": ["▲ CAP BREAKING", "up",', '"LID BREAKING": ["CAP BREAKING", "flat",'),
    ('"FLOOR UP": ["▲ FLOOR RISING", "up",', '"FLOOR UP": ["FLOOR RISING", "flat",'),
    ('"UP BUYERS": ["▲ UP · buyers", "up",', '"UP BUYERS": ["BUYERS · calls", "flat",'),
    ('"LID": ["▼ LID", "dn",', '"LID": ["LID", "flat",'),
    ('"FLOOR BREAKING": ["▼ FLOOR BREAKING", "dn",', '"FLOOR BREAKING": ["FLOOR BREAKING", "flat",'),
    ('"DOWN BUYERS": ["▼ DOWN · buyers", "dn",', '"DOWN BUYERS": ["BUYERS · puts", "flat",'),
])

# 3. make_mockup.py: v2 embeds days.json
patch(os.path.join(HERE, "make_mockup.py"), [
    ('data = open(os.path.join(HERE, "day.json"), encoding="utf-8").read()',
     'data = open(os.path.join(HERE, "days.json" if name == "mockup-v2" else "day.json"), encoding="utf-8").read()'),
    ('assert "__DAY_JSON__" in tpl', 'tag = "__DAYS_JSON__" if name == "mockup-v2" else "__DAY_JSON__"\nassert tag in tpl'),
    ('out = tpl.replace("__DAY_JSON__", data)', 'out = tpl.replace(tag, data)'),
])
print("round 3 patches applied")
