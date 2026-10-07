# -*- coding: utf-8 -*-
r"""MIX.AVI(arc3) 항목 사슬 (2026-10-04)
  항목 = 섹터 경계에서 시작, 머리 0x20 B [섹터 수][크기][크기][시각][시각][0×3] + 데이터. 0x14 섹터부터 빈틈없이 이어짐(8,252 = 목차 항목 수).
  시나리오 스크립트 = 데이터 u16 마다 NOT(실행 파일 0x06004AC0) → 명령 바이트 + Shift-JIS 문장.
  python tools/mix.py scan [1|2]  → work/mix_d<N>_items.tsv (번호·섹터·크기·종류·일본어 글자 수)
"""
import os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc

SJ = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc])+')


def items(d):
    """[(번호, 섹터, 섹터 수, 크기, 데이터)] — 데이터는 머리 뺀 원본 바이트"""
    lba, size = disc.listing(d)['MOVIE/MIX.AVI'][:2]
    N = (size + 2047) // 2048; out = []
    with open(disc.TRACK[d], 'rb') as fh:
        def rd(s, n):
            fh.seek((lba + s) * 2352); raw = fh.read(n * 2352)
            return b''.join(raw[k * 2352 + 16:k * 2352 + 2064] for k in range(n))
        s = struct.unpack_from('>I', rd(0, 1), 4 + 4 * 6)[0] if False else None
        h0 = rd(0, 1); ixb, ixn = struct.unpack_from('>II', h0, 0x18)
        s = ixb + (ixn + 2047) // 2048
        while s < N:
            h = rd(s, 1); cnt, sz, sz2 = struct.unpack_from('>III', h, 0)
            assert 0 < cnt and sz <= sz2 and sz2 <= cnt * 2048, ('사슬 깨짐', s, cnt, sz, sz2)
            out.append((len(out), s, cnt, sz, sz2))
            s += cnt
        assert s == N, (s, N)
    return out


def read(d, it):
    lba = disc.listing(d)['MOVIE/MIX.AVI'][0]
    with open(disc.TRACK[d], 'rb') as fh:
        fh.seek((lba + it[1]) * 2352); raw = fh.read(it[2] * 2352)
    b = b''.join(raw[k * 2352 + 16:k * 2352 + 2064] for k in range(it[2]))
    return b[0x20:0x20 + it[3]]


def unnot(b):
    return bytes(x ^ 0xFF for x in b)


def jp_count(b):
    n = 0
    for m in SJ.finditer(b):
        try: n += len(m.group().decode('cp932'))
        except UnicodeDecodeError: pass
    return n


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    its = items(d); rows = []
    for it in its:
        b = read(d, it); t = unnot(b)
        a, z = jp_count(b), jp_count(t)
        kind = 'scn' if z > 200 and z * 2 > len(b) * 0.15 else ('raw_sjis' if a > 200 and a * 2 > len(b) * 0.3 else '')
        rows.append((it[0], it[1], it[3], it[4], b[:4].hex(), kind, z if kind == 'scn' else a))
    p = os.path.join(ROOT, 'work', 'mix_d%d_items.tsv' % d)
    open(p, 'w', encoding='utf-8').write('번호\t섹터\t크기\t크기2\t앞4\t종류\t일본어\n' + '\n'.join('\t'.join(str(x) if not isinstance(x, int) or i in (0, 6) else hex(x) for i, x in enumerate(r)) for r in rows))
    sc = [r for r in rows if r[5] == 'scn']
    print('항목', len(rows), '· 스크립트', len(sc), '· 일본어 글자', sum(r[6] for r in sc), '· 그밖 SJIS', sum(1 for r in rows if r[5] == 'raw_sjis'))
