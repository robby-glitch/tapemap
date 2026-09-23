"""Rebuild ../fresh-screen.html from a fresh read-only snapshot.
    python snap.py && python build.py      (server must be running; GET only)"""
import pathlib
here = pathlib.Path(__file__).parent
t = (here / 'template.html').read_text(encoding='utf-8')
d = (here / 'snapshot.json').read_text(encoding='utf-8').replace('</', '<' + chr(92) + '/')
out = here.parent / 'fresh-screen.html'
out.write_text(t.replace('/*DATA*/', d, 1), encoding='utf-8')
print(out, out.stat().st_size)
