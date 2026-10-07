# -*- coding: utf-8 -*-
r"""대사 상자 조판 모델 (2026-10-07) — 엔진 0x06008316 그대로
  상자: left 0x64 · right 0x129 · 줄 16 px · 3줄. 글자 그리기 전 x + 16 ≥ right 이면 줄바꿈 — 단 걸침 문자(분기표 0x06008340 = 0x82)는 안 바꿈.
  걸침 문자 = «　、。，．・？！ー～）〕］》」』】» (‥ 는 아님 → 줄바꿈 대상).
  ★반칸 공백(tools/pagehook.py 훅): 전각 공백은 줄 맨 앞이 아니면 8 px 만 나아간다.
  화자 표시(【이름】·{E985}이름{E986})는 상자에 안 그려짐(얼굴 그림)."""
import re

LEFT, RIGHT, LINES = 0x64, 0x129, 3
HANG = set('　、。，．・？！ー～）〕］》」』】')
SPK = re.compile(r'^((?:\{[^}]*\})*)(【[^】]*】|\{E985\}.*?\{E986\})')


def layout(t, half=True):
    """정규화된 번역(전각) → 상자 줄 목록"""
    t = SPK.sub(r'\1', t)
    lines = []
    for seg in re.split(r'\{n00\}', t):
        seg = re.sub(r'\{[^}]*\}', '', seg)
        cur = ''; x = LEFT
        for ch in seg:
            if x + 16 >= RIGHT and ch not in HANG:
                lines.append(cur); cur = ''; x = LEFT
            cur += ch
            x += 8 if (half and ch == '　' and x != LEFT) else 16
        lines.append(cur)
    return lines


SMALL = set('、。，．・')                # 칸 왼쪽 아래에 작게 그려지는 걸침 문자 — 13번째 칸(x 284‥)에 걸려도 상자 안
VIS = LEFT + 12 * 16                     # 보이는 오른쪽 끝 292(원문은 이 안에서만 그림)


def spill(t, half=True):
    """상자 오른쪽 밖으로 삐져나가는 글자(？！～」 등이 줄 끝 걸침으로 x+16 > 292)"""
    t = SPK.sub(r'\1', t); out = []
    for seg in re.split(r'\{n00\}', t):
        seg = re.sub(r'\{[^}]*\}', '', seg); x = LEFT
        for ch in seg:
            if x + 16 >= RIGHT and ch not in HANG:
                x = LEFT
            if x + 16 > VIS and ch not in SMALL and ch != '　':
                out.append(ch)
            x += 8 if (half and ch == '　' and x != LEFT) else 16
    return out


def overflow(t, half=True):
    """넘치는 줄 수 + 오른쪽으로 삐져나간 글자 수(0 = 들어감)"""
    return max(0, len(layout(t, half)) - LINES) + len(spill(t, half))


def autofix(t, half=True):
    """삐져나가는 부호가 있으면 그 줄의 마지막 띄어쓰기를 {n00} 로 바꿔 마지막 낱말째 다음 줄로(빌더가 쓰는 순간 적용).
    → (새 글, 성공 여부). 3줄 안에 못 넣으면 원래 글과 False"""
    cur = t
    for _ in range(4):
        sp = spill(cur, half)
        if not sp:
            return cur, len(layout(cur, half)) <= LINES
        # 첫 삐짐이 있는 줄을 찾아, 그 줄 안 마지막 전각 공백 위치(원문 인덱스)를 구한다
        m = SPK.match(cur); i = m.end() if m else 0
        x = LEFT; line_sp = None; done = False
        while i < len(cur):
            if cur[i] == '{':
                j = cur.index('}', i) + 1
                if cur[i:j] == '{n00}':
                    x = LEFT; line_sp = None
                i = j; continue
            ch = cur[i]
            if x + 16 >= RIGHT and ch not in HANG:
                x = LEFT; line_sp = None
            if x + 16 > VIS and ch not in SMALL and ch != '　':
                done = True; break
            if ch == '　' and x != LEFT:
                line_sp = i
            x += 8 if (half and ch == '　' and x != LEFT) else 16
            i += 1
        if not done or line_sp is None:
            return t, False
        cur = cur[:line_sp] + '{n00}' + cur[line_sp + 1:]
    return t, False
