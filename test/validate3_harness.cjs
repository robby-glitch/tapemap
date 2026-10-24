// validate3_harness.cjs -- runs the Validate face's engine (ui-v2/public/validate2/engine.js) in node for test_validate3.py.
// stdin: [{fn, args}] where fn is a key of Engine.votes, or "validate" with {payload, decode: {idx: block}, call: [...]}.
// stdout: [{ok, out | err}] per call. The engine is a browser script; it is loaded as-is into a vm context.
const fs = require("fs"), vm = require("vm"), path = require("path");
const ctx = {}; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "ui-v2", "public", "validate2", "engine.js"), "utf8") + ";this.Engine = Engine;", ctx);
const E = ctx.Engine, R31_DEFAULT = E.R31.ON;                         // §1q: the engine as served (signed: ON)
const calls = JSON.parse(fs.readFileSync(0, "utf8"));
const out = calls.map(c => {
  try {
    E.R31.ON = !!c.r31;                                                  // rev 3 unless a call asks for rev 3.1 (§1q)
    if (c.fn === "validate") {
      E.load(c.payload);
      for (const [i, b] of Object.entries(c.decode || {})) E.setDecode(i, b);
      const v = E.validate(...c.call);
      return { ok: true, out: { rev: v.rev, word: v.word, counts: v.counts, flowSrc: v.flowSrc || null, checks: (v.checks || []).map(q => ({ name: q.name, st: q.st, cell: q.cell, tip: q.tip })), levels: (v.levels || []).map(l => ({ name: l.name, cond: l.cond })) } };
    }
    if (c.fn === "REV") return { ok: true, out: E.REV };
    if (c.fn === "R31_DEFAULT") return { ok: true, out: R31_DEFAULT };
    return { ok: true, out: E.votes[c.fn](...c.args) ?? null };
  } catch (e) { return { ok: false, err: String(e && e.stack || e) }; }
});
process.stdout.write(JSON.stringify(out));
