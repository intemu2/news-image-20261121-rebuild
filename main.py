#!/usr/bin/env python3
"""news-image-20261121 rebuild round 2. Stdlib only. Draws entry.png 1024x1024.
Vector stroke font (no bitmap 5x7): glyphs are polylines on a 0..5 x 0..7 grid,
drawn as thick lines into a per-glyph cache, then blitted as runs. Deterministic.
"""
import os, struct, zlib

W = 1024
H = 1024
PAPER = (247, 243, 232)
INK = (17, 17, 17)
NAVY = (15, 42, 68)
RED = (185, 28, 28)
BLUE = (29, 78, 137)
TEAL = (13, 116, 109)
GOLD = (180, 130, 20)
GREY = (90, 90, 90)
LIGHT = (255, 255, 255)
SKY = (173, 216, 240)
SEA = (46, 111, 160)
LAND = (222, 206, 160)
GREEN = (96, 140, 80)

# ---- canvas ----
pix = bytearray(PAPER[0:1] * 0)  # placeholder, filled in main
pix = bytearray(bytes(PAPER) * (W * H))

def rect(x0, y0, x1, y1, c):
    x0 = max(0, int(x0)); y0 = max(0, int(y0))
    x1 = min(W, int(x1)); y1 = min(H, int(y1))
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    for y in range(y0, y1):
        s = (y * W + x0) * 3
        pix[s:s + (x1 - x0) * 3] = row

def hline(x0, x1, y, c, t=1):
    rect(x0, y - t // 2, x1, y - t // 2 + t, c)

def disc(cx, cy, r, c):
    cx = int(cx); cy = int(cy); r = int(r)
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, c)

def tri(x0, y0, x1, y1, x2, y2, c):
    # filled triangle by scanlines
    pts = sorted([(x0, y0), (x1, y1), (x2, y2)], key=lambda p: p[1])
    (ax, ay), (bx, by), (cx, cy) = pts
    def interp(y, p, q):
        if q[1] == p[1]:
            return p[0]
        return p[0] + (q[0] - p[0]) * (y - p[1]) / (q[1] - p[1])
    for y in range(int(ay), int(cy) + 1):
        if y < by:
            xa = interp(y, (ax, ay), (bx, by)); xb = interp(y, (ax, ay), (cx, cy))
        else:
            xa = interp(y, (bx, by), (cx, cy)); xb = interp(y, (ax, ay), (cx, cy))
        if xa > xb:
            xa, xb = xb, xa
        rect(int(xa), y, int(xb) + 1, y + 1, c)

