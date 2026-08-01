# -*- coding: utf-8 -*-
"""v3 조립 — 내용에 최적화된 4가지 구도
   L: 좌텍스트/우씬   |   W: 상단텍스트/하단 와이드씬
   C: 중앙정렬 대형    |   S: 좌씬/우텍스트 (반전)
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
SCN = os.path.join(BASE, "scenes3")
OUT = os.path.join(BASE, "v3_out")
os.makedirs(OUT, exist_ok=True)

W, H = 2560, 1440
M = int(W * 0.030)

BLUE = (43, 110, 242)
INK = (22, 29, 43)
GREY = (122, 132, 148)
LINE = (228, 231, 236)
WHITE = (255, 255, 255)

FB = r"C:\Windows\Fonts\malgunbd.ttf"
FR = r"C:\Windows\Fonts\malgun.ttf"
FE = r"C:\Windows\Fonts\arialbd.ttf"

FOOT = "작성자 — 경영지도사 · 풀스택 개발"


def f(sz, p=FB):
    return ImageFont.truetype(p, sz)


def trim(im, thr=248):
    a = np.array(im.convert("L"))
    ys, xs = np.nonzero(a < thr)
    if not len(xs):
        return im
    p = 8
    return im.crop((max(0, xs.min() - p), max(0, ys.min() - p),
                    min(im.width, xs.max() + p), min(im.height, ys.max() + p)))


def scene(name):
    p = os.path.join(SCN, "%s.png" % name)
    return trim(Image.open(p).convert("RGB")) if os.path.exists(p) else None


def chrome(im, d, eyebrow, num, total):
    ey = int(H * 0.062)
    d.rounded_rectangle((M, ey + 12, M + 62, ey + 20), radius=4, fill=BLUE)
    d.text((M + 86, ey), eyebrow, font=f(30, FE), fill=BLUE)
    fn = f(38, FR)
    d.text((W - M - d.textlength(num, font=fn), ey - 4), num, font=fn, fill=(178, 186, 198))
    by = int(H * 0.889)
    d.line([(M, by), (W - M, by)], fill=LINE, width=2)
    ff = f(28, FR)
    d.text((M, by + 30), FOOT, font=ff, fill=GREY)
    pg = "%s / %02d" % (num, total)
    d.text((W - M - d.textlength(pg, font=ff), by + 30), pg, font=ff, fill=GREY)


def typo(d, x, y, head, sub, hsz=112, align="left", maxw=None):
    fh = f(hsz)
    for ln in head:
        tx = x if align == "left" else x - d.textlength(ln, font=fh) / 2
        d.text((tx, y), ln, font=fh, fill=INK)
        y += int(fh.size * 1.22)
    y += 34
    fs = f(38, FR)
    for ln in sub:
        tx = x if align == "left" else x - d.textlength(ln, font=fs) / 2
        d.text((tx, y), ln, font=fs, fill=GREY)
        y += int(fs.size * 1.52)
    return y


# ══════════ 구도별 빌더 ══════════
def lay_L(im, d, s):
    """좌 텍스트 / 우 씬 — 개념 설명용"""
    sc = scene(s["scene"])
    if sc:
        bw, bh = int(W * 0.42), int(H * 0.60)
        r = min(bw / sc.width, bh / sc.height)
        sc = sc.resize((int(sc.width * r), int(sc.height * r)), Image.LANCZOS)
        im.paste(sc, (W - M - int(W * 0.02) - sc.width,
                      int(H * 0.20) + (bh - sc.height) // 2))
    typo(d, M, int(H * 0.245), s["head"], s["sub"])


def lay_S(im, d, s):
    """좌 씬 / 우 텍스트 — 리듬 전환용(반전)"""
    sc = scene(s["scene"])
    if sc:
        bw, bh = int(W * 0.40), int(H * 0.60)
        r = min(bw / sc.width, bh / sc.height)
        sc = sc.resize((int(sc.width * r), int(sc.height * r)), Image.LANCZOS)
        im.paste(sc, (M + int(W * 0.02), int(H * 0.20) + (bh - sc.height) // 2))
    typo(d, int(W * 0.52), int(H * 0.245), s["head"], s["sub"])


def lay_W(im, d, s):
    """상단 텍스트 / 하단 와이드 씬 — 프로세스 플로우용"""
    y = typo(d, M, int(H * 0.16), s["head"], s["sub"], hsz=96)
    sc = scene(s["scene"])
    if sc:
        bw = W - M * 2 - int(W * 0.04)
        bh = int(H * 0.40)
        r = min(bw / sc.width, bh / sc.height)
        sc = sc.resize((int(sc.width * r), int(sc.height * r)), Image.LANCZOS)
        im.paste(sc, ((W - sc.width) // 2, int(H * 0.47) + (bh - sc.height) // 2))


def lay_C(im, d, s):
    """중앙 정렬 — 비교/교집합 등 대칭 구도용"""
    fh = f(96)
    y = int(H * 0.155)
    for ln in s["head"]:
        d.text(((W - d.textlength(ln, font=fh)) / 2, y), ln, font=fh, fill=INK)
        y += int(fh.size * 1.2)
    y += 20
    fs = f(36, FR)
    for ln in s["sub"]:
        d.text(((W - d.textlength(ln, font=fs)) / 2, y), ln, font=fs, fill=GREY)
        y += int(fs.size * 1.5)
    sc = scene(s["scene"])
    if sc:
        bh = int(H * 0.44)
        bw = int(W * 0.52)
        r = min(bw / sc.width, bh / sc.height)
        sc = sc.resize((int(sc.width * r), int(sc.height * r)), Image.LANCZOS)
        im.paste(sc, ((W - sc.width) // 2, int(H * 0.42) + (bh - sc.height) // 2))


LAY = {"L": lay_L, "S": lay_S, "W": lay_W, "C": lay_C}

SLIDES = [
    {"lay": "L", "eyebrow": "THE PROBLEM", "scene": "s1_gap",
     "head": ["경영과 기술은", "만나지 않습니다"],
     "sub": ["컨설턴트는 기술을 모르고", "개발자는 경영을 모른다"]},

    {"lay": "W", "eyebrow": "THE SOLUTION", "scene": "s2_flow",
     "head": ["진단부터 실행까지 한 사람이"],
     "sub": ["경영 관점과 기술 관점을 결합한 실행형 컨설팅"]},

    {"lay": "S", "eyebrow": "TRACK RECORD", "scene": "s3_stack",
     "head": ["매일 만들고", "공공이 검증했습니다"],
     "sub": ["연 2,800회 커밋 · 저장소 90개", "공공기관 10곳 이상 위촉"]},

    {"lay": "C", "eyebrow": "DIFFERENTIATION", "scene": "s4_venn",
     "head": ["둘 다 하는 사람은 드뭅니다"],
     "sub": ["진단만 하거나, 개발만 하거나"]},

    {"lay": "L", "eyebrow": "PROOF", "scene": "s5_saas",
     "head": ["직접 만든 제품이", "증거입니다"],
     "sub": ["AI SaaS 딸깍 · 1인 개발 운영", "공공기관 계약 체결"]},
]

if __name__ == "__main__":
    n = len(SLIDES)
    for i, s in enumerate(SLIDES):
        im = Image.new("RGB", (W, H), WHITE)
        d = ImageDraw.Draw(im)
        LAY[s["lay"]](im, d, s)
        chrome(im, d, s["eyebrow"], "%02d" % (i + 1), n)
        im.save(os.path.join(OUT, "slide_%02d.png" % (i + 1)))
        print("  %02d [%s] %s" % (i + 1, s["lay"], s["head"][0]))

    import fitz
    doc = fitz.open()
    for i in range(n):
        pg = doc.new_page(width=1280, height=720)
        pg.insert_image(pg.rect, filename=os.path.join(OUT, "slide_%02d.png" % (i + 1)))
    p = os.path.join(BASE, "작성자_컨설팅소개_v3.pdf")
    doc.save(p, deflate=True)
    print("→", p, "%.1f MB" % (os.path.getsize(p) / 1024 / 1024))
