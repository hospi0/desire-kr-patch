# -*- coding: utf-8 -*-
r"""MIX.AVI «b1» 그림 (2026-10-07)
  머리 6 B: 'b1' · u16 너비 · u16 높이 / 그다음 u16 낱말이 이어짐(빅엔디언):
    v & 0x8000 → RGB555 픽셀 하나(0x8000 = 검정) · 아니면 개수 = v >> 8(1‥127), 위치 = v & 0xFF
    (윗 4비트 dx · 아랫 4비트 dy, 부호 4비트) — 이미 그린 픽셀(k + dx + dy·너비)을 개수만큼 복사.
  python tools/b1.py <항목번호> → work/b1/<번호>.png"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)


def _sn(v):
    return v - 16 if v >= 8 else v


def decode(d):
    w, h = struct.unpack_from('>HH', d, 2)
    out = np.zeros(w * h, np.uint16); k = 0; i = 6
    while k < w * h:
        v = (d[i] << 8) | d[i + 1]; i += 2
        if v & 0x8000:
            out[k] = v; k += 1
        else:
            n = v >> 8; dx, dy = _sn((v >> 4) & 15), _sn(v & 15); off = dx + dy * w
            for _ in range(n):
                out[k] = out[k + off]; k += 1
    return w, h, out.reshape(h, w)


# 복사 위치 후보(앞서 그려진 칸만, 원본 58장이 쓰는 값만): dy −7‥−1 이면 dx −7‥7, dy = 0 이면 dx −7‥−1
OFFS = [(dx, dy) for dy in range(-7, 1) for dx in range(-7, 8) if dy < 0 or dx < 0]   # ⛔−8(니블 8)은 원본이 안 씀 — 실기에서 깨짐(2026-10-07)


def encode(img):
    """img(h×w uint16, 모든 값 bit15 = 1) → b1 바이트. 욕심쟁이: 가장 긴 복사(2‥127), 아니면 픽셀"""
    h, w = img.shape; p = img.reshape(-1).astype(np.uint16)
    assert (p & 0x8000).all(), 'b1 픽셀은 bit15 가 서야 함'
    out = bytearray(b'b1' + struct.pack('>HHH', w, h, 0)); k = 0; N = w * h   # 원본 58장 모두 머리 뒤 0x0000
    while k < N:
        best = (1, None); lim = min(127, w - k % w)   # ⛔복사가 줄 끝을 넘으면 실기에서 깨짐(원본 넘김 0회, 2026-10-07)
        for dx, dy in OFFS:
            off = dx + dy * w; s = k + off
            if s < 0:
                continue
            n = 0
            while n < lim and p[s + n] == p[k + n]:
                n += 1
            if n > best[0]:
                best = (n, (dx, dy))
                if n == lim:
                    break
        n, o = best
        if o is None or n < 2:
            out += struct.pack('>H', int(p[k])); k += 1
        else:
            dx, dy = o
            out += bytes([n, ((dx & 15) << 4) | (dy & 15)]); k += n
    return bytes(out)


def to_rgb(img):
    a = img.astype(np.int32)
    return np.stack([(a & 31) << 3, ((a >> 5) & 31) << 3, ((a >> 10) & 31) << 3], -1).astype(np.uint8)


def from_rgb(rgb):
    r, g, b = [(rgb[..., i].astype(np.int32) + 4) // 8 for i in range(3)]
    r, g, b = [np.clip(x, 0, 31) for x in (r, g, b)]
    return (0x8000 | r | (g << 5) | (b << 10)).astype(np.uint16)


if __name__ == '__main__':
    sys.path.insert(0, HERE); import mix
    from PIL import Image
    its = {it[0]: it for it in mix.items(1)}
    n = int(sys.argv[1]); w, h, im = decode(mix.read(1, its[n]))
    os.makedirs(os.path.join(ROOT, 'work', 'b1'), exist_ok=True)
    Image.fromarray(to_rgb(im)).save(os.path.join(ROOT, 'work', 'b1', '%04d.png' % n)); print(n, w, h)
