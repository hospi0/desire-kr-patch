# -*- coding: utf-8 -*-
r"""번역 교정: my files/desire번역/*.tsv(하스피 번역, 읽기만) → work/trans/desire_ko_NNN.tsv(빌더가 읽는 자리)

  python tools/ds_fix.py            # 교정본 쓰기 + work/text/ds_fix_log.tsv(바뀐 줄) + 남은 문제 보고

차례: ① 빈 번역 ← 빠진거.txt·빠진거2.txt(번호로)  ② 줄 교정 work/text/ds_fixes.tsv(통독 결과)
      ③ 화자 표시 되살리기(원문 【이름】/{E985}이름{E986} 이 번역에 없으면 같은 자리에)  ④ 고유명사 통일(뒤 조사까지 받침에 맞춤)
      ⑤ 「」 되살리기(원문에 「」가 있고 번역이 "…" 면)
검사: 빈 번역 · 가나 남음 · 제어 토큰 차례 다름 · 화자 다름 → 보고(빌드 때는 dsbuild 가 다시 막는다).
"""
import glob, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, 'my files', 'desire번역')
OUT = os.path.join(ROOT, 'work', 'trans')
FIXES = os.path.join(ROOT, 'work', 'text', 'ds_fixes.tsv')
LOG = os.path.join(ROOT, 'work', 'text', 'ds_fix_log.tsv')
TOK = re.compile(r'\{(?:[0-9A-F]{4}|[0-9A-F]{2}|[\x60-\x7f][0-9A-F]{2})\}')
SPK = re.compile(r'^((?:\{[^}]*\})*)(【(.*?)】|\{E985\}(.*?)\{E986\})')

# 인물 이름(원문 → 한국어). 화자 표시는 이 표로 쓴다.
NAMES = {
    'アル': '알', 'マコト': '마코토', 'マルチナ': '마르티나', 'レイコ': '레이코', 'シェリル': '셰릴', 'シルビア': '실비아',
    'ティーナ': '티나', 'カイル': '카일', 'カズミ': '카즈미', 'クリス': '크리스', 'グスタフ': '구스타프', 'エレナ': '엘레나',
    'ゲーツ': '게이츠', '男': '남자', '女': '여자', '声': '목소리', '編集長': '편집장', '男の人': '남자', '女性の声': '여자 목소리',
    '放送の声': '방송 목소리', '女の子': '여자아이', 'ツナギの女': '작업복 입은 여자', '女の人': '여자', 'オバサン': '아주머니',
    '男の声': '남자 목소리', '女の声': '여자 목소리', '少女': '소녀', 'アル・レイコ': '알・레이코', '通りがかりの男': '지나가던 남자',
    '見知らぬ女性': '낯선 여성', 'ティーナの声': '티나 목소리', 'アナウンス': '안내방송', '窓際の女性': '창가의 여성',
    'アルチナ': '마르티나',
}
# 본문 고유명사 통일: (틀린 꼴, 바른 꼴)
TERMS = [
    ('아루', '알'), ('아르', '알'), ('마르치나', '마르티나'), ('쉐릴', '셰릴'), ('게츠', '게이츠'), ('데자이어', '디자이어'),
    ('앨버트', '알버트'), ('아르버트', '알버트'), ('맥도걸', '맥두걸'), ('그란체스타', '그랜체스터'), ('그랜체스타', '그랜체스터'), ('그랑체스타', '그랜체스터'),
    ('구사나기', '쿠사나기'), ('메디컬센터', '메디컬 센터'), ('숙사', '숙소'), ('과부 아줌마', '노처녀'), ('구체 돔', '구형 돔'), ('반응 장치', '반응장치'), ('세릴', '셰릴'), ('이즈미 군', '이즈미 양'), ('쿠사나기 군', '쿠사나기 양'),
]
# 원문에 특정 말이 있는 줄에서만 바꾸는 번역어: (원문에 있는 말, 틀린 꼴, 바른 꼴)
CTX_TERMS = [
    ('むにゃ', '우물우물', '음냐음냐'), ('むにゃ', '우물', '음냐'),          # 잠꼬대
]
JOSA = [('이라고', '라고'), ('이라니까', '라니까'), ('이라는', '라는'), ('이라면', '라면'), ('이랑은', '랑은'), ('이랑도', '랑도'), ('은', '는'), ('이', '가'), ('을', '를'), ('과', '와'), ('으로', '로'), ('이랑', '랑'), ('아', '야'), ('이여', '여'), ('이나', '나'), ('이에요', '예요'), ('이야', '야'), ('이지', '지'), ('이라', '라')]
HANGUL = '가-힣'


