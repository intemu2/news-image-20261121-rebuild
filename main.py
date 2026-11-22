#!/usr/bin/env python3
"""news-image-20261121: draw one 1024x1024 newspaper page of the world news of
Saturday 21 November 2026. Pure Python standard library only: no network, no
PIL, no copied files. The program draws every pixel itself (own PNG encoder,
own drawing primitives, own 5x7 bitmap font) from the story data below, so two
runs write byte-identical output.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   (writes out/entry.png)
"""
import math
import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette ---
PAPER = (246, 241, 229)
CARD = (255, 253, 246)
INK = (25, 25, 25)
RED = (168, 30, 34)
DARKRED = (125, 20, 24)
WHITE = (255, 255, 255)
GRAY = (107, 107, 107)
LGRAY = (216, 210, 194)
NAVY = (16, 28, 51)
SKY = (178, 208, 224)
SEA = (207, 224, 232)
LAND = (232, 220, 192)
BLUE = (31, 58, 95)
ORANGE = (180, 83, 9)
GREEN = (46, 107, 52)
TEAL = (15, 118, 110)
PURPLE = (109, 40, 217)
GOLD = (201, 162, 39)
YELLOW = (245, 197, 66)
BROWN = (120, 84, 50)

# ------------------------------------------------------------------ canvas --
BUF = bytearray(W * H * 3)


def set_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        BUF[i], BUF[i + 1], BUF[i + 2] = c


def fill_rect(x, y, w, h, c):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            BUF[i], BUF[i + 1], BUF[i + 2] = c


def hline(x, y, w, c, t=1):
    fill_rect(x, y, w, t, c)


def vline(x, y, h, c, t=1):
    fill_rect(x, y, t, h, c)


def outline_rect(x, y, w, h, c, t=1):
    hline(x, y, w, c, t)
    hline(x, y + h - t, w, c, t)
    vline(x, y, h, c, t)
    vline(x + w - t, y, h, c, t)


