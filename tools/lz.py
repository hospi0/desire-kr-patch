# -*- coding: utf-8 -*-
r"""FONT.CMP LZ 압축기(2026-10-05) — 해제 0x0601358C(tools/font.decompress)와 짝
  b & 0x80 → 앞 내용 복사: 거리 (b & 0x7F) + 1 (1‥128), 길이 다음 바이트 + 3 (3‥258)
  아니면 b + 1 바이트(1‥128) 그대로
  탐욕(가장 긴 일치) — 원본 FONT.CMP 를 다시 압축해 크기를 대조한다."""


def compress(d):
    out = bytearray(); lit = bytearray(); i = 0; n = len(d)
    def flush():
        while lit:
            k = min(128, len(lit)); out.append(k - 1); out.extend(lit[:k]); del lit[:k]
    while i < n:
        best = 0; bd = 0
        for dist in range(1, min(128, i) + 1):
            j = i - dist; L = 0
            while L < 258 and i + L < n and d[j + L] == d[i + L]:
                L += 1
            if L > best:
                best, bd = L, dist
                if L == 258: break
        if best >= 3:
            flush(); out.append(0x80 | (bd - 1)); out.append(best - 3); i += best
        else:
            lit.append(d[i]); i += 1
    flush()
    return bytes(out)


if __name__ == '__main__':
    import os, sys, time
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import font
    src = open(os.path.join(font.MISC, 'FONT.CMP'), 'rb').read()
    g = font.decompress(src); t = time.time()
    c = compress(g)
    assert font.decompress(c) == g
    print('원본 %d B · 다시 압축 %d B · 풀린 %d B · %.1f초' % (len(src), len(c), len(g), time.time() - t))
