"""Livestream UI overlay (LIVE badge, viewer count, made-up scrolling chat, big caption) drawn over a rendered frame.
usage: overlay.py IN.png OUT.png [caption]"""
import sys
from PIL import Image, ImageDraw, ImageFont
F = lambda w, s: ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", s)
CHAT = [("pixel_pete", (120, 200, 255), "dex hollow live?? lets gooo"), ("mia.moon", (255, 150, 200), "he said ANYTHING lol"), ("bigmaple44", (255, 210, 90), "wait what is behind him"),
        ("tourbus_tina", (150, 255, 190), "IS THAT HIS VAN"), ("noodle_nate", (255, 170, 110), "DEX BEHIND U")]
def pill(d, box, fill, r=None):
    d.rounded_rectangle(box, radius=r or (box[3] - box[1]) // 2, fill=fill)
def draw(im, caption=None, n_chat=5, fade=True):
    W, H = im.size; ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    # LIVE badge + viewer count (top-left, under the status bar)
    x, y = 36, 150; pill(d, (x, y, x + 150, y + 62), (230, 30, 60, 255)); d.ellipse((x + 18, y + 22, x + 36, y + 40), fill=(255, 255, 255, 255)); d.text((x + 48, y + 8), "LIVE", font=F("ExtraBold", 38), fill=(255, 255, 255, 255))
    pill(d, (x + 164, y, x + 164 + 210, y + 62), (20, 16, 30, 190)); ex, ey = x + 190, y + 31
    d.ellipse((ex - 16, ey - 9, ex + 16, ey + 9), outline=(255, 255, 255, 255), width=3); d.ellipse((ex - 5, ey - 5, ex + 5, ey + 5), fill=(255, 255, 255, 255))
    d.text((x + 222, y + 11), "12,481", font=F("Bold", 36), fill=(255, 255, 255, 255))
    # chat (newest at the bottom; older ones fade out as they scroll up)
    cy = 260; rows = CHAT[-n_chat:]; fn, fm = F("Bold", 30), F("Medium", 30)
    for i, (u, col, m) in enumerate(rows):
        a = 255 if not fade else int(120 + 135 * (i + 1) / len(rows)); tw = d.textlength(u + "  ", font=fn) + d.textlength(m, font=fm); w = int(tw + 100)
        pill(d, (36, cy, 36 + w, cy + 66), (16, 12, 26, int(a * 0.72))); d.ellipse((48, cy + 11, 92, cy + 55), fill=col + (a,)); d.text((60, cy + 14), u[0].upper(), font=F("ExtraBold", 28), fill=(20, 16, 30, a))
        d.text((106, cy + 15), u + "  ", font=fn, fill=col + (a,)); d.text((106 + d.textlength(u + "  ", font=fn), cy + 15), m, font=fm, fill=(255, 255, 255, a)); cy += 80
    if caption:
        font = F("ExtraBold", 150); tw = d.textlength(caption, font=font); x0 = (W - tw) / 2; y0 = 1180
        d.text((x0, y0), caption, font=font, fill=(255, 63, 176, 255), stroke_width=18, stroke_fill=(26, 13, 51, 255))
    return Image.alpha_composite(im.convert("RGBA"), ov)
if __name__ == "__main__":
    im = Image.open(sys.argv[1]); draw(im, sys.argv[3] if len(sys.argv) > 3 else None).convert("RGB").save(sys.argv[2])
