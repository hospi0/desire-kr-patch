# -*- coding: utf-8 -*-
r"""MIX.AVI «arc3» 묶음 목차 (2026-10-04, 가설 — 실행 파일 0x0600F658 읽기 함수 기준)
  머리 0x2C B: [arc3][판][블록 0x800][?][전체 섹터][?][목차 블록][목차 바이트][?][?][?]
  목차 항목: 제어 c
    0xF1‥0xFE     → 새 이름 (c&15)자 통째 + 값 6B(u24,u24)  (무리 시작)
    0xF0 · 0xFF   → 앞 이름 그대로 + 값 3B
    그 밖          → 앞 이름 앞 (c>>4)자 + 새 (c&15)자 + 값 3B
  python tools/arc3.py [1|2]
"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, iso


def header(d):
    lba = disc.listing(d)['MOVIE/MIX.AVI'][0]
    with open(disc.TRACK[d], 'rb') as fh:
        h = iso.read_user(fh, lba, 1)
    assert h[:4] == b'arc3', h[:4]
    f = struct.unpack_from('>10I', h, 4)
    return lba, f


def index(d):
    lba, f = header(d)
    blk, ixb, ixn = f[1] // 0x800, f[5], f[6]
    with open(disc.TRACK[d], 'rb') as fh:
        ix = iso.read_user(fh, lba + ixb, (ixn + 2047) // 2048)[:ixn]
    i = 0; prev = ''; out = []
    while i < len(ix):
        c = ix[i]; i += 1
        if 0xF1 <= c <= 0xFE:
            name = ix[i:i + (c & 15)].decode('latin1'); i += c & 15
            v = (int.from_bytes(ix[i:i + 3], 'big'), int.from_bytes(ix[i + 3:i + 6], 'big')); i += 6
        elif c >= 0xF0:
            name = prev; v = (int.from_bytes(ix[i:i + 3], 'big'),); i += 3
        else:
            name = prev[:c >> 4] + ix[i:i + (c & 15)].decode('latin1'); i += c & 15
            v = (int.from_bytes(ix[i:i + 3], 'big'),); i += 3
        if not name or not all(32 <= ord(ch) < 127 for ch in name):
            raise SystemExit('목차 해석 실패 0x%X 제어 0x%02X %r' % (i, c, name))
        out.append((name, c, v)); prev = name
    return out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    d = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    lba, f = header(d); print('머리', [hex(x) for x in f])
    ix = index(d)
    print('항목', len(ix), '무리', sum(1 for x in ix if 0xF1 <= x[1] <= 0xFE), '이름', len({x[0] for x in ix}))
    for n, c, v in ix[:20]: print(repr(n), hex(c), [hex(x) for x in v])
