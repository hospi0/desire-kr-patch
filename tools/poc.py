# -*- coding: utf-8 -*-
r"""글꼴·대사 PoC (2026-10-05) — 1장 스크립트 항목 41 @0x434 «【アル】夢か‥‥しかし、えらくリアルな夢だったな。» 한 줄만 한글로
  ① 한글 글리프: 나눔고딕 굵게를 64px 로 그려 16×16 으로 줄인 계조(0 투명 · 1‥15) → CHARCODE 끝쪽 드문 한자 칸에 덮어씀(코드표 그대로)
  ② FONT.CMP 다시 압축(tools/lz — 원본을 다시 압축하면 원본과 같은 크기) → 원래 103 섹터 안
  ③ 대사: 같은 길이(50 B) 안에 한글(=한자 코드)로 제자리, NOT 다시 걸어 MIX.AVI 항목 섹터만 고쳐 씀(EDC/ECC)
  python tools/poc.py [--install]  → work/out/d1/트랙 1 (+ F: 복사)"""
import os, shutil, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import font, lz, mix, disc, scn
sys.path.append(r'C:\claude\project\falcom-kr-patch\tools')
import iso

ITEM, OFF = 41, 0x434
SRC = '{E985}アル{E986}夢か‥‥しかし、えらくリアルな夢だったな。'
KO = '{E985}알{E986}꿈인가‥‥그런데　굉장히　생생한　꿈이었어．'   # 띄어쓰기 = 전각 8140(⛔반각 0x20 은 실기에서 튕김 — 3차 PoC 2026-10-05)
TTF = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
OUT = os.path.join(ROOT, 'work', 'out', 'd1')
F_DIR = r'F:\hospi\roms\ss roms\Desire (Japan) (Disc 1)'
TRACK = 'Desire (Japan) (Disc 1) (Track 1).bin'


def render(ch, S=4):
    f = ImageFont.truetype(TTF, 15 * S)
    im = Image.new('L', (16 * S, 16 * S), 0); dr = ImageDraw.Draw(im)
    l, t, r, b = dr.textbbox((0, 0), ch, font=f)
    dr.text(((16 * S - (r - l)) / 2 - l, (16 * S - (b - t)) / 2 - t - S * 0.5), ch, font=f, fill=255)
    a = np.asarray(im, np.float32).reshape(16, S, 16, S).mean((1, 3)) / 255
    return np.where(a < 0.08, 0, np.clip(np.round(a * 15), 1, 15)).astype(np.uint8)


def encode(t, kmap, cc):
    out = bytearray(); i = 0
    while i < len(t):
        if t[i] == '{':
            j = t.index('}', i); out += bytes.fromhex(t[i + 1:j]); i = j + 1; continue
        ch = t[i]; i += 1
        if '가' <= ch <= '힣':
            out += struct.pack('>H', kmap[ch])
        else:
            b = ch.encode('cp932'); assert len(b) == 1 or int.from_bytes(b, 'big') in cc, ('글꼴에 없음', ch); out += b
    return bytes(out)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    cc = font.charcode(); ccs = set(cc)
    syl = sorted(set(c for c in KO if '가' <= c <= '힣'))
    free = [c for c in cc if 0x889F <= c < 0xE980]            # 한자 칸만(⛔E980‥E986 = 見る·調べる·【】 전용 그림 글자 — PoC 1차에서 【】를 덮어 «한·히»로 나왔음)
    slots = free[-len(syl):]                                 # 끝쪽 드문 한자(PoC 한정)
    kmap = dict(zip(syl, slots))
    print('한글 %d자 → 칸 %s' % (len(syl), ' '.join('%s=%s' % (k, bytes.fromhex('%04X' % v).decode('cp932')) for k, v in kmap.items())))
    # ① 글꼴
    src = open(os.path.join(font.MISC, 'FONT.CMP'), 'rb').read()
    g = bytearray(font.decompress(src))
    for ch, code in kmap.items():
        k = cc.index(code); px = render(ch)
        g[k * 128:(k + 1) * 128] = bytes((px.reshape(-1, 2)[:, 0] << 4) | px.reshape(-1, 2)[:, 1])
    cmp_ = lz.compress(bytes(g)); assert font.decompress(cmp_) == bytes(g)
    have = (len(src) + 2047) // 2048 * 2048
    print('FONT.CMP %d → %d B (자리 %d)' % (len(src), len(cmp_), have))
    if len(cmp_) > have:
        raise SystemExit('⛔FONT.CMP 넘침')
    # ③ 대사
    its = mix.items(1); it = its[ITEM]
    raw = mix.read(1, it); d = bytearray(mix.unnot(raw))
    head, body, e = scn.record(bytes(d), OFF)
    assert scn.show(body) == SRC, scn.show(body)
    nb = encode(KO, kmap, ccs)
    if len(nb) > len(body):
        raise SystemExit('⛔대사 넘침 %d > %d' % (len(nb), len(body)))
    s0 = OFF + len(head)
    d[s0:s0 + len(body)] = nb + bytes(len(body) - len(nb))
    print('대사 %d → %d B' % (len(body), len(nb)))
    new = mix.unnot(bytes(d))
    # 트랙 만들기
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, TRACK)
    shutil.copyfile(disc.TRACK[1], dst)
    iso.patch_sub(dst, {'MISC/FONT.CMP': cmp_})
    lba = disc.listing(1)['MOVIE/MIX.AVI'][0] + it[1]         # 항목 섹터: 머리 0x20 + 데이터
    with open(dst, 'r+b') as fh:
        buf = bytearray(iso.read_user(fh, lba, it[2]))
        assert bytes(buf[0x20:0x20 + it[3]]) == raw
        buf[0x20:0x20 + it[3]] = new
        for k in range(it[2]):
            fh.seek((lba + k) * 2352); fh.write(iso.sector(lba + k, bytes(buf[k * 2048:(k + 1) * 2048])))
    import hashlib
    h = hashlib.md5(open(dst, 'rb').read()).hexdigest()
    print('트랙 1 %s' % h)
    # 미리보기
    im = np.zeros((18, 18 * len(syl)), np.uint8)
    for n, ch in enumerate(syl):
        im[1:17, n * 18 + 1:n * 18 + 17] = render(ch) * 17
    Image.fromarray(im).resize((im.shape[1] * 4, im.shape[0] * 4), Image.NEAREST).save(os.path.join(ROOT, 'work', 'poc_glyphs.png'))
    if '--install' in sys.argv:
        shutil.copyfile(dst, os.path.join(F_DIR, TRACK)); print('F: 설치')


if __name__ == '__main__':
    main()
