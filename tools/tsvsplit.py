# -*- coding: utf-8 -*-
r"""번역용 고유 문장 표 (2026-10-04 밤) — work/text/scn_d1.tsv·scn_d2.tsv(위치별) → 같은 원문은 한 줄로
  work/text/desire.tsv (번호 · 첫 위치 · 개수 · 종류 · 원문 · 번역) + work/text/split/desire_NNN.tsv(UTF-8 29KB 단위, 자투리 합침)
  원문 표기: {n00} 등 = 글 안 제어(영문자+1바이트: n=줄바꿈·s=멈춤 추정 — 번역에서도 그대로 둘 것) · {E980}‥{E986} = 전용 그림 글자(E985/E986 = 이름 괄호 【】)
  python tools/tsvsplit.py"""
import collections, glob, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
T = os.path.join(ROOT, 'work', 'text')
HEAD = '#번호\t첫 위치\t개수\t종류\t원문\t번역\n'
LIMIT = 29 * 1024


def main():
    seen = collections.OrderedDict()
    for p in sorted(glob.glob(os.path.join(T, 'scn_d[12].tsv'))):
        for l in open(p, encoding='utf-8'):
            if l.startswith('#'):
                continue
            f = l.rstrip('\n').split('\t')
            key = f[5]
            if key not in seen:
                seen[key] = ['%s:%s:%s' % (f[0].split('-')[0], f[1], f[2]), 0, set()]
            seen[key][1] += 1; seen[key][2].add('선택지' if f[4] == '02' else '대사')
    lines = ['%05d\t%s\t%d\t%s\t%s\t' % (k + 1, v[0], v[1], '·'.join(sorted(v[2])), t) for k, (t, v) in enumerate(seen.items())]
    open(os.path.join(T, 'desire.tsv'), 'w', encoding='utf-8', newline='\n').write(HEAD + '\n'.join(lines) + '\n')
    out = os.path.join(T, 'split'); os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, 'desire_*.tsv')):
        os.remove(f)
    chunks = [[]]; size = len(HEAD.encode('utf-8'))
    for l in lines:
        b = len((l + '\n').encode('utf-8'))
        if size + b > LIMIT and chunks[-1]:
            chunks.append([]); size = len(HEAD.encode('utf-8'))
        chunks[-1].append(l); size += b
    for i, c in enumerate(chunks):
        open(os.path.join(out, 'desire_%03d.tsv' % (i + 1)), 'w', encoding='utf-8', newline='\n').write(HEAD + '\n'.join(c) + '\n')
    chars = sum(len(t) for t in seen)
    print('고유 문장 %d (전체 위치 %d) · 원문 약 %d자 · 분할 %d개 → %s' % (len(seen), sum(v[1] for v in seen.values()), chars, len(chunks), out))


if __name__ == '__main__':
    main()
