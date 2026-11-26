"""Painted source textures (PIL) for the HQ props: spirit board, sigil cloth, grimoire pages, wallpaper.
All designs are original. Images are later baked into each prop's atlas."""
import math, random, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_SERIF = "/usr/share/fonts/truetype/google-fonts/ofl/cardo/Cardo-Regular.ttf"
OUT = "/tmp/hqtex"
os.makedirs(OUT, exist_ok=True)


def _font(size):
    try:
        return ImageFont.truetype(FONT_SERIF, size)
    except Exception:
        return ImageFont.load_default()


def _noise(w, h, scale, seed=0, octaves=5):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp = 1.0
    for o in range(octaves):
        s = max(2, int(scale * 2 ** o))
        g = rng.random((s + 1, s + 1)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        out += amp * (np.asarray(im, np.float32) / 255 - 0.5)
        amp *= 0.5
    return out


def parchment(w, h, base=(214, 186, 136), seed=1, stain=0.35):
    n = _noise(w, h, 4, seed)
    n2 = _noise(w, h, 24, seed + 1, 3)
    y, x = np.mgrid[0:h, 0:w]
    vig = ((x / w - 0.5) ** 2 + (y / h - 0.5) ** 2) ** 0.5 * 1.4
    f = 1 - stain * np.clip(n * 1.6, -0.2, 1) - 0.12 * n2 - 0.35 * np.clip(vig - 0.45, 0, 1)
    img = np.clip(np.array(base, np.float32)[None, None] * f[..., None], 0, 255).astype(np.uint8)
    return Image.fromarray(img, "RGB")


def glyph(draw, cx, cy, R, w, fill):
    """The invented sigil: circle, inverted chevron, crossed bars, side flicks, three dots."""
    draw.ellipse([cx - R, cy - R, cx + R, cy + R], outline=fill, width=w)
    pts = [(cx - 0.55 * R, cy - 0.55 * R), (cx, cy + 0.75 * R), (cx + 0.55 * R, cy - 0.55 * R)]
    draw.line(pts, fill=fill, width=w, joint="curve")
    draw.line([(cx - 0.6 * R, cy - 0.1 * R), (cx + 0.6 * R, cy - 0.1 * R)], fill=fill, width=w)
    draw.line([(cx, cy - 0.9 * R), (cx, cy + 0.95 * R)], fill=fill, width=w)
    draw.line([(cx - 0.3 * R, cy - 0.6 * R), (cx + 0.3 * R, cy - 0.6 * R)], fill=fill, width=w)
    for s in (-1, 1):
        draw.line([(cx + s * 0.35 * R, cy + 0.35 * R), (cx + s * 0.75 * R, cy + 0.1 * R)], fill=fill, width=w)
    for dx in (-0.25, 0, 0.25):
        r = w * 1.3
        draw.ellipse([cx + dx * R - r, cy + 1.15 * R - r, cx + dx * R + r, cy + 1.15 * R + r], fill=fill)


def spirit_board(path=None):
    path = path or f"{OUT}/spirit_board.png"
    W, H = 2048, 1400
    im = parchment(W, H, (206, 176, 124), 3)
    im = Image.blend(im, Image.new('RGB', im.size, (206, 176, 124)), 0.35)
    d = ImageDraw.Draw(im)
    ink = (48, 28, 16)
    d.rounded_rectangle([40, 40, W - 40, H - 40], 90, outline=ink, width=10)
    d.rounded_rectangle([70, 70, W - 70, H - 70], 70, outline=ink, width=4)
    f_big, f_mid = _font(150), _font(110)

    def arc(text, cy, R, a0, a1, font):
        n = len(text)
        for i, ch in enumerate(text):
            a = a0 + (a1 - a0) * i / (n - 1)
            x = W / 2 + R * math.sin(a)
            y = cy - R * math.cos(a)
            g = Image.new("L", (240, 240), 0)
            ImageDraw.Draw(g).text((120, 120), ch, font=font, fill=255, anchor="mm")
            g = g.rotate(-math.degrees(a), resample=Image.BICUBIC)
            im.paste(Image.new("RGB", g.size, ink), (int(x - 120), int(y - 120)), g)
    arc("ABCDEFGHIJKLM", 1420, 960, -0.78, 0.78, f_big)
    arc("NOPQRSTUVWXYZ", 1420, 720, -0.98, 0.98, _font(130))
    d.text((W / 2, 1110), "1 2 3 4 5 6 7 8 9 0", font=f_mid, fill=ink, anchor="mm")
    d.text((W / 2, 1260), "GOOD  BYE", font=f_mid, fill=ink, anchor="mm")
    # sun (YES) and crescent moon (NO)
    sx, sy = 250, 230
    d.ellipse([sx - 70, sy - 70, sx + 70, sy + 70], outline=ink, width=8)
    for i in range(12):
        a = i * math.pi / 6
        d.line([(sx + 90 * math.cos(a), sy + 90 * math.sin(a)), (sx + 125 * math.cos(a), sy + 125 * math.sin(a))], fill=ink, width=7)
    d.text((sx + 260, sy), "YES", font=f_big, fill=ink, anchor="mm")
    mx, my = W - 250, 230
    cres = [(mx + 80 * math.cos(a), my + 80 * math.sin(a)) for a in np.linspace(0.6, 2 * math.pi - 0.6, 40)]
    cres += [(mx + 30 + 62 * math.cos(a), my + 62 * math.sin(a) * 1.05) for a in np.linspace(2 * math.pi - 0.95, 0.95, 40)]
    d.polygon(cres, fill=ink)
    d.text((mx - 260, my), "NO", font=f_big, fill=ink, anchor="mm")
    for i in range(22):   # little stars
        a = random.Random(i).uniform(0, 2 * math.pi)
        x = random.Random(i + 50).choice([random.Random(i + 7).uniform(160, 420), random.Random(i + 8).uniform(W - 420, W - 160)])
        y = random.Random(i + 90).uniform(420, 900)
        r = 10
        d.polygon([(x + r * math.cos(a + k * 2 * math.pi / 5 * 2), y + r * math.sin(a + k * 2 * math.pi / 5 * 2)) for k in range(5)], fill=ink)
    im = im.filter(ImageFilter.GaussianBlur(0.8))
    im.save(path)
    return path


def sigil_cloth(base=(70, 6, 10), seed=2, size=1024, name="sigil_cloth", gold=(190, 140, 50)):
    """Returns (colour, emission mask) paths: fabric with a painted sigil."""
    W = H = size
    n = _noise(W, H, 6, seed, 4)
    y, x = np.mgrid[0:H, 0:W]
    weave = 0.06 * (np.sin(x * 1.3) * np.sin(y * 1.3))
    f = 1 + 0.25 * n + weave
    col = Image.fromarray(np.clip(np.array(base)[None, None] * f[..., None], 0, 255).astype(np.uint8), "RGB")
    mask = Image.new("L", (W, H), 0)
    dm, dc = ImageDraw.Draw(mask), ImageDraw.Draw(col)
    R = W * 0.3
    glyph(dm, W / 2, H * 0.42, R, int(W * 0.022), 255)
    glyph(dc, W / 2, H * 0.42, R, int(W * 0.022), gold)
    dc.rectangle([W * 0.06, H * 0.03, W * 0.94, H * 0.97], outline=gold, width=int(W * 0.012))
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    cp, mp = f"{OUT}/{name}.png", f"{OUT}/{name}_emit.png"
    col.filter(ImageFilter.GaussianBlur(0.6)).save(cp); mask.save(mp)
    return cp, mp


def grimoire_pages(path=None, seed=5):
    path = path or f"{OUT}/grimoire.png"
    W, H = 2048, 1400
    im = parchment(W, H, (222, 200, 160), seed, 0.25)
    d = ImageDraw.Draw(im)
    ink = (40, 22, 14)
    rnd = random.Random(seed)
    for page, x0 in ((0, 120), (1, W // 2 + 80)):
        if page == 0:
            glyph(d, x0 + 400, 420, 250, 10, (120, 10, 10))
            y = 760
        else:
            y = 140
        while y < H - 140:
            x = x0
            while x < x0 + 820:
                L = rnd.randint(30, 110)
                for k in range(L // 12):   # pseudo-script strokes
                    cx = x + k * 12
                    d.line([(cx, y + rnd.randint(-6, 6)), (cx + 8, y + rnd.randint(-12, 12))], fill=ink, width=3)
                x += L + 24
            y += 48
    d.line([(W // 2, 0), (W // 2, H)], fill=(120, 95, 60), width=12)
    im = im.filter(ImageFilter.GaussianBlur(0.7))
    im.save(path)
    return path


def wallpaper(path=None, base=(96, 70, 62), fg=(140, 110, 86), seed=7):
    path = path or f"{OUT}/wallpaper.png"
    W = H = 512
    im = Image.new("RGB", (W, H), base)
    d = ImageDraw.Draw(im)
    for j in range(0, H, 64):
        for i in range(0, W, 64):
            ox = 32 if (j // 64) % 2 else 0
            cx, cy = i + ox, j + 32
            d.ellipse([cx - 10, cy - 18, cx + 10, cy + 18], outline=fg, width=3)
            d.line([(cx, cy - 26), (cx, cy + 26)], fill=fg, width=2)
    for i in range(0, W, 128):
        d.line([(i, 0), (i, H)], fill=tuple(int(c * 0.85) for c in base), width=4)
    im.save(path)
    return path


def engraving(lines, name, W=1024, H=1400, top=0.18, ornament=True):
    """White-on-black mask of carved lettering: lines = [(text, size_px), ...] stacked from `top`."""
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    y = H * top
    for text, size in lines:
        f = _font(size)
        for row in text.split("\n"):
            d.text((W / 2, y), row, font=f, fill=255, anchor="mm")
            y += size * 1.15
        y += size * 0.25
    if ornament:
        cx = W / 2
        d.line([(cx - 220, y + 10), (cx + 220, y + 10)], fill=255, width=6)
        d.ellipse([cx - 16, y - 6, cx + 16, y + 26], outline=255, width=5)
    im = im.filter(ImageFilter.GaussianBlur(3))
    p = f"{OUT}/{name}.png"
    im.save(p)
    return p


def wing_pattern(name="moth_wing", W=1024, seed=4):
    """Moth wing paint: dusky gradient, wavy bands, two eyespots. Returns (colour, emission mask)."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:W, 0:W] / W
    n = _noise(W, W, 5, seed, 5)
    band = np.sin((x * 1.0 + y * 0.6) * 22 + n * 6) * 0.5 + 0.5
    base = np.stack([0.34 + 0.12 * band + 0.15 * n, 0.26 + 0.09 * band + 0.1 * n, 0.19 + 0.06 * band + 0.08 * n], -1)
    vein = np.abs(np.sin(np.arctan2(y - 0.02, x - 0.02) * 14)) < 0.06
    base[vein] *= 0.55
    em = np.zeros((W, W), np.float32)
    for cx, cy, r in ((0.58, 0.32, 0.13), (0.4, 0.74, 0.09)):
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
        ring = (d < 1.0)
        base[ring] = np.array([0.75, 0.62, 0.3])
        base[d < 0.72] = np.array([0.05, 0.03, 0.03])
        base[d < 0.42] = np.array([0.7, 0.05, 0.03])
        em[d < 0.42] = 1.0
        base[d < 0.12] = np.array([0.95, 0.9, 0.8])
    col = Image.fromarray(np.clip(base * 255, 0, 255).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(1.2))
    emi = Image.fromarray((em * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2))
    cp, ep = f"{OUT}/{name}.png", f"{OUT}/{name}_emit.png"
    col.save(cp); emi.save(ep)
    return cp, ep
