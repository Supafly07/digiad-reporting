"""Measure cut-outs: colour, distance from the edges, separate objects; write review sheets."""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
names = sys.argv[1:]
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
tiles = []
for name in names:
    im = Image.open(f"public/images/{name}.png").convert("RGBA")
    a = np.asarray(im).astype(int); al = a[..., 3]; rgb = a[..., :3]; m = al > 32
    ys, xs = np.where(m); H, W = al.shape
    margin = min(xs.min(), ys.min(), W - 1 - xs.max(), H - 1 - ys.max())
    sat = (rgb.max(-1) - rgb.min(-1))[m]
    colored = (sat > 30).mean() * 100
    lab, n = ndimage.label(m)
    sizes = np.sort(np.bincount(lab.ravel())[1:])[::-1]
    big = int((sizes > sizes[0] * 0.02).sum())
    print(f"{name:18s} {W}x{H} margin={margin/min(W,H)*100:4.1f}% coloured={colored:5.2f}% objects={big} fill={m.mean()*100:4.1f}%")
    bg = Image.new("RGBA", im.size, (255, 0, 255, 255)); bg.alpha_composite(im)
    t = bg.convert("RGB"); t.thumbnail((440, 440)); canvas = Image.new("RGB", (450, 480), (60, 60, 60))
    canvas.paste(t, ((450 - t.width) // 2, 35)); ImageDraw.Draw(canvas).text((6, 4), name, fill=(255, 255, 255), font=font)
    tiles.append(canvas)
cols = 4
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (450 * cols, 480 * rows), (40, 40, 40))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * 450, (i // cols) * 480))
sheet.save("out/picture_review.jpg", quality=85)
