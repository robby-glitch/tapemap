"""Cache every replayable NIFTY day's Jarvis frame (fill=True) for the best-trade atlas. Read-only on data/."""
import tempfile
import json
import os
import sys
import time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import jarvis  # noqa: E402

OUT = os.path.join(tempfile.gettempdir(), "jarvis_atlas", "frames")
os.makedirs(OUT, exist_ok=True)
idx = sys.argv[1] if len(sys.argv) > 1 else "NIFTY"
for day in jarvis.days()[idx]:
    p = os.path.join(OUT, f"{idx}_{day}.json")
    if os.path.exists(p):
        continue
    t = time.time()
    try:
        d = jarvis.build(day, idx, None, fill=True)
    except Exception as e:
        print(day, "ERROR", type(e).__name__, e, flush=True)
        continue
    if not d.get("ok"):
        print(day, "NO", d.get("why"), flush=True)
        continue
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    print(day, len(d["mins"]), d["mins"][0], d["mins"][-1], f"{time.time() - t:.0f}s", flush=True)
print("done", flush=True)
