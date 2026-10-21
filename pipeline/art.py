#!/usr/bin/env python3
"""Generate channel art (profile 800x800, banner 2560x1440) into assets/channel-art/<channel>/.

Banner text stays inside YouTube's safe area (1546x423, centred) so it shows on every device.
Usage: .venv/bin/python pipeline/art.py
"""
import math
import random

from PIL import Image, ImageDraw

from render import ROOT, font, gradient, hsv, mix

OUT = ROOT / "assets" / "channel-art"
BW, BH = 2560, 1440
SAFE_TOP = (BH - 423) // 2


def pebkin(d, cx, cy, s):
    """Pebkin the pebble at scale s (1.0 = same size as in the kids videos)."""
    d.ellipse([cx - 165 * s, cy - 150 * s, cx + 165 * s, cy + 190 * s], fill=(167, 139, 250),
              outline=(109, 40, 217), width=int(7 * s))
    for ex in (cx - 100 * s, cx + 100 * s):
        d.ellipse([ex - 28 * s, cy + 30 * s, ex + 28 * s, cy + 60 * s], fill=(244, 170, 210))
    for ex in (cx - 60 * s, cx + 60 * s):
        d.ellipse([ex - 34 * s, cy - 64 * s, ex + 34 * s, cy + 4 * s], fill=(255, 255, 255))
        d.ellipse([ex - 7 * s, cy - 37 * s, ex + 23 * s, cy - 7 * s], fill=(46, 16, 101))
    d.chord([cx - 50 * s, cy + 30 * s, cx + 50 * s, cy + 110 * s], 0, 180, fill=(76, 29, 149))


def apple(d, x, y, r):
    d.ellipse([x - r, y - r * 0.9, x + r, y + r], fill=(239, 68, 68), outline=(153, 27, 27), width=max(2, int(r / 12)))
    d.rectangle([x - r * 0.08, y - r * 1.25, x + r * 0.08, y - r * 0.8], fill=(120, 72, 30))
    d.ellipse([x + r * 0.08, y - r * 1.3, x + r * 0.75, y - r * 0.95], fill=(34, 197, 94))
    d.ellipse([x - r * 0.55, y - r * 0.5, x - r * 0.22, y - r * 0.15], fill=(254, 202, 202))


def balls_ring(d, cx, cy, R, n, seed, width):
    rnd = random.Random(seed)
    gap = math.radians(34)
    d.arc([cx - R, cy - R, cx + R, cy + R], math.degrees(gap) - 60, 300, fill=(255, 255, 255), width=width)
    placed = []
    while len(placed) < n:
        r = rnd.uniform(R * 0.07, R * 0.13)
        a, dist = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, R - r - width)
        x, y = cx + math.cos(a) * dist, cy + math.sin(a) * dist
        if all(math.hypot(x - px, y - py) > r + pr + 4 for px, py, pr in placed):
            placed.append((x, y, r))
            d.ellipse([x - r, y - r, x + r, y + r], fill=hsv(rnd.random()), outline=(255, 255, 255), width=max(2, width // 3))


def centered(d, xy, text, f, **kw):
    d.text(xy, text, font=f, anchor="mm", **kw)


def kidsmath():
    out = OUT / "kidsmath"
    out.mkdir(parents=True, exist_ok=True)
    p = gradient(800, 800, (186, 230, 253), (240, 249, 255))
    d = ImageDraw.Draw(p)
    d.ellipse([-100, 600, 900, 1000], fill=(134, 239, 172))
    pebkin(d, 400, 380, 1.55)
    p.save(out / "profile.png")

    b = gradient(BW, BH, (186, 230, 253), (240, 249, 255))
    d = ImageDraw.Draw(b)
    d.rectangle([0, SAFE_TOP + 380, BW, BH], fill=(134, 239, 172))
    for cx, cy in [(400, 300), (2150, 260), (1500, 180)]:
        for dx, dy, r in [(-70, 10, 60), (0, -18, 80), (75, 10, 58)]:
            d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=(255, 255, 255))
    pebkin(d, 640, SAFE_TOP + 210, 0.95)
    centered(d, (1400, SAFE_TOP + 150), "Count With Pebkin", font("Fredoka.ttf", 120, "Bold"), fill=(76, 29, 149))
    centered(d, (1400, SAFE_TOP + 270), "Gentle math for little learners", font("Fredoka.ttf", 56, "Medium"), fill=(109, 40, 217))
    for k, x in enumerate([1820, 1930]):
        apple(d, x, SAFE_TOP + 330, 42)
    b.save(out / "banner.png")


def facts():
    out = OUT / "facts"
    out.mkdir(parents=True, exist_ok=True)
    p = gradient(800, 800, (168, 85, 247), (236, 72, 153))
    d = ImageDraw.Draw(p)
    d.ellipse([80, 80, 720, 720], fill=(0, 0, 0))
    centered(d, (400, 330), "?!", font("LuckiestGuy-Regular.ttf", 330), fill=(255, 226, 0), stroke_width=10, stroke_fill=(0, 0, 0))
    centered(d, (400, 560), "FACT LAB", font("Anton-Regular.ttf", 110), fill=(255, 255, 255))
    p.save(out / "profile.png")

    b = gradient(BW, BH, (168, 85, 247), (236, 72, 153))
    d = ImageDraw.Draw(b)
    rnd = random.Random(3)
    for _ in range(40):
        x, y, r = rnd.uniform(0, BW), rnd.uniform(0, BH), rnd.uniform(30, 140)
        d.ellipse([x - r, y - r, x + r, y + r], fill=mix((200, 80, 220), (255, 255, 255), 0.15))
    centered(d, (BW / 2, SAFE_TOP + 170), "USELESS FACT LAB", font("LuckiestGuy-Regular.ttf", 190), fill=(255, 255, 255),
             stroke_width=12, stroke_fill=(0, 0, 0))
    centered(d, (BW / 2, SAFE_TOP + 330), "Facts you'll never need and never forget", font("Anton-Regular.ttf", 72), fill=(255, 226, 0))
    b.save(out / "banner.png")


def stories():
    out = OUT / "stories"
    out.mkdir(parents=True, exist_ok=True)
    p = Image.new("RGB", (800, 800), (12, 10, 24))
    d = ImageDraw.Draw(p)
    balls_ring(d, 400, 400, 330, 16, 7, 22)
    p.save(out / "profile.png")

    b = Image.new("RGB", (BW, BH), (12, 10, 24))
    d = ImageDraw.Draw(b)
    balls_ring(d, 560, SAFE_TOP + 211, 190, 11, 11, 14)
    balls_ring(d, 2000, SAFE_TOP + 211, 190, 11, 12, 14)
    centered(d, (BW / 2, SAFE_TOP + 170), "STORY BALL PIT", font("LuckiestGuy-Regular.ttf", 150), fill=(255, 255, 255),
             stroke_width=10, stroke_fill=(0, 0, 0))
    centered(d, (BW / 2, SAFE_TOP + 300), "Ridiculous stories that escalate fast", font("LuckiestGuy-Regular.ttf", 58),
             fill=(255, 226, 0), stroke_width=5, stroke_fill=(0, 0, 0))
    b.save(out / "banner.png")


if __name__ == "__main__":
    kidsmath()
    facts()
    stories()
    print(f"saved to {OUT}")
