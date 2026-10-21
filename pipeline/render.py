#!/usr/bin/env python3
"""Render a script JSON into a finished video + post.md in ready-to-post/<channel>/<id>/.

Usage: .venv/bin/python pipeline/render.py queue/stories/s001.json
"""
import argparse
import colorsys
import json
import math
import random
import re
import subprocess
import warnings
import zlib
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
FPS = 30
SR = 24000
GAP = 0.18  # default silence between segments, seconds
LEAD_IN, TAIL = 0.3, 0.9

NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
                "nineteen", "twenty"]

# ---------------------------------------------------------------- audio

_kokoro = None


def tts(text, voice, speed):
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(ROOT / "assets/models/kokoro-v1.0.onnx"), str(ROOT / "assets/models/voices-v1.0.bin"))
    lang = "en-gb" if voice.startswith("b") else "en-us"
    samples, sr = _kokoro.create(text, voice=voice, speed=speed, lang=lang)
    assert sr == SR, sr
    return trim_silence(samples.astype(np.float32))


def trim_silence(a, thresh=0.01, pad=0.03):
    idx = np.where(np.abs(a) > thresh)[0]
    if not len(idx):
        return a
    p = int(pad * SR)
    return a[max(0, idx[0] - p): idx[-1] + p]


def build_audio(script):
    """Voice every segment and return (audio, segments-with-start/end-times)."""
    voice, speed = script["voice"], script.get("speed", 1.0)
    pieces = [np.zeros(int(LEAD_IN * SR), np.float32)]
    segs, n = [], len(pieces[0])
    for seg in script["segments"]:
        a = tts(seg["text"], seg.get("voice", voice), seg.get("speed", speed))
        segs.append({**seg, "start": n / SR, "end": (n + len(a)) / SR})
        silence = np.zeros(int(seg.get("pause", GAP) * SR), np.float32)
        pieces += [a, silence]
        n += len(a) + len(silence)
    pieces.append(np.zeros(int(TAIL * SR), np.float32))
    audio = np.concatenate(pieces)
    peak = np.max(np.abs(audio)) or 1.0
    return audio * (0.89 / peak), segs


def seg_words(seg):
    """Estimate per-word timing inside a segment, weighted by word length."""
    words = seg["text"].split()
    weights = [len(w) + 2 for w in words]
    total, acc, out = sum(weights), 0, []
    span = seg["end"] - seg["start"]
    for w, wt in zip(words, weights):
        st = seg["start"] + span * acc / total
        acc += wt
        out.append((w, st, seg["start"] + span * acc / total))
    return out


def caption_chunks(segs, max_words):
    chunks = []
    for seg in segs:
        cur = []
        for item in seg_words(seg):
            cur.append(item)
            if len(cur) >= max_words or item[0][-1] in ".,!?;:":
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
    return chunks


def rms_track(audio, n_frames):
    hop = SR // FPS
    out = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(audio) else 0.0
                    for i in range(n_frames)])
    loud = out[out > 0.005]
    ref = np.percentile(loud, 95) if len(loud) else 1.0
    out = np.clip(out / ref, 0, 1)
    return np.convolve(out, [0.25, 0.5, 0.25], mode="same")  # smooth jitter

# ---------------------------------------------------------------- drawing helpers

_fonts = {}


def font(name, size, variation=None):
    key = (name, size, variation)
    if key not in _fonts:
        f = ImageFont.truetype(str(FONTS / name), size)
        if variation:
            f.set_variation_by_name(variation)
        _fonts[key] = f
    return _fonts[key]


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def back_out(x):
    x = min(max(x, 0.0), 1.0)
    c = 1.7
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def hsv(h, s=0.75, v=1.0):
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h % 1, s, v))


def mix(a, b, k):
    return tuple(int(x + (y - x) * k) for x, y in zip(a, b))


def gradient(w, h, top, bottom):
    k = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(top)[None, None, :] * (1 - k) + np.array(bottom)[None, None, :] * k)
    return Image.fromarray(np.repeat(arr, w, axis=1).astype(np.uint8), "RGB")


def active_index(segs, t):
    idx = 0
    for i, s in enumerate(segs):
        if s["start"] <= t:
            idx = i
    return idx


