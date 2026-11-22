# news-image-20261121 — rebuild round 5 (leaderboard-driven revision)
# "Saturday 21 November 2026" — one-page newspaper, 37 stories.
# Python 3 stdlib only. No network. Deterministic: two runs are byte-identical.
# Output: /output/entry.png (and out/entry.png next to this script, same bytes).
#
# Design (verified by looking at the three dev-board leaders 22 Nov 2026):
#  - bold anti-aliased classic serif for masthead + headlines (sentence case),
#  - short coloured kicker banners (white caps sans on red/blue) on every card,
#  - 3 hero + 10 medium cards, scenes strictly ABOVE the title, never touching it,
#  - 37 stories total, ALSO ON in two columns, DATE CHECK footer.
# Story facts, numbers and sources come only from GO-REPORT.md /
# research-21nov-fresh.md (verified 22 Nov 2026) — plus, in round 6, the
# Bahrain/Hormuz-attack story from AFP reports verified by the coordinator
# (search 22 Nov ~17:27 WIB): Bahrain says Iran struck a civilian plant,
# two tankers hit off Khasab (UKMTO); IRGC claims US bases hit (claimed).

import binascii
import math
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (250, 243, 227)
INK = (26, 26, 26)
INK_SOFT = (74, 74, 74)
GREY = (128, 128, 128)
RULE = (26, 26, 26)
RED = (185, 28, 28)
RED_DK = (153, 27, 27)
BLUE = (29, 78, 216)
GREEN = (21, 128, 61)
PURPLE = (126, 34, 206)
ORANGE = (194, 65, 12)
TEAL = (15, 118, 110)
DARK = (17, 24, 39)
CREAM = (245, 238, 220)
SEA = (214, 232, 240)
LAND = (232, 217, 176)
LAND_DK = (210, 190, 140)
SKY = (186, 219, 238)
NIGHT = (16, 24, 48)
GOLD = (201, 162, 39)

REGION_COLOR = {
    "Middle East": RED, "Europe": BLUE, "Americas": GREEN, "Asia": PURPLE,
    "Africa": ORANGE, "Oceania": TEAL, "Global": DARK, "World": DARK,
}

# ---------------------------------------------------------------- PNG writer
def _chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    return c + struct.pack(">I", binascii.crc32(typ + data) & 0xFFFFFFFF)

