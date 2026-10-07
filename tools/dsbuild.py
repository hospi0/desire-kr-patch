# -*- coding: utf-8 -*-
r"""Desire 한글 빌더 (2026-10-05) — 대사·선택지 되넣기 + 한글 글꼴 + 디스크 트랙
  번역: work/trans/desire_ko*.tsv · my files/번역/desire_*.tsv — 열 [번호, …, 원문, 번역](번호 = work/text/desire.tsv 의 5자리, 원문이 맞아야 씀)
        (짧은 꼴 [번호, 번역] 도 받음). 원문 같은 문장은 위치가 여러 개여도 한 번역.
  되넣기(스크립트 = MIX.AVI 항목, NOT 푼 것):
    · 문장 구역엔 대사 말고도 다른 명령이 가리키는 이름(RASEN2·E0001·opst1 …)이 섞여 있다 → 통째 재배치 금지
    · 번역 기록(머리 + 글 + 00, 짝수 맞춤)이 원래 자리에 들어가면 제자리, 넘치면 빈자리(줄거나 옮겨 간 문장 자리) → 항목 끝,
      옮긴 문장은 80 35 첫 인자·80 02 선택지 포인터(워드 오프셋)만 고친다
    · 항목은 원래 섹터 수 안에서만(목차 arc3 는 안 건드림) · 항목 머리 [섹터 수][크기][크기2] 의 크기 두 칸만 새로
  글꼴: 번역에 쓰인 한글 음절 → 아직 쓰는 가나·한자(번역 안 된 문장·실행 파일 문자열)를 뺀 칸에 배정(⛔E980‥E986 전용 그림 글자),
        나눔고딕 굵게 64px → 16×16 계조(poc.render) · FONT.CMP 다시 압축(tools/lz) 원래 섹터 안
  쓰는 순간 규칙: 원문 제어 토큰({n00}{w00}{k00}{E985}…) 차례가 번역과 같아야 함(다르면 빌드 금지) · 부호 뒤 공백 삭제 ·
        띄어쓰기 → 전각 공백(반각 글리프 없음) · , → 、 · … → ‥ · ~ → ～ · ASCII ! ? . ( ) → 전각
  python tools/dsbuild.py [--dummy[=배율]] [--write] [--install]
    --dummy : 번역 대신 원문 글자 수 × 배율 만큼 «가나다…» 가짜 번역(빈자리·끝 배치 시험용)"""
import collections, glob, hashlib, os, re, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import font, lz, mix, disc, scn, poc, mixgrow, pagehook, boxfit, choicefit
sys.path.append(r'C:\claude\project\falcom-kr-patch\tools')
import iso

