# -*- coding: utf-8 -*-
r"""대사 상자 쪽 넘김 훅 (2026-10-07) — 00DESIRE.BIN(적재 0x06004000)
  대사 출력 0x060080C8: r12 = 글자 x · r13 = y · @(56,r14) = 대사 기록(백로그 0x00215000) 모드 — 상자(left 0x64·top 0x9E)일 때 1.
  줄바꿈은 두 곳 — 자동 줄바꿈 0x060083B6(x = [0x0602DE74], y += 16) · {n00} 0x060086A4(같은 일 + 밀어 올리기 모드면 0x060086BA).
  상자(left [0x0602DE74] = 0x64 · top [0x0602DE76] = 0x9E, 스테이트 5 확인)에는 4번째 줄 처리가 없어 상자 밖으로 그려진다(원문 최대 38자).
  ⚠1차(2026-10-07)는 top 0x9A·@56 = 0 조건으로 잘못 걸어 한 번도 안 돌았음(초기값 0x62/0x9A 는 다른 화면).
  → 두 곳 모두 훅으로: x·y 를 원래대로 바꾸고, 상자 모드이고 y ≥ top + 48(4번째 줄)이면
     {s00} 처리(0x06008730)와 같은 버튼 대기 고리 → 그려 둔 글자 목록 개수 [0x06035EC0](u16) = 0 → y = top.
  훅 자리 0x0602ED00: 0x0602EC90‥0x0602F690 의 0 구역(참조 0 · 스테이트 1·3·4·5 모두 0).
  ⛔{s00} 는 «버튼 대기 + 다음 음성 조각»(@36 개수·@40 포인터) — 쪽 나눔에 쓰면 음성이 어긋난다.
  ★반칸 공백 훅 0x0602EE00(2026-10-07 사용자 «반각에 다듬기»): 줄바꿈 검사 0x06008316 에서 전각 공백(줄 맨 앞 제외) x −8.
  조판 검사 모델 = tools/boxfit.py (빌더가 넘침 줄을 막는다).
  ★선택지 반칸 공백 훅 0x0602EF00(2026-10-07): 선택지 0x060089B0 은 공백을 폭 0·안 그림 → 첫머리 아닌 공백 8 px. 배치 검사 = tools/choicefit.py."""
import struct

LOAD = 0x06004000
HOOK = 0x0602ED00
HOOK2 = 0x0602EE00                     # 반칸 공백
HOOK3 = 0x0602EF00                     # 선택지 반칸 공백


def _asm_page():
    prog = [
        (0x4F22,), (0x2F86,),                                  # sts.l pr,@-r15 · mov.l r8,@-r15
        ('l', 1, 'left'), (0x6111,), (0x6C1D,),                # r12 = [left]
        (0x7D10,), (0x6DDD,),                                  # r13 += 16
        (0xE364,), (0x3C30,), ('bf', 'done'),                  # 상자 모드(left 0x64)만
        ('l', 1, 'top'), (0x6211,), (0x622D,),                 # r2 = [top]
        ('w', 3, 'w9e'), (0x3230,), ('bf', 'done'),            # 상자 모드(top 0x9E)만
        (0x6823,), (0x7230,), (0x3D23,), ('bf', 'done'),       # r8 = top · r13 ≥ top + 48 ?
        'wait',
        ('l', 0, 'f131d4'), (0x400B,), (0xE401,), (0x2008,), ('bt', 'clear'),
        ('l', 0, 'ffa14'), (0x400B,), (0x0009,),
        ('w', 4, 'w400'), ('l', 0, 'ffbec'), (0x400B,), (0x0009,), (0x2008,), ('bf', 'clear'),
        ('w', 4, 'w200'), ('l', 0, 'ffbec'), (0x400B,), (0x0009,), (0x2008,), ('bf', 'clear'),
        ('l', 0, 'ffc24'), (0x400B,), (0xE408,), (0x2008,), ('bt', 'wait'),
        'clear',
        ('l', 1, 'cnt'), (0xE000,), (0x2101,), (0x6D83,),      # 글자 목록 비움 · y = top
        'done',
        (0x68F6,), (0x4F26,), (0x000B,), (0x0009,),
    ]
    words = {'w400': 0x0400, 'w200': 0x0200, 'w9e': 0x009E}
    longs = {'left': 0x0602DE74, 'top': 0x0602DE76, 'f131d4': 0x060131D4, 'ffa14': 0x0600FA14,
             'ffbec': 0x0600FBEC, 'ffc24': 0x0600FC24, 'cnt': 0x06035EC0}
    return _asm(HOOK, prog, words, longs)