def write_png(path, w, h, rgb):
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) \
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.px), 3):
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b

    def set(self, x, y, col):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = col

    def blend(self, x, y, col, a):
        # a: 0..255 coverage of col over current pixel
        if a <= 0 or not (0 <= x < self.w and 0 <= y < self.h):
            return
        i = (y * self.w + x) * 3
        if a >= 255:
            self.px[i], self.px[i + 1], self.px[i + 2] = col
            return
        ia = 255 - a
        self.px[i] = (col[0] * a + self.px[i] * ia) // 255
        self.px[i + 1] = (col[1] * a + self.px[i + 1] * ia) // 255
        self.px[i + 2] = (col[2] * a + self.px[i + 2] * ia) // 255

    def rect(self, x0, y0, x1, y1, col):
        x0 = max(0, int(x0))
        y0 = max(0, int(y0))
        x1 = min(self.w, int(x1))
        y1 = min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = col
        for y in range(y0, y1):
            base = (y * self.w + x0) * 3
            for x in range(x1 - x0):
                i = base + x * 3
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b

    def hline(self, x0, x1, y, col, t=1):
        self.rect(x0, y, x1, y + t, col)

    def vline(self, x, y0, y1, col, t=1):
        self.rect(x, y0, x + t, y1, col)

    def disc(self, cx, cy, r, col):
        # filled circle, integer rasterisation
        r = int(r)
        if r <= 0:
            return
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(r * r - dy * dy))
            self.rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, col)

    def ring(self, cx, cy, ro, ri, col):
        ro, ri = int(ro), int(ri)
        for dy in range(-ro, ro + 1):
            dxo = int(math.sqrt(ro * ro - dy * dy))
            if abs(dy) < ri:
                dxi = int(math.sqrt(ri * ri - dy * dy))
                self.rect(cx - dxo, cy + dy, cx - dxi, cy + dy + 1, col)
                self.rect(cx + dxi + 1, cy + dy, cx + dxo + 1, cy + dy + 1, col)
            else:
                self.rect(cx - dxo, cy + dy, cx + dxo + 1, cy + dy + 1, col)

    def line(self, x0, y0, x1, y1, col, w=1):
        # thick line as a chain of discs
        dx, dy = x1 - x0, y1 - y0
        dist = math.hypot(dx, dy)
        if dist == 0:
            self.disc(int(x0), int(y0), max(1, w // 2), col)
            return
        steps = max(1, int(dist / max(1, w * 0.6)))
        r = max(1, w // 2)
        for i in range(steps + 1):
            t = i / steps
            self.disc(int(x0 + dx * t), int(y0 + dy * t), r, col)

    def poly(self, pts, col):
        # scanline filled polygon, pts = [(x,y), ...]
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = int(min(ys)), int(max(ys))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, ya = pts[i]
                x1, yb = pts[(i + 1) % n]
                if (ya <= y < yb) or (yb <= y < ya):
                    t = (y - ya) / (yb - ya)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self.rect(int(xs[k]), y, int(xs[k + 1]) + 1, y + 1, col)

    def arc(self, cx, cy, r, a0, a1, col, w=2):
        # arc stroke, angles in degrees, y-down coords, clockwise a0->a1
        a0 = math.radians(a0)
        a1 = math.radians(a1)
        if a1 < a0:
            a1 += 2 * math.pi
        span = a1 - a0
        steps = max(4, int(abs(span) * r / 4))
        prev = None
        for i in range(steps + 1):
            a = a0 + span * i / steps
            p = (cx + r * math.cos(a), cy + r * math.sin(a))
            if prev is not None:
                self.line(int(prev[0]), int(prev[1]), int(p[0]), int(p[1]), col, w)
            prev = p

# ---------------------------------------------------------------- fonts
# Glyph primitives in glyph units. Serif: cap height 100, baseline y=100,
# x-height top y=30, descender to y=125. Sans: cap height 80, baseline y=80.
#  R(x0,y0,x1,y1) rect | D(cx,cy,r) disc | G(cx,cy,ro,ri) ring
#  A(cx,cy,ro,ri,a0,a1) arc, angles deg, y-down, clockwise a0->a1
#  L(x0,y0,x1,y1,w) thick line
SERIF = {
 'A': (76, [('L', 8, 100, 35, 0, 15),
            ('L', 62, 100, 35, 0, 15),
            ('R', 24, 60, 46, 67),
            ('R', 1, 95, 15, 100),
            ('R', 55, 95, 69, 100)]),
 'B': (71, [('R', 6, 0, 26, 100),
            ('R', 3, 0, 29, 5),
            ('R', 3, 95, 29, 100),
            ('A', 24, 28, 30, 19, 270, 90),
            ('A', 24, 72, 34, 23, 270, 90),
            ('R', 24, 22, 44, 29),
            ('R', 24, 66, 48, 73)]),
 'C': (76, [('A', 38, 50, 46, 35, 45, 315), ('R', 60, 10, 72, 17), ('R', 60, 84, 72, 91)]),
 'D': (80, [('R', 6, 0, 26, 100),
            ('R', 3, 0, 29, 5),
            ('R', 3, 95, 29, 100),
            ('A', 24, 50, 50, 39, 270, 90),
            ('R', 24, 2, 52, 9),
            ('R', 24, 92, 52, 99)]),
 'E': (69, [('R', 6, 0, 26, 100),
            ('R', 3, 0, 29, 5),
            ('R', 3, 95, 29, 100),
            ('R', 24, 2, 62, 9),
            ('R', 24, 47, 54, 54),
            ('R', 24, 92, 64, 99)]),
 'F': (65, [('R', 6, 0, 26, 100),
            ('R', 3, 0, 29, 5),
            ('R', 3, 95, 29, 100),
            ('R', 24, 2, 60, 9),
            ('R', 24, 47, 52, 54)]),
 'G': (80, [('A', 38, 50, 46, 35, 45, 315),
            ('R', 60, 10, 72, 17),
            ('R', 60, 84, 72, 91),
            ('R', 38, 52, 66, 59),
            ('R', 58, 50, 66, 80)]),
 'H': (84, [('R', 6, 0, 26, 100),
            ('R', 54, 0, 74, 100),
            ('R', 3, 0, 29, 5),
            ('R', 51, 0, 77, 5),
            ('R', 3, 95, 29, 100),
            ('R', 51, 95, 77, 100),
            ('R', 24, 47, 56, 54)]),
 'I': (46, [('R', 12, 0, 32, 100), ('R', 5, 0, 39, 5), ('R', 5, 95, 39, 100)]),
 'J': (69, [('R', 42, 0, 62, 78), ('R', 35, 0, 69, 5), ('A', 36, 78, 28, 17, 0, 180)]),
 'K': (76, [('R', 6, 0, 26, 100),
            ('R', 3, 0, 29, 5),
            ('R', 3, 95, 29, 100),
            ('L', 24, 50, 60, 0, 13),
            ('L', 30, 45, 64, 100, 13)]),
 'L': (65, [('R', 6, 0, 26, 100),
            ('R', 3, 0, 29, 5),
            ('R', 3, 95, 29, 100),
            ('R', 24, 92, 62, 99)]),
 'M': (90, [('R', 4, 0, 24, 100),
            ('R', 62, 0, 82, 100),
            ('R', 1, 0, 27, 5),
            ('R', 59, 0, 85, 5),
            ('R', 1, 95, 27, 100),
            ('R', 59, 95, 85, 100),
            ('L', 22, 0, 43, 58, 13),
            ('L', 64, 0, 43, 58, 13)]),
 'N': (84, [('R', 4, 0, 24, 100),
            ('R', 56, 0, 76, 100),
            ('R', 1, 0, 27, 5),
            ('R', 53, 0, 79, 5),
            ('R', 1, 95, 27, 100),
            ('R', 53, 95, 79, 100),
            ('L', 22, 0, 58, 100, 13)]),
 'O': (82, [('G', 38, 50, 48, 37)]),
 'P': (69, [('R', 6, 0, 26, 100),
            ('R', 3, 0, 29, 5),
            ('R', 3, 95, 29, 100),
            ('A', 24, 32, 32, 21, 270, 90),
            ('R', 24, 2, 50, 9),
            ('R', 24, 56, 50, 63)]),
 'Q': (84, [('G', 38, 50, 48, 37), ('L', 52, 72, 70, 100, 12)]),
 'R': (74, [('R', 6, 0, 26, 100),
            ('R', 3, 0, 29, 5),
            ('R', 3, 95, 29, 100),
            ('A', 24, 32, 32, 21, 270, 90),
            ('R', 24, 2, 50, 9),
            ('R', 24, 56, 50, 63),
            ('L', 34, 58, 66, 100, 13)]),
 'S': (74, [('A', 38, 28, 24, 13, 90, 300), ('A', 38, 72, 24, 13, 270, 120)]),
 'T': (84, [('R', 4, 2, 76, 9), ('R', 30, 10, 50, 100), ('R', 25, 95, 55, 100)]),
 'U': (84, [('R', 6, 0, 26, 72), ('R', 54, 0, 74, 72), ('A', 40, 72, 32, 21, 0, 180)]),
 'V': (84, [('L', 8, 0, 40, 100, 15), ('L', 72, 0, 40, 100, 15)]),
 'W': (84, [('L', 4, 0, 22, 100, 13),
            ('L', 22, 100, 40, 30, 13),
            ('L', 40, 30, 58, 100, 13),
            ('L', 58, 100, 76, 0, 13)]),
 'X': (82, [('L', 8, 0, 72, 100, 14), ('L', 72, 0, 8, 100, 14)]),
 'Y': (80, [('L', 8, 0, 40, 52, 14),
            ('L', 72, 0, 40, 52, 14),
            ('R', 30, 52, 50, 100),
            ('R', 25, 95, 55, 100)]),
 'Z': (78, [('R', 4, 2, 72, 9), ('R', 4, 92, 72, 99), ('L', 66, 8, 10, 92, 13)]),
 'a': (67, [('G', 26, 65, 33, 22), ('R', 46, 30, 64, 100), ('R', 43, 95, 67, 100)]),
 'b': (67, [('R', 6, 0, 24, 100),
            ('R', 3, 0, 27, 5),
            ('R', 3, 95, 27, 100),
            ('A', 22, 65, 33, 22, 270, 90),
            ('R', 22, 34, 48, 41),
            ('R', 22, 90, 48, 97)]),
 'c': (63, [('A', 30, 65, 33, 22, 45, 315), ('R', 52, 40, 62, 47), ('R', 52, 84, 62, 91)]),
 'd': (71, [('A', 40, 65, 33, 22, 90, 270),
            ('R', 50, 0, 68, 100),
            ('R', 47, 0, 71, 5),
            ('R', 47, 95, 71, 100),
            ('R', 22, 34, 52, 41),
            ('R', 22, 90, 52, 97)]),
 'e': (65, [('A', 30, 65, 33, 22, 70, 20), ('R', 2, 60, 56, 67)]),
 'f': (56, [('R', 24, 10, 42, 100), ('A', 26, 24, 22, 11, 180, 360), ('R', 8, 46, 52, 53)]),
 'g': (67, [('G', 28, 65, 33, 22),
            ('R', 46, 30, 64, 104),
            ('A', 38, 104, 20, 10, 0, 180),
            ('R', 8, 100, 20, 112)]),
 'h': (69, [('R', 6, 0, 24, 100),
            ('R', 3, 0, 27, 5),
            ('R', 3, 95, 27, 100),
            ('A', 35, 50, 27, 16, 180, 360),
            ('R', 46, 30, 64, 100),
            ('R', 43, 95, 67, 100)]),
 'i': (43, [('R', 20, 30, 38, 100), ('D', 29, 12, 7), ('R', 17, 95, 41, 100)]),
 'j': (48, [('R', 28, 30, 46, 108), ('D', 37, 12, 7), ('A', 24, 108, 22, 11, 0, 180)]),
 'k': (63, [('R', 6, 0, 24, 100),
            ('R', 3, 0, 27, 5),
            ('R', 3, 95, 27, 100),
            ('L', 22, 62, 56, 30, 12),
            ('L', 30, 56, 58, 100, 12)]),
 'l': (43, [('R', 20, 0, 38, 100), ('R', 17, 95, 41, 100)]),
 'm': (99, [('R', 3, 30, 21, 100),
            ('R', 1, 95, 23, 100),
            ('A', 30, 50, 24, 13, 180, 360),
            ('R', 39, 48, 57, 100),
            ('A', 64, 50, 24, 13, 180, 360),
            ('R', 73, 30, 91, 100),
            ('R', 71, 95, 93, 100)]),
 'n': (69, [('R', 6, 30, 24, 100),
            ('R', 3, 95, 27, 100),
            ('A', 35, 50, 27, 16, 180, 360),
            ('R', 46, 30, 64, 100),
            ('R', 43, 95, 67, 100)]),
 'o': (67, [('G', 30, 65, 33, 22)]),
 'p': (67, [('R', 6, 30, 24, 125),
            ('A', 22, 65, 33, 22, 270, 90),
            ('R', 22, 34, 48, 41),
            ('R', 22, 90, 48, 97)]),
 'q': (71, [('A', 40, 65, 33, 22, 90, 270),
            ('R', 50, 30, 68, 125),
            ('R', 24, 34, 52, 41),
            ('R', 24, 90, 52, 97)]),
 'r': (58, [('R', 6, 30, 24, 100),
            ('R', 3, 95, 27, 100),
            ('A', 32, 50, 22, 11, 180, 330),
            ('R', 46, 38, 58, 58)]),
 's': (63, [('A', 30, 46, 22, 11, 90, 300), ('A', 30, 84, 22, 11, 270, 120)]),
 't': (56, [('R', 22, 8, 40, 100), ('R', 6, 42, 54, 49), ('A', 30, 100, 16, 7, 0, 90)]),
 'u': (69, [('R', 6, 30, 24, 72), ('R', 42, 30, 60, 100), ('A', 33, 72, 25, 14, 0, 180)]),
 'v': (67, [('L', 8, 30, 30, 100, 13), ('L', 54, 30, 30, 100, 13)]),
 'w': (69, [('L', 4, 30, 18, 100, 12),
            ('L', 18, 100, 31, 48, 12),
            ('L', 31, 48, 44, 100, 12),
            ('L', 44, 100, 58, 30, 12)]),
 'x': (65, [('L', 8, 30, 56, 100, 13), ('L', 56, 30, 8, 100, 13)]),
 'y': (67, [('L', 8, 30, 30, 88, 13), ('L', 54, 30, 30, 88, 13), ('L', 30, 88, 16, 125, 12)]),
 'z': (65, [('R', 6, 32, 56, 39), ('R', 6, 92, 56, 99), ('L', 50, 38, 12, 92, 11)]),
 '0': (69, [('G', 32, 50, 42, 31)]),
 '1': (67, [('R', 34, 0, 54, 100), ('L', 52, 0, 22, 24, 12), ('R', 21, 95, 63, 100)]),
 '2': (69, [('A', 32, 32, 32, 21, 90, 330), ('L', 58, 18, 10, 92, 13), ('R', 6, 92, 62, 99)]),
 '3': (69, [('A', 32, 30, 30, 19, 270, 90),
            ('A', 32, 70, 32, 21, 270, 90),
            ('R', 22, 47, 46, 54)]),
 '4': (69, [('R', 40, 0, 60, 100), ('L', 52, 0, 10, 62, 13), ('R', 6, 56, 62, 63)]),
 '5': (67, [('R', 8, 2, 60, 9),
            ('R', 6, 0, 26, 52),
            ('A', 34, 68, 32, 21, 270, 90),
            ('R', 8, 92, 60, 99)]),
 '6': (69, [('G', 32, 66, 34, 23), ('L', 58, 10, 26, 48, 13)]),
 '7': (67, [('R', 6, 2, 62, 9), ('L', 56, 8, 26, 100, 13)]),
 '8': (69, [('G', 32, 32, 30, 19), ('G', 32, 70, 32, 21)]),
 '9': (69, [('G', 32, 34, 34, 23), ('R', 41, 44, 61, 100)]),
 '.': (34, [('D', 30, 96, 6)]),
 ',': (34, [('D', 30, 96, 6), ('L', 30, 100, 22, 116, 8)]),
 "'": (30, [('L', 28, 2, 20, 28, 10)]),
 '’': (30, [('L', 28, 2, 20, 28, 10)]),
 '"': (44, [('L', 20, 2, 12, 28, 9), ('L', 38, 2, 30, 28, 9)]),
 ':': (34, [('D', 30, 42, 6), ('D', 30, 92, 6)]),
 ';': (34, [('D', 30, 42, 6), ('D', 30, 92, 6), ('L', 30, 96, 22, 114, 8)]),
 '!': (40, [('R', 23, 0, 41, 72), ('D', 32, 92, 7)]),
 '?': (58, [('A', 32, 32, 28, 17, 150, 30), ('L', 46, 50, 32, 72, 12), ('D', 32, 92, 7)]),
 '-': (60, [('R', 8, 60, 52, 67)]),
 '–': (66, [('R', 4, 60, 62, 67)]),
 '—': (74, [('R', 2, 60, 72, 67)]),
 '(': (40, [('A', 52, 50, 52, 41, 120, 240)]),
 ')': (40, [('A', 6, 50, 52, 41, 300, 60)]),
 '%': (72, [('G', 22, 28, 18, 9), ('G', 44, 72, 18, 9), ('L', 52, 4, 14, 96, 9)]),
 '$': (64, [('A', 32, 30, 22, 11, 90, 300),
            ('A', 32, 70, 22, 11, 270, 120),
            ('R', 25, 0, 39, 100)]),
 '&': (70, [('G', 30, 68, 26, 15), ('L', 52, 0, 12, 96, 11), ('A', 30, 28, 22, 11, 180, 360)]),
 '/': (52, [('L', 48, 0, 16, 100, 11)]),
 '+': (64, [('R', 26, 28, 38, 72), ('R', 12, 44, 52, 56)]),
 '*': (56, [('L', 30, 8, 30, 52, 8), ('L', 11, 20, 49, 40, 8), ('L', 49, 20, 11, 40, 8)]),
 '•': (40, [('D', 30, 58, 8)]),
 '◆': (56, [('R', 26, 38, 34, 46),
            ('R', 18, 46, 42, 54),
            ('R', 12, 54, 48, 62),
            ('R', 18, 62, 42, 70),
            ('R', 26, 70, 34, 78)]),
 '✓': (60, [('L', 8, 58, 26, 78, 10), ('L', 26, 78, 54, 30, 10)]),
 '°': (44, [('G', 30, 22, 12, 6)]),
 '·': (40, [('D', 30, 58, 6)]),
 ' ': (30, []),
}
SERIF_CELL, SERIF_BASE = 125, 100

# Bold sans, caps only (kickers, labels, numbers strip). Cap height 80 units.
SANS = {
 'A': (60, [('L', 6, 80, 30, 0, 13), ('L', 54, 80, 30, 0, 13), ('R', 18, 48, 42, 58)]),
 'B': (58, [('R', 6, 0, 20, 80), ('R', 20, 0, 48, 12), ('R', 20, 34, 46, 46),
            ('R', 20, 68, 50, 80), ('R', 40, 12, 54, 34), ('R', 42, 46, 56, 68)]),
 'C': (56, [('R', 14, 0, 54, 12), ('R', 14, 68, 54, 80), ('R', 14, 0, 26, 80)]),
 'D': (58, [('R', 6, 0, 20, 80), ('R', 20, 0, 48, 12), ('R', 20, 68, 48, 80),
            ('R', 44, 12, 56, 68)]),
 'E': (56, [('R', 6, 0, 20, 80), ('R', 20, 0, 54, 12), ('R', 20, 34, 48, 46),
            ('R', 20, 68, 56, 80)]),
 'F': (54, [('R', 6, 0, 20, 80), ('R', 20, 0, 54, 12), ('R', 20, 34, 48, 46)]),
 'G': (58, [('R', 14, 0, 54, 12), ('R', 14, 68, 54, 80), ('R', 14, 0, 26, 80),
            ('R', 34, 44, 54, 54), ('R', 44, 44, 54, 68)]),
 'H': (62, [('R', 6, 0, 20, 80), ('R', 42, 0, 56, 80), ('R', 20, 34, 42, 46)]),
 'I': (58, [('R', 22, 0, 36, 80), ('R', 8, 0, 50, 12), ('R', 8, 68, 50, 80)]),
 'J': (62, [('R', 28, 0, 60, 12), ('R', 40, 0, 54, 64), ('R', 14, 64, 54, 78),
            ('R', 14, 52, 26, 66)]),
 'K': (60, [('R', 6, 0, 20, 80), ('L', 20, 44, 54, 0, 13), ('L', 28, 38, 56, 80, 13)]),
 'L': (56, [('R', 6, 0, 20, 80), ('R', 20, 68, 56, 80)]),
 'M': (64, [('R', 6, 0, 20, 80), ('R', 44, 0, 58, 80), ('L', 20, 0, 32, 52, 12),
            ('L', 44, 0, 32, 52, 12)]),
 'N': (64, [('R', 6, 0, 20, 80), ('R', 44, 0, 58, 80), ('L', 20, 0, 44, 80, 12)]),
 'O': (60, [('R', 12, 0, 48, 12), ('R', 12, 68, 48, 80), ('R', 12, 0, 24, 80),
            ('R', 36, 0, 48, 80)]),
 'P': (56, [('R', 6, 0, 20, 80), ('R', 20, 0, 50, 12), ('R', 20, 34, 50, 46),
            ('R', 38, 12, 52, 34)]),
 'Q': (62, [('R', 12, 0, 48, 12), ('R', 12, 68, 48, 80), ('R', 12, 0, 24, 80),
            ('R', 36, 0, 48, 80), ('L', 38, 58, 56, 84, 11)]),
 'R': (58, [('R', 6, 0, 20, 80), ('R', 20, 0, 50, 12), ('R', 20, 34, 50, 46),
            ('R', 38, 12, 52, 34), ('L', 32, 40, 56, 80, 12)]),
 'S': (56, [('R', 14, 0, 50, 12), ('R', 14, 0, 26, 40), ('R', 14, 34, 50, 46),
            ('R', 38, 46, 50, 80), ('R', 14, 68, 50, 80)]),
 'T': (60, [('R', 4, 0, 56, 12), ('R', 23, 12, 37, 80)]),
 'U': (62, [('R', 6, 0, 20, 68), ('R', 42, 0, 56, 68), ('R', 6, 68, 56, 80)]),
 'V': (60, [('L', 6, 0, 30, 80, 14), ('L', 54, 0, 30, 80, 14)]),
 'W': (62, [('L', 2, 0, 15, 80, 12), ('L', 15, 80, 30, 28, 12),
            ('L', 30, 28, 45, 80, 12), ('L', 45, 80, 58, 0, 12)]),
 'X': (60, [('L', 6, 0, 54, 80, 13), ('L', 54, 0, 6, 80, 13)]),
 'Y': (60, [('L', 6, 0, 30, 44, 13), ('L', 54, 0, 30, 44, 13), ('R', 23, 44, 37, 80)]),
 'Z': (60, [('R', 4, 0, 56, 12), ('R', 4, 68, 56, 80), ('L', 50, 10, 10, 70, 12)]),
 '0': (60, [('R', 12, 0, 48, 12), ('R', 12, 68, 48, 80), ('R', 12, 0, 24, 80),
            ('R', 36, 0, 48, 80)]),
 '1': (58, [('R', 28, 0, 42, 80), ('L', 42, 0, 16, 22, 11), ('R', 12, 68, 52, 80)]),
 '2': (58, [('R', 8, 0, 52, 12), ('R', 40, 12, 52, 40), ('R', 8, 34, 52, 46),
            ('R', 8, 46, 20, 68), ('R', 8, 68, 52, 80)]),
 '3': (56, [('R', 8, 0, 50, 12), ('R', 38, 12, 50, 34), ('R', 20, 34, 50, 46),
            ('R', 38, 46, 50, 68), ('R', 8, 68, 50, 80)]),
 '4': (58, [('R', 38, 0, 52, 80), ('L', 52, 0, 8, 56, 12), ('R', 4, 48, 56, 60)]),
 '5': (56, [('R', 8, 0, 52, 12), ('R', 8, 0, 20, 40), ('R', 8, 34, 50, 46),
            ('R', 38, 46, 50, 68), ('R', 8, 68, 50, 80)]),
 '6': (56, [('R', 8, 0, 52, 12), ('R', 8, 0, 20, 80), ('R', 8, 34, 50, 46),
            ('R', 38, 46, 50, 68), ('R', 8, 68, 50, 80)]),
 '7': (56, [('R', 6, 0, 56, 12), ('L', 50, 10, 22, 80, 12)]),
 '8': (58, [('R', 10, 0, 50, 12), ('R', 10, 34, 50, 46), ('R', 10, 68, 50, 80),
            ('R', 10, 0, 22, 80), ('R', 38, 0, 50, 80)]),
 '9': (56, [('R', 8, 0, 52, 12), ('R', 8, 0, 20, 34), ('R', 38, 0, 50, 80),
            ('R', 8, 34, 50, 46), ('R', 8, 68, 50, 80)]),
 ':': (32, [('D', 30, 26, 6), ('D', 30, 62, 6)]),
 '.': (32, [('D', 30, 70, 6)]),
 ',': (32, [('D', 30, 70, 6), ('L', 30, 74, 22, 86, 7)]),
 '-': (56, [('R', 8, 36, 48, 46)]),
 '/': (52, [('L', 44, 0, 12, 80, 10)]),
 '%': (60, [('G', 18, 22, 14, 7), ('G', 40, 58, 14, 7), ('L', 48, 4, 10, 76, 8)]),
 '$': (56, [('R', 14, 0, 48, 12), ('R', 14, 0, 26, 40), ('R', 14, 34, 48, 46),
            ('R', 36, 46, 48, 80), ('R', 14, 68, 48, 80), ('R', 26, 0, 34, 80)]),
 '*': (52, [('L', 30, 8, 30, 52, 7), ('L', 11, 20, 49, 40, 7), ('L', 49, 20, 11, 40, 7)]),
 '(': (36, [('A', 48, 40, 44, 32, 120, 240)]),
 ')': (36, [('A', 8, 40, 44, 32, 300, 60)]),
 '\u00b7': (36, [('D', 30, 40, 6)]),
 '\u00b0': (40, [('G', 30, 18, 10, 5)]),
 '+': (60, [('R', 24, 22, 34, 58), ('R', 10, 32, 50, 42)]),
 '=': (58, [('R', 8, 32, 50, 42), ('R', 8, 50, 50, 60)]),
 '!': (44, [('R', 22, 0, 36, 56), ('D', 29, 70, 7)]),
 '?': (52, [('A', 29, 26, 24, 12, 150, 30), ('L', 40, 42, 29, 58, 10), ('D', 29, 70, 7)]),
 ' ': (30, []),
}
SANS_CELL, SANS_BASE = 80, 80

# ---------------------------------------------------------------- font engine
# Each glyph is rendered once per (font, char, size) into a coverage mask
# (analytic anti-aliasing, supersampled 2x for sizes >= 20), then blitted.
_GLYPH_CACHE = {}

def _clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)

def _prim_cov(prim, sx, sy, ss):
    # coverage of one subpixel centre (sx, sy) in PIXEL coords; ss = supersample
    k = prim[0]
    if k == 'R':
        _, x0, y0, x1, y1 = prim
        ax = min(sx + 0.5 / ss, x1) - max(sx - 0.5 / ss, x0)
        ay = min(sy + 0.5 / ss, y1) - max(sy - 0.5 / ss, y0)
        if ax <= 0.0 or ay <= 0.0:
            return 0.0
        return _clamp01(ax * ss) * _clamp01(ay * ss)
    if k == 'D':
        _, cx, cy, r = prim
        d = math.hypot(sx - cx, sy - cy)
        return _clamp01(r + 0.5 / ss - d)
    if k == 'G':
        _, cx, cy, ro, ri = prim
        d = math.hypot(sx - cx, sy - cy)
        co = _clamp01(ro + 0.5 / ss - d)
        ci = _clamp01(ri - 0.5 / ss - d)
        c = co - ci
        return 0.0 if c < 0.0 else (1.0 if c > 1.0 else c)
    if k == 'A':
        _, cx, cy, ro, ri, a0, a1 = prim
        d = math.hypot(sx - cx, sy - cy)
        co = _clamp01(ro + 0.5 / ss - d)
        if co <= 0.0:
            return 0.0
        ci = _clamp01(ri - 0.5 / ss - d)
        c = co - ci
        if c <= 0.0:
            return 0.0
        ang = math.degrees(math.atan2(sy - cy, sx - cx)) % 360.0
        a0m, a1m = a0 % 360.0, a1 % 360.0
        if a1m < a0m:
            a1m += 360.0
        a = ang
        if a < a0m:
            a += 360.0
        if a > a1m:
            return 0.0
        return c
    # 'L' thick line
    _, x0, y0, x1, y1, w = prim
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    if L2 == 0:
        d = math.hypot(sx - x0, sy - y0)
    else:
        t = ((sx - x0) * dx + (sy - y0) * dy) / L2
        t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
        d = math.hypot(sx - (x0 + dx * t), sy - (y0 + dy * t))
    return _clamp01(w / 2.0 + 0.5 / ss - d)

def _prim_bbox(prim, s):
    k = prim[0]
    if k == 'R':
        _, x0, y0, x1, y1 = prim
        return x0 * s, y0 * s, x1 * s, y1 * s
    if k == 'D':
        _, cx, cy, r = prim
        return (cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s
    if k in ('G', 'A'):
        _, cx, cy, ro, ri = prim[:5] if k == 'G' else prim[:5]
        return (cx - ro) * s, (cy - ro) * s, (cx + ro) * s, (cy + ro) * s
    _, x0, y0, x1, y1, w = prim
    hw = w / 2.0 + 1.0
    return (min(x0, x1) - hw) * s, (min(y0, y1) - hw) * s, \
        (max(x0, x1) + hw) * s, (max(y0, y1) + hw) * s

def _scale_prim(prim, s):
    k = prim[0]
    if k == 'R':
        _, x0, y0, x1, y1 = prim
        return ('R', x0 * s, y0 * s, x1 * s, y1 * s)
    if k == 'D':
        _, cx, cy, r = prim
        return ('D', cx * s, cy * s, r * s)
    if k == 'G':
        _, cx, cy, ro, ri = prim
        return ('G', cx * s, cy * s, ro * s, ri * s)
    if k == 'A':
        _, cx, cy, ro, ri, a0, a1 = prim
        return ('A', cx * s, cy * s, ro * s, ri * s, a0, a1)
    _, x0, y0, x1, y1, w = prim
    return ('L', x0 * s, y0 * s, x1 * s, y1 * s, w * s)

def _render_glyph(font, cell, base, ch, size):
    key = (id(font), ch, round(size, 2))
    hit = _GLYPH_CACHE.get(key)
    if hit is not None:
        return hit
    adv, prims = font.get(ch, font.get(' ', (28, [])))
    s = size / float(base)
    ss = 2 if size >= 20 else 1
    if not prims:
        res = (b'', 0, 0, 0, 0, adv * s)
        _GLYPH_CACHE[key] = res
        return res
    prims = [_scale_prim(p, s) for p in prims]
    x0 = min(_prim_bbox(p, 1.0)[0] for p in prims)
    y0 = min(_prim_bbox(p, 1.0)[1] for p in prims)
    x1 = max(_prim_bbox(p, 1.0)[2] for p in prims)
    y1 = max(_prim_bbox(p, 1.0)[3] for p in prims)
    fx0, fy0 = int(math.floor(x0)), int(math.floor(y0))
    fx1, fy1 = int(math.ceil(x1)), int(math.ceil(y1))
    mw, mh = fx1 - fx0, fy1 - fy0
    sw, sh = mw * ss, mh * ss
    buf = [0.0] * (sw * sh)
    for prim in prims:
        bx0, by0, bx1, by1 = _prim_bbox(prim, 1.0)
        si0 = max(0, int(math.floor(bx0 * ss)) - fx0 * ss)
        sj0 = max(0, int(math.floor(by0 * ss)) - fy0 * ss)
        si1 = min(sw, int(math.ceil(bx1 * ss)) - fx0 * ss)
        sj1 = min(sh, int(math.ceil(by1 * ss)) - fy0 * ss)
        for j in range(sj0, sj1):
            sy = fy0 + (j + 0.5) / ss
            row = j * sw
            for i in range(si0, si1):
                sx = fx0 + (i + 0.5) / ss
                c = _prim_cov(prim, sx, sy, ss)
                if c > 0.0 and c > buf[row + i]:
                    buf[row + i] = c
    mask = bytearray(mw * mh)
    if ss == 1:
        for k in range(mw * mh):
            mask[k] = int(buf[k] * 255.0 + 0.5)
    else:
        for y in range(mh):
            for x in range(mw):
                tot = 0.0
                for dj in range(ss):
                    row = (y * ss + dj) * sw + x * ss
                    for di in range(ss):
                        tot += buf[row + di]
                mask[y * mw + x] = int(tot / (ss * ss) * 255.0 + 0.5)
    res = (bytes(mask), mw, mh, fx0, fy0, adv * s)
    _GLYPH_CACHE[key] = res
    return res

SERIF_F = (SERIF, SERIF_CELL, SERIF_BASE)
SANS_F = (SANS, SANS_CELL, SANS_BASE)

def text_width(text, font, size, track=0.0):
    d, _, base = font
    s = size / float(base)
    w = 0.0
    for ch in text:
        adv = d.get(ch, d.get(' ', (28, [])))[0]
        w += adv * s + track
    return w - track if text else 0.0

def draw_text(cv, x, y, text, font, size, col, align='l', slant=0.0, track=0.0):
    # (x, y): pen position; y is the baseline. align l/c/r.
    d, _, base = font
    s = size / float(base)
    w = text_width(text, font, size, track)
    if align == 'c':
        x -= w / 2.0
    elif align == 'r':
        x -= w
    pen = x
    base_y = int(round(y))
    for ch in text:
        mask, mw, mh, fx0, fy0, adv = _render_glyph(d, 0, base, ch, size)
        if mw and mh:
            ox = int(round(pen)) + fx0
            oy = base_y - int(round(base * s)) + fy0
            for my in range(mh):
                cy = oy + my
                if cy < 0 or cy >= cv.h:
                    continue
                dxr = int((base_y - cy) * slant) if slant else 0
                row = my * mw
                for mx in range(mw):
                    a = mask[row + mx]
                    if a:
                        cv.blend(ox + mx + dxr, cy, col, a)
        pen += adv + track
    return pen

def wrap_text(text, font, size, max_w, track=0.0):
    words = text.split(' ')
    lines, cur = [], ''
    for wd in words:
        trial = wd if not cur else cur + ' ' + wd
        if text_width(trial, font, size, track) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines

def draw_lines(cv, x, y, lines, font, size, col, align='l', lh=None, slant=0.0,
               track=0.0):
    if lh is None:
        lh = size * 1.14
    for ln in lines:
        draw_text(cv, x, y, ln, font, size, col, align=align, slant=slant,
                  track=track)
        y += lh
    return y

# ---------------------------------------------------------------- scenes
def ellipse(cv, cx, cy, rx, ry, col):
    pts = []
    for i in range(28):
        a = 2 * math.pi * i / 28
        pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    cv.poly(pts, col)

def _band(cv, x, y, w, h, bg):
    cv.rect(x, y, x + w, y + h, bg)

def scene_cop31(cv, x, y, w, h):
    _band(cv, x, y, w, h, (222, 228, 232))
    # hall: back wall, rows of desks, flags, wall clock
    cv.rect(x, y, x + w, y + 26, (178, 190, 200))
    cv.rect(x, y + 26, x + w, y + 30, (120, 132, 142))
    for i in range(5):
        fx = x + 14 + i * 62
        cv.rect(fx, y + 8, fx + 34, y + 22, (240, 240, 235))
        cv.rect(fx + 4, y + 11, fx + 12, y + 19, (185, 28, 28))
        cv.rect(fx + 16, y + 11, fx + 24, y + 19, (29, 78, 216))
        cv.rect(fx + 27, y + 11, fx + 31, y + 19, (21, 128, 61))
    # desks
    for r in range(3):
        dy = y + 44 + r * 26
        cv.rect(x + 10, dy, x + w - 10, dy + 12, (146, 118, 84))
        cv.rect(x + 10, dy, x + w - 10, dy + 3, (120, 96, 64))
        for i in range(6):
            px = x + 22 + i * 48
            cv.disc(px, dy - 6, 5, (60, 60, 60))
            cv.rect(px - 4, dy - 10, px + 4, dy - 2, (200, 200, 200))
    # wall clock, right
    cx, cy = x + w - 44, y + 62
    cv.disc(cx, cy, 26, (250, 250, 248))
    cv.ring(cx, cy, 26, 23, INK)
    cv.line(cx, cy, cx, cy - 16, INK, 3)
    cv.line(cx, cy, cx + 12, cy + 6, INK, 3)
    cv.disc(cx, cy, 3, RED)

def scene_riyadh(cv, x, y, w, h):
    _band(cv, x, y, w, h, NIGHT)
    # stars
    for sx, sy in ((0.08, 0.15), (0.22, 0.08), (0.45, 0.12), (0.62, 0.07),
                   (0.78, 0.16), (0.9, 0.09), (0.33, 0.2), (0.55, 0.22)):
        cv.disc(int(x + w * sx), int(y + h * sy), 2, (240, 240, 220))
    # skyline
    base = y + h
    cv.rect(x, base - 34, x + 52, base, (8, 12, 26))
    cv.rect(x + 60, base - 52, x + 96, base, (8, 12, 26))
    cv.rect(x + 104, base - 26, x + 150, base, (8, 12, 26))
    cv.rect(x + 158, base - 44, x + 196, base, (8, 12, 26))
    cv.rect(x + 204, base - 30, x + 250, base, (8, 12, 26))
    cv.rect(x + 258, base - 58, x + 296, base, (8, 12, 26))
    # Kingdom Centre tower (arched top)
    tx = x + w - 58
    cv.rect(tx, base - 78, tx + 22, base, (8, 12, 26))
    cv.arc(tx + 11, base - 78, 11, 180, 360, (8, 12, 26), 6)
    for wx in range(x + 8, x + w - 8, 14):
        cv.rect(wx, base - 18, wx + 4, base - 12, (255, 214, 120))
    # three intercept trails
    for t in ((0.18, 0.62, 0.30, 0.30), (0.45, 0.68, 0.55, 0.26),
              (0.72, 0.60, 0.84, 0.32)):
        x0, y0, x1, y1 = x + w * t[0], y + h * t[1], x + w * t[2], y + h * t[3]
        cv.line(int(x0), int(y0), int(x1), int(y1), (255, 196, 90), 3)
        cv.disc(int(x1), int(y1), 7, (255, 220, 140))
        cv.disc(int(x1), int(y1), 3, (255, 255, 255))
        for dx, dy in ((-9, 0), (9, 0), (0, -9), (0, 9)):
            cv.line(int(x1), int(y1), int(x1 + dx), int(y1 + dy), (255, 220, 140), 2)

def scene_peru(cv, x, y, w, h):
    _band(cv, x, y, w, h, SKY)
    # Andes
    cv.poly([(x, y + h), (x + 70, y + 18), (x + 130, y + h)], (122, 96, 66))
    cv.poly([(x + 90, y + h), (x + 190, y + 8), (x + 290, y + h)], (96, 76, 54))
    cv.poly([(x + 170, y + 8), (x + 190, y + 8), (x + 200, y + 30),
             (x + 180, y + 30)], (250, 250, 248))
    cv.poly([(x + 52, y + 18), (x + 70, y + 18), (x + 78, y + 38),
             (x + 60, y + 38)], (250, 250, 248))
    # ground + crack
    cv.rect(x, y + h - 22, x + w, y + h, (168, 132, 88))
    cv.line(x + 30, y + h - 22, x + 80, y + h - 10, (60, 44, 28), 3)
    cv.line(x + 80, y + h - 10, x + 130, y + h - 20, (60, 44, 28), 3)
    cv.line(x + 130, y + h - 20, x + 200, y + h - 8, (60, 44, 28), 3)
    cv.line(x + 200, y + h - 8, x + 260, y + h - 18, (60, 44, 28), 3)
    # seismograph trace
    pts = [(x + 12, y + 52), (x + 40, y + 52), (x + 52, y + 38), (x + 64, y + 66),
           (x + 76, y + 44), (x + 88, y + 60), (x + 100, y + 52)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 2)
    # small houses
    for hx in (x + 220, x + 250, x + 280):
        cv.rect(hx, y + h - 38, hx + 20, y + h - 22, (200, 90, 70))
        cv.poly([(hx - 2, y + h - 38), (hx + 10, y + h - 48), (hx + 22, y + h - 38)],
                (120, 60, 40))

def scene_bridge(cv, x, y, w, h):
    _band(cv, x, y, w, h, SKY)
    cv.rect(x, y + h - 16, x + w, y + h, (120, 170, 210))
    cv.line(x + 6, y + 22, x + w - 6, y + 22, (60, 60, 60), 4)
    cv.arc(x + w // 2, y + 22, 52, 180, 360, (150, 40, 40), 4)
    for px in range(x + 20, x + w - 10, 22):
        cv.line(px, y + 22, px, y + h - 16, (90, 90, 90), 2)
    cv.rect(x + 8, y + h - 30, x + 26, y + h - 16, (200, 200, 200))
    cv.rect(x + w - 30, y + h - 30, x + w - 12, y + h - 16, (200, 200, 200))

def scene_hormuz(cv, x, y, w, h):
    _band(cv, x, y, w, h, (150, 195, 225))
    cv.rect(x, y + h - 18, x + w, y + h, (36, 90, 150))
    cv.line(x, y + h - 18, x + w, y + h - 18, (255, 255, 255), 2)
    # tanker
    cv.rect(x + 18, y + h - 34, x + 120, y + h - 18, (40, 40, 40))
    cv.rect(x + 30, y + h - 46, x + 52, y + h - 34, (120, 40, 40))
    cv.rect(x + 88, y + h - 42, x + 96, y + h - 34, (200, 200, 200))
    # smoke + fire on deck
    cv.disc(x + 44, y + h - 52, 7, (90, 90, 90))
    cv.disc(x + 56, y + h - 58, 6, (120, 120, 120))
    cv.disc(x + 40, y + h - 38, 6, (255, 140, 40))
    cv.disc(x + 48, y + h - 36, 4, (255, 220, 90))
    # drone above
    dx, dy = x + w - 48, y + 16
    cv.rect(dx - 10, dy - 3, dx + 10, dy + 3, (30, 30, 30))
    cv.line(dx - 16, dy - 8, dx + 16, dy - 8, (30, 30, 30), 2)
    cv.line(dx - 16, dy + 8, dx + 16, dy + 8, (30, 30, 30), 2)
    cv.disc(dx - 16, dy - 8, 3, (120, 120, 120))
    cv.disc(dx + 16, dy - 8, 3, (120, 120, 120))
    cv.disc(dx - 16, dy + 8, 3, (120, 120, 120))
    cv.disc(dx + 16, dy + 8, 3, (120, 120, 120))
    cv.line(dx, dy + 4, dx, dy + 16, (30, 30, 30), 2)

def scene_bahrain(cv, x, y, w, h):
    # map of Bahrain / Strait of Hormuz: sea, Arabia (left), Iran (top
    # right), Bahrain island pinned, two tankers on the strait, one afire.
    _band(cv, x, y, w, h, (168, 205, 228))
    # Arabian peninsula (left/bottom)
    cv.poly([(x, y + h), (x, y + h * 0.42), (x + w * 0.30, y + h * 0.52),
             (x + w * 0.44, y + h * 0.78), (x + w * 0.38, y + h)],
            (232, 217, 176))
    # Iran (top right)
    cv.poly([(x + w * 0.52, y), (x + w, y), (x + w, y + h * 0.34),
             (x + w * 0.72, y + h * 0.30), (x + w * 0.58, y + h * 0.16)],
            (210, 190, 140))
    # Bahrain island + pin
    bx, by = int(x + w * 0.40), int(y + h * 0.46)
    ellipse(cv, bx, by, 7, 5, (232, 217, 176))
    cv.disc(bx, by, 5, RED)
    cv.ring(bx, by, 5, 3, (255, 255, 255))
    # dashed tanker route through the strait
    for t in range(0, 11):
        fx = t / 10.0
        px = x + w * (0.48 + 0.40 * fx)
        py = y + h * (0.52 + 0.22 * fx)
        cv.disc(int(px), int(py), 2, RED)
    # tanker 1, afire, mid-strait
    t1x, t1y = int(x + w * 0.62), int(y + h * 0.66)
    cv.rect(t1x - 34, t1y - 6, t1x + 34, t1y + 6, (40, 40, 40))
    cv.rect(t1x - 22, t1y - 14, t1x - 6, t1y - 6, (120, 40, 40))
    cv.disc(t1x - 14, t1y - 20, 7, (90, 90, 90))
    cv.disc(t1x - 4, t1y - 26, 6, (120, 120, 120))
    cv.disc(t1x - 12, t1y - 10, 6, (255, 140, 40))
    cv.disc(t1x - 4, t1y - 8, 4, (255, 220, 90))
    # tanker 2, east of Khasab
    t2x, t2y = int(x + w * 0.86), int(y + h * 0.80)
    cv.rect(t2x - 30, t2y - 5, t2x + 30, t2y + 5, (60, 60, 60))
    cv.rect(t2x + 8, t2y - 11, t2x + 18, t2y - 5, (200, 200, 200))
    cv.disc(t2x + 26, t2y - 12, 4, (255, 140, 40))

def scene_tehran(cv, x, y, w, h):
    # dome kept small and centred: clear margin to the label below (r2 defect)
    _band(cv, x, y, w, h, (232, 222, 196))
    cx = x + w // 2
    base = y + h - 6
    cv.rect(cx - 34, base - 16, cx + 34, base, (120, 90, 60))
    cv.disc(cx, base - 16, 30, (20, 110, 110))
    cv.rect(cx - 30, base - 16, cx + 30, base - 10, (20, 110, 110))
    cv.disc(cx, base - 48, 4, GOLD)
    cv.line(cx, base - 48, cx, base - 40, GOLD, 2)
    cv.rect(cx - 52, base - 34, cx - 44, base, (150, 120, 80))
    cv.disc(cx - 48, base - 36, 5, (150, 120, 80))
    cv.rect(cx + 44, base - 34, cx + 52, base, (150, 120, 80))
    cv.disc(cx + 48, base - 36, 5, (150, 120, 80))

def scene_washington(cv, x, y, w, h):
    _band(cv, x, y, w, h, (214, 228, 240))
    cx = x + w // 2
    base = y + h - 4
    cv.rect(cx - 40, base - 12, cx + 40, base, (240, 240, 238))
    cv.rect(cx - 26, base - 20, cx + 26, base - 12, (220, 220, 216))
    cv.disc(cx, base - 20, 16, (240, 240, 238))
    cv.line(cx, base - 40, cx, base - 34, INK, 2)
    cv.disc(cx, base - 42, 3, INK)
    for px in (cx - 52, cx + 44):
        cv.rect(px, base - 22, px + 8, base, (200, 200, 196))
    # server rack right
    rx = x + w - 34
    cv.rect(rx, y + 8, rx + 24, base, (30, 30, 34))
    for ry in range(y + 12, base - 6, 8):
        cv.rect(rx + 4, ry, rx + 12, ry + 3, (80, 200, 120))
        cv.rect(rx + 15, ry, rx + 20, ry + 3, (220, 220, 220))

def scene_beijing(cv, x, y, w, h):
    _band(cv, x, y, w, h, (246, 226, 200))
    cx = x + w // 2
    base = y + h - 4
    tiers = [(46, 8), (38, 8), (30, 8)]
    yy = base
    for tw, th in tiers:
        cv.rect(cx - tw // 2, yy - th, cx + tw // 2, yy, (150, 50, 40))
        cv.rect(cx - tw // 2 - 6, yy - th - 3, cx + tw // 2 + 6, yy - th, (90, 30, 25))
        yy -= th + 3
    cv.rect(cx - 3, yy - 10, cx + 3, yy, (90, 30, 25))
    cv.disc(cx, yy - 12, 4, GOLD)
    cv.rect(x, base, x + w, base + 4, (120, 100, 70))

def scene_davao(cv, x, y, w, h):
    _band(cv, x, y, w, h, SKY)
    cv.rect(x, y + h - 10, x + w, y + h - 6, (90, 90, 90))
    for px in range(x + 6, x + w - 6, 18):
        cv.rect(px, y + h - 9, px + 8, y + h - 7, (255, 255, 255))
    # plane side view
    px, py = x + 22, y + h // 2 - 4
    cv.rect(px, py - 6, px + 110, py + 6, (240, 240, 240))
    cv.poly([(px + 110, py - 6), (px + 138, py - 1), (px + 110, py + 6)], (220, 220, 220))
    cv.poly([(px + 6, py - 6), (px + 22, py - 22), (px + 34, py - 6)], (200, 40, 40))
    cv.poly([(px + 70, py + 6), (px + 92, py + 18), (px + 102, py + 6)], (180, 180, 180))
    cv.poly([(px + 96, py - 6), (px + 116, py - 20), (px + 124, py - 6)], (200, 40, 40))
    for wx in range(px + 12, px + 104, 14):
        cv.rect(wx, py - 3, wx + 6, py + 1, (29, 78, 216))

def scene_canberra(cv, x, y, w, h):
    # AI circle kept small and centred: clear margin to the label below
    _band(cv, x, y, w, h, (226, 236, 244))
    cx, cy = x + w // 2, y + h // 2
    cv.disc(cx, cy, 22, TEAL)
    cv.ring(cx, cy, 22, 19, (255, 255, 255))
    for dx, dy in ((-8, -6), (8, -6), (-8, 8), (8, 8)):
        cv.disc(cx + dx, cy + dy, 3, (255, 255, 255))
    cv.line(cx - 8, cy - 6, cx + 8, cy + 8, (255, 255, 255), 2)
    cv.line(cx + 8, cy - 6, cx - 8, cy + 8, (255, 255, 255), 2)
    cv.disc(cx - 30, cy - 14, 3, (29, 78, 216))
    cv.disc(cx + 30, cy + 14, 3, (185, 28, 28))

def scene_bitcoin(cv, x, y, w, h):
    _band(cv, x, y, w, h, (18, 20, 28))
    # down chart
    pts = [(x + 10, y + 14), (x + 40, y + 20), (x + 60, y + 12), (x + 90, y + 26),
           (x + 120, y + 22), (x + 150, y + 40), (x + 170, y + 34)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], (255, 90, 90), 3)
    cv.line(x + 8, y + h - 8, x + w - 8, y + h - 8, (80, 80, 90), 1)
    # coin
    cx, cy = x + w - 34, y + 20
    cv.disc(cx, cy, 14, (247, 147, 26))
    cv.ring(cx, cy, 14, 11, (180, 110, 10))
    cv.rect(cx - 2, cy - 7, cx + 2, cy + 7, (120, 70, 0))
    cv.rect(cx - 6, cy - 7, cx - 2, cy - 2, (120, 70, 0))
    cv.rect(cx - 6, cy + 2, cx - 2, cy + 7, (120, 70, 0))

def scene_f1(cv, x, y, w, h):
    _band(cv, x, y, w, h, (232, 232, 228))
    # checkered strip top
    for i in range(12):
        cv.rect(x + i * 16, y + 2, x + i * 16 + 8, y + 10,
                INK if i % 2 == 0 else (255, 255, 255))
    # car side view
    px, py = x + 24, y + h - 20
    cv.poly([(px, py), (px + 18, py - 12), (px + 78, py - 12), (px + 96, py - 4),
             (px + 128, py - 4), (px + 138, py), (px, py)], (185, 28, 28))
    cv.poly([(px + 40, py - 12), (px + 52, py - 22), (px + 78, py - 22),
             (px + 86, py - 12)], (40, 40, 40))
    cv.disc(px + 30, py + 1, 9, INK)
    cv.disc(px + 30, py + 1, 4, (200, 200, 200))
    cv.disc(px + 108, py + 1, 9, INK)
    cv.disc(px + 108, py + 1, 4, (200, 200, 200))
    cv.rect(px - 6, py - 14, px + 2, py - 2, INK)

def scene_cricket(cv, x, y, w, h):
    _band(cv, x, y, w, h, (120, 180, 100))
    cv.rect(x, y + h - 12, x + w, y + h, (90, 140, 70))
    # stumps
    for sx in (x + 34, x + 42, x + 50):
        cv.rect(sx, y + h - 34, sx + 4, y + h - 12, (240, 220, 160))
    # bat
    cv.line(x + 96, y + 10, x + 126, y + h - 20, (220, 180, 130), 7)
    cv.line(x + 90, y + 4, x + 96, y + 10, (120, 90, 60), 5)
    # ball
    cv.disc(x + 150, y + 16, 8, (185, 28, 28))
    cv.arc(x + 150, y + 16, 5, 200, 340, (255, 255, 255), 2)

# ---------------------------------------------------------------- world map
MAP_PINS = [  # (story no, lon, lat)
    (1, 50.6, 26.2), (2, 36.9, 36.9), (3, -76.0, -11.0), (4, 30.5, 50.5),
    (5, 56.5, 26.5), (6, 51.4, 35.7), (7, -77.0, 39.0), (8, 116.4, 39.9),
    (9, 125.6, 7.1), (10, 46.7, 24.7), (12, -115.0, 36.0), (13, 174.8, -41.3),
]
MAP_LAND = [  # (lon, lat, rx, ry) ellipses, degrees
    (-100, 48, 28, 14), (-88, 38, 18, 10), (-95, 62, 20, 8), (-150, 64, 14, 7),
    (-85, 20, 8, 6), (-42, 74, 10, 5), (-60, -10, 12, 12), (-65, -25, 8, 10),
    (-70, -38, 5, 8), (15, 52, 14, 7), (25, 60, 10, 6), (10, 44, 8, 5),
    (-2, 54, 3, 4), (18, 8, 16, 12), (25, -12, 12, 10), (35, -25, 8, 8),
    (60, 55, 30, 12), (90, 50, 22, 10), (105, 35, 14, 9), (78, 22, 9, 8),
    (115, 30, 10, 7), (135, 40, 10, 6), (100, 15, 7, 6), (139, 37, 4, 6),
    (115, -2, 10, 3), (134, -25, 12, 7), (172, -41, 3, 4),
]

def draw_map(cv, x, y, w, h):
    _band(cv, x, y, w, h, SEA)
    def px(lon, lat):
        return x + (lon + 168.0) / 360.0 * w, y + (78.0 - lat) / 136.0 * h
    for lon, lat, rx, ry in MAP_LAND:
        cx, cy = px(lon, lat)
        ellipse(cv, cx, cy, rx / 360.0 * w, ry / 136.0 * h, LAND)
    # graticule
    for lon in (-120, -60, 0, 60, 120):
        gx, _ = px(lon, 0)
        cv.vline(int(gx), y, y + h, (190, 210, 220), 1)
    for lat in (40, 0, -40):
        _, gy = px(0, lat)
        cv.hline(x, x + w, int(gy), (190, 210, 220), 1)
    for no, lon, lat in MAP_PINS:
        cx, cy = px(lon, lat)
        cv.disc(int(cx), int(cy), 9, RED)
        cv.ring(int(cx), int(cy), 9, 7, (255, 255, 255))
        draw_text(cv, int(cx), int(cy) + 3, str(no), SANS_F, 10,
                  (255, 255, 255), align='c')

# ---------------------------------------------------------------- story data
# Facts, figures and sources ONLY from GO-REPORT.md / research-21nov-fresh.md.
# NOTE (hero check, round 6): the dev-board top 3 all lead with the
# Iran/Bahrain + tanker story. It was missing from our research data, but
# the coordinator verified it from AFP reports (22 Nov ~17:27 WIB), so it
# is hero 1 here. Only the verified facts below are used; the IRGC claim
# is NOT stated as fact (status CONFIRMED covers the fire + tanker hits,
# reported by Bahrain/AFP/UKMTO).
HEROES = [
    dict(no=1, kicker="BAHRAIN: IRAN STRIKES", region="Middle East", topic="CONFLICT",
         place="BAHRAIN, HORMUZ",
         status="CONFIRMED", sources="AFP, UKMTO",
         title="Iran strikes Bahrain as tankers hit in Hormuz",
         summary="Bahrain says Iran hit a civilian plant; fire, no one hurt. "
                 "Two tankers struck off Khasab.",
         scene=scene_bahrain),
    dict(no=2, kicker="COP31: OVERTIME", region="Global", topic="CLIMATE",
         place="ANTALYA, TURKIYE",
         status="CONFIRMED", sources="REUTERS, AP",
         title="COP31 overtime, day 13",
         summary="No deal yet: draft cut to 80 paras, no fossil fuels named. "
                 "Third draft due Saturday morning.",
         scene=scene_cop31),
    dict(no=3, kicker="PERU: QUAKE 6.7", region="Americas", topic="EARTHQUAKE",
         place="JUNIN, PERU",
         status="CONFIRMED", sources="USGS, IGP",
         title="M6.7 quake shakes Peru, 8 hurt",
         summary="108 km deep; 8 hurt, 128 homes hit. "
                 "Felt in Lima; no tsunami.",
         scene=scene_peru),
]
MEDIUM = [
    dict(no=4, kicker="4 \u00b7 KYIV \u2014 WAR", region="Europe",
         status="REPORTED", sources="NBC",
         title="Crimea bridge will not stay",
         summary="Zelensky warns of rising Russian double-tap strikes.",
         scene=scene_bridge),
    dict(no=5, kicker="5 \u00b7 HORMUZ \u2014 WAR", region="Middle East",
         status="REPORTED", sources="IRIB",
         title="Iran downs US drone",
         summary="IRGC claims its 58th MQ-9 downed; US has not confirmed.",
         scene=scene_hormuz),
    dict(no=6, kicker="6 \u00b7 TEHRAN \u2014 DIPLOMACY", region="Asia",
         status="OFFICIAL", sources="IRNA",
         title="Uranium stays at home",
         summary="Araghchi: the material stays; seeks a fair solution.",
         scene=scene_tehran),
    dict(no=7, kicker="7 \u00b7 WASHINGTON \u2014 TECHNOLOGY", region="Americas",
         status="REPORTED", sources="REUTERS",
         title="Trump vows data-centre tax",
         summary="\u2018Tremendous tax\u2019 for US firms building abroad.",
         scene=scene_washington),
    dict(no=8, kicker="8 \u00b7 BEIJING \u2014 DIPLOMACY", region="Asia",
         status="OFFICIAL", sources="AFP",
         title="Fix Taiwan words, China says",
         summary="Beijing: Tokyo must correct its Taiwan remarks.",
         scene=scene_beijing),
    dict(no=9, kicker="9 \u00b7 DAVAO \u2014 AVIATION", region="Oceania",
         status="CONFIRMED", sources="AP",
         title="Jet lands safe after fire",
         summary="PX19 diverted; 146 aboard, all safe, out by slide.",
         scene=scene_davao),
    dict(no=10, kicker="10 \u00b7 RIYADH \u2014 WAR", region="Middle East",
         status="CONFIRMED", sources="REUTERS, AFP",
         title="3 missiles down over Riyadh",
         summary="Shot down before dawn; no casualties. "
                 "Second attack in days.",
         scene=scene_riyadh),
    dict(no=11, kicker="11 \u00b7 WORLD \u2014 MARKETS", region="World",
         status="CONFIRMED", sources="COINGECKO",
         title="Bitcoin slips below $59,000",
         summary="$58,960, down 4.8% in a day; lowest since September 2024.",
         scene=scene_bitcoin),
    dict(no=12, kicker="12 \u00b7 LAS VEGAS \u2014 FORMULA 1", region="Americas",
         status="OFFICIAL", sources="FORMULA 1",
         title="Verstappen on pole",
         summary="Antonelli fastest in qualifying but takes a five-grid penalty.",
         scene=scene_f1),
    dict(no=13, kicker="13 \u00b7 WELLINGTON \u2014 CRICKET", region="Oceania",
         status="CONFIRMED", sources="AFP",
         title="Rahul century lifts India",
         summary="Rahul 124* at tea, day three of the first Test; India 344 for 2.",
         scene=scene_cricket),
]
# ALSO ON: 24 items, two columns of 12. Round 6: Canberra (no. 10) moved
# here as no. 18; London rugby (48) cut; Riyadh (old no. 2) is medium no. 10;
# Bahrain is the new hero 1. Cut from the research file (r5 numbers):
# 24 Canada trial, 26 Sejong derail, 30 Akvan rain, 31 Myanmar,
# 33 Cummins, 34 Russell, 42 Sozcu TV, 45 France UN meeting, 46 Estonia,
# 47 drone output, 48 London rugby, 49 Islamabad sentence, 50 Rohingya pact.
ALSO_ON = [
    (14, "Kryvyi Rih: double-tap strike kills 2, injures 60", "AP"),
    (15, "Copenhagen: Denmark says it foiled a Russian plot", "AJ"),
    (16, "Antalya: EU warns COP31 risks a \u201cfossil summit\u201d", "AFP"),
    (17, "Antalya: Panama threatens to block climate text", "AJ"),
    (18, "Canberra: Australia and China agree AI talks", "ABC"),
    (19, "Yemen: Houthis threaten Jeddah and Red Sea ports", "AJ"),
    (20, "Washington: Vance says Iran strikes were Trump\u2019s call", "Reuters"),
    (21, "Texas: execution of a man of 70 takes 63 minutes", "ABC"),
    (22, "Los Angeles: jury convicts man of starting Palisades fire", "ABC"),
    (23, "Missouri: judge approves $7.25bn Roundup settlement", "AFP"),
    (25, "Pyongyang: Kim tours factories after no Trump meeting", "AFP"),
    (27, "Taipei: budget and cash payout are passed", "TT"),
    (28, "Bangkok: six-point plan on arsenic in two rivers", "Nation"),
    (29, "New Delhi: Pakistani minister joins SCO forum in India", "Dawn"),
    (32, "Port Louis: African ratings agency talks to 15 states", "AJ"),
    (35, "Mexico: \u201cEl Chapo Isidro\u201d captured in Sinaloa", "AP"),
    (36, "Baltic: Russian cargo ship Sparta II on fire after drone hit", "Reuters"),
    (37, "Washington: Trump weighs new strikes on Iran, officials say", "NYT"),
    (38, "Paris: French police sentenced over Zecler beating", "AP"),
    (39, "Geneva: UN talks agree to keep working on AI weapons rules", "AP"),
    (40, "Port-au-Prince: Salvadoran troops fight gangs in Haiti", "AP"),
    (41, "Southern Ethiopia: 700,000 displaced", "AP"),
    (43, "Gaza: at least 4 killed in Israeli strikes amid truce", "AP"),
    (44, "Baghdad: fire at Iraqi power plant kills 4", "AP"),
]
NUMBERS = [("13", "COP31 DAY"), ("2", "TANKERS HORMUZ"), ("6.7", "PERU QUAKE"),
           ("146", "SAFE IN DAVAO"), ("$58,960", "BITCOIN"), ("124*", "RAHUL")]
REGIONS = [("EUROPE", "Europe", 7), ("MIDDLE EAST", "Middle East", 7),
           ("AMERICAS", "Americas", 11), ("ASIA", "Asia", 6),
           ("AFRICA", "Africa", 2), ("OCEANIA", "Oceania", 2),
           ("GLOBAL", "Global", 2)]
DATE_CHECK = ("Not 21 Nov, so left out: 20 Nov \u2014 Wall Street falls; Kyiv bridge "
              "strikes; missiles in Poland; UK\u2013EU deal; Cyclone Akvan lands; "
              "2 missiles over Jazan. 19 Nov \u2014 PIF tower hit; ICJ Myanmar ruling. "
              "18 Nov \u2014 Voyager 1 light-day. Not yet confirmed: BepiColombo "
              "enters Mercury orbit.")

# ---------------------------------------------------------------- layout
MX = 10  # outer margin

def fit_lines(text, font, size0, size_min, max_w, max_lines=2):
    # shrink the font until the title fits in max_lines lines
    size = size0
    while size > size_min:
        lines = wrap_text(text, font, size, max_w)
        if len(lines) <= max_lines:
            return lines, size
        size -= 2
    return wrap_text(text, font, size, max_w)[:max_lines], size

def pill(cv, x, y, text, font, size, bg, fg):
    w = int(text_width(text, font, size) + 10)
    h = int(size + 6)
    cv.rect(x, y, x + w, y + h, bg)
    draw_text(cv, x + 5, y + size + 1, text, font, size, fg)
    return w

def status_pill(cv, x, y, status, font, size):
    if status == "CONFIRMED":
        return pill(cv, x, y, "\u2713 CONFIRMED", font, size, GREEN, (255, 255, 255))
    if status == "OFFICIAL":
        w = int(text_width("OFFICIAL", font, size) + 10)
        h = int(size + 6)
        cv.rect(x, y, x + w, y + h, PAPER)
        cv.rect(x, y, x + w, y + 1, DARK)
        cv.rect(x, y + h - 1, x + w, y + h, DARK)
        cv.rect(x, y, x + 1, y + h, DARK)
        cv.rect(x + w - 1, y, x + w, y + h, DARK)
        draw_text(cv, x + 5, y + size + 1, "OFFICIAL", font, size, DARK)
        return w
    w = int(text_width("REPORTED", font, size) + 10)
    h = int(size + 6)
    cv.rect(x, y, x + w, y + h, PAPER)
    cv.rect(x, y, x + w, y + 1, GREY)
    cv.rect(x, y + h - 1, x + w, y + h, GREY)
    cv.rect(x, y, x + 1, y + h, GREY)
    cv.rect(x + w - 1, y, x + w, y + h, GREY)
    draw_text(cv, x + 5, y + size + 1, "REPORTED", font, size, GREY)
    return w

def build():
    cv = Canvas(W, H, PAPER)
    # ---- top bar
    draw_text(cv, MX, 13, "THE WORLD IN ONE DAY", SANS_F, 10, INK)
    draw_text(cv, W // 2, 13, "37 STORIES \u00b7 7 REGIONS", SANS_F, 10, RED,
              align='c')
    draw_text(cv, W - MX, 13, "ALL TIMES UTC", SANS_F, 10, INK, align='r')
    cv.hline(MX, W - MX, 18, RULE, 2)
    # ---- masthead
    size = 60
    while text_width("Saturday 21 November 2026", SERIF_F, size) > W - 2 * MX:
        size -= 2
    draw_text(cv, W // 2, 86, "Saturday 21 November 2026", SERIF_F, size, INK,
              align='c')
    cv.hline(MX, W - MX, 94, RULE, 2)
    # ---- subhead (faux italic serif)
    draw_text(cv, W // 2, 114,
              "Iran strikes Bahrain \u25c6 COP31 runs into overtime "
              "\u25c6 Peru quake M6.7",
              SERIF_F, 16, INK, align='c', slant=0.18)
    cv.hline(MX, W - MX, 120, RULE, 1)
    # ---- number strip
    y0, y1 = 122, 170
    cellw = (W - 2 * MX) / 6.0
    for i, (num, lab) in enumerate(NUMBERS):
        cx = MX + cellw * i
        if i:
            cv.vline(int(cx), y0 + 4, y1 - 4, GREY, 1)
        draw_text(cv, cx + cellw / 2, y0 + 30, num, SERIF_F, 30, RED, align='c')
        draw_text(cv, cx + cellw / 2, y0 + 45, lab, SANS_F, 10, INK_SOFT,
                  align='c')
    cv.hline(MX, W - MX, y1, RULE, 2)
    # ---- region bar
    y0, y1 = 172, 188
    labw = 120
    cv.rect(MX, y0, MX + labw, y1, DARK)
    draw_text(cv, MX + 6, y0 + 12, "STORIES BY REGION", SANS_F, 8.5,
              (255, 255, 255))
    tot = sum(n for _, _, n in REGIONS)
    rx = MX + labw
    avail = W - MX - rx
    for label, cname, n in REGIONS:
        sw = avail * n / tot
        cv.rect(int(rx), y0, int(rx + sw), y1, REGION_COLOR[cname])
        draw_text(cv, int(rx) + 4, y0 + 12, "%s %d" % (label, n), SANS_F, 8,
                  (255, 255, 255))
        rx += sw
    cv.hline(MX, W - MX, y1, RULE, 2)
    # ---- heroes
    hy0, hy1 = 190, 452
    hw = 328
    for i, st in enumerate(HEROES):
        x = MX + i * (hw + 10)
        cv.rect(x, hy0, x + hw, hy1, PAPER)
        cv.rect(x, hy0, x + hw, hy0 + 1, RULE)
        cv.rect(x, hy1 - 1, x + hw, hy1, RULE)
        cv.rect(x, hy0, x + 1, hy1, RULE)
        cv.rect(x + hw - 1, hy0, x + hw, hy1, RULE)
        # scene band with kicker banner on top (like the leaders)
        st['scene'](cv, x + 1, hy0 + 1, hw - 2, 132)
        col = REGION_COLOR[st['region']]
        bw = int(text_width(st['kicker'], SANS_F, 13) + 14)
        cv.rect(x + 7, hy0 + 7, x + 7 + bw, hy0 + 29, col)
        draw_text(cv, x + 14, hy0 + 24, st['kicker'], SANS_F, 13,
                  (255, 255, 255))
        # kicker line: place + topic, status pill right-aligned
        kx, ky = x + 8, hy0 + 150
        draw_text(cv, kx, ky, "%s \u00b7 %s" % (st['place'], st['topic']),
                  SANS_F, 10, col)
        ptxt = "\u2713 CONFIRMED" if st['status'] == 'CONFIRMED' else st['status']
        pw = int(text_width(ptxt, SANS_F, 9) + 10)
        status_pill(cv, x + hw - 8 - pw, hy0 + 138, st['status'], SANS_F, 9)
        # title (2 lines max), summary (2 lines), source
        lines, tsize = fit_lines(st['title'], SERIF_F, 20, 16, hw - 16)
        t_y = hy0 + 180 + max(0, 2 - len(lines)) * tsize * 1.28 / 2
        draw_lines(cv, x + 8, t_y, lines, SERIF_F, tsize, INK,
                   lh=tsize * 1.28)
        sl = wrap_text(st['summary'], SERIF_F, 11.5, hw - 16)
        draw_lines(cv, x + 8, hy0 + 226, sl[:2], SERIF_F, 11.5, INK_SOFT, lh=14)
        draw_text(cv, x + 8, hy0 + 252, "%d. %s \u2014 %s" % (st['no'], st['sources'],
                  st['status']), SANS_F, 9, GREY)
    # ---- medium cards, two rows of five
    mw = 194
    for r in range(2):
        y0 = 452 + r * 178
        y1 = y0 + 178
        for c in range(5):
            st = MEDIUM[r * 5 + c]
            x = MX + c * (mw + 8)
            cv.rect(x, y0, x + mw, y1, PAPER)
            cv.rect(x, y0, x + mw, y0 + 1, RULE)
            cv.rect(x, y1 - 1, x + mw, y1, RULE)
            cv.rect(x, y0, x + 1, y1, RULE)
            cv.rect(x + mw - 1, y0, x + mw, y1, RULE)
            col = REGION_COLOR[st['region']]
            cv.rect(x + 1, y0 + 1, x + mw - 1, y0 + 17, col)
            draw_text(cv, x + 7, y0 + 13, st['kicker'], SANS_F, 9,
                      (255, 255, 255))
            # status lives in the source line below the summary, not here:
            # the strip is too narrow for kicker + status without overlap.
            st['scene'](cv, x + 1, y0 + 17, mw - 2, 56)
            lines, tsize = fit_lines(st['title'], SERIF_F, 17, 13, mw - 14)
            t_y = y0 + 101 + max(0, 2 - len(lines)) * tsize * 1.28 / 2
            draw_lines(cv, x + 7, t_y, lines, SERIF_F, tsize, INK,
                       lh=tsize * 1.28)
            sl = wrap_text(st['summary'], SERIF_F, 10, mw - 14)
            draw_lines(cv, x + 7, y0 + 143, sl[:2], SERIF_F, 10, INK_SOFT,
                       lh=12)
            draw_text(cv, x + 7, y0 + 170, "%d. %s \u2014 %s" % (st['no'],
                      st['sources'], st['status']), SANS_F, 8, GREY)
    # ---- map + ALSO ON
    y0, y1 = 810, 946
    draw_text(cv, MX, y0 + 11, "WHERE IT HAPPENED", SANS_F, 11, RED)
    draw_text(cv, MX + 158, y0 + 11, "pins match story numbers",
              SERIF_F, 10, INK_SOFT)
    draw_map(cv, MX, y0 + 16, 330, y1 - y0 - 16)
    ax = MX + 344
    draw_text(cv, ax, y0 + 11, "ALSO ON SATURDAY 21 NOVEMBER 2026 \u2014 24 MORE",
              SANS_F, 11, RED)
    colw = (W - MX - ax) / 2.0
    for i, (no, txt, src) in enumerate(ALSO_ON):
        col = i // 12
        row = i % 12
        bx = ax + col * colw
        by = y0 + 15 + row * 10
        draw_text(cv, bx, by + 8, str(no), SANS_F, 8.5, RED)
        draw_text(cv, bx + 20, by + 8, "%s (%s)" % (txt, src), SERIF_F, 8.5,
                  INK, track=-0.5)
    cv.hline(MX, W - MX, y1, RULE, 2)
    # ---- DATE CHECK
    y0, y1 = 948, 986
    lw = int(text_width("DATE CHECK", SANS_F, 10) + 12)
    cv.rect(MX, y0 + 2, MX + lw, y0 + 18, RED)
    draw_text(cv, MX + 6, y0 + 14, "DATE CHECK", SANS_F, 10, (255, 255, 255))
    dl = wrap_text(DATE_CHECK, SERIF_F, 10.5, W - 2 * MX - lw - 12)
    draw_lines(cv, MX + lw + 8, y0 + 14, dl[:2], SERIF_F, 10.5, INK, lh=13)
    # ---- footer legend
    draw_text(cv, W // 2, 1000,
              "HOW SURE   \u2713 CONFIRMED = 2+ major outlets   \u00b7   "
              "OFFICIAL = on the record   \u00b7   REPORTED = one major outlet",
              SERIF_F, 10, INK_SOFT, align='c')
    draw_text(cv, W // 2, 1016,
              "Every story here happened or was first reported on Saturday "
              "21 November 2026 (UTC), as the named outlets reported it.",
              SERIF_F, 10, INK_SOFT, align='c', slant=0.12)
    return cv

def main():
    cv = build()
    out1 = "/output/entry.png"
    here = os.path.dirname(os.path.abspath(__file__))
    out2 = os.path.join(here, "out", "entry.png")
    for path in (out1, out2):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write_png(path, W, H, cv.px)
        except OSError:
            pass
    import hashlib
    data = open(out2, "rb").read() if os.path.exists(out2) else b""
    sys.stderr.write("entry sha256=%s bytes=%d\n"
                     % (hashlib.sha256(data).hexdigest(), len(data)))

if __name__ == "__main__":
    main()
