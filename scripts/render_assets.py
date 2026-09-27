#!/usr/bin/env python3
"""Render the organization profile's animated SVGs (dark and light) into profile/assets/.

GitHub shows README images without web fonts, so every word is converted to outlines with the
brand faces (Kanit, JetBrains Mono), shaped by HarfBuzz for correct kerning. Animation is plain
CSS inside each SVG and switches off for readers who prefer reduced motion.

    pip install fonttools uharfbuzz
    python scripts/render_assets.py

Fonts download from google/fonts on first run into scripts/.fonts/ (gitignored).
"""

from __future__ import annotations

import base64
import io
import pathlib
import urllib.request

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "profile" / "assets"
FONTS = ROOT / "scripts" / ".fonts"
MARK = ROOT / "scripts" / "brand" / "verne-mark.png"
GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/main/"
SOURCES = {
    "kanit-500": "ofl/kanit/Kanit-Medium.ttf",
    "kanit-600": "ofl/kanit/Kanit-SemiBold.ttf",
    "jetbrains-mono": "ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}

THEMES = {
    "dark": {
        "bg0": "#020707", "bg1": "#051917", "stroke": "#153a36", "grid": "#0e2a27",
        "text": "#e8f4f1", "text2": "#a3b8b3", "text3": "#6d8581",
        "g1": "#93e6d4", "g2": "#3bffd9", "g3": "#297bff",
        "glow_a": "#008c8c", "glow_a_op": 0.34, "glow_b": "#297bff", "glow_b_op": 0.24,
        "rail": "#1b3f3b", "node_fill": "#020707", "sheen": "#ffffff",
    },
    "light": {
        "bg0": "#ffffff", "bg1": "#f2f9f7", "stroke": "#d5e6e2", "grid": "#e8f2ef",
        "text": "#0b1f1d", "text2": "#46605b", "text3": "#728a85",
        "g1": "#00a3a3", "g2": "#008c8c", "g3": "#1f5fd6",
        "glow_a": "#3bffd9", "glow_a_op": 0.22, "glow_b": "#297bff", "glow_b_op": 0.12,
        "rail": "#d3e5e1", "node_fill": "#ffffff", "sheen": "#ffffff",
    },
}


def fetch_font(key: str) -> bytes:
    path = FONTS / f"{key}.ttf"
    if not path.exists():
        FONTS.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(GOOGLE_FONTS + SOURCES[key], timeout=60) as r:
            path.write_bytes(r.read())
    return path.read_bytes()


def num(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


class Face:
    """A font that turns strings into SVG path data (HarfBuzz shaping, fontTools outlines)."""

    def __init__(self, key: str, wght: int | None = None):
        data = fetch_font(key)
        tt = TTFont(io.BytesIO(data))
        if wght is not None and "fvar" in tt:
            tt = instantiateVariableFont(tt, {"wght": wght})
            buf = io.BytesIO()
            tt.save(buf)
            data = buf.getvalue()
            tt = TTFont(io.BytesIO(data))
        self.glyphs = tt.getGlyphSet()
        self.order = tt.getGlyphOrder()
        self.upm = tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(data))

    def shape(self, text: str):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True})
        return buf.glyph_infos, buf.glyph_positions

    def width(self, text: str, size: float, tracking: float = 0) -> float:
        infos, pos = self.shape(text)
        return sum(p.x_advance for p in pos) * size / self.upm + tracking * size * (len(infos) - 1)

    def path(self, text: str, size: float, x: float, y: float, tracking: float = 0, anchor: str = "start") -> str:
        infos, pos = self.shape(text)
        scale = size / self.upm
        w = self.width(text, size, tracking)
        x0 = x - (w if anchor == "end" else w / 2 if anchor == "middle" else 0)
        pen = SVGPathPen(self.glyphs, ntos=num)
        cx = 0.0
        for info, p in zip(infos, pos):
            t = TransformPen(pen, (scale, 0, 0, -scale, x0 + cx + p.x_offset * scale, y - p.y_offset * scale))
            self.glyphs[self.order[info.codepoint]].draw(t)
            cx += p.x_advance * scale + tracking * size
        return pen.getCommands()


DISPLAY = Face("kanit-500")
WORDMARK = Face("kanit-600")
MONO = Face("jetbrains-mono", wght=500)
MARK_B64 = base64.b64encode(MARK.read_bytes()).decode()
MARK_RATIO = 257 / 240


