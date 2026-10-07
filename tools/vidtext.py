# -*- coding: utf-8 -*-
r"""tVid 그림 글자 한글화 (2026-10-07) — tools/tvid.py 로 풀고 다시 쌓음
  글자 자리(R)마다: 그 프레임 원래 글자 색(자리 안 가장 밝은 색) × 한글 알파 → 가장 가까운 팔레트 번호. 자리 밖은 원래 그대로.
  python tools/vidtext.py [--preview]  → work/vid/kr/<이름>.VID (+ 미리보기 PNG)"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, tvid
TTF = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
OUT = os.path.join(ROOT, 'work', 'vid', 'kr')

# 이름: [(자리 x0,y0,x1,y1, [(글자, 가운데 x, 가운데 y, 칸 크기)])]
JOBS = {
    'TITLE': [((98, 97, 222, 115), [('디', 110, 105.5, 14), ('자', 144, 105.5, 14), ('이', 175, 105.5, 14), ('어', 209, 105.5, 14)])],
}


def glyph_alpha(ch, size, S=8):
    """한 글자를 size×size 칸에 꽉 차게(굵게) — 알파 0‥1"""
    f = ImageFont.truetype(TTF, int(size * S * 1.05))
    im = Image.new('L', (size * S * 2, size * S * 2), 0); dr = ImageDraw.Draw(im)
    l, t, r, b = dr.textbbox((0, 0), ch, font=f)
    dr.text((size * S - (l + r) / 2, size * S - (t + b) / 2), ch, font=f, fill=255)
    a = np.asarray(im, np.float32) / 255
    return a.reshape(size * 2, S, size * 2, S).mean((1, 3))           # 가운데 기준 2배 칸


def mask(shape, items):
    h, w = shape; m = np.zeros((h, w), np.float32)
    for ch, cx, cy, size in items:
        a = glyph_alpha(ch, size); s = a.shape[0]
        x0 = int(round(cx - s / 2)); y0 = int(round(cy - s / 2))
        for yy in range(s):
            for xx in range(s):
                X, Y = x0 + xx, y0 + yy
                if 0 <= X < w and 0 <= Y < h:
                    m[Y, X] = max(m[Y, X], a[yy, xx])
    return m


def nearest(pal, rgb):
    """rgb (…,3) → 팔레트 번호(…)"""
    p = pal.astype(np.int32); q = rgb.reshape(-1, 3).astype(np.int32)
    d = ((q[:, None, :] - p[None, :, :]) ** 2).sum(-1)
    return d.argmin(1).reshape(rgb.shape[:-1])


def build(name):
    d = disc.read(1, 'SOUND/%s.VID' % name)
    w, h, pal, fs = tvid.frames(d)
    tg = [f.copy() for f in fs]
    for (x0, y0, x1, y1), items in JOBS[name]:
        m = mask((h, w), items)[y0:y1, x0:x1]
        for k, f in enumerate(fs):
            sub = pal[np.clip(f[y0:y1, x0:x1], 0, 239)].astype(np.float32)
            lum = sub.sum(-1)
            if lum.max() < 8:
                continue                                        # 아직 안 나온 프레임
            fg = sub.reshape(-1, 3)[lum.argmax()]               # 그 프레임 글자 색
            bg = np.zeros(3, np.float32)                        # 바탕 = 검정
            rgb = m[..., None] * fg + (1 - m[..., None]) * bg
            tg[k][y0:y1, x0:x1] = nearest(pal, rgb)
    nd = tvid.rebuild(d, tg)
    w2, h2, pal2, fs2 = tvid.frames(nd)
    assert all((a == b).all() for a, b in zip(tg, fs2)), '되풀기 불일치'
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, name + '.VID'), 'wb').write(nd)
    return d, nd, pal, fs2


# ── 오프닝 스태프(OPST1‥4): 직함(작은 글씨, 나타남) + 이름(굵게, 밑줄 아래에서 솟아오름) ─────────
STAFF = {   # 이름: (직함, 이름)  ★이름 읽기는 추정(사용자 «스태프 이름은 한글로»)
    'OPST1': ('디렉터 / CG 감독', '와타나베 고'),
    'OPST2': ('캐릭터 디자인 / 작화 감독', '타지마 나오'),
    'OPST3': ('CG 디자인', '타카오카 요시후미'),
    'OPST4': ('애니메이션 콘티 / 연출', '노구치 마사츠네'),
}
GOTHIC = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
ROLE_BOX = (60, 52, 262, 68)        # 직함 줄 y 55‥65
NAME_BOX = (60, 68, 262, 99)        # 이름 줄 y 70‥96 · 밑줄 y 99(안 건드림)


def line_alpha(text, w, h, px, maxw, font):
    """w×h 칸 가운데에 text 를 그린 알파(높이 px, 너비 maxw 넘으면 줄임)"""
    f = ImageFont.truetype(font, int(px * 8 * 1.1))
    im = Image.new('L', (w * 8, h * 8), 0); dr = ImageDraw.Draw(im)
    l, t, r, b = dr.textbbox((0, 0), text, font=f)
    sc = min(1.0, maxw * 8 / (r - l))
    if sc < 1:
        f = ImageFont.truetype(font, int(px * 8 * 1.1 * sc)); l, t, r, b = dr.textbbox((0, 0), text, font=f)
    dr.text((w * 4 - (l + r) / 2, h * 4 - (t + b) / 2), text, font=f, fill=255)
    return np.asarray(im, np.float32).reshape(h, 8, w, 8).mean((1, 3)) / 255


def build_staff(name):
    d = disc.read(1, 'SOUND/%s.VID' % name)
    w, h, pal, fs = tvid.frames(d)
    role, person = STAFF[name]
    tg = [f.copy() for f in fs]
    x0, y0, x1, y1 = ROLE_BOX
    ra = line_alpha(role, x1 - x0, y1 - y0, 11, 196, GOTHIC)
    nx0, ny0, nx1, ny1 = NAME_BOX
    na_full = line_alpha(person, nx1 - nx0, 27, 25, 182, TTF)        # 27 줄 높이(원본 이름 y 70‥96)
    final_top = 70
    for k, f in enumerate(fs):
        rgb = pal[np.clip(f, 0, 239)].astype(np.float32)
        sub = rgb[y0:y1, x0:x1]; lum = sub.sum(-1)                    # 직함: 그 프레임 글자 색으로
        if lum.max() >= 8:
            fg = sub.reshape(-1, 3)[lum.argmax()]
            tg[k][y0:y1, x0:x1] = nearest(pal, ra[..., None] * fg)
        sub = rgb[ny0:ny1, nx0:nx1]; ink = sub[..., 1] > 60             # 이름: 원본 글자 맨 위 높이만큼 내려서, 밑줄 위만
        a = np.zeros((ny1 - ny0, nx1 - nx0), np.float32); fg = np.zeros(3, np.float32)
        if ink.any():
            top = ny0 + np.where(ink.any(1))[0][0]; off = top - final_top
            fg = sub.reshape(-1, 3)[sub.sum(-1).argmax()]
            for yy in range(27):
                Y = final_top + yy + off - ny0
                if 0 <= Y < ny1 - ny0:
                    a[Y] = na_full[yy]
        tg[k][ny0:ny1, nx0:nx1] = nearest(pal, a[..., None] * fg)
    nd = tvid.rebuild(d, tg)
    fs2 = tvid.frames(nd)[3]
    assert all((a == b).all() for a, b in zip(tg, fs2)), '되풀기 불일치'
    os.makedirs(OUT, exist_ok=True); open(os.path.join(OUT, name + '.VID'), 'wb').write(nd)
    return d, nd, pal, fs2


if __name__ == '__main__':
    for name in list(JOBS) + list(STAFF):
        d, nd, pal, fs = (build if name in JOBS else build_staff)(name)
        print(name, '원본 %d → %d B (섹터 %d → %d)' % (len(d), len(nd), (len(d) + 2047) // 2048, (len(nd) + 2047) // 2048))
        if '--preview' in sys.argv:
            ims = [Image.fromarray(pal[np.clip(fs[k], 0, 239)]) for k in (len(fs) // 3, len(fs) // 2, len(fs) - 1)]
            s = Image.new('RGB', (320 * 3, ims[0].height))
            for i, im in enumerate(ims): s.paste(im, (i * 320, 0))
            s.resize((s.width * 2, s.height * 2), Image.NEAREST).save(os.path.join(OUT, name + '_preview.png'))