def batchim(s):
    c = ord(s[-1]) - 0xAC00
    return 0 <= c < 11172 and c % 28 != 0


def fix_josa(word, josa):
    """word 받침에 맞게 조사 고침(받침 있으면 앞쪽 꼴)"""
    for a, b in JOSA:
        if josa in (a, b):
            return a if batchim(word) and not (a == '으로' and word[-1] in '을를') else b
    return josa


NEUTRAL = ['한테라면', '한테는', '한테도', '에게는', '에게도', '의', '에', '에서', '에게', '한테', '도', '만', '까지', '부터', '보다', '처럼', '같이', '하고', '께', '께서', '씨', '님', '들']   # 받침과 상관없는 조사


def replace_term(t, bad, good):
    """bad 를 낱말로만(앞이 한글이 아님, 뒤는 조사 또는 한글 아님) 바꾸고 뒤 조사를 받침에 맞춤"""
    if batchim(bad) == batchim(good) and ' ' not in bad:     # 받침 같으면 뒤에 뭐가 붙든 조사·어미가 안 바뀜(숙사구나→숙소구나)
        return re.sub(r'(?<![%s])%s' % (HANGUL, re.escape(bad)), good, t)
    js = '|'.join(sorted({x for p in JOSA for x in p} | set(NEUTRAL), key=len, reverse=True))
    pat = re.compile(r'(?<![%s])%s(%s)?(?![%s])' % (HANGUL, re.escape(bad), js, HANGUL))
    def rep(m):
        j = m.group(1) or ''
        if j in ('야', '아') and batchim(good) != batchim(bad):
            return m.group(0)                      # 부름(아루야→알)·서술(아루야→알이야) 구분 불가 → 그대로, 검사에서 보고
        return good + (fix_josa(good, j) if j and j not in NEUTRAL else j)
    return pat.sub(rep, t)


def read_missing():
    out = {}
    for fn in ('빠진거.txt', '빠진거2.txt'):
        p = os.path.join(SRC, fn)
        if not os.path.exists(p):
            continue
        s = open(p, encoding='utf-8-sig').read().replace('\r', ' ').replace('\n', ' ')
        parts = re.split(r'(?:^|\s)(\d{5})[}\s]', s)          # «06798} 꽉-» 처럼 번호 뒤 } 도
        for k, v in zip(parts[1::2], parts[2::2]):
            v = re.sub(r'^D\d:\S+\s+\d+\s+\S+\s+', '', v.strip())          # 「번호 위치 개수 종류 번역」 꼴
            v = re.sub(r'^\[(.+?)\]\s*', r'【\1】', v)                       # [알] → 【알】
            m = re.search(r'【[가-힣][^】]*】', v)                               # «원문 일본어 + 한국어» 덩어리면 한국어 화자부터
            if re.match(r'【[^】]*[ァ-ヺ][^】]*】', v) and m:
                v = v[m.start():]
            out.setdefault(k, v)
    return out


def read_fixes():
    fx = {}; first = set()
    files = [FIXES] + sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'fixes', 'fix_*.tsv')))   # 통독 결과는 파일별
    for p in files:
        if not os.path.exists(p):
            continue
        for ln in open(p, encoding='utf-8-sig').read().splitlines()[1:]:
            if ln.strip() and not ln.startswith('#'):
                k, new, why = (ln.split('\t') + ['', ''])[:3]
                assert k not in fx or k in first or os.path.basename(p) == 'fix_zz_fit.tsv', '같은 번호 두 번: ' + k   # 1차(ds_fixes) 줄은 통독 결과가, 통독 결과는 상자 맞춤(fix_zz_fit)이 덮어씀
                if k in fx:
                    why = fx[k][1] + ' · ' + why; first.discard(k)
                fx[k] = (new, why)
                if p == FIXES:
                    first.add(k)
    return fx


