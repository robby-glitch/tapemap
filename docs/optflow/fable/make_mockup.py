"""Embeds day.json into mockup.html. Run from tapemap/:  python -I -X utf8 docs/optflow/fable/make_mockup.py
(day.json comes from study.py --json). The page is light only, no external files, scripts in an IIFE."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
name = sys.argv[1] if len(sys.argv) > 1 else "mockup"          # mockup | mockup-v2
data = open(os.path.join(HERE, "days.json" if name == "mockup-v2" else "day.json"), encoding="utf-8").read()
tpl = open(os.path.join(HERE, name + ".tpl.html"), encoding="utf-8").read()
tag = "__DAYS_JSON__" if name == "mockup-v2" else "__DAY_JSON__"
assert tag in tpl
# JSON inside a <script type=application/json>: the only thing that can break it is "</script"
data = data.replace("</", "<\\/")
out = tpl.replace(tag, data)
p = os.path.join(HERE, name + ".html")
open(p, "w", encoding="utf-8").write(out)
print("wrote", p, os.path.getsize(p) // 1024, "KB")