def _asm_space():
    """0x06008316 줄바꿈 검사 직전(r9 = 글자 · r12 = x): 전각 공백이고 줄 맨 앞이 아니면 x -= 8(그려진 뒤 +16 → 8 px).
    원래 하던 일 r1 = [right] · r2 = x + 16 을 돌려준다(뒤 cmp/ge r1,r2 그대로)."""
    prog = [
        ('l', 0, 'sp'), (0x3090,), ('bf', 'x'),               # r9 == 0x8140 ?
        ('l', 1, 'left'), (0x6111,), (0x611D,), (0x3C10,), ('bt', 'x'),   # 줄 맨 앞이면 그대로
        (0x7CF8,),                                             # x -= 8
        'x',
        ('l', 1, 'right'), (0x6111,), (0x611D,), (0x62C3,), (0x7210,),
        (0x000B,), (0x0009,),
    ]
    return _asm(HOOK2, prog, {}, {'sp': 0x00008140, 'left': 0x0602DE74, 'right': 0x06035EC2})


def _asm_choice():
    """선택지 0x060089B0 의 두 고리(r1 = 글자)가 같은 리터럴 0x06008C00(원래 0x8140)으로 부른다 — pr 로 구별.
      폭 재기(돌아갈 곳 0x06008A66, r5 = 폭): 공백 아니면 +16 · 공백이면 앞에 글자가 있을 때만 +8
      그리기(돌아갈 곳 0x06008B2C, r4 = x · r8 = 항목 시작 x): 공백 아니면 그대로 그리러 · 공백이면 첫머리 아닐 때 x += 8 하고 0x06008B62(건너뜀)로
    ⛔원래는 공백을 폭 0·안 그림 → 띄어쓰기가 붙어 나옴(2026-10-07 «취재허가에대해»). 맨 앞 공백은 원래대로 0."""
    prog = [
        (0x002A,), ('l', 2, 'ra_m'), (0x3200,), ('bf', 'draw'),    # sts pr,r0 · r2 = 0x06008A66 · cmp/eq r0,r2
        ('l', 0, 'sp'), (0x3100,), ('bt', 'msp'),                  # 폭 재기: 공백?
        (0x000B,), (0x7510,),                                      # rts · add #16,r5
        'msp',
        (0x2558,), ('bt', 'mret'), (0x7508,),                      # tst r5,r5 · (앞에 글자 있으면) add #8,r5
        'mret',
        (0x000B,), (0x0009,),
        'draw',
        ('l', 0, 'sp'), (0x3100,), ('bf', 'dret'),                 # 그리기: 공백 아니면 그대로
        (0x3840,), ('bt', 'dskip'), (0x7408,),                     # cmp/eq r4,r8 · (첫머리 아니면) add #8,r4
        'dskip',
        ('l', 0, 'skip'), (0x402A,),                               # lds r0,pr → 0x06008B62
        'dret',
        (0x000B,), (0x0009,),
    ]
    return _asm(HOOK3, prog, {}, {'ra_m': 0x06008A66, 'sp': 0x00008140, 'skip': 0x06008B62})


def _asm(org, prog, words, longs):
    """명령 = (코드,) · ('bt'/'bf', 표지) · ('l', 레지스터, 표지) = mov.l · ('w', 레지스터, 표지) = mov.w · 문자열 = 표지"""
    L = {}
    pc = org
    for p in prog:
        if isinstance(p, str):
            L[p] = pc
        else:
            pc += 2
    for k in words:
        L[k] = pc; pc += 2
    pc = (pc + 3) & ~3
    for k in longs:
        L[k] = pc; pc += 4
    out = bytearray(); pc = org
    for p in prog:
        if isinstance(p, str):
            continue
        if len(p) == 1:
            w = p[0]
        elif p[0] in ('bt', 'bf'):
            d = (L[p[1]] - (pc + 4)) // 2
            assert -128 <= d < 128
            w = (0x8900 if p[0] == 'bt' else 0x8B00) | (d & 0xFF)
        elif p[0] == 'l':
            d = (L[p[2]] - ((pc & ~3) + 4)) // 4
            assert 0 <= d < 256 and L[p[2]] % 4 == 0
            w = 0xD000 | (p[1] << 8) | d
        else:
            d = (L[p[2]] - (pc + 4)) // 2
            assert 0 <= d < 256
            w = 0x9000 | (p[1] << 8) | d
        out += struct.pack('>H', w); pc += 2
    for k, v in words.items():
        out += struct.pack('>H', v)
    while len(out) % 4:
        out += b'\0\x09'[:4 - len(out) % 4] if False else b'\0'
    for k, v in longs.items():
        out += struct.pack('>I', v)
    return bytes(out)