def line(x0, y0, x1, y1, c, t=2):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    r = max(0, t // 2)
    for i in range(n + 1):
        f = i / max(1, n)
        cx = int(x0 + (x1 - x0) * f); cy = int(y0 + (y1 - y0) * f)
        rect(cx - r, cy - r, cx + r + 1, cy + r + 1, c)

# ---- vector stroke font: polylines on grid x 0..5, y 0..7 (0 top) ----
S = {
 'A': [[(0,7),(2.5,0),(5,7)],[(1.3,4.5),(3.7,4.5)]],
 'B': [[(0,0),(0,7)],[(0,0),(3.5,0),(5,1),(5,2.5),(3.5,3.5),(0,3.5)],[(0,3.5),(3.5,3.5),(5,4.5),(5,6),(3.5,7),(0,7)]],
 'C': [[(5,1),(4,0),(1,0),(0,1),(0,6),(1,7),(4,7),(5,6)]],
 'D': [[(0,0),(0,7)],[(0,0),(3,0),(5,1.5),(5,5.5),(3,7),(0,7)]],
 'E': [[(0,0),(0,7)],[(0,0),(5,0)],[(0,3.5),(4,3.5)],[(0,7),(5,7)]],
 'F': [[(0,0),(0,7)],[(0,0),(5,0)],[(0,3.5),(4,3.5)]],
 'G': [[(5,1),(4,0),(1,0),(0,1),(0,6),(1,7),(4,7),(5,6),(5,3.5),(3,3.5)]],
 'H': [[(0,0),(0,7)],[(5,0),(5,7)],[(0,3.5),(5,3.5)]],
 'I': [[(0.5,0),(4.5,0)],[(2.5,0),(2.5,7)],[(0.5,7),(4.5,7)]],
 'J': [[(5,0),(5,5.5),(4,7),(2,7),(0.5,5.5)],[(1,0),(5,0)]],
 'K': [[(0,0),(0,7)],[(5,0),(0,3.5)],[(1.8,3.5),(5,7)]],
 'L': [[(0,0),(0,7)],[(0,7),(5,7)]],
 'M': [[(0,7),(0,0),(2.5,3.5),(5,0),(5,7)]],
 'N': [[(0,7),(0,0),(5,7),(5,0)]],
 'O': [[(1,0),(4,0),(5,1),(5,6),(4,7),(1,7),(0,6),(0,1),(1,0)]],
 'P': [[(0,0),(0,7)],[(0,0),(3.5,0),(5,1),(5,2.5),(3.5,3.5),(0,3.5)]],
 'Q': [[(1,0),(4,0),(5,1),(5,6),(4,7),(1,7),(0,6),(0,1),(1,0)],[(3,5),(5,7.5)]],
 'R': [[(0,0),(0,7)],[(0,0),(3.5,0),(5,1),(5,2.5),(3.5,3.5),(0,3.5)],[(2.5,3.5),(5,7)]],
 'S': [[(5,1),(4,0),(1,0),(0,1),(0,2.5),(1,3.5),(4,3.5),(5,4.5),(5,6),(4,7),(1,7),(0,6)]],
 'T': [[(0,0),(5,0)],[(2.5,0),(2.5,7)]],
 'U': [[(0,0),(0,6),(1,7),(4,7),(5,6),(5,0)]],
 'V': [[(0,0),(2.5,7),(5,0)]],
 'W': [[(0,0),(1.2,7),(2.5,3),(3.8,7),(5,0)]],
 'X': [[(0,0),(5,7)],[(5,0),(0,7)]],
 'Y': [[(0,0),(2.5,3.5),(5,0)],[(2.5,3.5),(2.5,7)]],
 'Z': [[(0,0),(5,0),(0,7),(5,7)]],
 '0': [[(1,0),(4,0),(5,1),(5,6),(4,7),(1,7),(0,6),(0,1),(1,0)]],
 '1': [[(1,1),(2.5,0),(2.5,7)],[(0,7),(5,7)]],
 '2': [[(0,1),(1,0),(4,0),(5,1),(5,3),(0,7),(5,7)]],
 '3': [[(0,1),(1,0),(4,0),(5,1),(5,3),(3,3.5)],[(3,3.5),(5,4),(5,6),(4,7),(1,7),(0,6)]],
 '4': [[(3.5,0),(0,4.5),(4.5,4.5)],[(4,0),(4,7)]],
 '5': [[(5,0),(0,0),(0,3.5),(3,3.5),(5,4.5),(5,6),(4,7),(1,7),(0,6)]],
 '6': [[(5,1),(4,0),(1,0),(0,1),(0,6),(1,7),(4,7),(5,6),(5,4),(4,3.5),(1,3.5),(0,4.5)]],
 '7': [[(0,0),(5,0),(2,7)]],
 '8': [[(1,0),(4,0),(5,1),(5,2.5),(4,3.5),(1,3.5),(0,2.5),(0,1),(1,0)],[(1,3.5),(4,3.5),(5,4.5),(5,6),(4,7),(1,7),(0,6),(0,4.5),(1,3.5)]],
 '9': [[(0,6),(0,1),(1,0),(4,0),(5,1),(5,6),(4,7),(1,7),(0,6)],[(5,6),(5,3),(4,3.5),(1,3.5)]],
 '.': [[(2.3,6.3),(2.7,6.3)],[(2.3,6.3),(2.3,6.9)]],
 ',': [[(2.3,6.3),(2.7,6.3)],[(2.5,6.5),(1.5,8)]],
 ':': [[(2.3,2.3),(2.7,2.3)],[(2.3,6.3),(2.7,6.3)]],
 ';': [[(2.3,2.3),(2.7,2.3)],[(2.3,6.3),(2.7,6.3)],[(2.5,6.5),(1.5,8)]],
 '!': [[(2.5,0),(2.5,5)],[(2.3,6.3),(2.7,6.3)]],
 '?': [[(1,1),(2,0),(4,0),(5,1),(5,2.5),(4,3.5),(2.5,3.5),(2.5,5)],[(2.3,6.3),(2.7,6.3)]],
 "'": [[(2,0),(1.5,2)]],
 '"': [[(1.5,0),(1,2)],[(3.5,0),(3,2)]],
 '-': [[(0.5,3.5),(4.5,3.5)]],
 '(': [[(4,0),(2,1.5),(1,3.5),(2,5.5),(4,7)]],
 ')': [[(1,0),(3,1.5),(4,3.5),(3,5.5),(1,7)]],
 '/': [[(0.5,7),(4.5,0)]],
 '%': [[(0.5,1.5),(1,0.5),(2,0.5),(2.5,1.5),(2,2.5),(1.5,3),(0.5,2.5),(0.5,1.5)],[(0.5,7),(4.5,0)],[(2.5,4.5),(3,3.5),(4,3.5),(4.5,4.5),(4,5.5),(3.5,6),(2.5,5.5),(2.5,4.5)]],
 '$': [[(5,1),(4,0),(1,0),(0,1),(0,2.5),(1,3.5),(4,3.5),(5,4.5),(5,6),(4,7),(1,7),(0,6)],[(2.5,-0.5),(2.5,7.5)]],
 '+': [[(0.5,3.5),(4.5,3.5)],[(2.5,1),(2.5,6)]],
 '=': [[(0.5,2.5),(4.5,2.5)],[(0.5,4.5),(4.5,4.5)]],
 '*': [[(2.5,1),(2.5,6)],[(0.5,2),(4.5,5)],[(4.5,2),(0.5,5)]],
 '#': [[(1.5,0),(1.5,7)],[(3.5,0),(3.5,7)],[(0,2.5),(5,2.5)],[(0,4.5),(5,4.5)]],
 '_': [[(0,7),(5,7)]],
}

# ---- glyph cache: stroke font rasterised once per (char,size), blitted as runs ----
_GCACHE = {}
_NARROW = set(".,:;'\"!|")

def _norm(ch):
    return {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
            "\u2013": "-", "\u2014": "-", "\u2022": ".", "\u00b0": "o"}.get(ch, ch)

def _glyph(ch, size):
    key = (ch, size)
    if key in _GCACHE:
        return _GCACHE[key]
    unit = size / 7.0
    t = 2 if size < 15 else max(2, int(round(size * 0.16)))
    r = t // 2
    pad = r + 1
    gw = int(round(5 * unit)) + 2 * pad
    gh = int(round(8.5 * unit)) + 2 * pad
    mask = [bytearray(gw) for _ in range(gh)]
    strokes = S.get(ch.upper() if ch.isalpha() else ch)
    if strokes:
        for poly in strokes:
            for (ax, ay), (bx, by) in zip(poly, poly[1:]):
                x0 = ax * unit + pad; y0 = ay * unit + pad
                x1 = bx * unit + pad; y1 = by * unit + pad
                steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
                for i in range(steps + 1):
                    f = i / max(1, steps)
                    cx = int(round(x0 + (x1 - x0) * f))
                    cy = int(round(y0 + (y1 - y0) * f))
                    for yy in range(max(0, cy - r), min(gh, cy + r + 1)):
                        row = mask[yy]
                        a = max(0, cx - r); b = min(gw, cx + r + 1)
                        if b > a:
                            row[a:b] = b"\x01" * (b - a)
    runs = []
    for yy, row in enumerate(mask):
        x = 0
        while x < gw:
            if row[x]:
                x0 = x
                while x < gw and row[x]:
                    x += 1
                runs.append((yy, x0, x))
            else:
                x += 1
    adv = 3 * unit if ch in _NARROW else 6 * unit
    out = (gw, gh, runs, adv)
    _GCACHE[key] = out
    return out

def _char_size(ch, size):
    if ch.islower():
        return max(8, int(round(size * 0.72)))
    return size

def text_w(s, size):
    w = 0.0
    for ch in s:
        ch = _norm(ch)
        if ch == " ":
            w += 6 * (size / 7.0)
        elif ch in S:
            w += _glyph(ch, _char_size(ch, size))[3]
        else:
            w += 6 * (size / 7.0)
    return w

def wrap(s, size, maxw):
    words = s.split(" ")
    lines = []
    cur = ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_w(trial, size) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines

def draw_text(x, y, s, size, c, align="l", maxw=None, leading=None, cx=None):
    """y = top of cap height. Returns height used."""
    if leading is None:
        leading = int(size * 1.18) + 1
    lines = [s] if maxw is None else wrap(s, size, maxw)
    rowbytes_cache = {}
    for li, ln in enumerate(lines):
        lw = text_w(ln, size)
        if align == "c" and cx is not None:
            sx = int(cx - lw / 2)
        elif align == "r":
            sx = int(x - lw)
        else:
            sx = int(x)
        sy = int(y) + li * leading
        px = sx
        for ch in ln:
            ch = _norm(ch)
            if ch == " ":
                px += int(round(6 * (size / 7.0)))
                continue
            cs = _char_size(ch, size)
            gw, gh, runs, adv = _glyph(ch, cs)
            off = size - cs if ch.islower() else 0
            rowb = rowbytes_cache.get((c, 1))
            for (gy, gx0, gx1) in runs:
                py = sy + off + gy
                if 0 <= py < H:
                    ax0 = px + gx0; ax1 = px + gx1
                    if ax1 > 0 and ax0 < W:
                        a0 = max(0, ax0); a1 = min(W, ax1)
                        if a1 > a0:
                            s0 = (py * W + a0) * 3
                            pix[s0:s0 + (a1 - a0) * 3] = bytes(c) * (a1 - a0)
            px += int(round(adv))
    return len(lines) * leading

def panel(x0, y0, x1, y1, bg, border=None):
    rect(x0, y0, x1, y1, bg)
    if border:
        rect(x0, y0, x1, y0 + 2, border)
        rect(x0, y1 - 2, x1, y1, border)
        rect(x0, y0, x0 + 2, y1, border)
        rect(x1 - 2, y0, x1, y1, border)

def tag(x, y, s, size, fg, bg):
    w = int(text_w(s, size)) + 10
    rect(x, y, x + w, y + size + 6, bg)
    draw_text(x + 5, y + 3, s, size, fg)
    return w

# ---- scene illustrations (drawn from primitives, one per card) ----
def scene(ax, ay, aw, ah, kind):
    rect(ax, ay, ax + aw, ay + ah, SKY)
    if kind == "cop":
        rect(ax, ay, ax + aw, ay + ah, NAVY)
        rect(ax + 8, ay + 8, ax + aw - 8, ay + 42, LIGHT)
        draw_text(ax + 14, ay + 12, "COP31", 22, NAVY)
        draw_text(ax + aw - 90, ay + 16, "DAY 13", 16, RED)
        for r in range(3):
            y = ay + 52 + r * 16
            rect(ax + 10, y, ax + aw - 10, y + 10, (70, 110, 150))
            for i in range(5):
                disc(ax + 22 + i * 52, y - 6, 5, (230, 200, 120))
    elif kind == "riyadh":
        rect(ax, ay, ax + aw, ay + ah, (10, 16, 40))
        for (sx, sy) in [(20, 12), (60, 26), (110, 10), (160, 30), (210, 14), (260, 24)]:
            disc(ax + sx % aw, ay + sy, 2, LIGHT)
        for i, bx in enumerate([30, 90, 150, 210]):
            bh = 40 + (i % 3) * 18
            rect(ax + bx, ay + ah - bh, ax + bx + 34, ay + ah, (25, 35, 60))
            for wy in range(4):
                rect(ax + bx + 6, ay + ah - bh + 8 + wy * 10, ax + bx + 28, ay + ah - bh + 12 + wy * 10, (255, 220, 100))
        line(ax + 40, ay + 12, ax + 120, ay + 62, (255, 180, 60), 3)
        line(ax + 200, ay + 8, ax + 150, ay + 58, (255, 220, 120), 3)
        line(ax + 280, ay + 16, ax + 230, ay + 60, LIGHT, 3)
        disc(ax + 120, ay + 62, 9, (255, 140, 40)); disc(ax + 120, ay + 62, 4, (255, 240, 160))
        disc(ax + 150, ay + 58, 8, (255, 140, 40))
    elif kind == "peru":
        tri(ax, ay + ah, ax + aw * 0.25, ay + 18, ax + aw * 0.5, ay + ah, (120, 110, 95))
        tri(ax + aw * 0.4, ay + ah, ax + aw * 0.65, ay + 8, ax + aw * 0.9, ay + ah, (90, 85, 75))
        rect(ax, ay + ah - 26, ax + aw, ay + ah, (150, 120, 80))
        line(ax + 10, ay + ah - 26, ax + 90, ay + ah - 12, INK, 3)
        line(ax + 90, ay + ah - 12, ax + 170, ay + ah - 24, INK, 3)
        line(ax + 170, ay + ah - 24, ax + aw - 10, ay + ah - 8, INK, 3)
        rect(ax + 30, ay + ah - 58, ax + 86, ay + ah - 26, (200, 90, 60))
        line(ax + 30, ay + ah - 58, ax + 86, ay + ah - 40, INK, 2)
        rect(ax + aw - 90, ay + ah - 48, ax + aw - 30, ay + ah - 26, (220, 220, 210))
    elif kind == "kyiv":
        rect(ax, ay + ah - 30, ax + aw, ay + ah, SEA)
        for i, bx in enumerate([20, 70, 120, 170, 220]):
            rect(ax + bx, ay + 30, ax + bx + 26, ay + ah - 30, (120, 120, 125))
        line(ax, ay + 34, ax + aw, ay + 34, INK, 4)
        line(ax + 40, ay + 34, ax + 120, ay + 8, RED, 3)
        line(ax + 120, ay + 8, ax + 200, ay + 34, RED, 3)
        disc(ax + aw - 40, ay + 16, 12, (255, 220, 100))
    elif kind == "hormuz":
        rect(ax, ay + ah - 34, ax + aw, ay + ah, SEA)
        rect(ax + 60, ay + ah - 58, ax + aw - 60, ay + ah - 34, (60, 60, 70))
        rect(ax + 120, ay + ah - 78, ax + 150, ay + ah - 58, (60, 60, 70))
        rect(ax + 30, ay + 20, ax + 70, ay + 28, (80, 80, 90))
        line(ax + 50, ay + 20, ax + 50, ay + 10, INK, 2)
        disc(ax + aw - 46, ay + 18, 13, (255, 220, 100))
        line(ax + 90, ay + 44, ax + 200, ay + 44, LIGHT, 2)
    elif kind == "tehran":
        rect(ax, ay, ax + aw, ay + ah, (200, 220, 235))
        rect(ax + 60, ay + 40, ax + aw - 60, ay + ah, (180, 160, 120))
        disc(ax + aw // 2, ay + 40, 26, (30, 90, 140))
        rect(ax + aw // 2 - 4, ay + 8, ax + aw // 2 + 4, ay + 22, GOLD)
        rect(ax + aw // 2 - 2, ay + 8, ax + aw // 2 + 26, ay + 20, (0, 140, 80))
        for i in range(3):
            rect(ax + 78 + i * 30, ay + 62, ax + 92 + i * 30, ay + ah - 8, (90, 60, 40))
    elif kind == "washington":
        rect(ax, ay, ax + aw, ay + ah, (210, 225, 240))
        rect(ax + 50, ay + 44, ax + aw - 50, ay + ah, LIGHT)
        tri(ax + 70, ay + 44, ax + aw // 2, ay + 18, ax + aw - 70, ay + 44, LIGHT)
        disc(ax + aw // 2, ay + 30, 10, LIGHT)
        for i in range(4):
            rect(ax + 70 + i * 36, ay + 56, ax + 78 + i * 36, ay + ah - 6, (180, 180, 180))
        rect(ax + aw - 60, ay + 14, ax + aw - 20, ay + 34, RED)
        draw_text(ax + aw - 58, ay + 16, "TAX", 13, LIGHT)
    elif kind == "beijing":
        rect(ax, ay, ax + aw, ay + ah, (240, 200, 180))
        for i, (bw, by) in enumerate([(90, 66), (70, 48), (50, 30)]):
            rect(ax + aw // 2 - bw // 2, ay + by, ax + aw // 2 + bw // 2, ay + by + 16, (160, 40, 40))
            tri(ax + aw // 2 - bw // 2 - 8, ay + by, ax + aw // 2, ay + by - 10, ax + aw // 2 + bw // 2 + 8, ay + by, (120, 25, 25))
        rect(ax + 16, ay + ah - 22, ax + 70, ay + ah, (90, 90, 100))
        rect(ax + aw - 70, ay + ah - 30, ax + aw - 16, ay + ah, (90, 90, 100))
        disc(ax + 30, ay + 16, 11, (255, 220, 100))
    elif kind == "davao":
        rect(ax, ay + ah - 22, ax + aw, ay + ah, (90, 90, 95))
        rect(ax + 30, ay + 30, ax + aw - 50, ay + 46, LIGHT)
        tri(ax + aw - 60, ay + 30, ax + aw - 20, ay + 12, ax + aw - 20, ay + 46, (200, 40, 40))
        tri(ax + 90, ay + 46, ax + 130, ay + 62, ax + 170, ay + 46, (180, 180, 190))
        disc(ax + aw - 70, ay + 50, 7, (255, 140, 40)); disc(ax + aw - 70, ay + 50, 3, (255, 230, 120))
        for i in range(5):
            rect(ax + 50 + i * 18, ay + 34, ax + 58 + i * 18, ay + 40, BLUE)
    elif kind == "canberra":
        rect(ax, ay, ax + aw, ay + ah, (190, 215, 230))
        disc(ax + aw // 2, ay + ah // 2 - 6, 26, TEAL)
        draw_text(ax + aw // 2 - 14, ay + ah // 2 - 16, "AI", 22, LIGHT)
        rect(ax + 20, ay + 14, ax + 48, ay + 40, (0, 60, 120))
        rect(ax + aw - 48, ay + 14, ax + aw - 20, ay + 40, (200, 40, 40))
        rect(ax + 30, ay + ah - 18, ax + aw - 30, ay + ah - 8, (120, 90, 60))
    elif kind == "bitcoin":
        rect(ax, ay, ax + aw, ay + ah, (20, 25, 45))
        pts = [(0, 20), (40, 30), (80, 18), (120, 42), (160, 52), (200, 70)]
        for (px, py), (qx, qy) in zip(pts, pts[1:]):
            line(ax + px, ay + py, ax + qx, ay + qy, (255, 90, 90), 3)
        disc(ax + aw - 44, ay + 22, 18, GOLD)
        draw_text(ax + aw - 52, ay + 12, "B", 22, (20, 25, 45))
        draw_text(ax + 10, ay + ah - 24, "-4.8%", 16, (255, 120, 120))

# ---- world map, correct equirectangular aspect ----
CONTINENTS = [
 [(-168,66),(-140,70),(-120,72),(-100,73),(-85,70),(-75,62),(-60,50),(-70,42),(-75,35),(-80,26),(-85,20),(-95,18),(-105,20),(-115,28),(-125,40),(-125,50),(-150,60)],
 [(-80,10),(-60,0),(-50,-5),(-35,-8),(-40,-20),(-50,-30),(-60,-40),(-70,-50),(-75,-35),(-80,-20),(-80,-5)],
 [(-18,15),(-10,30),(0,35),(10,37),(20,32),(30,31),(35,28),(40,15),(48,11),(45,0),(40,-10),(35,-20),(30,-30),(20,-35),(15,-30),(12,-18),(9,-5),(9,4),(-8,4),(-15,10)],
 [(-10,36),(-9,43),(-5,48),(0,50),(5,55),(10,58),(18,56),(20,60),(25,65),(30,70),(40,68),(45,60),(40,50),(35,45),(30,42),(25,40),(20,40),(15,38),(10,38),(5,36),(0,36)],
 [(40,68),(60,70),(80,73),(100,76),(120,73),(140,72),(160,70),(170,66),(160,60),(140,55),(135,45),(127,40),(120,35),(110,30),(100,25),(90,20),(80,15),(75,8),(70,20),(60,25),(55,30),(50,35),(45,40)],
 [(113,-22),(122,-14),(132,-12),(142,-11),(150,-22),(153,-27),(150,-37),(140,-38),(130,-32),(122,-34),(114,-30)],
]
PINS = [(1,30.7,36.9),(2,46.7,24.6),(3,-76.0,-10.9),(4,30.5,50.4),(5,56.0,26.5),
        (6,51.4,35.7),(7,-77.0,38.9),(8,116.4,39.9),(9,125.6,7.1),(10,149.1,-35.3)]

def poly_fill(pts, c):
    ys = [p[1] for p in pts]
    for y in range(int(min(ys)), int(max(ys)) + 1):
        xs = []
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            rect(int(xs[i]), y, int(xs[i + 1]) + 1, y + 1, c)

def draw_map(mx0, my0, mw, mh):
    rect(mx0, my0, mx0 + mw, my0 + mh, (190, 220, 235))
    scale = min(mw / 360.0, mh / 130.0)
    ox = mx0 + (mw - 360 * scale) / 2
    oy = my0 + (mh - 130 * scale) / 2
    def conv(lon, lat):
        return (ox + (lon + 180) * scale, oy + (75 - lat) * scale)
    for cont in CONTINENTS:
        poly_fill([conv(lo, la) for (lo, la) in cont], LAND)
    for cont in CONTINENTS:
        pp = [conv(lo, la) for (lo, la) in cont]
        for (x1, y1), (x2, y2) in zip(pp, pp[1:] + pp[:1]):
            line(x1, y1, x2, y2, (120, 105, 70), 1)
    pin_xy = {}
    off = {5: (-2, 10), 6: (8, -2)}
    for (n, lo, la) in PINS:
        x, y = conv(lo, la)
        pin_xy[n] = (int(x), int(y))
        dx, dy = off.get(n, (0, 0))
        if (dx, dy) != (0, 0):
            line(int(x), int(y), int(x) + dx, int(y) + dy, RED, 1)
            disc(int(x), int(y), 2, RED)
        disc(int(x) + dx, int(y) + dy, 7, RED)
        draw_text(0, int(y) + dy - 6, str(n), 10, LIGHT, align="c", cx=int(x) + dx)
    return pin_xy

# ---- story data (from research-21nov-fresh.md, verified 21 Nov 2026) ----
HEROES = [
 dict(num=1, place="ANTALYA, TURKIYE", cat="CLIMATE", kind="cop",
      title="COP31 OVERTIME DAY 13",
      summ="Draft cut to 80 paras, no fossil fuels named.",
      src="REUTERS, AP - CONFIRMED"),
 dict(num=2, place="RIYADH", cat="WAR", kind="riyadh",
      title="3 MISSILES DOWN OVER RIYADH",
      summ="Shot down before dawn; no casualties reported.",
      src="REUTERS, AFP - CONFIRMED"),
 dict(num=3, place="JUNIN, PERU", cat="EARTHQUAKE", kind="peru",
      title="PERU QUAKE M6.7, 8 HURT",
      summ="108 km deep; 8 hurt, 128 homes hit.",
      src="USGS, IGP - CONFIRMED"),
]
MEDIUM = [
 dict(num=4, place="KYIV", cat="WAR", kind="kyiv",
      title="CRIMEA BRIDGE WILL NOT STAY", src="NBC - REPORTED"),
 dict(num=5, place="STRAIT OF HORMUZ", cat="WAR", kind="hormuz",
      title="IRAN DOWNS US DRONE", src="IRIB - REPORTED"),
 dict(num=6, place="TEHRAN", cat="DIPLOMACY", kind="tehran",
      title="URANIUM STAYS AT HOME", src="IRNA - OFFICIAL"),
 dict(num=7, place="WASHINGTON", cat="TECHNOLOGY", kind="washington",
      title="TRUMP VOWS DATA-CENTRE TAX", src="REUTERS - REPORTED"),
 dict(num=8, place="BEIJING", cat="DIPLOMACY", kind="beijing",
      title="FIX TAIWAN WORDS, CHINA SAYS", src="AFP - OFFICIAL"),
 dict(num=9, place="DAVAO", cat="AVIATION", kind="davao",
      title="JET LANDS SAFE AFTER ENGINE FIRE", src="AP - CONFIRMED"),
 dict(num=10, place="CANBERRA", cat="DIPLOMACY", kind="canberra",
      title="AUSTRALIA, CHINA AGREE AI TALKS", src="ABC - OFFICIAL"),
 dict(num=11, place="WORLD", cat="MARKETS", kind="bitcoin",
      title="BITCOIN SLIPS BELOW $59,000", src="COINGECKO - CONFIRMED"),
]
ALSO = [
 "Verstappen on pole in Las Vegas (F1)",
 "Rahul 124* puts India on top (AFP)",
 "Kryvyi Rih strike kills 2, injures 60 (AP)",
 "Denmark says it foiled a Russian plot (AJ)",
 "EU warns COP31 risks 'fossil summit' (AFP)",
 "Panama threatens to block climate text (AJ)",
 "PLN signs clean-power deals (Antara)",
 "Houthis threaten Jeddah, Red Sea ports (AJ)",
 "Vance: Iran strikes were Trump's call",
 "Texas execution takes 63 minutes (ABC)",
 "Jury convicts Palisades fire starter (ABC)",
 "Judge OKs $7.25bn Roundup settlement (AFP)",
 "Canada rests defence in climate trial (AFP)",
 "Kim tours factories, no Trump meeting (AFP)",
 "Freight train derails; no one hurt (KH)",
 "Taipei passes budget and cash payout (TT)",
 "Bangkok plan on arsenic in two rivers",
 "Pakistani minister joins SCO forum (Dawn)",
 "Rain alerts as Akvan remnants move inland",
 "Rights groups urge sanctions on Myanmar (AP)",
 "African ratings agency talks to 15 states",
 "Cummins keeps Australian captaincy (ABC)",
 "Russell hits out at Verstappen (Sky)",
 "'El Chapo Isidro' captured in Sinaloa (AP)",
 "Russian ship Sparta II on fire (Reuters)",
 "Trump weighs new strikes on Iran (NYT)",
 "French police sentenced over beating (AP)",
 "UN talks continue on AI weapons rules (AP)",
 "Salvadoran troops fight gangs in Haiti (AP)",
 "Southern Ethiopia: 700,000 displaced (AP)",
 "Turkey takes control of Sozcu TV (Reuters)",
 "Gaza: 4 killed in Israeli strikes (AP)",
 "Baghdad power plant fire kills 4 (AP)",
 "France seeks UN meeting after Kyiv raids (AFP)",
 "Estonia urges halt to war (AP)",
 "German-Ukrainian drone output up 5x (Reuters)",
 "England beat NZ by record margin (AP)",
 "Man sentenced to death over posts (AP)",
 "Malaysia-Turkey pact shelters 10,000 Rohingya",
]
PIN_LABELS = {1: "Antalya - COP31", 2: "Riyadh - missiles", 3: "Junin - quake M6.7",
              4: "Kyiv - Crimea bridge", 5: "Hormuz - US drone", 6: "Tehran - uranium",
              7: "Washington - data tax", 8: "Beijing - Taiwan", 9: "Davao - jet lands",
              10: "Canberra - AI talks"}

def build():
    rect(0, 0, W, 8, NAVY)
    rect(0, 1020, W, 1024, NAVY)
    draw_text(0, 12, "THE WORLD IN ONE PAGE  |  50 STORIES  |  7 REGIONS  |  ONE DAY", 12, RED, align="c", cx=512)
    draw_text(0, 28, "SATURDAY 21 NOVEMBER 2026", 42, INK, align="c", cx=512)
    hline(16, 1008, 76, INK, 2)
    draw_text(0, 80, "COP31 INTO DAY 13  |  MISSILES DOWN OVER RIYADH  |  PERU QUAKE M6.7", 15, NAVY, align="c", cx=512)
    # strip: 6 key numbers
    strip = [("13", "COP31 DAY"), ("3", "MISSILES RIYADH"), ("6.7", "PERU QUAKE"),
             ("146", "SAFE IN DAVAO"), ("$58,960", "BITCOIN"), ("124*", "RAHUL")]
    for i, (num, lab) in enumerate(strip):
        x0 = 16 + i * 166
        panel(x0, 100, x0 + 160, 144, LIGHT, NAVY)
        draw_text(0, 103, num, 26, RED, align="c", cx=x0 + 80)
        draw_text(0, 130, lab, 10, INK, align="c", cx=x0 + 80)
    # heroes
    for i, h in enumerate(HEROES):
        x0 = 16 + i * 334; y0 = 148; cw = 324; ch = 240
        panel(x0, y0, x0 + cw, y0 + ch, LIGHT, GREY)
        rect(x0, y0, x0 + cw, y0 + 4, RED if i == 1 else NAVY)
        scene(x0 + 4, y0 + 8, cw - 8, 96, h["kind"])
        draw_text(x0 + 8, y0 + 110, h["place"] + " - " + h["cat"], 11, RED)
        draw_text(x0 + 8, y0 + 126, h["title"], 23, INK, maxw=cw - 16, leading=26)
        draw_text(x0 + 8, y0 + 182, h["summ"], 13, (40, 40, 40), maxw=cw - 16, leading=15)
        draw_text(x0 + 8, y0 + 216, str(h["num"]) + ". " + h["src"], 10, GREY)
    # medium: 4 x 2, larger cards
    for i, m in enumerate(MEDIUM):
        col = i % 4; row = i // 4
        x0 = 16 + col * 250; y0 = 392 + row * 142; cw = 242; ch = 138
        panel(x0, y0, x0 + cw, y0 + ch, LIGHT, GREY)
        scene(x0 + 3, y0 + 3, cw - 6, 44, m["kind"])
        draw_text(x0 + 6, y0 + 51, m["place"] + " - " + m["cat"], 10, RED)
        draw_text(x0 + 6, y0 + 63, m["title"], 18, INK, maxw=cw - 12, leading=19)
        draw_text(x0 + 6, y0 + ch - 13, str(m["num"]) + ". " + m["src"], 9, GREY)
    # map, full-width section, correct aspect, pins listed at the sides
    draw_text(16, 678, "THE WORLD - WHERE IT HAPPENED", 12, NAVY)
    draw_text(1008, 678, "MAP: NUMBERS MATCH THE STORIES ABOVE", 11, GREY, align="r")
    draw_map(330, 694, 364, 112)
    for n in range(1, 6):
        yy = 700 + (n - 1) * 20
        disc(28, yy + 6, 8, RED)
        draw_text(24, yy, str(n), 10, LIGHT)
        draw_text(42, yy, PIN_LABELS[n], 11, INK)
    for n in range(6, 11):
        yy = 700 + (n - 6) * 20
        disc(724, yy + 6, 8, RED)
        draw_text(720, yy, str(n) if n < 10 else "10", 10, LIGHT)
        draw_text(738, yy, PIN_LABELS[n], 11, INK)
    # ALSO ON: 39 items, 3 columns
    draw_text(16, 810, "ALSO ON 21 NOVEMBER", 13, NAVY)
    hline(16, 1008, 828, INK, 1)
    for ci in range(3):
        x0 = 16 + ci * 334
        for ri in range(13):
            item = ALSO[ci * 13 + ri]
            draw_text(x0, 830 + ri * 9, item, 8, INK)
    # DATE CHECK footer
    rect(0, 950, W, 952, RED)
    draw_text(16, 956, "DATE CHECK - NOT 21 NOV, SO LEFT OUT:", 12, RED)
    draw_text(16, 972, "20 Nov: Wall Street fall; Kyiv bridge strikes; missile in Poland; UK-EU deal; Cyclone Akvan lands.", 10, INK)
    draw_text(16, 986, "20 Nov: 2 missiles over Jazan. 19 Nov: PIF tower hit. 18 Nov: Voyager 1 light-day. Unconfirmed: BepiColombo.", 10, INK)
    draw_text(16, 1000, "CONFIRMED = wire-verified  |  OFFICIAL = govt statement  |  REPORTED = claimed, not confirmed", 10, GREY)

def png_bytes():
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += pix[y * W * 3:(y + 1) * W * 3]
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return c
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))

def main():
    build()
    data = png_bytes()
    outs = []
    env = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env:
        outs.append(env)
    outs.append("/output")
    outs.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    seen = set()
    for d in outs:
        if d in seen:
            continue
        seen.add(d)
        try:
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "entry.png"), "wb") as f:
                f.write(data)
        except OSError:
            pass

if __name__ == "__main__":
    main()