OUT = os.path.join(ROOT, 'work', 'out')
F_DIR = {1: r'F:\hospi\roms\ss roms\Desire (Japan) (Disc 1)', 2: r'F:\hospi\roms\ss roms\Desire (Japan) (Disc 2) (2M)'}
SPECIAL = range(0xE980, 0xE987)
LIMIT = 0x15000                       # 스크립트 적재 한도(00DESIRE.BIN 리터럴 0x06004B00·0x06007DCC, 버퍼 0x200000 — 뒤 0x2176E0~ 다른 데이터라 못 올림)
TOK = re.compile(r'\{(?:[0-9A-F]{4}|[0-9A-F]{2}|[\x60-\x7f][0-9A-F]{2})\}')     # {E985} 2 B · {1B} 1 B · {n00} 영문자+1 B
FW = {',': '、', '，': '、', '。': '．', '…': '‥', '~': '～', '!': '！', '?': '？', '.': '．', '(': '（', ')': '）', ':': '：', '-': '－', '"': '”', "'": '’'}
FW.update({c: chr(ord(c) + 0xFEE0) for c in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz%&/+=*#@'})   # 반각 영숫자 글리프 없음 → 전각
PICT = {'{E980}', '{E981}', '{E982}', '{E983}', '{E984}'}
PUNCT = set('、。．！？」』）～‥・,.!?)')


PUNCT_GLYPH = {0x8141: ',', 0x8144: '.'}   # «、»·«．» 칸 → 한국식 «,»·«.» (사용자 2026-10-07 «일본식 마침표와 쉼표») · 걸침 표 0x06008340 에 들어 있는 칸이라 줄 끝 처리 그대로


def render_punct(ch, S=4):
    """«,»·«.» 를 한글과 같은 기준선에 두고 칸 왼쪽(앞 글자 바로 뒤)에 그림"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(poc.TTF, 15 * S)
    im = Image.new('L', (16 * S, 16 * S), 0); dr = ImageDraw.Draw(im)
    l, t, r, b = dr.textbbox((0, 0), '가', font=f)
    y = (16 * S - (b - t)) / 2 - t - S * 0.5                               # poc.render 와 같은 세로 자리(한글 기준선)
    l2, _, _, _ = dr.textbbox((0, 0), ch, font=f)
    dr.text((S * 1 - l2, y), ch, font=f, fill=255)
    a = np.asarray(im, np.float32).reshape(16, S, 16, S).mean((1, 3)) / 255
    return np.where(a < 0.08, 0, np.clip(np.round(a * 15), 1, 15)).astype(np.uint8)


def tokens_of(t):
    return [x for x in TOK.findall(t) if x not in PICT]          # 그림 글자 {E980}‥{E984}(메뉴 «見る・調べる»)는 한글로 바꿔도 됨 · ⛔{s00} = 버튼 대기+다음 음성 조각 → 더 넣거나 빼면 음성 어긋남


# ── 번역 ───────────────────────────────────────────────────────────────
def load_src():
    src = {}
    for l in open(os.path.join(ROOT, 'work', 'text', 'desire.tsv'), encoding='utf-8'):
        if l.startswith('#') or not l.strip():
            continue
        f = l.rstrip('\n').split('\t'); src[f[0]] = f[4]
    return src


def load_trans(src):
    tr = {}; files = []
    for d, pat in ((os.path.join(ROOT, 'work', 'trans'), r'desire_ko.*\.tsv$'), (os.path.join(ROOT, 'my files', '번역'), r'desire_.*\.tsv$')):
        if os.path.isdir(d):
            files += [os.path.join(d, n) for n in sorted(os.listdir(d)) if re.match(pat, n)]
    bad = []
    for p in files:
        for l in open(p, encoding='utf-8-sig'):
            if l.startswith('#') or not l.strip():
                continue
            f = [x[1:-1].replace('""', '"') if len(x) >= 2 and x[0] == x[-1] == '"' else x for x in l.rstrip('\r\n').split('\t')]
            k = f[0]
            if k not in src:
                continue
            if len(f) >= 6:
                if f[4] != src[k]:
                    bad.append((k, '원문 다름')); continue
                t = f[5]
            elif len(f) == 2:
                t = f[1]
            else:
                continue
            if t.strip():
                tr[src[k]] = (k, t)
    return tr, files, bad


def dummy(src, scale, d1only=False):
    """가짜 번역 — d1only: 2장에도 나오는 문장은 1.0배(2장 항목 41 은 같은 이름이라 못 옮기고 +3.2% 가 한도 → 옮기기 경로 시험용)"""
    syl = '가나다라마바사아자차카타파하거너더러머버서어저처'
    d2 = set()
    if d1only:
        for l in open(os.path.join(ROOT, 'work', 'text', 'scn_d2.tsv'), encoding='utf-8'):
            if not l.startswith('#'):
                d2.add(l.rstrip('\n').split('\t')[5])
    out = {}; n = 0
    for k, s in src.items():
        parts = re.split(r'(\{[^}]+\})', s); t = ''
        for p in parts:
            if p.startswith('{'):
                t += p; continue
            m = int(round(len(p) * (1.0 if s in d2 else scale)))
            for _ in range(m):
                t += syl[n % len(syl)]; n += 1
        out[s] = (k, t)
    return out


def normalize(t):
    t = ''.join(p if p.startswith('{') else ''.join(FW.get(c, c) for c in p)
                for p in re.split(r'(\{[^}]*\})', t))                          # 제어 토큰 {E985} 안은 그대로
    t = re.sub(r'(?<=[%s]) +' % re.escape(''.join(PUNCT)), '', t)      # 부호 뒤 공백 삭제(전프로젝트 규칙)
    return t.replace(' ', '　')


def encode(t, kmap, cc):
    out = bytearray(); i = 0
    while i < len(t):
        if t[i] == '{':
            m = TOK.match(t, i)
            if not m:
                raise SystemExit('⛔토큰 해석 실패 %r' % t[i:i + 8])
            x = m.group()[1:-1]
            out += bytes([ord(x[0])]) + bytes.fromhex(x[1:]) if len(x) == 3 else bytes.fromhex(x)
            i = m.end(); continue
        ch = t[i]; i += 1
        if '가' <= ch <= '힣':
            out += struct.pack('>H', kmap[ch]); continue
        b = ch.encode('cp932')
        if len(b) != 2 or int.from_bytes(b, 'big') not in cc:
            raise SystemExit('⛔글꼴에 없는 글자 %r (%s)' % (ch, t))
        out += b
    return bytes(out)


# ── 글꼴 칸 ────────────────────────────────────────────────────────────
def used_codes(texts):
    """아직 화면에 쓰일 SJIS 코드: 번역 안 된 문장 + 실행 파일 문자열"""
    u = set()
    for t in texts:
        b = t if isinstance(t, (bytes, bytearray)) else None
        if b is None:
            for ch in re.sub(r'\{[^}]+\}', '', t):
                try:
                    e = ch.encode('cp932')
                    if len(e) == 2: u.add(int.from_bytes(e, 'big'))
                except UnicodeEncodeError:
                    pass
    exe = disc.read(1, '00DESIRE.BIN')
    for m in mix.SJ.finditer(exe):
        g = m.group()
        if len(g) >= 4:
            for k in range(0, len(g) - 1, 2):
                u.add(int.from_bytes(g[k:k + 2], 'big'))
    return u


# ── 스크립트 되넣기 ────────────────────────────────────────────────────
def rebuild(d, tr_bytes, cap):
    """d = NOT 푼 항목 → (새 바이트, 통계). tr_bytes: {글 바이트(원문): 새 글 바이트}"""
    d = bytearray(d)
    R = scn.refs(bytes(d)); res, end = scn.ops(bytes(d)); s0 = end * 2
    st = collections.Counter()
    recs = {}                                                     # 시작 → (머리, 글, 끝(짝수 포함))
    for o, srcs in R.items():
        ks = {k for _, k in srcs}
        if not (ks & {'35', '02'}) or not (s0 <= o < len(d)):
            continue
        head, body, e = scn.record(bytes(d), o)
        span = e + 1; span += span & 1
        recs[o] = (head, body, span)
    starts = set(R)                                               # 무엇이든 가리키는 곳(빈자리로 쓰면 안 되는 시작점)
    # ★채워 넣기(2026-10-05): 번역할 대사 기록을 전부 먼저 비워 이름(RASEN2·E0001 …) 사이 큰 빈칸을 만들고, 원래 차례대로 앞에서부터 채운다
    #   (넘치는 것만 옮기면 옛 자리가 조각나 못 써서 1.25배 가짜 번역에서 항목 70 이 순수 증가 13 KB 대신 25 KB 늘었음). 이름 데이터는 안 움직임.
    move = {}; holes = []; plan = []
    for o, (head, body, span) in sorted(recs.items()):
        nb = tr_bytes.get(bytes(body))
        if nb is None:
            continue
        rec = head + nb + b'\0'; rec += b'\0' * (len(rec) & 1)
        if not [x for x in starts if o < x < span]:                # 기록 한가운데를 가리키는 다른 참조가 있으면 옛 자리는 그대로 두고 옮기기만
            d[o:span] = bytes(span - o); holes.append([o, span])
        plan.append((o, rec))
    holes.sort(); merged = []
    for h in holes:                                               # 맞닿은 빈자리 합치기
        if merged and h[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], h[1])
        else:
            merged.append(list(h))
    holes = merged
    tail = len(d) + (len(d) & 1)
    for o, rec in plan:
        h = next((h for h in holes if h[1] - h[0] >= len(rec)), None)
        if h:
            at = h[0]; h[0] += len(rec); st['제자리' if at == o else '빈자리'] += 1
        else:
            at = tail; tail += len(rec); st['끝에'] += 1
            if at > len(d):
                d += bytes(at - len(d))
        if at + len(rec) > len(d):
            d += bytes(at + len(rec) - len(d))
        d[at:at + len(rec)] = rec
        if at != o:
            move[o] = at
    if len(d) > cap:
        raise SystemExit('⛔항목 넘침 %d > 섹터 자리 %d (끝에 %d)' % (len(d), cap, st['끝에']))
    # 포인터 고치기
    for i, op, a in res:
        if op == 0x35 and a and a[0] * 2 in move:
            struct.pack_into('>H', d, (i + 1) * 2, move[a[0] * 2] // 2); st['포인터'] += 1
        elif op == 0x02 and a:
            k_ = 1; pos = i + 2
            for _ in range(a[0]):
                c = a[k_]; k_ += 1 + 2 * c; pos = i + 1 + k_
                if a[k_] * 2 in move:
                    struct.pack_into('>H', d, pos * 2, move[a[k_] * 2] // 2); st['포인터'] += 1
                k_ += 2
    return bytes(d), st


def compact(d, tr_bytes, cap):
    """★빈칸 없이 다시 쌓기(2026-10-07): 채워 넣기로도 한도를 넘는 항목만(D2 41 — 대사 사이사이 음성 이름 35v 9.7 KB 가
    못 움직여서 조각 낭비 4.4 KB). 문장 구역을 «참조 시작점마다 끊은 조각»으로 나눠 원래 차례대로 빈틈없이 다시 붙이고
    80 35 대사·35v·80 02 포인터를 전부 고친다. 조각 = 한 시작점부터 다음 시작점까지(참조 없는 뒤 바이트도 함께 움직임)."""
    R = scn.refs(d); res, end = scn.ops(d); s0 = end * 2
    st = collections.Counter()
    starts = sorted(o for o in R if s0 <= o < len(d))
    if not starts or starts[0] != s0:
        raise SystemExit('⛔다시 쌓기: 문장 구역 첫 참조가 구역 시작이 아님')
    out = bytearray(d[:s0]); move = {}
    for k, o in enumerate(starts):
        nxt = starts[k + 1] if k + 1 < len(starts) else len(d)
        chunk = d[o:nxt]
        if {x for _, x in R[o]} & {'35', '02'}:
            head, body, e = scn.record(d, o)
            span = e + 1; span += span & 1
            if span > nxt:
                raise SystemExit('⛔다시 쌓기: 기록 한가운데를 가리키는 참조 %#x' % o)
            nb = tr_bytes.get(bytes(body))
            if nb is not None:
                rec = head + nb + b'\0'; rec += b'\0' * (len(rec) & 1)
                chunk = rec + d[span:nxt]; st['다시 쌓음'] += 1
        if len(out) & 1:
            out += b'\0'
        move[o] = len(out); out += chunk
    if len(out) > cap:
        raise SystemExit('⛔항목 넘침(다시 쌓기) %d > %d' % (len(out), cap))
    for i, op, a in res:                                          # 포인터 고치기(워드 위치 = 명령 + 1 + 인자 번호)
        if op == 0x35 and a:
            ix = [0] + (list(range(2, 2 + a[1])) if len(a) >= 2 else [])
        elif op == 0x02 and a:
            ix = []; k_ = 1
            for _ in range(a[0]):
                k_ += 1 + 2 * a[k_]; ix.append(k_); k_ += 2
        else:
            continue
        for x in ix:
            if a[x] * 2 in move:
                struct.pack_into('>H', out, (i + 1 + x) * 2, move[a[x] * 2] // 2); st['포인터'] += 1
    return bytes(out), st


def verify(old, new, tr_bytes):
    """새 항목을 다시 읽어 명령(포인터 빼고)이 같고, 대사·선택지가 기대한 글인지"""
    ro, _ = scn.ops(old); rn, _ = scn.ops(new)
    assert [(i, op, len(a)) for i, op, a in ro] == [(i, op, len(a)) for i, op, a in rn], '명령 구조 바뀜'
    def ptrs(a, op):                                             # 명령 인자 차례대로 대사·선택지 포인터(바이트)
        if op == 0x35 and a:
            return [a[0] * 2]
        out = []
        if op == 0x02 and a:
            k_ = 1
            for _ in range(a[0]):
                k_ += 1 + 2 * a[k_]; out.append(a[k_] * 2); k_ += 2
        return out
    bad = 0
    for (i, op, a), (_, _, b) in zip(ro, rn):                    # (선택지가 여럿이면 크기순 짝짓기는 엇갈린다 — 1.12배 시험에서 127곳 오탐)
        if op not in (0x35, 0x02):
            if a != b:
                bad += 1                                         # 대사·선택지 말고는 인자가 그대로여야
            continue
        for oo, on in zip(ptrs(a, op), ptrs(b, op)):
            _, bo, _ = scn.record(old, oo); _, bn, _ = scn.record(new, on)
            if bytes(bn) != tr_bytes.get(bytes(bo), bytes(bo)):
                bad += 1
        if op == 0x35 and len(a) >= 2:                           # 35v(음성 이름 등)는 글자 그대로여야
            for po, pn in zip(a[2:2 + a[1]], b[2:2 + b[1]]):
                zo = old.find(b'\0', po * 2); zn = new.find(b'\0', pn * 2)
                if old[po * 2:zo] != new[pn * 2:zn]:
                    bad += 1
    return bad


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src = load_src()
    dm = next((a for a in sys.argv if a.startswith('--dummy')), None)
    if dm:
        tr = dummy(src, float(dm.split('=')[1]) if '=' in dm else 1.0, '--d1' in sys.argv); files, badsrc = ['(가짜 번역)'], []
    else:
        tr, files, badsrc = load_trans(src)
    print('번역 파일 %d · 번역 %d / %d 문장 · 원문 안 맞음 %d' % (len(files), len(tr), len(src), len(badsrc)))
    # 쓰는 순간 검사: 토큰 차례
    errs = []; norm = {}
    for s, (k, t) in tr.items():
        t2 = normalize(t)
        if tokens_of(t2) != tokens_of(s):
            errs.append((k, tokens_of(s), tokens_of(t2)))
        norm[s] = boxfit.autofix(t2)[0]                                   # 줄 끝 ？！」 가 상자 밖으로 나가면 마지막 띄어쓰기를 {n00} 로(tools/boxfit)
    if errs:
        for e in errs[:10]: print('  ⛔토큰', e)
        raise SystemExit('⛔원문 제어 토큰과 다른 번역 %d줄' % len(errs))
    over = [(k, ' | '.join(boxfit.layout(t2))) for s, (k, t) in tr.items() for t2 in [norm[s]] if boxfit.overflow(t2)]   # 상자 12칸 × 3줄(반칸 공백 훅 기준)
    if over:
        for e in sorted(over)[:10]: print('  ⛔상자 넘침', *e)
        raise SystemExit('⛔대사 상자 3줄을 넘는 번역 %d줄 (tools/boxfit.py)' % len(over))
    if not dm:
        cbad = choicefit.check(norm, lambda t: t)                         # 선택지 창: 한 줄 최대 2개 흐름 배치 · 3줄(반칸 공백 훅 기준)
        if cbad:
            for e in cbad: print('  ⛔선택지 넘침 D%d 항목 %d @%05X %d→%d줄' % e[:5], ' / '.join(e[5]))
            raise SystemExit('⛔선택지 창 3줄(또는 항목 폭)을 넘는 묶음 %d개 (tools/choicefit.py)' % len(cbad))
    cc = font.charcode(); ccs = set(cc)
    untr = [s for s in src.values() if s not in norm]
    used = used_codes(untr)
    syl = sorted(set(c for t in norm.values() for c in t if '가' <= c <= '힣'), key=lambda c: c)
    free = [c for c in cc if c >= 0x829F and c not in SPECIAL and c not in used]
    print('한글 음절 %d · 쓸 수 있는 칸 %d (아직 쓰는 코드 %d)' % (len(syl), len(free), len(used)))
    if len(syl) > len(free):
        raise SystemExit('⛔글꼴 칸 모자람 %d > %d' % (len(syl), len(free)))
    kmap = dict(zip(syl, free[::-1][:len(syl)]))
    # 원문 글 바이트 → 새 글 바이트
    tr_bytes = {}
    for dn in (1, 2):
        for no, d in scn.scripts(dn):
            R = scn.refs(d)
            for o, srcs in R.items():
                if {k for _, k in srcs} & {'35', '02'} and 0 <= o < len(d):
                    _, body, _ = scn.record(d, o); s = scn.show(body)
                    if s in norm and bytes(body) not in tr_bytes:
                        tr_bytes[bytes(body)] = encode(norm[s], kmap, ccs)
    print('바꿀 글 %d종' % len(tr_bytes))
    # 글꼴
    srcf = disc.read(1, 'MISC/FONT.CMP')
    g = bytearray(font.decompress(srcf))
    for ch, code in kmap.items():
        k = cc.index(code); px = poc.render(ch)
        g[k * 128:(k + 1) * 128] = bytes((px.reshape(-1, 2)[:, 0] << 4) | px.reshape(-1, 2)[:, 1])
    for code, ch in PUNCT_GLYPH.items():                                   # 한국식 쉼표·마침표(줄 끝 걸침 문자 칸을 그대로 쓰고 그림만 바꿈)
        k = cc.index(code); px = render_punct(ch)
        g[k * 128:(k + 1) * 128] = bytes((px.reshape(-1, 2)[:, 0] << 4) | px.reshape(-1, 2)[:, 1])
    fcmp = lz.compress(bytes(g)); assert font.decompress(fcmp) == bytes(g)
    fhave = (len(srcf) + 2047) // 2048 * 2048
    print('FONT.CMP %d → %d B (자리 %d)' % (len(srcf), len(fcmp), fhave))
    if len(fcmp) > fhave:
        raise SystemExit('⛔FONT.CMP 넘침')
    # 스크립트 — 적재 한도(0x15000) 안이면 되고, 원래 섹터를 넘는 항목은 제자리에서 늘리고 뒤 항목을 민다(tools/mixgrow.shift — 같은 이름 항목 차례 보존)
    tot = collections.Counter(); newitems = {1: {}, 2: {}}
    for dn in (1, 2):
        its = {it[0]: it for it in mix.items(dn)}
        with open(disc.TRACK[dn], 'rb') as fh:
            f, _, ents = mixgrow.toc(fh, disc.listing(dn)['MOVIE/MIX.AVI'][0])
        name = {v + f[2]: nm for nm, v, _ in ents}
        for no, d in scn.scripts(dn):
            it = its[no]; cap = it[2] * 2048 - 0x20
            nd, st = rebuild(d, tr_bytes, 10 ** 7)
            if len(nd) > LIMIT:                                          # 채워 넣기로 넘치면 빈칸 없이 다시 쌓기
                nd, st = compact(d, tr_bytes, LIMIT)
            bad = verify(d, nd, tr_bytes)
            if bad:
                raise SystemExit('⛔D%d 항목 %d 되읽기 불일치 %d' % (dn, no, bad))
            tot.update(st)
            mv = len(nd) > cap
            if mv:
                tot['항목 늘림'] += 1
            if nd != d:
                newitems[dn][no] = (it, nd, mv)
            if st['끝에'] or mv or st['다시 쌓음']:
                print('  D%d 항목 %4d %-10s %6d → %6d (섹터 자리 %6d · 한도 %d)%s  %s' % (dn, no, name[it[1]], len(d), len(nd), cap, LIMIT, ' → 늘림(뒤 항목 밀기)' if mv else '', dict(st)))
    print('되넣기 %s · 바뀐 항목 %d·%d' % (dict(tot), len(newitems[1]), len(newitems[2])))
    if '--write' not in sys.argv and '--install' not in sys.argv:
        return
    B1 = {}                                                                   # 원본 b1 바이트 → 한글 b1 (tools/b1text.py 결과)
    its1 = {it[0]: it for it in mix.items(1)}
    for p in glob.glob(os.path.join(ROOT, 'work', 'b1', 'kr', '*.b1')):
        B1[mix.read(1, its1[int(os.path.basename(p)[:-3])])] = open(p, 'rb').read()
    print('그림 b1 %d장 준비' % len(B1))
    for dn in (1, 2):
        os.makedirs(os.path.join(OUT, 'd%d' % dn), exist_ok=True)
        fname = os.path.basename(disc.TRACK[dn]); dst = os.path.join(OUT, 'd%d' % dn, fname)
        shutil.copyfile(disc.TRACK[dn], dst)
        mlba = disc.listing(dn)['MOVIE/MIX.AVI'][0]
        grown = {}
        with open(dst, 'rb') as fh:
            for no, (it, nd, mv) in newitems[dn].items():
                grown[it[1]] = (iso.read_user(fh, mlba + it[1])[:0x20], mix.unnot(nd))
        with open(dst, 'rb') as fh:                                           # ★그림 글자(b1): work/b1/kr/<항목>.b1 — 원본 바이트가 같은 항목을 두 디스크에서 찾아 바꿈
            for it in mix.items(dn):
                if it[3] < 6:
                    continue
                raw = mix.read(dn, it)
                if raw[:2] == b'b1' and raw in B1:
                    grown[it[1]] = (iso.read_user(fh, mlba + it[1])[:0x20], B1[raw]); tot['그림 b1'] += 1
        newsec, G = mixgrow.shift(dst, grown) if grown else ({}, 0)
        moves = [1] * sum(1 for v in newitems[dn].values() if v[2])
        if 'MISC/FONT.CMP' in disc.listing(dn):
            iso.patch_sub(dst, {'MISC/FONT.CMP': fcmp}, log=lambda *a: None)
        vids = {'SOUND/' + os.path.basename(v): open(v, 'rb').read() for v in glob.glob(os.path.join(ROOT, 'work', 'vid', 'kr', '*.VID'))}
        vids = {k: v for k, v in vids.items() if k in disc.listing(dn)}
        if vids:                                                              # ★그림 글자(tVid): 제목 로고·오프닝 스태프(tools/vidtext.py)
            iso.patch_sub(dst, vids, log=lambda *a: None); print('  그림 영상 %d개 %s' % (len(vids), ' '.join(sorted(os.path.basename(k) for k in vids))))
        exe2 = pagehook.apply(disc.read(dn, '00DESIRE.BIN'))                    # 대사 상자 쪽 넘김 훅(tools/pagehook.py)
        iso.patch_sub(dst, {'00DESIRE.BIN': exe2}, log=lambda *a: None)
        # 되읽기: 목차로 스크립트를 찾아 기대한 바이트인지
        with open(dst, 'rb') as fh:
            T = iso.tree(fh); ml = T['MOVIE/MIX.AVI'][0]
            f, _, ents = mixgrow.toc(fh, ml)
            bysec = {}
            for nm, v, _ in ents:
                bysec[v + f[2]] = nm
            for no, (it, nd, mv) in newitems[dn].items():
                sec = newsec.get(it[1], it[1])
                assert sec in bysec, ('목차에 없음', dn, no)
                h = iso.read_user(fh, ml + sec, 1)
                cnt_, sz = struct.unpack_from('>II', h, 0)
                raw = iso.read_user(fh, ml + sec, cnt_)[0x20:0x20 + sz]
                assert mix.unnot(raw) == nd, ('되읽기 불일치', dn, no)
            assert iso.read_user(fh, T['00DESIRE.BIN'][0], (len(exe2) + 2047) // 2048)[:len(exe2)] == exe2
            assert iso.read_user(fh, T['MISC/FONT.CMP'][0], (len(fcmp) + 2047) // 2048)[:len(fcmp)] == fcmp if 'MISC/FONT.CMP' in T else True
        h = hashlib.md5(open(dst, 'rb').read()).hexdigest()
        print('D%d 트랙 1 %s%s' % (dn, h, ' · 항목 늘림 %d' % len(moves) if moves else ''))
        if '--install' in sys.argv:
            shutil.copyfile(dst, os.path.join(F_DIR[dn], fname)); print('  F: 설치')

if __name__ == '__main__':
    main()
