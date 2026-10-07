# -*- coding: utf-8 -*-
r"""선택지 창 배치 흉내 (2026-10-07) — 00DESIRE.BIN 0x060089B0(선택지 그리기) 그대로
  항목마다 폭 w = 16 × (전각 공백 아닌 글자) [+ 8 × (항목 첫머리 아닌 전각 공백) — choicehook 이후]
  앞 항목이 줄 첫머리(x = 왼쪽)에서 시작했고 「앞 끝 x + 16 + w ≤ 오른쪽(0x129)」이면 같은 줄 오른쪽에, 아니면 다음 줄(+16).
  한 줄 최대 2개. 창에 보이는 줄 = 3 (위 0x9E · 대사 상자와 같음) → 넘으면 4번째 줄부터 상자 밖.
  python tools/choicefit.py → 3줄 넘는 선택지 묶음 목록"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
LEFT, RIGHT, ROWS = 0x64, 0x129, 3
VIS = 292                                   # 상자 안쪽 오른쪽 끝(boxfit.VIS) — 항목 하나가 이보다 길면 글자가 상자 밖
SP = '　'


def width(t, half=True):
    """t = 정규화한 글(전각 공백 = '　', 제어 토큰 {…} = 그림 글자 한 칸)"""
    w = 0
    for p in re.split(r'(\{[^}]*\})', t):
        if p.startswith('{'):
            w += 16; continue
        for ch in p:
            if ch == SP:
                w += 8 if (half and w) else 0
            else:
                w += 16
    return w


def rows(ws):
    """항목 폭 목록 → 줄 수(0x06008A72‥0x06008AC8)"""
    n = 0; prev_start = None; x = None
    for w in ws:
        if prev_start == LEFT and x + 16 + w <= RIGHT:
            prev_start = -1; x = x + 16 + w                      # 같은 줄 오른쪽(가운데·오른쪽 맞춤 — 줄 수엔 상관없음)
        else:
            n += 1; prev_start = LEFT; x = LEFT + w
    return n


def groups():
    """[(장, 항목, 명령 위치, [원문 글])] — 80 02 선택지 명령마다"""
    import scn
    out = []
    for dn in (1, 2):
        for it, d in scn.scripts(dn):
            res, end = scn.ops(d)
            for i, op, a in res:
                if op != 0x02 or not a:
                    continue
                k_ = 1; ps = []
                for _ in range(a[0]):
                    if k_ >= len(a):
                        break
                    k_ += 1 + 2 * a[k_]
                    if k_ >= len(a):
                        break
                    ps.append(a[k_] * 2); k_ += 2
                if len(ps) != a[0]:
                    continue
                out.append((dn, it, i * 2, [scn.show(scn.record(d, p)[1]) for p in ps]))
    return out


def check(trans, normalize):
    """trans: 원문 → 번역(정규화 전) · → [(장, 항목, 위치, 원래 줄, 새 줄, [번역])] 3줄을 넘고 원래보다 늘어난 묶음 + 항목 폭이 상자를 넘는 묶음"""
    bad = []
    for dn, it, pos, srcs in groups():
        new = [normalize(trans.get(s, s)) for s in srcs]
        r0 = rows([width(s, False) for s in srcs]); r1 = rows([width(t) for t in new])
        if r1 > max(ROWS, r0) or any(LEFT + width(t) > VIS for t in new):
            bad.append((dn, it, pos, r0, r1, new))
    return bad


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    import dsbuild
    src = dsbuild.load_src(); tr, _, _ = dsbuild.load_trans(src)
    G = groups(); r0max = max(rows([width(s, False) for s in g[3]]) for g in G)
    print('선택지 묶음 %d · 원문 최대 %d줄' % (len(G), r0max))
    bad = check({s: t for s, (k, t) in tr.items()}, dsbuild.normalize)
    print('3줄 넘는 묶음 %d' % len(bad))
    for dn, it, pos, r0, r1, new in bad:
        print('D%d 항목 %d @%05X  %d → %d줄  %s' % (dn, it, pos, r0, r1, ' / '.join(new)))
