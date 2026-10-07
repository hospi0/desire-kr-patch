# -*- coding: utf-8 -*-
r"""b1 그림 글자 한글화 (2026-10-07) — tools/b1.py 로 풀고, 글자 자리를 지우고 한글을 그려 다시 쌓음
  python tools/b1text.py [--preview]  → work/b1/kr/<항목>.b1 (+ 미리보기 PNG)"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import b1, mix
FONTS = {'myeongjo': r'C:\claude\utils\font\nanum-myeongjo\NanumMyeongjoBold.ttf',
         'gothic': r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'}
OUT = os.path.join(ROOT, 'work', 'b1', 'kr')
S = 4                                                         # 미세 표본(안티에일리어싱)


def draw_text(rgb, box, lines, font='myeongjo', px=12, color=(248, 248, 248), bg=None, align='center', gap=None):
    """rgb(h×w×3) 의 box(x0,y0,x1,y1) 를 bg 로 지우고 lines 를 그림. px = 한글 높이(픽셀)"""
    x0, y0, x1, y1 = box; W, H = x1 - x0, y1 - y0
    if bg is not None:
        rgb[y0:y1, x0:x1] = bg
    base = rgb[y0:y1, x0:x1].astype(np.float32)
    f = ImageFont.truetype(FONTS[font], int(px * S * 1.12))
    im = Image.new('L', (W * S, H * S), 0); dr = ImageDraw.Draw(im)
    gap = px + 2 if gap is None else gap
    tot = gap * (len(lines) - 1) + px
    for k, ln in enumerate(lines):
        l, t, r, b = dr.textbbox((0, 0), '가', font=f)                # 기준 = 한글 높이
        cy = (H - tot) / 2 + k * gap + px / 2
        tw = dr.textlength(ln, font=f)
        x = (W * S - tw) / 2 if align == 'center' else 0
        dr.text((x, cy * S - (t + b) / 2), ln, font=f, fill=255)
    a = np.asarray(im, np.float32).reshape(H, S, W, S).mean((1, 3))[..., None] / 255
    rgb[y0:y1, x0:x1] = (a * np.array(color, np.float32) + (1 - a) * base).round().astype(np.uint8)


# 항목 번호: (상자, 줄들, 옵션)
OPENING = {
    42: ['사람은 어디에서 와서 어디로 가는 걸까‥‥.'],
    44: ['이 영원한 나선에서 구해 줄 사람은, 누구?'],
    46: ['나를 구해 줄, 그 사람은‥‥‥‥.'],
}


def build_opening(its):
    out = {}
    for n, lines in OPENING.items():
        w, h, im = b1.decode(mix.read(1, its[n]))
        rgb = b1.to_rgb(im)
        draw_text(rgb, (0, 0, w, h), lines, 'myeongjo', 12, (248, 248, 248), bg=(0, 0, 0))
        out[n] = rgb
    return out


def save(res):
    os.makedirs(OUT, exist_ok=True); data = {}
    for n, rgb in res.items():
        e = b1.encode(b1.from_rgb(rgb)); data[n] = e
        open(os.path.join(OUT, '%04d.b1' % n), 'wb').write(e)
        Image.fromarray(b1.to_rgb(b1.decode(e)[2])).save(os.path.join(OUT, '%04d.png' % n))
    return data


# ── 인물 카드(224×120) ─────────────────────────────────────────────────
LABELS = ['본명', '', '출신지', '나이', '키', '몸무게', '국적', '비고', '']
CARDS = {   # 항목: [본명1, 본명2, 출신지, 나이, 키, 몸무게, 국적, 비고1, 비고2]
    1520: ['마코토 이즈미', '', '일본', '24세', '161센티', '46킬로', '미국', '미혼', ''],
    1523: ['레이코 쿠사나기', '', '미국', '25세', '170센티', '51킬로', '미국', '미혼', ''],
    1526: ['실비아', '브라더', '영국', '22세', '166센티', '49킬로', '영국', '미혼', ''],
    1529: ['카즈미 M.', '그랜체스터', '영국', '23세', '168센티', '48킬로', '영국', '미혼', ''],
    1532: ['크리스티', '셰퍼드', '캐나다', '28세', '169센티', '51킬로', '영국', '이혼 경력 있음.', ''],
    1535: ['셰릴', '샤트레트', '브라질', '22세', '159센티', '44킬로', '브라질', '미혼', ''],
    1538: ['카일 K.', '커츠', '미국', '26세', '188센티', '90킬로', '미국', '미혼', ''],
    1541: ['엘레나', '프랑수아', '프랑스', '18세', '161센티', '43킬로', '러시아', '미혼', ''],
    1544: ['마르티나 T.', '스텔라도비치', '미상', '미상', '173센티', '52킬로', '러시아', '생년월일 미상', '기혼, 단 사별'],
    1547: ['구스타프 G.', '스텔라도비치', '러시아', '', '180센티', '80킬로', '러시아', '사망 시 데이터', ''],
    1550: ['티나', '스텔라도비치', '러시아', '', '145센티', '35킬로', '러시아', '사망 시 데이터', ''],
    1553: ['알버트', '맥두걸', '미국', '24세', '178센티', '70킬로', '미국', '미혼', ''],
}
CARD_TOP, CARD_PITCH = 5, 12
CARD_COLS = [(58, 97), (99, 197)]                             # 항목 · 값 (x 97 = 칸 줄)


def card_text(rgb, x0, x1, yc, text, px=11):
    """짝수 줄에만 진하게(원본 줄무늬 방식). 바탕은 줄마다 원래 색"""
    if not text:
        return
    W = x1 - x0; y0 = int(yc - 7); H = 14
    f = ImageFont.truetype(FONTS['myeongjo'], int(px * S * 1.12))
    im = Image.new('L', (W * S, H * S), 0); dr = ImageDraw.Draw(im)
    l, t, r, b = dr.textbbox((0, 0), '가', font=f)
    dr.text((1 * S, (H * S - (t + b)) / 2), text, font=f, fill=255)
    a = np.asarray(im, np.float32).reshape(H, S, W, S).mean((1, 3)) / 255
    for yy in range(H):
        y = y0 + yy
        ink = np.array([56, 56, 56] if y % 2 == 0 else [104, 104, 104], np.float32)   # 원본: 짝수 줄 40‥80 · 홀수 줄 90‥120
        row = rgb[y, x0:x1].astype(np.float32)
        aa = np.clip(a[yy] * 1.4, 0, 1)[:, None]
        rgb[y, x0:x1] = (aa * ink + (1 - aa) * row).round().astype(np.uint8)


def build_cards(its):
    import collections
    out = {}
    for n, vals in CARDS.items():
        w, h, im = b1.decode(mix.read(1, its[n])); rgb = b1.to_rgb(im)
        for (x0, x1) in CARD_COLS:                            # 글자 지우기: 줄마다 가장 흔한 색
            for y in range(CARD_TOP, CARD_TOP + CARD_PITCH * 9 + 2):
                c = collections.Counter(map(tuple, rgb[y, 58:197][:, :3])).most_common(1)[0][0]
                rgb[y, x0:x1] = c
        for i in range(9):
            yc = CARD_TOP + CARD_PITCH * i + 6
            card_text(rgb, 58, 97, yc, LABELS[i])
            card_text(rgb, 99, 197, yc, vals[i])
        out[n] = rgb
    return out


# ── 세이브·디스크 안내 ─────────────────────────────────────────────────
SYSMSG = {
    8237: ['본체 RAM의 백업', '준비가 아직 되지 않았습니다.', '(초기화되지 않았습니다.)'],
    8238: ['카트리지 RAM의 백업', '준비가 아직 되지 않았습니다.', '(초기화되지 않았습니다.)'],
    8239: ['세가새턴 본체의', '저장 데이터 관리 화면에서,', '모든 기록을 지워 주세요.', '(초기화해 주세요.)'],
    8240: ['L 버튼 또는 R 버튼을', '누른 채로 리셋 버튼을 누르면,', '세가새턴 본체의', '저장 데이터 관리 화면으로 넘어갑니다.'],
    8241: ['기록을 저장하기 위한', '빈 용량이 없습니다.', '이대로 게임을 시작하면,', '기록을 저장할 수 없습니다.', '또한, 중간까지밖에', '플레이할 수 없습니다.', '그래도 게임을 시작하겠습니까?'],
    8242: ['이 게임의 기록을', '저장하려면', '39의 빈 용량이 필요합니다'],
    8243: ['세가새턴 본체의', '저장 데이터 관리 화면에서,', '다른 게임의 기록을 지우거나,', '카트리지 RAM에 복사한 뒤,', '게임을 다시 시작해 주세요.'],
    8244: ['본체 RAM과 카트리지 RAM 중', '어느 쪽 기록을 사용하겠습니까?'],
    8245: ['본체 RAM     or     카트리지 RAM'],
    8246: ['본체 RAM의 기록을', '제대로 읽어 들이지', '못했습니다.', '이 기록은 사용할 수 없습니다.'],
    8247: ['카트리지 RAM의 기록을', '제대로 읽어 들이지', '못했습니다.', '이 기록은 사용할 수 없습니다.'],
    8248: ['기록을 제대로 저장하지', '못했습니다.', '다시 한번 해 주세요.'],
    8249: ['본체 RAM의 빈 용량이 부족하므로,', '카트리지 RAM을 사용합니다.'],
}
DISCMSG = {
    8210: ['DISC2로 진행할 수 있게 되었습니다', 'DISC2로 진행하려면 새턴 본체의', '오픈 버튼을 눌러 멀티', '플레이어 화면으로 가 주세요', '그 뒤 DISC1과 DISC2를 바꿔 넣고', '본체 CD 도어를 닫은 뒤', '게임을 시작해 주세요', 'DISC2로 진행하지 않으려면', 'C 버튼을 누르면 타이틀로 돌아갑니다'],
    8250: ['아직 DISC2로는 진행할 수 없습니다', 'START 버튼을 누르거나', '새턴 본체의', '오픈 버튼을 누르면', '멀티 플레이어 화면으로 넘어갑니다', 'DISC2와 DISC1을 바꿔 넣은 뒤', '본체 CD 도어를 닫고', '게임을 시작해 주세요'],
}
DISCMSG[8251] = DISCMSG[8210]


def build_sysmsg(its):
    out = {}
    for n, lines in SYSMSG.items():                              # 288×144: 검은 칸 x 4‥283 · y 8‥135
        w, h, im = b1.decode(mix.read(1, its[n])); rgb = b1.to_rgb(im)
        pitch = min(18, 124 // len(lines))
        draw_text(rgb, (4, 8, 284, 136), lines, 'myeongjo', 12, (248, 248, 248), bg=(0, 0, 0), gap=pitch)
        out[n] = rgb
    import cv2
    for n, lines in DISCMSG.items():                             # 무늬 바탕: 글자+그림자를 지우고(인페인팅) 그림자째 다시
        w, h, im = b1.decode(mix.read(1, its[n])); rgb = b1.to_rgb(im)
        lum = rgb.astype(np.int32).sum(-1)
        m = (lum > 420).astype(np.uint8) * 255
        m = cv2.dilate(m, np.ones((5, 5), np.uint8), iterations=2)                 # 그림자(오른쪽 아래 1‥2 px)까지
        m[:14] = 0; m[-14:] = 0
        bgr = cv2.inpaint(rgb[..., ::-1].copy(), m, 4, cv2.INPAINT_TELEA)[..., ::-1]
        rgb = np.ascontiguousarray(bgr)
        box = (8, 16, 312, 208); pitch = min(20, 190 // len(lines))
        sh = rgb.copy()
        draw_text(sh, (box[0] + 1, box[1] + 1, box[2] + 1, box[3] + 1), lines, 'myeongjo', 12, (0, 0, 0), gap=pitch)
        rgb = np.minimum(rgb, sh) if False else sh                 # 그림자
        draw_text(rgb, box, lines, 'myeongjo', 12, (248, 248, 248), gap=pitch)
        out[n] = rgb
    return out


if __name__ == '__main__':
    its = {it[0]: it for it in mix.items(1)}
    res = build_opening(its); res.update(build_cards(its)); res.update(build_sysmsg(its))
    data = save(res)
    for n, e in data.items():
        print(n, len(mix.read(1, its[n])), '→', len(e))
    if '--preview' in sys.argv:
        ims = [Image.open(os.path.join(OUT, '%04d.png' % n)) for n in OPENING]
        s = Image.new('RGB', (320, 16 * len(ims)))
        for k, i in enumerate(ims): s.paste(i, (0, k * 16))
        s.resize((960, 48 * len(ims)), Image.NEAREST).save(os.path.join(OUT, 'opening_preview.png'))
        ims = [Image.open(os.path.join(OUT, '%04d.png' % n)).crop((56, 0, 224, 120)).resize((336, 240), Image.NEAREST) for n in CARDS]
        s = Image.new('RGB', (336 * 3, 240 * 4))
        for k, i in enumerate(ims): s.paste(i, ((k % 3) * 336, (k // 3) * 240))
        s.save(os.path.join(OUT, 'cards_preview.png'))
        ns = list(SYSMSG) + list(DISCMSG)
        ims = [Image.open(os.path.join(OUT, '%04d.png' % n)) for n in ns]
        s = Image.new('RGB', (320 * 4, 224 * 4))
        for k, i in enumerate(ims): s.paste(i, ((k % 4) * 320, (k // 4) * 224))
        s.save(os.path.join(OUT, 'sys_preview.png'))