def speaker(t):
    m = SPK.match(t)
    if not m:
        return None
    return (m.group(1), m.group(3) if m.group(3) is not None else m.group(4), m.group(2)[0] == '【')


def restore_speaker(src, kr):
    s = speaker(src)
    if not s:
        return kr, None
    lead, name, bracket = s
    kname = NAMES.get(name)
    if kname is None:
        return kr, '화자 표 없음: ' + name
    tag = ('【%s】' if bracket else '{E985}%s{E986}') % kname
    k = speaker(kr)
    body = kr[len(k[0]) + len(SPK.match(kr).group(2)):] if k else kr[len(lead):] if kr.startswith(lead) else kr
    new = lead + tag + body
    return new, None


def quotes(src, kr):
    if '「' in src and '「' not in kr:
        kr = re.sub(r'["“]([^"”]*)["”]', r'「\1」', kr)
    return kr


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    miss, fx = read_missing(), read_fixes()
    os.makedirs(OUT, exist_ok=True)
    log = ['번호\t원문\t전\t후\t이유']
    prob = collections.Counter(); bad = []
    seen = set(); nrow = 0
    for f in sorted(glob.glob(os.path.join(SRC, 'desire_*.tsv'))):
        n = re.search(r'desire_(\d+)', os.path.basename(f)).group(1)
        lines = open(f, encoding='utf-8-sig').read().split('\n')
        out = [lines[0]]
        for ln in lines[1:]:
            c = ln.rstrip('\r').split('\t')
            if len(c) < 5:
                if ln.strip():
                    out.append(ln)
                continue
            while len(c) < 6:
                c.append('')
            k, src, before = c[0], c[4], c[5]
            nrow += 1
            t, why = before, []
            if not t.strip() and k in miss:
                t = miss[k]; why.append('빠진거 파일로 채움')
            if k in fx:
                t = fx[k][0]; why.append(fx[k][1]); seen.add(k)
            if t.strip():
                t2, err = restore_speaker(src, t)
                if err:
                    bad.append((k, err))
                if t2 != t:
                    t = t2; why.append('화자 표시')
                for a, b in TERMS:
                    t2 = replace_term(t, a, b)
                    if t2 != t:
                        t = t2; why.append('표기 통일 %s→%s' % (a, b))
                if 'ドクター' in src and not re.search('取得|保有', src):      # 게이츠 호칭 = 닥터(학위는 그대로)
                    t2 = re.sub(r'게이츠\s*박사님?', '닥터 게이츠', t)
                    t2 = replace_term(t2, '닥터 게이츠', '닥터 게이츠')                  # 뒤 조사 받침 맞춤
                    for a in (['의사 선생님', '박사님', '박사'] + ([] if '先生' in src else ['선생님'])):
                        t2 = replace_term(t2, a, '닥터')
                    t2 = re.sub(r'(?<![가-힣])[박선서의], ?(?=닥터)', '닥, ', t2)          # 더듬기 «박, 박사님»·«서, 선생님»→«닥, 닥터»
                    if t2 != t:
                        t = t2; why.append('호칭 통일 ドクター=닥터')
                for jp, a, b in CTX_TERMS:
                    if jp in src and a in t:
                        t = t.replace(a, b); why.append('번역어 %s→%s' % (a, b))
                t2 = re.sub(r'(?<=[가-힣])[ーㅡ]+', '～', t)   # 한글 뒤 장음 부호(알ー！·알ㅡ!!) → 물결
                if t2 != t:
                    t = t2; why.append('장음 ー→～')
                t2 = re.sub(r'^(【[^】]+】)대사 \1', r'\1', t)                       # «【알】대사 【알】…» 겹친 화자
                if not re.match(r'^(【[^】]+】|\{E985\}[^{]*\{E986\})[ 　]', src):
                    t2 = re.sub(r'^(【[^】]+】|\{E985\}[^{]*\{E986\})[ 　]+', r'\1', t2)    # 화자 뒤 공백(전각이 되어 들여쓰기·2 B)
                if not re.search(r'[ 　]\{n00\}|\{n00\}[ 　]', src):
                    t2 = re.sub(r' *\{n00\} *', '{n00}', t2)                                  # 줄바꿈 앞뒤 공백(줄 머리 들여쓰기·2 B)
                t2 = re.sub(r'[―─—]+', '～', t2).replace('·', '・')                   # 글꼴에 없는 줄표·가운뎃점
                t2 = re.sub(r'\.{2,}', '‥‥', t2)                                       # 반각 «...» → 빌더에서 «．．．»가 됨
                t2 = re.sub(r'・{2,}', lambda m: '‥' * max(2, (len(m.group()) + 1) // 2), t2)   # «・・・・» 줄임표 → 원문식 ‥‥
                t2 = re.sub(r'(?<=‥)・(?!・)', '', t2)                                     # «‥‥・» 줄임표 끝에 남은 점 하나
                q = '『』' if '『' in src else '「」'
                t2 = re.sub(r"['‘’]([^'‘’]*)['‘’]", lambda m: q[0] + m.group(1) + q[1], t2)   # 작은따옴표 글리프 없음 → 낫표
                if t2 != t:
                    t = t2; why.append('글꼴 없는 부호·겹친 화자')
                if src.startswith('　') and not t.startswith('　') and not t.startswith('{'):   # 선택지 앞 전각 공백
                    t = '　' + t.lstrip(' '); why.append('선택지 앞 전각 공백')
                t2 = quotes(src, t)
                if t2 != t:
                    t = t2; why.append('「」 되살림')
                if [x for x in TOK.findall(src) if (not x.startswith('{E98') or x in ('{E985}', '{E986}'))] != [x for x in TOK.findall(t) if (not x.startswith('{E98') or x in ('{E985}', '{E986}'))]:
                    prob['토큰 차례 다름'] += 1; bad.append((k, '토큰 ' + ' '.join(TOK.findall(src)) + ' / ' + ' '.join(TOK.findall(t))))
                for a, b in TERMS:
                    if re.search(r'(?<![%s])%s[\uc57c\uc544](?![%s])' % (HANGUL, re.escape(a), HANGUL), t):
                        prob['\uc774\ub984+\uc57c \ud655\uc778'] += 1; bad.append((k, '\uc774\ub984+\uc57c \ud655\uc778(%s\u2192%s): %s' % (a, b, t)))
                if re.search('[\u3040-\u30fa\u30fd-\u30ff]', re.sub(r'\{[^}]*\}', '', t)):     # \u30fb\u30fc \ub294 \ube7c\uace0
                    prob['가나 남음'] += 1; bad.append((k, '가나: ' + t))
            else:
                prob['빈 번역'] += 1; bad.append((k, '빈 번역: ' + src))
            if t != before:
                c[5] = t
                log.append('\t'.join((k, src, before, t, ' / '.join(dict.fromkeys(why)))))
            out.append('\t'.join(c))
        open(os.path.join(OUT, 'desire_ko_%s.tsv' % n), 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
    assert not (set(fx) - seen), '없는 번호의 교정: %s' % sorted(set(fx) - seen)[:10]
    open(LOG, 'w', encoding='utf-8', newline='\n').write('\n'.join(log) + '\n')
    open(os.path.join(ROOT, 'work', 'text', 'ds_problems.tsv'), 'w', encoding='utf-8', newline='\n').write(
        '\n'.join('%s\t%s' % b for b in bad) + '\n')
    print('줄 %d · 바뀐 줄 %d · 남은 문제 %s → work/text/ds_problems.tsv' % (nrow, len(log) - 1, dict(prob)))


if __name__ == '__main__':
    main()
