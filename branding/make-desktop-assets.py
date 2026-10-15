#!/usr/bin/env python3
"""Regenerate WenWen AI desktop packaging image assets from the brand logo.

Outputs (run from repo root):
  desktop/src/build/appicon.png            512x512  (Windows .ico / Linux source)
  desktop/src/build/appicon-macos.png      1024x1024 (macOS .icns source)
  desktop/src/build/darwin/dmg-background.jpeg      (DMG window background)

Design: black rounded-square app icon with the inverted mascot
(white dialogue bubble + black W + ai dot badge), matching the
black-white minimal brand. The DMG background keeps upstream's
pink-peach gradient layout with the product name swapped to WenWen AI.
Requires: Pillow, DejaVu fonts (present on CI runners).
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "desktop/src/build"
BLACK = (17, 17, 17, 255)
WHITE = (255, 255, 255, 255)
DEJAVU = "/usr/share/fonts/truetype/dejavu"


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size, size], radius=int(size * 0.225), fill=BLACK)
    # mascot geometry in wenwen-mascot.svg inner coords;
    # content bounds x[92,456] y[74,436], center (274,255)
    s = (size * 0.60) / 362.0
    tx = size / 2 - 274 * s
    ty = size / 2 - 255 * s

    def P(x, y):
        return (tx + x * s, ty + y * s)

    d.polygon([P(168, 344), P(138, 436), P(238, 344)], fill=WHITE)  # tail
    x0, y0 = P(92, 112)
    x1, y1 = P(92 + 328, 112 + 244)
    d.rounded_rectangle([x0, y0, x1, y1], radius=76 * s, fill=WHITE)  # bubble
    pts = [P(*p) for p in [(172, 192), (214, 296), (256, 212), (298, 296), (340, 192)]]
    d.line(pts, fill=BLACK, width=int(36 * s), joint="curve")  # W
    for p in (pts[0], pts[-1]):  # round caps
        r = 18 * s
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=BLACK)
    cx, cy = P(412, 118)
    r = 44 * s  # ai badge
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=WHITE,
              outline=BLACK, width=max(2, int(6 * s)))
    font = ImageFont.truetype(f"{DEJAVU}/DejaVuSans-Bold.ttf", int(40 * s))
    d.text((cx, P(412, 134)[1]), "ai", font=font, fill=BLACK, anchor="mm")
    return img


def make_dmg_background() -> None:
    W, H, BAND = 2560, 1696, 650
    # gradient stops sampled from the upstream background (row 60)
    stops = [(0, (251, 171, 184)), (640, (252, 158, 174)), (1280, (251, 132, 126)),
             (1920, (251, 191, 167)), (2559, (252, 253, 247))]
    WHITE3 = (253, 253, 253)

    def hgrad(x):
        for i in range(len(stops) - 1):
            x0, c0 = stops[i]
            x1, c1 = stops[i + 1]
            if x0 <= x <= x1:
                t = (x - x0) / (x1 - x0)
                return tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3))
        return stops[-1][1]

    img = Image.new("RGB", (W, H), WHITE3)
    px = img.load()
    for y in range(BAND):
        f = min(1.0, max(0.0, (y - 350) / 300.0))  # fade to white
        for x in range(W):
            c = hgrad(x)
            px[x, y] = tuple(int(c[k] + (WHITE3[k] - c[k]) * f) for k in range(3))
    # bottom half (white + arrow) carries no branding; keep it as a flat fill
    # plus a redrawn chevron so no upstream pixels are reused.
    d = ImageDraw.Draw(img)
    parts = [("Drag ", "regular"), ("WenWen AI", "bold"),
             (" to your Applications folder", "regular")]

    def fonts(sz):
        return {"regular": ImageFont.truetype(f"{DEJAVU}/DejaVuSans.ttf", sz),
                "bold": ImageFont.truetype(f"{DEJAVU}/DejaVuSans-Bold.ttf", sz)}

    f96 = fonts(96)
    w96 = sum(d.textlength(t, font=f96[k]) for t, k in parts)
    size = int(96 * 2312 / w96)
    f = fonts(size)
    x = 128
    for text, kind in parts:
        d.text((x, 192), text, font=f[kind], fill=(20, 20, 20), anchor="la")
        x += d.textlength(text, font=f[kind])
    # chevron (matches upstream placement, drawn fresh)
    cx, cy = W // 2 + 30, 1420
    d.line([(cx - 120, cy - 140), (cx + 40, cy), (cx - 120, cy + 140)],
           fill=(110, 110, 110), width=44, joint="curve")
    for px_, py_ in [(cx - 120, cy - 140), (cx + 40, cy), (cx - 120, cy + 140)]:
        d.ellipse([px_ - 22, py_ - 22, px_ + 22, py_ + 22], fill=(110, 110, 110))
    img.save(BUILD / "darwin/dmg-background.jpeg", quality=92)


def main() -> None:
    draw_icon(1024).save(BUILD / "appicon-macos.png")
    draw_icon(512).save(BUILD / "appicon.png")
    make_dmg_background()
    print("desktop assets regenerated")


if __name__ == "__main__":
    main()
