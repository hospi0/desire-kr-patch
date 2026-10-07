# -*- coding: utf-8 -*-
r"""MIX.AVI 항목 옮기기(2026-10-05) — 커진 스크립트 항목을 MIX.AVI 끝에 붙이고 arc3 목차 값만 고친다
  목차(arc3, MIX.AVI 블록 f[5] 부터 f[6] B): 항목 = [제어][이름 조각][u24 값(무리 첫 항목은 u24 두 개)]
    u24 값 = 항목 섹터(MIX.AVI 안) − 머리 f[2](D1 20 · D2 5) — 실행 파일 0x0600F3B0(이름 일치 + 기준값에 가장 가까운 항목) → 0x0600F7AC
    ⛔같은 이름이 둘 이상인 항목(D2 scoc01 = 항목 41·1137)은 «가까운 값»으로 고르므로 옮기지 않는다
  트랙: MIX.AVI 끝에 G 섹터를 붙이고, 그 뒤에 있던 파일들(D1 = MISC 18개 235 섹터)을 G 만큼 뒤로 밀고 뒷여백을 다시 만든다.
        디렉터리 기록(LBA·크기 양 엔디안) · PVD 볼륨 크기 · arc3 머리 f[3](전체 섹터) 갱신, 쓴 섹터는 EDC/ECC.
  from mixgrow import toc, grow"""
import os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(r'C:\claude\project\falcom-kr-patch\tools')
import iso