def mark(x: float, y: float, h: float, gid: str) -> str:
    """The Verne mark: the PNG's alpha is a mask over a brand-gradient rectangle."""
    w = h * MARK_RATIO
    return f"""
  <mask id="{gid}-m" maskUnits="userSpaceOnUse" x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" style="mask-type:alpha">
    <image href="data:image/png;base64,{MARK_B64}" x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}"/>
  </mask>
  <rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="url(#{gid}-g)" mask="url(#{gid}-m)"/>"""


def mark_gradient(gid: str, t: dict, x: float, y: float, h: float) -> str:
    w = h * MARK_RATIO
    return f"""<linearGradient id="{gid}-g" gradientUnits="userSpaceOnUse" x1="{num(x)}" y1="{num(y)}" x2="{num(x + w)}" y2="{num(y + h)}">
      <stop offset="0" stop-color="{t['g1']}"/><stop offset=".45" stop-color="{t['g2']}"/><stop offset="1" stop-color="{t['g3']}"/>
    </linearGradient>"""


def hero(t: dict) -> str:
    W, H = 1200, 380
    L = 64  # left margin
    line1, line2 = "We build software", "inside real operations."
    sub = "ai systems · data infrastructure · operational software"
    size, sub_size = 54, 17
    sub_x = L + MONO.width("$ ", sub_size)
    sub_w = MONO.width(sub, sub_size)
    l2_w = DISPLAY.width(line2, size)

    # Delivery loop: four phases on a rail, a pulse walks it every 8 s.
    phases = ["discover", "deploy", "build", "transfer"]
    rx0, rx1, ry = 836, 1116, 214
    nodes = [rx0 + i * (rx1 - rx0) / 3 for i in range(4)]
    rail_len = rx1 - rx0
    reach = [0, 25, 50, 75]  # % of the loop when the pulse reaches each node

    node_css = "\n".join(
        f"""  @keyframes n{i} {{ 0%, {max(0, p - 0.01)}% {{ opacity: {1 if p == 0 else .38}; }} {p}%, 93% {{ opacity: 1; }} 100% {{ opacity: .38; }} }}
  .n{i} {{ animation: n{i} 8s linear infinite; }}"""
        for i, p in enumerate(reach)
    )
    node_svg = "\n".join(
        f"""  <circle cx="{num(x)}" cy="{ry}" r="8" fill="{t['node_fill']}" stroke="{t['rail']}" stroke-width="2"/>
  <g class="n{i} on">
    <circle cx="{num(x)}" cy="{ry}" r="8" fill="none" stroke="{t['g2']}" stroke-width="2"/>
    <circle cx="{num(x)}" cy="{ry}" r="3.2" fill="{t['g2']}"/>
    <path d="{MONO.path(phases[i], 13, x, ry + 34, anchor='middle')}" fill="{t['text']}"/>
  </g>"""
        for i, x in enumerate(nodes)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Verne</title>
<desc id="d">We build software inside real operations: AI systems, data infrastructure and operational software. Delivery loop: discover, deploy, build, transfer. Ownership moves when the tests pass.</desc>
<defs>
  <linearGradient id="panel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t['bg0']}"/><stop offset="1" stop-color="{t['bg1']}"/></linearGradient>
  <radialGradient id="ga" cx=".06" cy="1.1" r=".62"><stop offset="0" stop-color="{t['glow_a']}" stop-opacity="{t['glow_a_op']}"/><stop offset="1" stop-color="{t['glow_a']}" stop-opacity="0"/></radialGradient>
  <radialGradient id="gb" cx="1.02" cy="-.1" r=".55"><stop offset="0" stop-color="{t['glow_b']}" stop-opacity="{t['glow_b_op']}"/><stop offset="1" stop-color="{t['glow_b']}" stop-opacity="0"/></radialGradient>
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{t['grid']}" stroke-width="1"/></pattern>
  <radialGradient id="gridFade" cx=".62" cy=".45" r=".6"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <mask id="gridMask"><rect width="{W}" height="{H}" fill="url(#gridFade)"/></mask>
  <clipPath id="clip"><rect width="{W}" height="{H}" rx="22"/></clipPath>
  <linearGradient id="accent" gradientUnits="userSpaceOnUse" x1="{L}" y1="0" x2="{num(L + l2_w)}" y2="0">
    <stop offset="0" stop-color="{t['g1']}"/><stop offset=".5" stop-color="{t['g2']}"/><stop offset="1" stop-color="{t['g3']}"/>
  </linearGradient>
  <linearGradient id="railGrad" gradientUnits="userSpaceOnUse" x1="{rx0}" y1="0" x2="{rx1}" y2="0">
    <stop offset="0" stop-color="{t['g1']}"/><stop offset=".5" stop-color="{t['g2']}"/><stop offset="1" stop-color="{t['g3']}"/>
  </linearGradient>
  <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{t['sheen']}" stop-opacity="0"/><stop offset=".5" stop-color="{t['sheen']}" stop-opacity=".55"/><stop offset="1" stop-color="{t['sheen']}" stop-opacity="0"/>
  </linearGradient>
  <clipPath id="line2"><path d="{DISPLAY.path(line2, size, L, 240)}"/></clipPath>
  <clipPath id="typing"><rect class="type" x="{num(sub_x)}" y="{298 - 20}" width="{num(sub_w + 2)}" height="28"/></clipPath>
  <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>
  {mark_gradient("hm", t, L, 50, 40)}
</defs>
<style>
  * {{ transform-box: fill-box; }}
  .rise {{ animation: rise .9s cubic-bezier(.22,1,.36,1) both; }}
  .d1 {{ animation-delay: .08s; }} .d2 {{ animation-delay: .18s; }} .d3 {{ animation-delay: .3s; }} .d4 {{ animation-delay: .45s; }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
  .type {{ transform-origin: left; animation: type 1.8s steps({len(sub)}) .7s both; }}
  @keyframes type {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
  .cursor {{ animation: blink 1.1s steps(1) infinite; }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  .sweep {{ animation: sweep 7s cubic-bezier(.5,0,.3,1) 2.4s infinite; }}
  @keyframes sweep {{ 0% {{ transform: translateX(-160px); }} 22%, 100% {{ transform: translateX({num(l2_w + 40)}px); }} }}
  .halo {{ animation: breathe 4.5s ease-in-out infinite; }}
  @keyframes breathe {{ 50% {{ opacity: .25; }} }}
  .rail {{ stroke-dasharray: {rail_len}; animation: rail 8s linear infinite; }}
  @keyframes rail {{ 0% {{ stroke-dashoffset: {rail_len}; opacity: 1; }} 75%, 93% {{ stroke-dashoffset: 0; opacity: 1; }} 100% {{ stroke-dashoffset: 0; opacity: 0; }} }}
  .pulse {{ animation: pulse 8s linear infinite; }}
  @keyframes pulse {{ 0% {{ transform: translateX(0); opacity: 1; }} 75% {{ transform: translateX({rail_len}px); opacity: 1; }} 93%, 100% {{ transform: translateX({rail_len}px); opacity: 0; }} }}
{node_css}
  @media (prefers-reduced-motion: reduce) {{
    *, .on, .rail, .pulse, .type, .cursor, .sweep, .halo {{ animation: none !important; }}
    .pulse, .sweep {{ display: none; }}
  }}
</style>
<g clip-path="url(#clip)">
  <rect width="{W}" height="{H}" fill="url(#panel)"/>
  <rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#gridMask)"/>
  <rect width="{W}" height="{H}" fill="url(#ga)"/>
  <rect width="{W}" height="{H}" fill="url(#gb)"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="21.5" fill="none" stroke="{t['stroke']}"/>

<g class="rise">
  <g class="halo" filter="url(#soft)" opacity=".55">{mark(L, 50, 40, "hm")}</g>
  {mark(L, 50, 40, "hm")}
  <path d="{WORDMARK.path("VERNE", 19, L + 58, 77, tracking=0.18)}" fill="{t['text']}"/>
  <rect x="{num(L + 58 + WORDMARK.width("VERNE", 19, 0.18) + 18)}" y="62" width="1" height="18" fill="{t['stroke']}"/>
  <path d="{MONO.path("FORWARD-DEPLOYED ENGINEERING", 12, L + 58 + WORDMARK.width("VERNE", 19, 0.18) + 37, 76, tracking=0.14)}" fill="{t['g2']}"/>
</g>

<path class="rise d1" d="{DISPLAY.path(line1, size, L, 176)}" fill="{t['text']}"/>
<g class="rise d2">
  <path d="{DISPLAY.path(line2, size, L, 240)}" fill="url(#accent)"/>
  <g clip-path="url(#line2)"><rect class="sweep" x="{L}" y="190" width="120" height="64" fill="url(#sheen)" opacity=".5"/></g>
</g>

<g class="rise d3">
  <path d="{MONO.path("$", sub_size, L, 298)}" fill="{t['g2']}"/>
  <g clip-path="url(#typing)"><path d="{MONO.path(sub, sub_size, sub_x, 298)}" fill="{t['text2']}"/></g>
  <rect class="cursor" x="{num(sub_x + sub_w + 6)}" y="283" width="9" height="19" fill="{t['g2']}"/>
</g>

<g class="rise d4">
  <path d="{MONO.path("// delivery loop", 13, rx0 - 6, ry - 50)}" fill="{t['text3']}"/>
  <line x1="{rx0}" y1="{ry}" x2="{rx1}" y2="{ry}" stroke="{t['rail']}" stroke-width="2"/>
  <line class="rail" x1="{rx0}" y1="{ry}" x2="{rx1}" y2="{ry}" stroke="url(#railGrad)" stroke-width="2"/>
{node_svg}
  <g class="pulse"><circle cx="{rx0}" cy="{ry}" r="9" fill="{t['g2']}" opacity=".35" filter="url(#soft)"/><circle cx="{rx0}" cy="{ry}" r="4" fill="{t['g2']}"/></g>
  <path d="{MONO.path("ownership moves when the tests pass", 13, rx0 - 6, ry + 84)}" fill="{t['text3']}"/>
</g>
</svg>
"""


def footer(t: dict) -> str:
    W, H = 1200, 110
    tail = "forward-deployed engineering · dhaka · 23.81°N 90.41°E"
    mono_size, word_size = 13, 15
    word_w = WORDMARK.width("VERNE", word_size, 0.18)
    tail_w = MONO.width(tail, mono_size)
    mark_h = 22
    total = mark_h * MARK_RATIO + 12 + word_w + 22 + tail_w + 16
    x = (W - total) / 2
    word_x = x + mark_h * MARK_RATIO + 12
    tail_x = word_x + word_w + 22
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">
<title id="t">Verne, forward-deployed engineering, Dhaka</title>
<defs>
  <linearGradient id="hair" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{t['g1']}" stop-opacity="0"/><stop offset=".5" stop-color="{t['g2']}" stop-opacity=".55"/><stop offset="1" stop-color="{t['g3']}" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="spark" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{t['g2']}" stop-opacity="0"/><stop offset=".5" stop-color="{t['g2']}"/><stop offset="1" stop-color="{t['g2']}" stop-opacity="0"/>
  </linearGradient>
  {mark_gradient("fm", t, x, 44, mark_h)}
</defs>
<style>
  * {{ transform-box: fill-box; }}
  .spark {{ animation: spark 6s cubic-bezier(.5,0,.3,1) infinite; }}
  @keyframes spark {{ 0% {{ transform: translateX(-140px); opacity: 0; }} 10% {{ opacity: 1; }} 60% {{ transform: translateX({W * .7}px); opacity: 1; }} 61%, 100% {{ opacity: 0; transform: translateX({W * .7}px); }} }}
  .cursor {{ animation: blink 1.1s steps(1) infinite; }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .spark, .cursor {{ animation: none; }} .spark {{ display: none; }} }}
</style>
<rect x="{W * .15}" y="12" width="{W * .7}" height="1" fill="url(#hair)"/>
<clipPath id="hairClip"><rect x="{W * .15}" y="8" width="{W * .7}" height="10"/></clipPath>
<g clip-path="url(#hairClip)"><rect class="spark" x="{W * .15}" y="11.5" width="140" height="2" fill="url(#spark)"/></g>
{mark(x, 44, mark_h, "fm")}
<path d="{WORDMARK.path("VERNE", word_size, word_x, 61, tracking=0.18)}" fill="{t['text']}"/>
<path d="{MONO.path(tail, mono_size, tail_x, 60)}" fill="{t['text3']}"/>
<rect class="cursor" x="{num(tail_x + tail_w + 7)}" y="48" width="7" height="15" fill="{t['g2']}"/>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, t in THEMES.items():
        for kind, render in (("hero", hero), ("footer", footer)):
            svg = render(t)
            (OUT / f"{kind}-{name}.svg").write_text(svg, encoding="utf-8", newline="\n")
            print(f"{kind}-{name}.svg  {len(svg.encode()) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
