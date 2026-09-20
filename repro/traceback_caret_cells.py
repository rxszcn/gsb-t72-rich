import io, os, subprocess, sys
from rich.traceback import Traceback
from rich.console import Console
from rich.cells import cell_len, split_graphemes

def char_at_cell(line, col):
    spans, _ = split_graphemes(line)
    acc = 0
    for s, e, w in spans:
        if acc + w > col:
            return line[s:e]
        acc += w
    return "<past end>"

FILES = {
    "tab_demo.py":  "def f():\n\treturn (\n",
    "cjk_demo.py":  'def g():\n    你好世界 = [1, 2\n',
    "ascii_demo.py": "def h():\n    return [1, 2\n",
}
os.makedirs("/tmp/rc9", exist_ok=True)
for fn, src in FILES.items():
    open("/tmp/rc9/" + fn, "w", encoding="utf-8").write(src)

for fn, src in FILES.items():
    r = subprocess.run([sys.executable, "/tmp/rc9/" + fn], capture_output=True, text=True)
    ref = [l for l in r.stderr.split("\n") if "^" in l or "File" in l]
    err = None
    try:
        compile(src, "/tmp/rc9/" + fn, "exec")
    except SyntaxError as e:
        err = e
    tb = Traceback.from_exception(type(err), err, err.__traceback__)
    c = Console(file=io.StringIO(), width=80, color_system=None)
    c.print(tb)
    lines = [l.rstrip() for l in c.file.getvalue().split("\n")]
    ci = next(i for i, l in enumerate(lines) if "▲" in l)
    src_line, caret_line = lines[ci - 1], lines[ci]
    caret_col = caret_line.index("▲")
    raw = (err.text or "").rstrip("\n")
    target = max(0, (err.offset or 1) - 1)
    want = raw[target:target + 1]
    # cell column of the offending char within the rendered source line
    lead = 2  # panel border + padding
    want_col = lead + cell_len(raw[:target].expandtabs(8)) + (1 if want == "\t" else 0)
    got_char = char_at_cell(src_line, caret_col)
    print("== %-13s python offset=%r line=%r" % (fn, err.offset, raw))
    print("   cpython ref : %r" % (ref[-2:] if len(ref) > 1 else ref))
    print("   rich src    : %r" % src_line)
    print("   rich caret  : %r" % caret_line)
    print("   ▲ at cell %d -> marks %r   but the offending char is %r (expected cell %d)"
          % (caret_col, got_char, want, want_col))
    print("   ALIGNED" if want_col == caret_col else "   MISALIGNED by %+d cells" % (want_col - caret_col))
    print()

# err is still the ascii_demo SyntaxError here
import re
print("== underline control codes (truecolor render)")
tb2 = Traceback.from_exception(type(err), err, err.__traceback__)
c2 = Console(file=io.StringIO(), width=80, color_system="truecolor", force_terminal=True)
c2.print(tb2)
codes = sorted(set(re.findall(r"\x1b\[([0-9;]+)m", c2.file.getvalue())))
print("   SGR codes seen:", codes)
print("   underline (4m) present:", any("4" in x.split(";") for x in codes))

