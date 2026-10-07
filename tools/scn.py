# -*- coding: utf-8 -*-
r"""시나리오 스크립트(MIX.AVI 항목, NOT 푼 것) 문장 추출 (2026-10-04 밤)
  u16 워드 단위 · 0x80xx = 명령. 앞 = 명령 구역, 뒤 = 문장 구역.
  문장 참조(워드 오프셋 → 바이트 = ×2):
    80 35 [ptr]                      대사·지문 (가장 많음)
    80 02 [n] { [u16][ptr][u16] } × n  선택지(스테이트 새로운선택지등장: 見る·調べる / 移動する / 話す / 待つ)
  문장 기록 = [선택 머리 66 xx(표정·음성 등 추정)] + 글 + 00 (+ 짝수 맞춤 00)
  글 안 특수 코드: 0xE980‥0xE984 = «見る·調べる» 전용 그림 글자(CHARCODE 끝쪽) → TSV 에 {E980} 꼴
  python tools/scn.py [1|2] → work/text/scn_d<N>.tsv (번호·항목·바이트 위치·머리·원문)
"""
import collections, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import mix, font

CC = set(font.charcode())
BAD02 = []


def words(d):
    return [struct.unpack_from('>H', d, i)[0] for i in range(0, len(d) - 1, 2)]


def ops(d):
    """명령 구역을 0x80xx 워드로 끊음 → [(워드 위치, op, [인자])] · 구역 끝 = 첫 80 35 문장 대상(가장 앞)
    ⚠인자가 0x80xx 꼴(바이트 오프셋 0x10000‥0x101FE 포인터)이면 잘못 끊길 수 있음 — 명령 길이 통계(work/oplen.txt)로 검사"""
    w = words(d)
    end = len(w)
    for i in range(len(w) - 1):                    # 대략 끝: 80 35 의 첫 인자 중 가장 작은 값
        if w[i] == 0x8035 and w[i + 1] * 2 > i * 2:
            end = min(end, w[i + 1])
    res = []; i = 0
    while i < end:
        if w[i] >> 8 == 0x80:
            op = w[i] & 0xFF
            if op == 0x35 and i + 2 < len(w):                 # [문장][n][n] — 포인터가 0x80xx 꼴(바이트 0x10000 이상)이어도 인자로
                j = i + 3 + w[i + 2]
            elif op == 0x02 and i + 1 < len(w):               # [n] { [k][2k][문장][분기] }
                j = i + 2
                for _ in range(w[i + 1]):
                    j += 1 + 2 * w[j] + 2
            else:
                j = i + 1
                while j < end and w[j] >> 8 != 0x80:
                    j += 1
            res.append((i, op, w[i + 1:j])); i = j
        else:
            i += 1
    return res, end


def refs(d):
    """문장 참조 → {바이트 위치: [(명령 위치, 종류)]} — 35 = 대사 첫 인자 · 35v = 80 35 뒤 덧붙은 포인터(음성 등) · 02 = 선택지"""
    out = collections.defaultdict(list)
    res, end = ops(d)
    for i, op, a in res:
        if op == 0x35 and a:
            out[a[0] * 2].append((i * 2, '35'))
            if len(a) >= 2:
                for p in a[2:2 + a[1]]:
                    out[p * 2].append((i * 2, '35v'))
        elif op == 0x02 and a:                     # 선택지: [n] { [k][조건 2k워드][문장][분기] } × n
            k_ = 1; ps = []
            for j in range(a[0]):
                if k_ >= len(a):
                    break
                c = a[k_]; k_ += 1 + 2 * c
                if k_ + 1 >= len(a) + 1:
                    break
                ps.append(a[k_]); k_ += 2
            if k_ == len(a) and len(ps) == a[0]:
                for p in ps:
                    out[p * 2].append((i * 2, '02'))
            else:
                BAD02.append((i * 2, a))
    return out


