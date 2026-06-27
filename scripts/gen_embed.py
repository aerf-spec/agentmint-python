#!/usr/bin/env python3
# Generate a self-contained, AgentMint-branded HTML embed of the demo.
# Runs the demo chunks, converts their ANSI truecolor output to HTML spans
# using the AgentMint palette, and writes docs/demo_embed.html.
import contextlib
import html
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import demo
import chunks

# Strip pacing + screen clears so capture is instant and clean.
demo.pause = lambda *a, **k: None
chunks.pause = lambda *a, **k: None
demo.clear = lambda: None

COLORMAP = {
    "38;2;226;232;240": "fg",
    "38;2;148;163;184": "gray",
    "38;2;100;116;139": "dim",
    "38;2;59;130;246": "blue",
    "38;2;16;185;129": "green",
    "38;2;239;68;68": "red",
    "38;2;251;191;36": "yellow",
}
TOKEN = re.compile(r"\x1b\[([0-9;]*)m")


def ansi_to_html(text):
    out = []
    color = None
    bold = False
    pos = 0
    for m in TOKEN.finditer(text):
        chunk = text[pos:m.start()]
        if chunk:
            cls = []
            if color:
                cls.append(color)
            if bold:
                cls.append("b")
            esc = html.escape(chunk)
            out.append('<span class="%s">%s</span>' % (" ".join(cls), esc) if cls else esc)
        code = m.group(1)
        if code == "0":
            color, bold = None, False
        elif code == "1":
            bold = True
        elif code in COLORMAP:
            color = COLORMAP[code]
        pos = m.end()
    tail = text[pos:]
    if tail:
        out.append(html.escape(tail))
    return "".join(out)


def capture(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return ansi_to_html(buf.getvalue().rstrip("\n"))


# enforce first so verify/tamper have a fresh audit_pack.json
TABS = [
    ("wrong", "Without AgentMint", chunks.do_baseline),
    ("instrument", "Instrument", lambda: (chunks.do_plan(), chunks.do_wrapping())),
    ("right", "With AgentMint", chunks.do_enforce),
    ("verify", "Verify", chunks.do_verify),
    ("tamper", "Tamper", chunks.do_tamper),
]

# Run enforce up front to (re)write the pack used by verify/tamper.
with contextlib.redirect_stdout(io.StringIO()):
    chunks.do_enforce()

panels = []
buttons = []
for i, (key, label, fn) in enumerate(TABS):
    active = " active" if i == 0 else ""
    buttons.append('<button class="tab%s" data-tab="%s">%s</button>' % (active, key, label))
    body = capture(fn)
    panels.append('<pre class="term-body%s" id="panel-%s">%s</pre>' % (active, key, body))

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Local Demo | AgentMint</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#0B1120;--fg:#E2E8F0;--surface:#141E30;--border:#1E3A5F;--code-bg:#0D1117;--code-border:#21262d;--blue:#3B82F6;--green:#10B981;--red:#EF4444;--yellow:#FBBF24;--gray:#94A3B8;--dim:#64748B;}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:var(--fg);line-height:1.6;-webkit-font-smoothing:antialiased;}
.nav{padding:14px 20px;border-bottom:1px solid var(--border);background:rgba(11,17,32,.95);}
.nav-inner{max-width:980px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;}
.nav-brand{font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:var(--fg);text-decoration:none;}
.nav-brand span{color:var(--blue);}
.nav-link{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--gray);text-decoration:none;}
main{max-width:980px;margin:0 auto;padding:40px 20px 64px;}
h1{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:700;margin-bottom:8px;}
.sub{color:var(--gray);font-size:14px;margin-bottom:8px;}
.flow{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--blue);margin-bottom:28px;}
.tabs{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;}
.tab{font-family:'JetBrains Mono',monospace;font-size:12px;padding:8px 14px;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--gray);cursor:pointer;transition:.15s;}
.tab:hover{border-color:var(--blue);color:var(--fg);}
.tab.active{border-color:var(--blue);background:rgba(59,130,246,.12);color:var(--fg);}
.terminal{background:var(--code-bg);border:1px solid var(--code-border);border-radius:10px;overflow:hidden;}
.term-bar{display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid var(--code-border);}
.dot{width:11px;height:11px;border-radius:50%;}
.dot.r{background:#ff5f56;}.dot.y{background:#ffbd2e;}.dot.g{background:#27c93f;}
.term-title{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim);margin-left:6px;}
.term-body{display:none;font-family:'JetBrains Mono',monospace;font-size:12.5px;line-height:1.55;padding:18px 20px;white-space:pre;overflow-x:auto;color:var(--fg);}
.term-body.active{display:block;}
.legend{margin-top:18px;display:flex;flex-wrap:wrap;gap:16px;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--gray);}
.legend b{font-weight:600;}
.note{margin-top:18px;font-size:13px;color:var(--gray);line-height:1.7;}
.note code{font-family:'JetBrains Mono',monospace;background:var(--surface);padding:2px 6px;border-radius:4px;color:var(--fg);}
.footer{border-top:1px solid var(--border);padding:24px 0;text-align:center;color:var(--dim);font-size:12px;}
.fg{color:var(--fg);}.gray{color:var(--gray);}.dim{color:var(--dim);}.blue{color:var(--blue);}
.green{color:var(--green);}.red{color:var(--red);}.yellow{color:var(--yellow);}.b{font-weight:700;}
</style>
</head>
<body>
<nav class="nav"><div class="nav-inner">
  <a href="/" class="nav-brand">Agent<span>Mint</span></a>
  <a class="nav-link" href="https://github.com/aerf-spec/agentmint-python" target="_blank">GitHub</a>
</div></nav>
<main>
  <h1>AgentMint &mdash; Local Demo</h1>
  <p class="sub">Signed-plan gating for an AI agent's tool calls. Synthetic prior-auth scenario.</p>
  <p class="flow">flow: plan -&gt; gate -&gt; tools -&gt; receipts -&gt; verify</p>
  <div class="tabs">__BUTTONS__</div>
  <div class="terminal">
    <div class="term-bar"><span class="dot r"></span><span class="dot y"></span><span class="dot g"></span><span class="term-title">demo.py &middot; chunks.py</span></div>
    __PANELS__
  </div>
  <div class="legend">
    <span><b class="green">&#10003; ALLOW</b> matched signed scope</span>
    <span><b class="yellow">&#9208; CHECKPOINT</b> held for human sign-off</span>
    <span><b class="red">&#10007; BLOCK</b> outside scope</span>
  </div>
  <p class="note">Output is real terminal output from <code>python3 chunks.py</code>, recolored to the AgentMint palette. The "With AgentMint" tab shows the deterministic gated run; the live path (<code>python3 chunks.py right</code>) uses local Qwen via LM Studio when available.</p>
</main>
<footer class="footer">Generated from the AgentMint local demo.</footer>
<script>
document.querySelectorAll('.tab').forEach(function(t){
  t.addEventListener('click',function(){
    var k=t.getAttribute('data-tab');
    document.querySelectorAll('.tab').forEach(function(x){x.classList.remove('active');});
    document.querySelectorAll('.term-body').forEach(function(x){x.classList.remove('active');});
    t.classList.add('active');
    document.getElementById('panel-'+k).classList.add('active');
  });
});
</script>
</body>
</html>
"""

out = HTML.replace("__BUTTONS__", "\n    ".join(buttons)).replace("__PANELS__", "\n    ".join(panels))
dest = os.path.join(ROOT, "docs", "demo_embed.html")
with open(dest, "w") as f:
    f.write(out)
print("wrote", dest, "(%d bytes)" % len(out))