def draw_caption(img, chunks, t, fnt, y, max_w, hl=(255, 226, 0), upper=True, stroke=10):
    chunk = None
    for i, ch in enumerate(chunks):
        nxt = chunks[i + 1][0][1] if i + 1 < len(chunks) else math.inf
        if ch[0][1] <= t < min(nxt, ch[-1][2] + 0.4):
            chunk = ch
    if not chunk:
        return
    words = [w.upper() if upper else w for w, _, _ in chunk]
    f = fnt
    total = sum(f.getlength(w) for w in words) + f.getlength(" ") * (len(words) - 1)
    if total > max_w:
        f = fnt.font_variant(size=int(fnt.size * max_w / total))
        total = sum(f.getlength(w) for w in words) + f.getlength(" ") * (len(words) - 1)
    dy = -18 * (1 - ease_out((t - chunk[0][1]) / 0.12))
    d = ImageDraw.Draw(img)
    x = (img.width - total) / 2
    for word, (_, ws, we) in zip(words, chunk):
        color = hl if ws <= t < we else (255, 255, 255)
        d.text((x, y + dy), word, font=f, fill=color, stroke_width=stroke, stroke_fill=(0, 0, 0), anchor="lm")
        x += f.getlength(word) + f.getlength(" ")


def draw_progress(img, t, dur, color=(255, 226, 0)):
    d = ImageDraw.Draw(img)
    d.rectangle([0, img.height - 14, img.width * min(1, t / dur), img.height], fill=color)

# ---------------------------------------------------------------- styles


class Stories:
    """Vertical: AI narration over a self-generated 'balls escaping a spinning ring' simulation."""
    W, H = 1080, 1920
    MAX_BALLS = 40

    def __init__(self, ctx):
        self.ctx = ctx
        self.rnd = random.Random(ctx["seed"])
        self.bgimg = Image.new("RGB", (self.W, self.H), (12, 10, 24))
        self.trail = self.bgimg.copy()
        self.c = np.array([self.W / 2, self.H * 0.63])
        self.R = 420.0
        self.rot, self.gap, self.spin = 0.0, math.radians(34), math.radians(70)
        self.balls = [self.new_ball()]
        self.flash = 0.0
        self.cap_font = font("LuckiestGuy-Regular.ttf", 118)
        self.small = font("LuckiestGuy-Regular.ttf", 64)

    def new_ball(self):
        a = self.rnd.uniform(0, 2 * math.pi)
        sp = self.rnd.uniform(700, 1000)
        return {"p": self.c + self.rnd.uniform(-30, 30), "v": np.array([math.cos(a) * sp, math.sin(a) * sp]),
                "r": 22.0, "h": self.rnd.random(), "out": False}

    def step(self, dt, sub=4):
        self.rot = (self.rot + self.spin * dt) % (2 * math.pi)
        h = dt / sub
        for _ in range(sub):
            keep, spawn = [], 0
            for b in self.balls:
                b["v"][1] += 1500 * h
                b["p"] = b["p"] + b["v"] * h
                if b["out"]:
                    if -200 < b["p"][0] < self.W + 200 and b["p"][1] < self.H + 200:
                        keep.append(b)
                    continue
                d = b["p"] - self.c
                dist = float(np.hypot(*d))
                if dist + b["r"] >= self.R:
                    rel = (math.atan2(d[1], d[0]) - self.rot) % (2 * math.pi)
                    if rel < self.gap or dist > self.R:
                        if dist - b["r"] > self.R:
                            b["out"] = True
                            spawn += 2
                    else:
                        n = d / dist
                        vn = float(b["v"] @ n)
                        if vn > 0:
                            b["v"] = b["v"] - 2 * vn * n
                            sp = float(np.hypot(*b["v"]))
                            b["v"] *= min(max(sp, 900), 2400) / sp
                            b["r"] = min(b["r"] + 1.2, 48)
                            b["h"] = (b["h"] + 0.04) % 1
                            self.flash = 1.0
                        b["p"] = self.c + n * (self.R - b["r"])
                keep.append(b)
            for _ in range(min(spawn, self.MAX_BALLS - len(keep))):
                keep.append(self.new_ball())
            if not any(not b["out"] for b in keep):
                keep.append(self.new_ball())
            self.balls = keep

    def frame(self, i, t):
        self.step(1 / FPS)
        self.trail = Image.blend(self.trail, self.bgimg, 0.22)
        d = ImageDraw.Draw(self.trail)
        for b in self.balls:
            x, y, r = b["p"][0], b["p"][1], b["r"]
            d.ellipse([x - r, y - r, x + r, y + r], fill=hsv(b["h"], 0.8, 0.7))
        img = self.trail.copy()
        d = ImageDraw.Draw(img)
        self.flash *= 0.85
        cx, cy, R = self.c[0], self.c[1], self.R + 9
        d.arc([cx - R, cy - R, cx + R, cy + R], math.degrees(self.rot + self.gap), math.degrees(self.rot) + 360,
              fill=mix((255, 255, 255), (255, 70, 200), self.flash), width=14)
        for b in self.balls:
            x, y, r = b["p"][0], b["p"][1], b["r"]
            d.ellipse([x - r, y - r, x + r, y + r], fill=hsv(b["h"]), outline=(255, 255, 255), width=3)
        inside = sum(1 for b in self.balls if not b["out"])
        d.text((self.W / 2, cy + R + 110), f"{inside} BALL{'' if inside == 1 else 'S'}", font=self.small, fill=(255, 255, 255),
               stroke_width=6, stroke_fill=(0, 0, 0), anchor="mm")
        draw_caption(img, self.ctx["chunks"], t, self.cap_font, 470, self.W - 120)
        draw_progress(img, t, self.ctx["dur"])
        return img