def record(d, o):
    """→ (머리, 글 바이트, 끝) — 글은 00 앞까지"""
    head = b''
    if 0x60 <= d[o] < 0x80:                        # 머리 [66/67/6E …][플래그] (표정·음성 등 추정)
        head = d[o:o + 2]; o += 2
    e = o
    while e < len(d) and d[e] != 0:                # 글 안 제어 = [영문자 0x60‥0x7F][인자 1 B] (n 00 = 줄바꿈 · s 00 = 멈춤 추정)
        b = d[e]
        e += 2 if (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF or 0x60 <= b < 0x80) else 1
    return head, d[o:e], e


def show(b):
    out = []; i = 0
    while i < len(b):
        c = b[i]
        if 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            code = (c << 8) | b[i + 1]
            try:
                ch = bytes(b[i:i + 2]).decode('cp932')
            except UnicodeDecodeError:
                ch = None
            if ch is None or code >= 0xE980 or code not in CC:
                out.append('{%04X}' % code)
            else:
                out.append(ch)
            i += 2
        elif 0x60 <= c < 0x80:
            out.append('{%s%02X}' % (chr(c), b[i + 1])); i += 2
        elif 0x20 <= c < 0x60 or 0xA1 <= c <= 0xDF:
            out.append(bytes([c]).decode('cp932')); i += 1
        else:
            out.append('{%02X}' % c); i += 1
    return ''.join(out)


def scripts(disc_no):
    """[(항목 번호, NOT 푼 바이트)] — 문장 참조가 있는 항목만"""
    out = []
    for it in mix.items(disc_no):
        raw = mix.read(disc_no, it)
        if len(raw) < 64:
            continue
        d = mix.unnot(raw)
        if d[:2] != b'\x80\x01':
            continue
        out.append((it[0], d))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    dn = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    rows = []; bad = collections.Counter(); kinds = collections.Counter()
    orphan = 0
    for no, d in scripts(dn):
        R = refs(d)
        good = {}; covered = set()
        for o, srcs in R.items():
            ks = {k for _, k in srcs}
            if not (ks & {'35', '02'}) or not (0 <= o < len(d)):
                continue                                                         # 35v = 음성 파일 이름(번역 안 함)
            head, body, e = record(d, o)
            if body:
                good[o] = (head, body, [x for x in srcs if x[1] != '35v'])
                covered.update(range(o, e))
        _, end = ops(d)
        for m in mix.SJ.finditer(d, end * 2):                                        # 참조 안 된 일본어(빠진 명령 찾기용)
            if m.start() not in covered and len(m.group()) >= 4:
                orphan += 1
                if orphan <= 8:
                    print('  참조 없음', no, hex(m.start()), show(m.group())[:30])
        for o in sorted(good):
            head, body, srcs = good[o]
            t = show(body)
            for m in re.findall(r'\{([0-9A-F]{2})\}', t):
                bad[m] += 1
            kinds['+'.join(sorted(set(k for _, k in srcs)))] += 1
            rows.append((no, o, head.hex(), '+'.join(sorted(set(k for _, k in srcs))), t))
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    p = os.path.join(ROOT, 'work', 'text', 'scn_d%d.tsv' % dn)
    with open(p, 'w', encoding='utf-8', newline='\n') as w:
        w.write('#번호\t항목\t위치\t머리\t참조\t원문\t번역\n')
        for k, (no, o, h, kd, t) in enumerate(rows):
            w.write('D%d-%05d\t%d\t%05X\t%s\t%s\t%s\t\n' % (dn, k + 1, no, o, h, kd, t))
    chars = sum(len(re.sub(r'\{[0-9A-F]+\}', '', r[4])) for r in rows)
    print('스크립트 %d · 문장 %d · 글자 %d · 참조 종류 %s' % (len(set(r[0] for r in rows)), len(rows), chars, dict(kinds)))
    print('선택지 해석 실패', len(BAD02), BAD02[:3])
    print('1바이트 제어 코드', bad.most_common(20), '· 참조 없는 문장', orphan)


if __name__ == '__main__':
    main()
