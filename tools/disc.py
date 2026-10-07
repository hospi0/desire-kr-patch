# -*- coding: utf-8 -*-
r"""Desire (새턴 JP 2장) 디스크 읽기 (2026-10-04)
  python tools/disc.py list [1|2]         → 파일 목록(LBA 순)
  python tools/disc.py dump [1|2]         → work/disc/d<N>/ 에 전부 꺼내기
  from disc import read; read(1, 'FILE.BIN')
트랙 1 = MODE1/2352. ISO 디렉터리(하위 폴더 포함)를 그대로 읽는다(falcom iso.tree 재사용).
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.append(r'C:\claude\project\falcom-kr-patch\tools')
import iso

TRACK = {1: r'C:\claude\roms\ss\Desire (Japan) (Disc 1)\Desire (Japan) (Disc 1) (Track 1).bin',
         2: r'C:\claude\roms\ss\Desire (Japan) (Disc 2) (2M)\Desire (Japan) (Disc 2) (2M) (Track 1).bin'}
MD5 = {1: '5b7a90e8931a61733e970b578ad51e6d', 2: '061b3d54d7e326f17230ca7d9ebc2df3'}


def listing(d):
    with open(TRACK[d], 'rb') as fh:
        return iso.tree(fh)


def read(d, name):
    lba, size = listing(d)[name][:2]
    with open(TRACK[d], 'rb') as fh:
        return iso.read_user(fh, lba, (size + 2047) // 2048)[:size]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    cmd, d = sys.argv[1], int(sys.argv[2])
    t = listing(d)
    if cmd == 'list':
        for n, (lba, size, _, _) in sorted(t.items(), key=lambda x: x[1][0]):
            print('%8d %10d  %s' % (lba, size, n))
        print('파일 %d개 · 합계 %d B' % (len(t), sum(v[1] for v in t.values())))
    elif cmd == 'dump':
        out = os.path.join(ROOT, 'work', 'disc', 'd%d' % d)
        with open(TRACK[d], 'rb') as fh:
            for n, (lba, size, _, _) in t.items():
                p = os.path.join(out, n); os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, 'wb').write(iso.read_user(fh, lba, (size + 2047) // 2048)[:size])
        print(out)


if __name__ == '__main__':
    main()