def line(x0, y0, x1, y1, c, t=1):
    """Bresenham line, thickness t (square brush)."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        fill_rect(x0 - t // 2, y0 - t // 2, t, t, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def filled_circle(cx, cy, r, c):
    for yy in range(cy - r, cy + r + 1):
        dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
        hline(cx - dx, yy, 2 * dx + 1, c)


def circle_outline(cx, cy, r, c, t=1):
    steps = max(24, int(2 * 3.14159 * r))
    prev = None
    for i in range(steps + 1):
        a = 2 * 3.14159 * i / steps
        p = (int(cx + r * math.cos(a)), int(cy + r * math.sin(a)))
        if prev is not None:
            line(prev[0], prev[1], p[0], p[1], c, t)
        prev = p


def filled_poly(points, c):
    """Scanline fill of a simple polygon (even-odd)."""
    if not points:
        return
    ys = [p[1] for p in points]
    y0, y1 = min(ys), max(ys)
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x0, yy0 = points[i]
            x1, yy1 = points[(i + 1) % n]
            if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                xs.append(x0 + (y - yy0) * (x1 - x0) / (yy1 - yy0))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            hline(int(xs[k]), y, max(1, int(xs[k + 1]) - int(xs[k])), c)


def poly_outline(points, c, t=1):
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        line(x0, y0, x1, y1, c, t)


# ------------------------------------------------------------ 5x7 bitmap font
# Each glyph: 7 rows of 5 bits, '1' = ink. Written from scratch for this entry.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
}
FONT.update({
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11110", "01000", "01000", "01000", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ";": ("00000", "00000", "01100", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "@": ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    "|": ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
    "\\": ("10000", "01000", "01000", "00100", "00010", "00010", "00001"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "~": ("00000", "00000", "01001", "10110", "00000", "00000", "00000"),
    "^": ("00100", "01010", "00000", "00000", "00000", "00000", "00000"),
    "`": ("00100", "01000", "00000", "00000", "00000", "00000", "00000"),
})


def text_w(text, scale):
    return len(text) * 6 * scale


def draw_text(x, y, scale, color, text, bold=False):
    """Draw text with the 5x7 font. Unknown chars render blank."""
    cx = x
    for ch in text:
        g = FONT.get(ch)
        if g is None:
            cx += 6 * scale
            continue
        for r in range(7):
            row = g[r]
            for col in range(5):
                if row[col] == "1":
                    fill_rect(cx + col * scale, y + r * scale, scale, scale, color)
                    if bold and scale >= 2:
                        fill_rect(cx + col * scale + 1, y + r * scale, scale - 1, scale, color)
        cx += 6 * scale
    return cx


def draw_text_center(x, y, w, scale, color, text, bold=False):
    tw = text_w(text, scale)
    draw_text(x + (w - tw) // 2, y, scale, color, text, bold=bold)


def wrap_text(text, max_w, scale):
    """Greedy word wrap. Returns list of lines (each fits max_w)."""
    max_chars = max(1, max_w // (6 * scale))
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for wd in words:
            trial = wd if not cur else cur + " " + wd
            if len(trial) <= max_chars:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                # hard-split a word longer than the line
                while len(wd) > max_chars:
                    lines.append(wd[:max_chars])
                    wd = wd[max_chars:]
                cur = wd
        if cur:
            lines.append(cur)
    return lines


def draw_wrapped(x, y, max_w, scale, color, text, line_h=None, bold=False, max_lines=None):
    lines = wrap_text(text, max_w, scale)
    if max_lines is not None:
        lines = lines[:max_lines]
    lh = line_h if line_h is not None else 7 * scale + 2
    for i, ln in enumerate(lines):
        draw_text(x, y + i * lh, scale, color, ln, bold=bold)
    return len(lines)


# -------------------------------------------------------------- PNG writer ---
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, w, h, buf):
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += buf[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n"
    data += _chunk(b"IHDR", ihdr)
    data += _chunk(b"IDAT", comp)
    data += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)
    return len(data)

# ---------------------------------------------------------------- story data --
# All copy is ASCII only (the 5x7 font above covers it). Every story happened,
# or was first reported, on Saturday 21 November 2026. Sources are real wires
# and outlets, verified in research-21nov-fresh.md. No invented source names.

HERO = [
    {
        "num": 1, "place": "ANTALYA, TURKIYE - CLIMATE",
        "title": "COP31: OVERTIME", "chip": "NO DEAL - DAY 13",
        "headline": "COP31 runs past its deadline",
        "summary": "Draft drops fossil fuels; no deal as talks run on",
        "source": "Sources: Reuters, AP", "art": "cop31",
    },
    {
        "num": 2, "place": "RIYADH - WAR",
        "title": "SAUDI: MISSILES", "chip": "3 SHOT DOWN",
        "headline": "Missiles downed over Riyadh",
        "summary": "Three downed before dawn; no damage reported",
        "source": "Sources: Reuters, AFP", "art": "riyadh",
    },
    {
        "num": 3, "place": "JUNIN, PERU - EARTHQUAKE",
        "title": "PERU: QUAKE 6.7", "chip": "6.7 - 108 KM DEEP",
        "headline": "Deep 6.7 quake rattles Peru",
        "summary": "Felt in Lima; 8 hurt, 128 homes hit, INDECI says",
        "source": "Sources: USGS, IGP", "art": "peru",
    },
]

# Medium cards: headline <= 36 chars, summary <= 37 chars (fits 2 + 1 lines).
MEDIUM = [
    {"num": 4, "label": "KYIV: WARNING", "headline": "Zelensky: bridge 'will not stay'",
     "summary": "He warns of double-tap strikes. (NBC)", "art": "bridge"},
    {"num": 5, "label": "HORMUZ: DRONE", "headline": "Iran says it downed a US drone",
     "summary": "58th MQ-9 claimed; US silent. (IRIB)", "art": "drone"},
    {"num": 6, "label": "IRAN: URANIUM", "headline": "Iran: uranium stays at home",
     "summary": "Still seeks a 'fair solution'. (IRNA)", "art": "atom"},
    {"num": 7, "label": "TRUMP: AI TAX", "headline": "Trump vows tax on data centres",
     "summary": "No rate or details given yet. (ABC)", "art": "tax"},
    {"num": 8, "label": "CHINA-JAPAN", "headline": "China: 'correct' your Taiwan words",
     "summary": "Tokyo: stance is unchanged. (AFP)", "art": "flags"},
    {"num": 9, "label": "DAVAO: 146 SAFE", "headline": "Jet lands safely after fire alert",
     "summary": "All 146 safe; slides used. (AP)", "art": "plane"},
    {"num": 10, "label": "CANBERRA: AI", "headline": "Australia and China agree to AI talks",
     "summary": "Albanese ends an 11-day trip. (ABC)", "art": "aichat"},
    {"num": 11, "label": "BITCOIN: $58,960", "headline": "Bitcoin slips below $59,000",
     "summary": "Down 4.8% in a day. (CoinGecko)", "art": "chart"},
    {"num": 12, "label": "VERSTAPPEN: POLE", "headline": "Verstappen on pole in Las Vegas",
     "summary": "Antonelli fastest but drops 5. (F1)", "art": "race"},
    {"num": 13, "label": "RAHUL: 124*", "headline": "Rahul century puts India on top",
     "summary": "India 344 for 2 at tea. (AFP)", "art": "cricket"},
]

# Also-on list: one line each (wrapped if longer). Number, text, region.
ALSO = [
    (14, "Kryvyi Rih: strike kills 2, injures 60 (AP)", "Europe"),
    (15, "Copenhagen: Denmark foils a plot (Al Jazeera)", "Europe"),
    (16, "Antalya: EU warns of a 'fossil summit' (AFP)", "Europe"),
    (17, "Antalya: Panama may block text (Al Jazeera)", "Americas"),
    (18, "Indonesia signs clean-power deals (Antara)", "Asia"),
    (19, "Yemen: Houthis threaten Jeddah ports (Al Jazeera)", "Middle East"),
    (20, "Washington: Vance on Iran strikes (Reuters)", "Americas"),
    (21, "Texas: execution takes 63 minutes (ABC)", "Americas"),
    (22, "Los Angeles: jury in Palisades fire case (ABC)", "Americas"),
    (23, "Missouri: $7.25bn Roundup deal approved (AFP)", "Americas"),
    (24, "Vancouver: youth climate trial rests (AFP)", "Americas"),
    (25, "Pyongyang: Kim tours factories (AFP)", "Asia"),
    (26, "Sejong: train derails, no one hurt (Korea Herald)", "Asia"),
    (27, "Taipei: budget, cash payout pass (Taipei Times)", "Asia"),
    (28, "Bangkok: arsenic plan for two rivers (The Nation)", "Asia"),
    (29, "New Delhi: Pakistan minister at SCO forum (Dawn)", "Asia"),
    (30, "Eastern India: Akvan rain alerts (ETV)", "Asia"),
    (31, "Myanmar: groups urge sanctions (AP)", "Asia"),
    (32, "Port Louis: AfCRA talks to 15 states (Al Jazeera)", "Africa"),
    (33, "Melbourne: Cummins keeps captaincy (ABC)", "Oceania"),
    (34, "Russell hits out at Verstappen (Sky Sports)", "Americas"),
    (35, "Mexico: 'El Chapo Isidro' captured (AP)", "Americas"),
    (36, "Baltic: Sparta II ablaze after drone hit (Reuters)", "Europe"),
    (37, "Washington: Trump weighs new Iran strikes (NYT)", "Americas"),
    (38, "Paris: police sentenced over Zecler beating (AP)", "Europe"),
    (39, "Geneva: UN talks on AI weapons go on (AP)", "Europe"),
    (40, "Port-au-Prince: troops fight gangs in Haiti (AP)", "Americas"),
    (41, "Southern Ethiopia: 700,000 displaced (AP)", "Africa"),
    (42, "Turkey takes control of Sozcu TV (Reuters)", "Europe"),
    (43, "Gaza: 4 killed in strikes amid truce (AP)", "Middle East"),
    (44, "Baghdad: fire at power plant kills 4 (AP)", "Middle East"),
    (45, "Paris: France seeks UN Council meeting (AFP)", "Europe"),
    (46, "Tallinn: Estonia urges halt to war (AP)", "Europe"),
    (47, "Berlin: drone output to rise fivefold (Reuters)", "Europe"),
    (48, "London: England beat NZ by record margin (AP)", "Europe"),
    (49, "Islamabad: death sentence over posts (AP)", "Asia"),
    (50, "Kuala Lumpur: pact to shelter Rohingya (AP)", "Asia"),
]

STATS = [
    ("13", "DAY OF COP31, MEANT TO CLOSE ON DAY 12"),
    ("3", "MISSILES SHOT DOWN OVER RIYADH"),
    ("6.7", "MAGNITUDE OF THE PERU QUAKE"),
    ("146", "PEOPLE SAFE AFTER THE DAVAO LANDING"),
    ("$58,960", "BITCOIN EARLY SATURDAY, DOWN 4.8% IN A DAY"),
    ("124*", "K L RAHUL'S SCORE AT TEA, WELLINGTON"),
]

REGIONS = [
    ("EUROPE 13", BLUE),
    ("ASIA 12", ORANGE),
    ("MIDDLE EAST 6", RED),
    ("AFRICA 2", GREEN),
    ("AMERICAS 13", TEAL),
    ("OCEANIA 3", PURPLE),
    ("GLOBAL 1", GRAY),
]

DATE_CHECK = (
    "DATE CHECK - Left out as Friday 20 November news: Wall Street's fall into "
    "correction; the Russian barrage that hit Kyiv's bridges; the missile that "
    "landed in Poland; the UK-EU deal; Cyclone Akvan's landfall; two missiles "
    "over Jazan. Older still: Voyager 1's light-day (18 Nov). Not confirmed "
    "when drawn, so not shown: BepiColombo in Mercury orbit."
)

CREDIT = ("Every story here happened, or was first reported, on Saturday "
          "21 November 2026. Sources named beside each story - original drawings")

# ------------------------------------------------------------------ art ------
def draw_art(key, x, y, w, h):
    """Small scene illustrations, drawn with the primitives above."""
    if key == "bridge":  # Kyiv: bridge over water, flash of a strike
        fill_rect(x, y, w, h, (200, 220, 235))
        fill_rect(x, y + h - 10, w, 10, (120, 160, 190))
        line(x + 10, y + h - 10, x + w - 10, y + h - 10, INK, 2)
        for tx in (x + w // 3, x + 2 * w // 3):
            fill_rect(tx - 2, y + 4, 4, h - 12, INK)
        line(x + w // 3, y + 4, x + w // 2, y + h - 12, INK, 1)
        line(x + 2 * w // 3, y + 4, x + w // 2, y + h - 12, INK, 1)
        filled_circle(x + w // 2, y + 8, 5, YELLOW)
        filled_circle(x + w // 2, y + 8, 3, ORANGE)
    elif key == "drone":  # Hormuz: drone in a pale sky
        fill_rect(x, y, w, h, (210, 225, 235))
        fill_rect(x + w // 2 - 14, y + h // 2 - 3, 28, 6, INK)
        line(x + w // 2 - 22, y + h // 2 - 8, x + w // 2 + 22, y + h // 2 - 8, INK, 2)
        line(x + w // 2 + 14, y + h // 2 - 3, x + w // 2 + 26, y + h // 2 + 4, INK, 2)
        filled_circle(x + w // 2 - 20, y + h // 2 - 10, 3, INK)
        filled_circle(x + w // 2 + 20, y + h // 2 - 10, 3, INK)
        line(x + 8, y + h - 6, x + w - 8, y + h - 6, GRAY, 1)
    elif key == "atom":  # Iran: atom, dark blue
        fill_rect(x, y, w, h, NAVY)
        circle_outline(x + w // 2, y + h // 2, 12, WHITE, 1)
        circle_outline(x + w // 2, y + h // 2, 8, GOLD, 1)
        filled_circle(x + w // 2, y + h // 2, 3, GOLD)
        filled_circle(x + w // 2 + 12, y + h // 2, 2, WHITE)
        filled_circle(x + w // 2 - 8, y + h // 2 - 6, 2, WHITE)
    elif key == "tax":  # Trump: capitol-style building + dollar
        fill_rect(x, y, w, h, (232, 222, 200))
        filled_poly([(x + w // 2 - 30, y + 8), (x + w // 2 + 30, y + 8),
                     (x + w // 2, y + 2)], INK)
        for cx in (x + w // 2 - 20, x + w // 2, x + w // 2 + 20):
            fill_rect(cx - 2, y + 10, 4, h - 16, INK)
        fill_rect(x + 8, y + h - 6, w - 16, 4, INK)
        draw_text(x + w - 34, y + 2, 2, GOLD, "$", bold=True)
    elif key == "flags":  # China-Japan: two flags
        fill_rect(x, y, w, h, (220, 228, 235))
        vline(x + 30, y + 3, h - 6, INK, 2)
        vline(x + w - 30, y + 3, h - 6, INK, 2)
        fill_rect(x + 32, y + 4, 34, 14, RED)
        filled_circle(x + 40, y + 9, 2, YELLOW)
        filled_circle(x + 50, y + 8, 1, YELLOW)
        fill_rect(x + w - 66, y + 4, 34, 14, WHITE)
        outline_rect(x + w - 66, y + 4, 34, 14, INK, 1)
        filled_circle(x + w - 49, y + 11, 5, RED)
    elif key == "plane":  # Davao: jet on approach, slide out
        fill_rect(x, y, w, h, (200, 222, 238))
        line(x + 20, y + 10, x + w - 30, y + 16, INK, 3)
        filled_poly([(x + w // 2 - 10, y + 12), (x + w // 2 + 6, y + 12),
                     (x + w // 2 + 2, y + 24)], INK)
        line(x + w - 34, y + 15, x + w - 22, y + 8, INK, 2)
        line(x + 8, y + h - 5, x + w - 8, y + h - 5, INK, 2)
        filled_poly([(x + w - 60, y + h - 6), (x + w - 40, y + h - 6),
                     (x + w - 50, y + h - 14)], ORANGE)
    elif key == "aichat":  # Canberra: two chat bubbles
        fill_rect(x, y, w, h, (222, 232, 240))
        fill_rect(x + 12, y + 4, 52, 14, WHITE)
        outline_rect(x + 12, y + 4, 52, 14, INK, 1)
        filled_poly([(x + 18, y + 18), (x + 26, y + 18), (x + 18, y + 26)], WHITE)
        for i, dx in enumerate((22, 34, 46)):
            filled_circle(x + dx, y + 11, 2, BLUE)
        fill_rect(x + w - 64, y + h - 18, 52, 14, (200, 225, 245))
        outline_rect(x + w - 64, y + h - 18, 52, 14, INK, 1)
        filled_poly([(x + w - 22, y + h - 18), (x + w - 30, y + h - 18),
                     (x + w - 22, y + h - 10)], (200, 225, 245))
        for i, dx in enumerate((w - 54, w - 42, w - 30)):
            filled_circle(x + dx, y + h - 11, 2, TEAL)
    elif key == "chart":  # Bitcoin: falling line
        fill_rect(x, y, w, h, CARD)
        line(x + 8, y + 4, x + 8, y + h - 6, INK, 1)
        line(x + 8, y + h - 6, x + w - 6, y + h - 6, INK, 1)
        pts = [(x + 12, y + 8), (x + w // 3, y + 12), (x + w // 2, y + 10),
               (x + 2 * w // 3, y + 20), (x + w - 12, y + h - 10)]
        for i in range(len(pts) - 1):
            line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 2)
        filled_poly([(x + w - 18, y + h - 12), (x + w - 8, y + h - 12),
                     (x + w - 13, y + h - 4)], RED)
    elif key == "race":  # Las Vegas: road + chequered flag
        fill_rect(x, y, w, h, (210, 215, 225))
        fill_rect(x, y + h - 14, w, 14, (60, 60, 60))
        for dx in range(6, w - 6, 16):
            hline(x + dx, y + h - 7, 8, YELLOW, 2)
        for r in range(3):
            for c in range(4):
                if (r + c) % 2 == 0:
                    fill_rect(x + 10 + c * 5, y + 4 + r * 5, 5, 5, INK)
                else:
                    fill_rect(x + 10 + c * 5, y + 4 + r * 5, 5, 5, WHITE)
        fill_rect(x + w - 70, y + 4, 40, 8, RED)
        filled_circle(x + w - 60, y + 14, 4, INK)
        filled_circle(x + w - 40, y + 14, 4, INK)
    elif key == "cricket":  # Wellington: stumps, bat, ball
        fill_rect(x, y, w, h, (140, 180, 110))
        hline(x + 8, y + h - 6, w - 16, (240, 235, 210), 2)
        for dx in (w // 2 - 6, w // 2, w // 2 + 6):
            vline(x + dx, y + 6, 12, YELLOW, 2)
        line(x + w // 2 + 26, y + 6, x + w // 2 + 12, y + h - 10, BROWN, 4)
        filled_circle(x + w - 30, y + 8, 4, RED)
        filled_circle(x + 24, y + 10, 3, WHITE)
    elif key == "cop31":  # hero: globe, clock, thermometer
        fill_rect(x, y, w, h, (168, 200, 222))
        fill_rect(x, y + h - 10, w, 10, (90, 130, 80))
        filled_circle(x + 78, y + 52, 36, (90, 160, 220))
        filled_poly([(x + 52, y + 40), (x + 66, y + 34), (x + 70, y + 46),
                     (x + 58, y + 54)], GREEN)
        filled_poly([(x + 82, y + 30), (x + 98, y + 36), (x + 94, y + 50),
                     (x + 80, y + 44)], GREEN)
        filled_poly([(x + 60, y + 62), (x + 78, y + 58), (x + 88, y + 70),
                     (x + 66, y + 74)], GREEN)
        circle_outline(x + 78, y + 52, 36, INK, 2)
        filled_circle(x + 205, y + 48, 26, WHITE)
        circle_outline(x + 205, y + 48, 26, INK, 2)
        line(x + 205, y + 48, x + 205, y + 30, INK, 2)
        line(x + 205, y + 48, x + 218, y + 56, INK, 2)
        filled_circle(x + 205, y + 48, 3, INK)
        fill_rect(x + 272, y + 18, 10, 52, WHITE)
        outline_rect(x + 272, y + 18, 10, 52, INK, 1)
        filled_circle(x + 277, y + 78, 12, RED)
        fill_rect(x + 274, y + 40, 6, 32, RED)
        draw_text(x + 296, y + 30, 2, RED, "13", bold=True)
    elif key == "riyadh":  # hero: night sky, skyline, missile trails, bursts
        fill_rect(x, y, w, h, NAVY)
        for sx, sy in ((30, 12), (90, 26), (150, 10), (210, 22), (270, 14), (300, 30),
                       (60, 40), (180, 34), (240, 8)):
            filled_circle(x + sx, y + sy, 1, WHITE)
        filled_circle(x + 290, y + 18, 10, (235, 235, 210))
        for bx, bw, bh in ((20, 34, 46), (58, 26, 62), (88, 40, 38), (132, 30, 56),
                            (166, 36, 44), (206, 28, 66), (238, 34, 40), (276, 30, 52)):
            fill_rect(x + bx, y + h - bh, bw, bh, (10, 16, 32))
            for wy in range(y + h - bh + 6, y + h - 6, 10):
                for wx in range(x + bx + 5, x + bx + bw - 5, 10):
                    if (wx + wy) % 20 == 0:
                        fill_rect(wx, wy, 3, 3, YELLOW)
        for (tx, ty, bx, by) in ((70, 6, 90, 44), (160, 2, 185, 40), (250, 8, 268, 46)):
            line(x + tx, y + ty, x + bx, y + by, (255, 240, 180), 2)
            filled_circle(x + bx, y + by, 7, ORANGE)
            filled_circle(x + bx, y + by, 4, YELLOW)
            line(x + bx - 10, y + by, x + bx + 10, y + by, YELLOW, 1)
            line(x + bx, y + by - 10, x + bx, y + by + 10, YELLOW, 1)
    elif key == "peru":  # hero: seismograph, mountains, cracked house
        fill_rect(x, y, w, h, (205, 220, 232))
        filled_poly([(x, y + 58), (x + 60, y + 22), (x + 120, y + 58),
                     (x + 180, y + 30), (x + 240, y + 58), (x + 325, y + 40),
                     (x + 325, y + 62), (x, y + 62)], (140, 150, 165))
        fill_rect(x, y + 62, w, h - 62, (178, 148, 108))
        fill_rect(x + 14, y + 14, 120, 34, WHITE)
        outline_rect(x + 14, y + 14, 120, 34, INK, 1)
        zx = [20, 34, 44, 58, 66, 80, 92, 104, 116, 128]
        zy = [31, 22, 40, 24, 38, 26, 40, 30, 38, 31]
        for i in range(len(zx) - 1):
            line(x + zx[i], y + zy[i], x + zx[i + 1], y + zy[i + 1], INK, 2)
        hx, hy = x + 200, y + 66
        fill_rect(hx, hy, 56, 30, (235, 220, 190))
        filled_poly([(hx - 4, hy), (hx + 28, hy - 16), (hx + 60, hy)], DARKRED)
        outline_rect(hx, hy, 56, 30, INK, 1)
        line(hx + 24, hy + 30, hx + 30, hy + 14, INK, 1)
        line(hx + 30, hy + 14, hx + 26, hy, INK, 1)
        line(hx + 10, y + h - 2, hx + 18, y + 76, INK, 2)
        line(hx + 18, y + 76, hx + 12, y + 68, INK, 2)
        line(hx + 12, y + 68, hx + 22, y + 62, INK, 2)


# ------------------------------------------------------------------- map ------
CONTINENTS = [
    [(-168, 66), (-140, 70), (-125, 72), (-110, 73), (-95, 80), (-85, 76),
     (-75, 72), (-65, 62), (-55, 52), (-60, 45), (-70, 42), (-75, 35),
     (-80, 32), (-85, 29), (-90, 21), (-95, 19), (-100, 23), (-105, 22),
     (-110, 25), (-115, 30), (-120, 34), (-125, 40), (-125, 48), (-135, 58),
     (-150, 60), (-165, 60)],
    [(-80, 10), (-75, 5), (-70, 0), (-80, -5), (-81, -10), (-77, -15),
     (-70, -18), (-70, -25), (-65, -35), (-60, -40), (-65, -50), (-70, -55),
     (-68, -50), (-65, -40), (-60, -30), (-55, -25), (-50, -15), (-45, -10),
     (-40, -5), (-35, -8), (-40, -15), (-45, -22), (-50, -30), (-55, -35),
     (-60, -35), (-62, -30), (-58, -22), (-52, -15), (-45, -8), (-38, -3),
     (-44, 2), (-52, 4), (-58, 8), (-65, 10), (-72, 12)],
    [(-10, 36), (-9, 43), (-2, 48), (-5, 50), (0, 51), (5, 53), (8, 57),
     (10, 59), (18, 56), (21, 55), (24, 59), (30, 60), (30, 65), (25, 70),
     (20, 70), (15, 68), (10, 64), (5, 58), (0, 55), (-5, 50), (-10, 45)],
    [(-17, 15), (-17, 21), (-10, 30), (-5, 35), (0, 36), (10, 37), (20, 32),
     (30, 31), (32, 31), (35, 28), (37, 22), (40, 15), (43, 11), (48, 11),
     (51, 10), (51, 12), (46, 5), (41, 0), (40, -5), (38, -10), (35, -18),
     (32, -25), (28, -32), (20, -35), (15, -30), (12, -18), (12, -10),
     (13, -5), (9, 4), (4, 6), (-8, 4), (-13, 8), (-17, 12)],
    [(30, 36), (35, 36), (36, 33), (42, 38), (45, 40), (50, 40), (52, 45),
     (55, 50), (60, 55), (65, 60), (70, 65), (75, 70), (80, 72), (90, 75),
     (100, 75), (110, 73), (120, 72), (130, 70), (140, 72), (150, 70),
     (160, 68), (170, 66), (178, 65), (178, 62), (170, 60), (160, 60),
     (155, 55), (150, 60), (142, 55), (140, 50), (135, 45), (130, 42),
     (127, 40), (122, 38), (120, 32), (118, 25), (112, 22), (108, 18),
     (105, 10), (103, 8), (100, 8), (98, 12), (95, 15), (92, 20), (90, 22),
     (88, 22), (85, 20), (82, 17), (80, 13), (77, 8), (75, 12), (72, 20),
     (70, 23), (66, 25), (62, 25), (58, 25), (56, 26), (54, 26), (52, 25),
     (50, 28), (48, 29), (48, 30), (45, 32), (42, 36), (40, 38), (35, 36)],
    [(113, -22), (114, -30), (115, -33), (118, -35), (124, -33), (129, -32),
     (132, -32), (135, -35), (137, -35), (140, -38), (145, -38), (150, -37),
     (153, -32), (153, -27), (150, -23), (146, -19), (142, -11), (137, -12),
     (135, -15), (132, -12), (130, -13), (126, -14), (122, -17), (118, -20)],
    [(-55, 60), (-50, 60), (-45, 60), (-40, 64), (-35, 68), (-30, 68),
     (-25, 70), (-20, 70), (-22, 74), (-30, 76), (-40, 76), (-50, 74),
     (-55, 70), (-58, 65)],
]

PINS = [
    (1, 30.7, 36.9), (2, 46.7, 24.7), (3, -76.0, -11.0), (4, 30.5, 50.4),
    (5, 56.5, 26.5), (6, 51.4, 35.7), (7, -77.0, 38.9), (8, 116.4, 39.9),
    (9, 125.6, 7.1), (10, 149.1, -35.3), (11, -30.0, 10.0), (12, -115.1, 36.2),
    (13, 174.8, -41.3),
]


def draw_map(mx, my, mw, mh):
    fill_rect(mx, my, mw, mh, SEA)
    outline_rect(mx, my, mw, mh, INK, 1)
    lat_top, lat_bot = 72.0, -58.0

    def px(lon):
        return mx + int((lon + 180.0) / 360.0 * mw)

    def py(lat):
        return my + int((lat_top - lat) / (lat_top - lat_bot) * mh)

    for cont in CONTINENTS:
        pts = [(px(lon), py(lat)) for lon, lat in cont]
        filled_poly(pts, LAND)
        poly_outline(pts, INK, 1)
    for label, lon, lat in (("PACIFIC", -150, -8), ("ATLANTIC", -30, -18),
                            ("INDIAN", 80, -28)):
        draw_text(px(lon) - 20, py(lat), 1, GRAY, label)
    for num, lon, lat in PINS:
        cx, cy = px(lon), py(lat)
        filled_circle(cx, cy, 8, RED)
        circle_outline(cx, cy, 8, WHITE, 1)
        s = str(num)
        draw_text(cx - text_w(s, 1) // 2, cy - 3, 1, WHITE, s, bold=True)


# ---------------------------------------------------------------- layout ------
def draw_centered_lines(x, y, w, scale, color, text, max_lines, line_h, bold=False):
    lines = wrap_text(text, w, scale)[:max_lines]
    for i, ln in enumerate(lines):
        draw_text(x + (w - text_w(ln, scale)) // 2, y + i * line_h, scale, color, ln, bold=bold)
    return len(lines)


def draw_hero_card(x, y, w, h, hero):
    fill_rect(x, y, w, h, CARD)
    outline_rect(x, y, w, h, INK, 1)
    draw_art(hero["art"], x + 1, y + 1, w - 2, 100)
    ty = y + 102
    fill_rect(x + 1, ty, w - 2, 22, RED)
    draw_text(x + 8, ty + 4, 2, WHITE, hero["title"], bold=True)
    chip = hero["chip"]
    draw_text(x + w - 8 - text_w(chip, 1), ty + 8, 1, WHITE, chip, bold=True)
    draw_text(x + 8, y + 128, 1, RED, hero["place"], bold=True)
    draw_wrapped(x + 8, y + 142, w - 16, 3, INK, hero["headline"],
                 line_h=24, bold=True, max_lines=2)
    draw_wrapped(x + 8, y + 194, w - 16, 2, INK, hero["summary"],
                 line_h=17, max_lines=2)
    draw_text(x + 8, y + h - 8, 1, GRAY, hero["source"])


def draw_medium_card(x, y, w, h, story):
    fill_rect(x, y, w, h, CARD)
    outline_rect(x, y, w, h, INK, 1)
    draw_art(story["art"], x + 1, y + 1, w - 2, 30)
    bx, by = x + 4, y + 4
    fill_rect(bx, by, 16, 16, RED)
    s = str(story["num"])
    draw_text(bx + (16 - text_w(s, 1)) // 2, by + 5, 1, WHITE, s, bold=True)
    ty = y + 32
    fill_rect(x + 1, ty, w - 2, 16, RED)
    draw_text(x + 6, ty + 5, 1, WHITE, story["label"], bold=True)
    draw_wrapped(x + 6, y + 49, w - 12, 2, INK, story["headline"],
                 line_h=16, bold=True, max_lines=2)
    draw_text(x + 6, y + 80, 1, GRAY, story["summary"])


def draw_legend_box(x, y, w, h):
    fill_rect(x, y, w, h, (238, 232, 214))
    outline_rect(x, y, w, h, INK, 1)
    draw_text(x + 10, y + 8, 2, RED, "HOW WE CHECKED", bold=True)
    draw_text(x + 10, y + 30, 1, INK, "CONFIRMED = 2+ outlets - OFFICIAL = on the record")
    draw_text(x + 10, y + 42, 1, INK, "REPORTED = one outlet - CLAIM = one side's account")
    draw_text(x + 10, y + 54, 1, INK, "Sources named beside each story. All drawings original.")
    draw_text(x + 10, y + 68, 1, INK, "50 stories - 7 regions - 4 sport stories")


def main():
    fill_rect(0, 0, W, H, PAPER)

    # top bar
    fill_rect(0, 0, W, 26, RED)
    draw_text(16, 6, 2, WHITE, "THE WORLD IN ONE DAY", bold=True)
    right = "50 STORIES - 7 REGIONS - EVERY ONE DATED SATURDAY 21 NOVEMBER 2026"
    draw_text(W - 16 - text_w(right, 1), 9, 1, WHITE, right)

    # masthead + subhead
    draw_text_center(0, 30, W, 6, INK, "Saturday 21 November 2026", bold=True)
    draw_text_center(0, 78, W, 2, INK,
                     "COP31 talks run into overtime - missiles over Riyadh - a quake shakes Peru")
    hline(16, 96, 992, INK, 2)

    # stat strip
    colw, gap, x0 = 160, 6, 17
    for i, (num, label) in enumerate(STATS):
        cx = x0 + i * (colw + gap)
        draw_text_center(cx, 102, colw, 3, RED, num, bold=True)
        draw_centered_lines(cx, 128, colw, 1, INK, label, 2, 9)
        if i < 5:
            vline(cx + colw + 3, 106, 40, LGRAY)

    # region bar
    widths = [142, 142, 141, 142, 141, 142, 142]
    rx = 16
    for (name, color), wd in zip(REGIONS, widths):
        fill_rect(rx, 152, wd, 18, color)
        draw_text_center(rx, 158, wd, 1, WHITE, name, bold=True)
        rx += wd

    # hero row
    for i, hero in enumerate(HERO):
        draw_hero_card([16, 349, 682][i], 174, 325, 236, hero)

    # map band (full width, middle of the page)
    draw_text(16, 414, 2, INK, "WHERE IT HAPPENED - STORIES 1-13", bold=True)
    note = "EACH NUMBER MATCHES A STORY ABOVE"
    draw_text(W - 16 - text_w(note, 1), 418, 1, GRAY, note)
    draw_map(16, 434, 992, 140)

    # medium grid: 4 cols x 3 rows (last row: 2 cards + legend box)
    gy = 578
    for row in range(3):
        for col in range(4):
            gx = 16 + col * 250
            gy2 = gy + row * 92
            if row == 2 and col >= 2:
                continue
            draw_medium_card(gx, gy2, 242, 88, MEDIUM[row * 4 + col])
    draw_legend_box(516, gy + 2 * 92, 492, 88)

    # also-on list, 3 columns, flowing
    ay = 854
    draw_text(16, ay, 2, INK, "ALSO ON SATURDAY 21 NOVEMBER - 37 MORE STORIES", bold=True)
    col_items = [ALSO[0:13], ALSO[13:25], ALSO[25:37]]
    col_x = [16, 352, 688]
    max_lines = 0
    for ci, items in enumerate(col_items):
        cy = ay + 18
        nlines = 0
        for num, text, _region in items:
            lines = wrap_text("%d %s" % (num, text), 320, 1)
            for ln in lines:
                draw_text(col_x[ci], cy, 1, INK, ln)
                cy += 7
                nlines += 1
        max_lines = max(max_lines, nlines)
    band_bottom = ay + 18 + max_lines * 7

    # date check
    dy = band_bottom + 6
    fill_rect(16, dy, 992, 38, (238, 232, 214))
    outline_rect(16, dy, 992, 38, RED, 2)
    draw_wrapped(24, dy + 5, 976, 1, INK, "DATE CHECK - " + DATE_CHECK,
                 line_h=8, max_lines=3)
    cy2 = dy + 38 + 6
    draw_text_center(0, cy2, W, 1, GRAY, CREDIT)
    print("layout: also-on lines/col max=%d band_bottom=%d date_y=%d credit_y=%d final_y=%d"
          % (max_lines, band_bottom, dy, cy2, cy2 + 8))

    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not outdir:
        outdir = "/output" if os.path.isdir("/output") else "out"
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    size = write_png(path, W, H, BUF)
    print("wrote %s (%d bytes, %dx%d)" % (path, size, W, H))
    print("stories: hero=%d medium=%d also=%d total=%d"
          % (len(HERO), len(MEDIUM), len(ALSO), len(HERO) + len(MEDIUM) + len(ALSO)))
    regions = {}
    for _n, _t, r in ALSO:
        regions[r] = regions.get(r, 0) + 1
    print("also-on regions: %s" % (regions,))


if __name__ == "__main__":
    main()