class Facts:
    """Vertical: bold gradients, a persistent label ('USELESS FACT #3'), a huge pop-in keyword, captions."""
    W, H = 1080, 1920
    PALETTES = [((255, 94, 98), (255, 153, 102)), ((86, 204, 242), (47, 128, 237)),
                ((168, 85, 247), (236, 72, 153)), ((34, 197, 94), (13, 148, 136)),
                ((250, 204, 21), (249, 115, 22)), ((99, 102, 241), (14, 165, 233))]

    def __init__(self, ctx):
        self.ctx = ctx
        rnd = random.Random(ctx["seed"])
        self.grads = {}
        self.blobs = [(rnd.uniform(0, self.W), rnd.uniform(0, self.H), rnd.uniform(-40, 40),
                       rnd.uniform(-60, -20), rnd.uniform(60, 180)) for _ in range(9)]
        self.cap_font = font("LuckiestGuy-Regular.ttf", 112)
        self.label_font = font("Anton-Regular.ttf", 96)
        labels, cur = [], ""
        for s in ctx["segs"]:
            cur = s.get("label", cur)
            labels.append(cur)
        self.labels = labels

    def grad(self, k):
        if k not in self.grads:
            self.grads[k] = gradient(self.W, self.H, *self.PALETTES[k % len(self.PALETTES)])
        return self.grads[k]

    def frame(self, i, t):
        segs = self.ctx["segs"]
        si = active_index(segs, t)
        seg, age = segs[si], t - segs[si]["start"]
        top = self.PALETTES[si % len(self.PALETTES)][0]
        img = self.grad(si).copy()
        d = ImageDraw.Draw(img)
        for x0, y0, vx, vy, r in self.blobs:
            x = (x0 + vx * t) % (self.W + 2 * r) - r
            y = (y0 + vy * t) % (self.H + 2 * r) - r
            d.ellipse([x - r, y - r, x + r, y + r], fill=mix(top, (255, 255, 255), 0.18))
        if self.labels[si]:
            d.rounded_rectangle([90, 230, self.W - 90, 390], radius=36, fill=(0, 0, 0))
            d.text((self.W / 2, 310), self.labels[si].upper(), font=self.label_font, fill=(255, 255, 255), anchor="mm")
        if seg.get("big"):
            size = max(20, int(230 * back_out(age / 0.3)))
            f = font("LuckiestGuy-Regular.ttf", size)
            if f.getlength(seg["big"].upper()) > self.W - 120:
                f = f.font_variant(size=int(size * (self.W - 120) / f.getlength(seg["big"].upper())))
            d.text((self.W / 2, 860), seg["big"].upper(), font=f, fill=(255, 255, 255), stroke_width=14,
                   stroke_fill=(0, 0, 0), anchor="mm")
        draw_caption(img, self.ctx["chunks"], t, self.cap_font, 1380, self.W - 120)
        draw_progress(img, t, self.ctx["dur"], (255, 255, 255))
        return img