# 고칠 자리: (주소, 원래 바이트, 새 바이트)
SITES = [
    # 자동 줄바꿈: mov.l @(lit),r1 · mov.w @r1,r1 · extu.w r1,r12 · mov r13,r1 · add #16,r1 · extu.w r1,r13 → mov.l(그대로) · jsr @r1 · nop×4
    (0x060083B6, bytes.fromhex('D1786111 6C1D61D3 71106D1D'.replace(' ', '')), bytes.fromhex('D178410B 00090009 00090009'.replace(' ', ''))),
    (0x06008598, bytes.fromhex('0602DE74'), struct.pack('>I', HOOK)),
    # {n00}: mov.l · mov.w · mov.l @(56,r14),r0 · extu · mov · add · tst · bf/s · extu → mov.l · jsr · nop · mov.l @(56,r14),r0 · tst · bf/s · nop · nop · nop
    (0x060086A4, bytes.fromhex('D11A6111 50EE6C1D 61D37110 20088F02 6D1D'.replace(' ', '')),
                 bytes.fromhex('D11A410B 000950EE 20088F04 00090009 0009'.replace(' ', ''))),
    (0x06008710, bytes.fromhex('0602DE74'), struct.pack('>I', HOOK)),
    # 글자마다 줄바꿈 검사: mov r12,r2 · mov.l @(lit),r1 · mov.w @r1,r1 · add #16,r2 · extu.w r1,r1 → mov.l @(같은 lit),r1 · jsr @r1 · nop×3
    (0x06008316, bytes.fromhex('62C3D19D 61117210 611D'.replace(' ', '')), bytes.fromhex('D19E410B 00090009 0009'.replace(' ', ''))),
    (0x06008590, bytes.fromhex('06035EC2'), struct.pack('>I', HOOK2)),
    # 선택지 폭 재기: mov.l @(lit),r0 · cmp/eq r0,r1 · bt · add #16,r5 → mov.l(그대로) · jsr @r0 · nop · nop
    (0x06008A60, bytes.fromhex('D0673100 89007510'), bytes.fromhex('D067400B 00090009')),
    # 선택지 그리기: mov.l @(lit),r0 · cmp/eq r0,r1 · bt 0x06008B62 → mov.l(그대로) · jsr @r0 · nop
    (0x06008B26, bytes.fromhex('D0363100 891A'), bytes.fromhex('D036400B 0009')),
    (0x06008C00, bytes.fromhex('00008140'), struct.pack('>I', HOOK3)),       # 이 리터럴은 위 두 곳만 읽음
]


def apply(exe):
    exe = bytearray(exe)
    for org, code in ((HOOK, _asm_page()), (HOOK2, _asm_space()), (HOOK3, _asm_choice())):
        o = org - LOAD
        assert exe[o:o + len(code)] == bytes(len(code)), '훅 자리가 비어 있지 않음'
        exe[o:o + len(code)] = code
    for a, old, new in SITES:
        o = a - LOAD
        assert exe[o:o + len(old)] == old, ('원래 바이트 다름', hex(a))
        assert len(old) == len(new)
        exe[o:o + len(new)] = new
    return bytes(exe)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, __import__('os').path.dirname(__file__))
    sys.stdout.reconfigure(encoding='utf-8')
    import disc, sh2dis
    e = disc.read(1, '00DESIRE.BIN'); n = apply(e)
    print('\n'.join(sh2dis.dis(n, LOAD, HOOK, 70)))
    for a, _, new in SITES:
        if len(new) > 4:
            print('\n'.join(sh2dis.dis(n, LOAD, a, len(new) // 2 + 2)))