def toc(fh, mlba):
    """→ (머리 f(10칸), 목차 바이트, [(이름, 값 = 첫 u24, 값 위치)])"""
    h = iso.read_user(fh, mlba, 1)
    assert h[:4] == b'arc3', h[:4]
    f = list(struct.unpack_from('>10I', h, 4))
    ixb, ixn = f[5], f[6]
    ix = iso.read_user(fh, mlba + ixb, (ixn + 2047) // 2048)[:ixn]
    out = []; i = 0; prev = ''
    while i < len(ix):
        c = ix[i]; i += 1
        if 0xF1 <= c <= 0xFE:
            name = ix[i:i + (c & 15)].decode('latin1'); i += c & 15
            out.append((name, int.from_bytes(ix[i:i + 3], 'big'), i)); i += 6
        elif c >= 0xF0:
            name = prev; out.append((name, int.from_bytes(ix[i:i + 3], 'big'), i)); i += 3
        else:
            name = prev[:c >> 4] + ix[i:i + (c & 15)].decode('latin1'); i += c & 15
            out.append((name, int.from_bytes(ix[i:i + 3], 'big'), i)); i += 3
        prev = name
    return f, bytearray(ix), out


def write_run(fh, lba, data):
    n = (len(data) + 2047) // 2048
    pad = data + bytes(n * 2048 - len(data))
    for k in range(n):
        fh.seek((lba + k) * 2352); fh.write(iso.sector(lba + k, pad[k * 2048:(k + 1) * 2048]))
    return n


def shift(dst, grown, log=print):
    """★밀기(2026-10-05): grown = {항목 섹터(MIX.AVI 안): (항목 머리 0x20 B, NOT 건 새 데이터)} — 커진 항목은 제자리에서 늘리고
    그 뒤 항목을 전부 늘어난 만큼 뒤로 민다. 항목 차례가 그대로라 같은 이름(D1 scoa090_2 = 항목 3360·3820, D2 scoc01)의
    «기준값에 가장 가까운 항목» 고르기가 안 깨진다. 목차 값은 모두 새 섹터로. → {옛 섹터: 새 섹터}"""
    with open(dst, 'r+b') as fh:
        T = iso.tree(fh)
        ml, ms, mdl, moff = T['MOVIE/MIX.AVI']
        N = (ms + 2047) // 2048; mend = ml + N
        f, ix, ents = toc(fh, ml)
        assert f[3] == N, ('arc3 전체 섹터 ≠ MIX.AVI 섹터', f[3], N)
        chain = []; s = f[2]                                            # 항목 사슬(섹터, 섹터 수)
        while s < N:
            cnt = struct.unpack_from('>I', iso.read_user(fh, ml + s), 0)[0]
            chain.append((s, cnt)); s += cnt
        assert s == N
        newsec = {}; extra = 0; first = None
        for s, cnt in chain:
            newsec[s] = s + extra
            if s in grown:
                need = (0x20 + len(grown[s][1]) + 2047) // 2048
                if need > cnt:
                    extra += need - cnt
                    first = s if first is None else first
        G = extra
        if not G:                                                      # 늘어난 항목 없음 → 바뀐 항목만 제자리
            for s, cnt in chain:
                if s in grown:
                    head, data = grown[s]
                    h = bytearray(head); struct.pack_into('>III', h, 0, cnt, len(data), len(data))
                    write_run(fh, ml + s, bytes(h) + data + bytes(cnt * 2048 - 0x20 - len(data)))
            log('  MIX.AVI 항목 %d개 제자리(섹터 안)' % len(grown))
            return newsec, 0
        total = os.path.getsize(dst) // 2352
        after = sorted((v[0], v[1], n, v[2], v[3]) for n, v in T.items() if v[0] >= mend)
        fend = max([mend] + [l + (s + 2047) // 2048 for l, s, *_ in after])
        post = total - fend
        saved = [(l, s, n, dl, off, iso.read_user(fh, l, max(1, (s + 2047) // 2048))[:s]) for l, s, n, dl, off in after]
        for l, s, n, dl, off, data in saved[::-1]:                     # 뒤 파일 먼저(뒤에서부터 써야 덮어쓰지 않음)
            write_run(fh, l + G, data)
        for s, cnt in chain[::-1]:                                     # 항목: 뒤에서부터 옮겨 씀(first 앞은 바뀐 항목만 제자리)
            if s < first and s not in grown:
                continue
            ns = newsec[s]
            if s in grown:
                head, data = grown[s]
                need = (0x20 + len(data) + 2047) // 2048
                h = bytearray(head); struct.pack_into('>III', h, 0, max(need, cnt), len(data), len(data))
                write_run(fh, ml + ns, bytes(h) + data + bytes(max(need, cnt) * 2048 - 0x20 - len(data)))
            elif ns != s:
                for k in range(cnt - 1, -1, -1):
                    fh.seek((ml + s + k) * 2352 + 16); blk = fh.read(2048)
                    fh.seek((ml + ns + k) * 2352); fh.write(iso.sector(ml + ns + k, blk))
        for nm, v, p in ents:                                           # 목차 값
            ix[p:p + 3] = (newsec[v + f[2]] - f[2]).to_bytes(3, 'big')
        dirs = {}
        for l, s, n, dl, off, data in saved:
            ds = dl + off // 2048
            sec = dirs.setdefault(ds, bytearray(iso.read_user(fh, ds))); o = off % 2048
            struct.pack_into('<I', sec, o + 2, l + G); struct.pack_into('>I', sec, o + 6, l + G)
        ds = mdl + moff // 2048
        sec = dirs.setdefault(ds, bytearray(iso.read_user(fh, ds))); o = moff % 2048
        nsize = (N + G) * 2048
        struct.pack_into('<I', sec, o + 10, nsize); struct.pack_into('>I', sec, o + 14, nsize)
        for ds, sec in dirs.items():
            write_run(fh, ds, bytes(sec))
        for k in range(post):
            write_run(fh, fend + G + k, bytes(2048))
        fh.truncate((fend + G + post) * 2352)
        pvd = bytearray(iso.read_user(fh, 16))
        vs = struct.unpack_from('<I', pvd, 80)[0] + G
        struct.pack_into('<I', pvd, 80, vs); struct.pack_into('>I', pvd, 84, vs)
        write_run(fh, 16, bytes(pvd))
        h0 = bytearray(iso.read_user(fh, ml)); struct.pack_into('>I', h0, 4 + 3 * 4, N + G)
        write_run(fh, ml, bytes(h0))
        ixl = ml + f[5]; ixn = (len(ix) + 2047) // 2048
        old = bytearray(iso.read_user(fh, ixl, ixn)); old[:len(ix)] = ix
        write_run(fh, ixl, bytes(old))
        log('  MIX.AVI 항목 %d개 늘림 · +%d 섹터(섹터 %d 부터 밀기) · 뒤 파일 %d개 · 트랙 %d → %d 섹터' % (len(grown), G, first, len(saved), total, fend + G + post))
    return newsec, G


def grow(dst, moves, log=print):
    """dst 트랙(이미 복사본)에서 moves = [(항목 섹터(MIX.AVI 안), 항목 머리 0x20 B, NOT 건 데이터)] 를 MIX.AVI 끝에 붙임
    → {옛 섹터: 새 섹터}"""
    with open(dst, 'r+b') as fh:
        T = iso.tree(fh)
        ml, ms, mdl, moff = T['MOVIE/MIX.AVI']
        N = (ms + 2047) // 2048; mend = ml + N
        f, ix, ents = toc(fh, ml)
        assert f[3] == N, ('arc3 전체 섹터 ≠ MIX.AVI 섹터', f[3], N)
        names = {}
        for nm, v, p in ents:
            names.setdefault(nm, []).append((v, p))
        bysec = {v + f[2]: (nm, p) for nm, v, p in ents}
        blobs = []; G = 0; newsec = {}
        for sec, head, data in moves:
            nm, p = bysec[sec]
            if len(names[nm]) > 1:
                raise SystemExit('⛔같은 이름 항목은 옮기지 않음: %s' % nm)
            cnt = (0x20 + len(data) + 2047) // 2048
            h = bytearray(head); struct.pack_into('>III', h, 0, cnt, len(data), len(data))
            blobs.append((N + G, bytes(h) + data)); newsec[sec] = N + G
            ix[p:p + 3] = (N + G - f[2]).to_bytes(3, 'big')
            G += cnt
        total = os.path.getsize(dst) // 2352
        after = sorted((v[0], v[1], n, v[2], v[3]) for n, v in T.items() if v[0] >= mend)
        fend = max([mend] + [l + (s + 2047) // 2048 for l, s, *_ in after])
        post = total - fend
        saved = [(l, s, n, dl, off, iso.read_user(fh, l, max(1, (s + 2047) // 2048))[:s]) for l, s, n, dl, off in after]
        for at, blob in blobs:                                         # 항목 붙이기
            write_run(fh, ml + at, blob)
        dirs = {}
        for l, s, n, dl, off, data in saved:                           # 뒤 파일 밀기
            write_run(fh, l + G, data)
            ds = dl + off // 2048
            sec = dirs.setdefault(ds, bytearray(iso.read_user(fh, ds))); o = off % 2048
            struct.pack_into('<I', sec, o + 2, l + G); struct.pack_into('>I', sec, o + 6, l + G)
        ds = mdl + moff // 2048                                        # MIX.AVI 크기
        sec = dirs.setdefault(ds, bytearray(iso.read_user(fh, ds))); o = moff % 2048
        nsize = (N + G) * 2048
        struct.pack_into('<I', sec, o + 10, nsize); struct.pack_into('>I', sec, o + 14, nsize)
        for ds, sec in dirs.items():
            write_run(fh, ds, bytes(sec))
        for k in range(post):                                          # 뒷여백
            write_run(fh, fend + G + k, bytes(2048))
        fh.truncate((fend + G + post) * 2352)
        pvd = bytearray(iso.read_user(fh, 16))
        vs = struct.unpack_from('<I', pvd, 80)[0] + G
        struct.pack_into('<I', pvd, 80, vs); struct.pack_into('>I', pvd, 84, vs)
        write_run(fh, 16, bytes(pvd))
        h0 = bytearray(iso.read_user(fh, ml)); struct.pack_into('>I', h0, 4 + 3 * 4, N + G)   # arc3 f[3]
        write_run(fh, ml, bytes(h0))
        ixl = ml + f[5]; ixn = (len(ix) + 2047) // 2048
        old = bytearray(iso.read_user(fh, ixl, ixn)); old[:len(ix)] = ix
        write_run(fh, ixl, bytes(old))
        log('  MIX.AVI 항목 %d개 끝에 붙임 · +%d 섹터 · 뒤 파일 %d개 밀기 · 트랙 %d → %d 섹터' % (len(moves), G, len(saved), total, fend + G + post))
    return newsec