class KidsMath:
    """Landscape: Pebkin the pebble mascot teaches simple sums with apples. Scenes are authored per segment."""
    W, H = 1920, 1080
    ROW_Y = 430

    def __init__(self, ctx):
        self.ctx = ctx
        bg = gradient(self.W, self.H, (186, 230, 253), (240, 249, 255))
        d = ImageDraw.Draw(bg)
        d.rectangle([0, 900, self.W, self.H], fill=(134, 239, 172))
        d.ellipse([-200, 860, 900, 980], fill=(134, 239, 172))
        d.ellipse([1100, 870, 2200, 960], fill=(134, 239, 172))
        for cx, cy in [(1500, 140), (700, 110), (1820, 260)]:
            for dx, dy, r in [(-60, 10, 50), (0, -15, 65), (65, 10, 48)]:
                d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], fill=(255, 255, 255))
        self.bg = bg
        self.eq_font = font("Fredoka.ttf", 150, "Bold")
        self.badge_font = font("Fredoka.ttf", 44, "Bold")
        # scenes inherit from the previous segment; count-badge times come from spoken number words
        scenes, cur = [], {}
        for s in ctx["segs"]:
            cur = s.get("scene", cur)
            scenes.append(cur)
        self.scenes = scenes
        self.count_times, prev_times = [], []
        for i, s in enumerate(ctx["segs"]):
            sc = scenes[i]
            prev = scenes[i - 1] if i else {}
            if "count" in sc.get("show", []) and ("count" not in prev.get("show", []) or self.key(prev) != self.key(sc)):
                n = len(self.counted(sc))
                nums = [st for w, st, _ in seg_words(s) if re.sub(r"\W", "", w).lower() in NUMBER_WORDS]
                if len(nums) < n:
                    span = s["end"] - s["start"]
                    nums = [s["start"] + span * k / n for k in range(n)]
                prev_times = nums[:n]
            elif "count" not in sc.get("show", []):
                prev_times = []
            self.count_times.append(prev_times)
        rnd = random.Random(ctx["seed"])
        self.confetti = [(rnd.uniform(0, self.W), rnd.uniform(-300, 0), rnd.uniform(350, 650), rnd.uniform(0, 6.3),
                          hsv(rnd.random(), 0.7, 1.0)) for _ in range(90)]

    @staticmethod
    def key(sc):
        return (sc.get("a"), sc.get("b"), sc.get("op"))

    def result(self, sc):
        return sc["a"] + sc["b"] if sc.get("op", "+") == "+" else sc["a"] - sc["b"]

    def layout(self, sc):
        """Return list of (x, y, group) for every apple in the scene; also sets apple size for the scene."""
        widest = min(5, max(sc["a"], sc["b"]) if sc.get("op", "+") == "+" else sc["a"])
        self.ITEM_R = 80 if widest <= 3 else 55
        self.SPACING = self.ITEM_R * 2.6

        def grid(n, cx):
            cols = min(n, 5)
            pts = []
            for k in range(n):
                row, col = divmod(k, cols)
                in_row = min(cols, n - row * cols)
                pts.append((cx + (col - (in_row - 1) / 2) * self.SPACING, self.ROW_Y + row * self.SPACING))
            return pts
        if sc.get("op", "+") == "+":
            return [(x, y, "a") for x, y in grid(sc["a"], 880)] + [(x, y, "b") for x, y in grid(sc["b"], 1500)]
        pts = grid(sc["a"], 1190)
        return [(x, y, "b" if k >= sc["a"] - sc["b"] else "a") for k, (x, y) in enumerate(pts)]

    def counted(self, sc):
        items = self.layout(sc)
        return items if sc.get("op", "+") == "+" else [p for p in items if p[2] == "a"]

    def apple(self, d, x, y, s, grey=False):
        r = self.ITEM_R * s
        if r < 2:
            return
        body, line = ((209, 213, 219), (107, 114, 128)) if grey else ((239, 68, 68), (153, 27, 27))
        d.ellipse([x - r, y - r * 0.9, x + r, y + r], fill=body, outline=line, width=max(1, int(4 * s)))
        d.rectangle([x - 4 * s, y - r * 1.25, x + 4 * s, y - r * 0.8], fill=(120, 72, 30))
        d.ellipse([x + 4 * s, y - r * 1.3, x + r * 0.75, y - r * 0.95], fill=(34, 197, 94))
        d.ellipse([x - r * 0.55, y - r * 0.5, x - r * 0.22, y - r * 0.15], fill=(255, 255, 255) if grey else (254, 202, 202))

    def pip(self, d, t, amp):
        x, y = 280, 600 + math.sin(t * 2.2) * 8
        d.ellipse([x - 150, 870, x + 150, 915], fill=(110, 200, 140))
        d.ellipse([x - 165, y - 150, x + 165, y + 190], fill=(167, 139, 250), outline=(109, 40, 217), width=7)
        for cx in (x - 100, x + 100):
            d.ellipse([cx - 28, y + 30, cx + 28, y + 60], fill=(244, 170, 210))
        blink = (t % 3.6) < 0.13
        for ex in (x - 60, x + 60):
            if blink:
                d.line([ex - 28, y - 30, ex + 28, y - 30], fill=(46, 16, 101), width=9)
            else:
                d.ellipse([ex - 34, y - 64, ex + 34, y + 4], fill=(255, 255, 255))
                d.ellipse([ex - 7, y - 37, ex + 23, y - 7], fill=(46, 16, 101))
        h = 10 + 62 * amp
        d.ellipse([x - 40, y + 60, x + 40, y + 60 + h], fill=(76, 29, 149))

    def frame(self, i, t):
        segs = self.ctx["segs"]
        si = active_index(segs, t)
        seg, age = segs[si], t - segs[si]["start"]
        sc = self.scenes[si]
        prev = self.scenes[si - 1] if si and self.key(self.scenes[si - 1]) == self.key(sc) else {}
        show, before = set(sc.get("show", [])), set(prev.get("show", []))
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        self.pip(d, t, self.ctx["rms"][min(i, len(self.ctx["rms"]) - 1)])
        if not sc:
            return img

        def pop(token, delay=0.0):
            return 1.0 if token in before else back_out((age - delay) / 0.35)

        items = self.layout(sc)
        minus = sc.get("op", "+") == "-"
        if minus:
            visible = [(x, y, g, pop("a", k * 0.12)) for k, (x, y, g) in enumerate(items)] if "a" in show else []
        else:
            ka = [p for p in items if p[2] == "a"]
            kb = [p for p in items if p[2] == "b"]
            visible = ([(x, y, g, pop("a", k * 0.12)) for k, (x, y, g) in enumerate(ka)] if "a" in show else []) + \
                      ([(x, y, g, pop("b", k * 0.12)) for k, (x, y, g) in enumerate(kb)] if "b" in show else [])
            if "op" in show:
                s = pop("op")
                f = font("Fredoka.ttf", max(10, int(130 * s)), "Bold")
                d.text((1190, self.ROW_Y), "+", font=f, fill=(76, 29, 149), anchor="mm")
        times = self.count_times[si]
        counted = self.counted(sc)
        for x, y, g, s in visible:
            crossed = minus and g == "b" and "b" in show
            if (x, y, g) in counted and times:
                k = counted.index((x, y, g))
                if k < len(times) and t >= times[k]:
                    glow = 1 - ease_out((t - times[k]) / 0.5)
                    gr = self.ITEM_R * (1.35 + 0.25 * glow)
                    d.ellipse([x - gr, y - gr, x + gr, y + gr], fill=mix((254, 240, 138), (250, 204, 21), glow))
                    bx, by = x, y - self.ITEM_R - 58 - 10 * glow
                    d.ellipse([bx - 34, by - 34, bx + 34, by + 34], fill=(250, 204, 21), outline=(161, 98, 7), width=4)
                    d.text((bx, by), str(k + 1), font=self.badge_font, fill=(66, 32, 6), anchor="mm")
            self.apple(d, x, y, s, grey=crossed)
            if crossed:
                c = pop("b") * self.ITEM_R * 0.9
                d.line([x - c, y - c, x + c, y + c], fill=(75, 85, 99), width=14)
                d.line([x - c, y + c, x + c, y - c], fill=(75, 85, 99), width=14)
        if "eq" in show:
            parts = [(str(sc["a"]), (76, 29, 149)), (f" {'+' if not minus else '−'} ", (76, 29, 149)),
                     (str(sc["b"]), (76, 29, 149)), (" = ", (76, 29, 149))]
            ans = "ans" in show
            parts.append((str(self.result(sc)) if ans else "?", (236, 72, 153) if ans else (148, 163, 184)))
            f = self.eq_font
            total = sum(f.getlength(p) for p, _ in parts)
            x = 1190 - total / 2
            for k, (p, col) in enumerate(parts):
                pf = f
                if k == len(parts) - 1 and ans:
                    pf = font("Fredoka.ttf", max(10, int(150 * pop("ans"))), "Bold")
                d.text((x + f.getlength(p) / 2, 800), p, font=pf, fill=col, anchor="mm")
                x += f.getlength(p)
            if ans and "ans" not in before and age < 2.6:
                for cx, cy, sp, ph, col in self.confetti:
                    yy = cy + sp * age
                    xx = cx + math.sin(ph + age * 4) * 30
                    d.rectangle([xx - 9, yy - 5, xx + 9, yy + 5], fill=col)
        return img


