# -*- coding: utf-8 -*-
r"""MISC/FONT.CMP · CHARCODE (2026-10-04)
  적재 00DESIRE.BIN 0x0601218C: CHARCODE → 0x06038020(최대 0x1130 B = 2,200자, 개수 = 크기/2), FONT.CMP → 버퍼, FONT.PAL → 색 RAM 0x25F00000(32 B)
  압축 해제 0x0601358C(글자를 처음 그릴 때 한 번, 0x060122A0): FONT.CMP → VDP1 VRAM 0x25C10000(최대 0x44C00 = 2,200자 × 128 B)
    b & 0x80 → 앞 내용 복사: 거리 (b & 0x7F) + 1, 길이 다음 바이트 + 3 · 아니면 b + 1 바이트 그대로
  글리프 = 16×16 4bpp(128 B), 칸 번호 = CHARCODE 안 차례(SJIS 이진 탐색 0x06012124 → CHARCODE 는 오름차순 유지)
python tools/font.py → work/font/glyphs.png (32칸 × 줄, 칸 번호 순)"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MISC = os.path.join(ROOT, 'work', 'disc', 'd1', 'MISC')


def decompress(s):
    out = bytearray(); i = 0
    while i < len(s):
        b = s[i]
        if b & 0x80:
            dist = (b & 0x7F) + 1; n = s[i + 1] + 3; i += 2
            for _ in range(n):
                out.append(out[-dist])
        else:
            n = b + 1; out += s[i + 1:i + 1 + n]; i += 1 + n
    return bytes(out)


def charcode():
    d = open(os.path.join(MISC, 'CHARCODE'), 'rb').read()
    return [struct.unpack_from('>H', d, k)[0] for k in range(0, len(d), 2)]


def glyphs():
    g = decompress(open(os.path.join(MISC, 'FONT.CMP'), 'rb').read())
    a = np.frombuffer(g, np.uint8)
    n = len(a) // 128
    px = np.stack([a[:n * 128] >> 4, a[:n * 128] & 15], 1).reshape(n, 16, 16)
    return px


def main():
    from PIL import Image
    sys.stdout.reconfigure(encoding='utf-8')
    cc = charcode(); px = glyphs()
    print('CHARCODE %d자 · 글리프 %d개 · 정렬 %s' % (len(cc), len(px), cc == sorted(cc)))
    W = 32; H = (len(px) + W - 1) // W
    im = np.zeros((H * 17, W * 17), np.uint8)
    for k, g in enumerate(px):
        y, x = divmod(k, W); im[y * 17:y * 17 + 16, x * 17:x * 17 + 16] = g * 17
    os.makedirs(os.path.join(ROOT, 'work', 'font'), exist_ok=True)
    Image.fromarray(im).save(os.path.join(ROOT, 'work', 'font', 'glyphs.png'))
    print(''.join(bytes.fromhex('%04x' % c).decode('cp932', 'replace') for c in cc[:120]))


if __name__ == '__main__':
    main()