STYLES = {"stories": Stories, "facts": Facts, "kidsmath": KidsMath}
CAPTION_WORDS = {"stories": 3, "facts": 3, "kidsmath": 6}

# ---------------------------------------------------------------- output


def write_post(script, out_dir, dur):
    ch = script["channel"]
    tags = " ".join("#" + h.lstrip("#") for h in script.get("hashtags", []))
    lines = [f"# {script['title']}", "", f"- Channel: **{ch}**  |  Length: {dur:.0f}s  |  ID: {script['id']}", "",
             "## YouTube", f"**Title:** {script['title']}", "", "**Description:**", "```",
             script.get("description", ""), "", tags, "```"]
    if ch == "kidsmath":
        lines += ["- Audience: **Yes, it's made for kids** (required)", "- Upload as a regular video (landscape)"]
    else:
        lines += ["- Audience: Not made for kids", "- Vertical and under 3 min → becomes a Short automatically"]
    lines += ["- Altered/synthetic content: No (fictional/animated, AI voice only)", ""]
    if ch != "kidsmath":
        lines += ["## TikTok", "**Caption:**", "```", f"{script.get('tiktok_caption', script['title'])} {tags}", "```",
                  "- Turn ON the 'AI-generated content' label (AI voice)", ""]
    (out_dir / "post.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    args = ap.parse_args()
    script = json.loads(Path(args.script).read_text())
    ch = script["channel"]
    out_dir = ROOT / "ready-to-post" / ch / script["id"]
    out_dir.mkdir(parents=True, exist_ok=True)

    audio, segs = build_audio(script)
    dur = len(audio) / SR
    n = int(math.ceil(dur * FPS))
    ctx = {"segs": segs, "dur": dur, "seed": script.get("seed", zlib.crc32(script["id"].encode())),
           "chunks": caption_chunks(segs, CAPTION_WORDS[ch]), "rms": rms_track(audio, n)}
    style = STYLES[ch](ctx)
    wav = out_dir / "voice.wav"
    sf.write(wav, audio, SR)

    video = out_dir / "video.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{style.W}x{style.H}", "-r", str(FPS), "-i", "-", "-i", str(wav),
           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
           "-movflags", "+faststart", str(video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    thumb_frame = int(script.get("thumb_t", min(2.0, dur / 2)) * FPS)
    for i in range(n):
        img = style.frame(i, i / FPS)
        if i == thumb_frame:
            img.save(out_dir / "thumbnail.jpg", quality=90)
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("ffmpeg failed")
    wav.unlink()
    write_post(script, out_dir, dur)
    print(f"{video}  ({dur:.1f}s)")


if __name__ == "__main__":
    main()
