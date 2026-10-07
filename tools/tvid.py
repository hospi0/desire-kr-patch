# -*- coding: utf-8 -*-
r"""SOUND/*.VID «tVid» 그림 영상 (2026-10-07) — 00DESIRE.BIN 0x06013B28(vdat 해독) 그대로
  머리 0x40 B: 'tVid' · u32×3 · 너비 · 높이 · 0x7530 · 프레임 수 … / 팔레트 0x40‥0x400 = 240 × (R,G,B,0)
  덩어리: 'vdat' u32 0 · u32 크기 · u32 0 · 데이터 · 'vblt' 12 B (… 'end ')
  데이터 = 화면 버퍼(앞 프레임 위)에 줄마다 덮어쓰기. b ≤ 0xEF 팔레트 픽셀 하나 ·
    F0 n: n+2 건너뜀(앞 프레임 그대로) · F1‥F7 n: 버퍼의 이웃(F1 x+1 · F2 x−1,y+1 · F3 y+1 · F4 x+1,y+1 · F5 x−1,y−1 · F6 y−1 · F7 x+1,y−1)에서 n+2 복사 ·
    F8 n: 바로 앞 픽셀 n+2 번 · F9‥FC: 2‥5 건너뜀 · FD‥FF: 바로 앞 픽셀 2‥4 번.
  python tools/tvid.py OPST1 → work/vid/OPST1/프레임 PNG"""
import os, re, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
NB = {1: 1, 2: -1, 3: 0, 4: 1, 5: -1, 6: 0, 7: 1}          # x 어긋남
NY = {1: 0, 2: 1, 3: 1, 4: 1, 5: -1, 6: -1, 7: -1}         # y 어긋남


def parse(d):
    w, h = struct.unpack_from('>II', d, 16); nf = struct.unpack_from('>I', d, 28)[0]
    pal = np.array([list(d[0x40 + i * 4:0x40 + i * 4 + 3]) for i in range(240)], np.uint8)
    chunks = []                                           # (데이터 시작, 크기)
    for m in re.finditer(b'vdat', d):
        p = m.start(); sz = struct.unpack_from('>I', d, p + 8)[0]
        chunks.append((p + 16, sz))
    return w, h, nf, pal, chunks


def decode_frame(buf, f, w, h):
    """buf(int16 h×w 팔레트 번호, 앞 프레임) 위에 덮어씀"""
    b = buf.reshape(-1); i = 0
    for y in range(h):
        x = 0; base = y * w
        while x < w:
            c = f[i]; i += 1
            if c <= 0xEF:
                b[base + x] = c; x += 1
            elif c <= 0xF8:
                n = f[i] + 2; i += 1; op = c - 0xF0
                if op == 0:
                    x += n
                elif op == 8:
                    v = b[base + x - 1]; b[base + x:base + x + n] = v; x += n
                else:
                    for j in range(n):
                        s = base + x + NB[op] + NY[op] * w
                        b[base + x] = b[s]; x += 1
            elif c <= 0xFC:
                x += c - 0xF7
            else:
                n = c - 0xFB; v = b[base + x - 1]; b[base + x:base + x + n] = v; x += n
    return i


def frames(d):
    w, h, nf, pal, chunks = parse(d)
    buf = np.zeros((h, w), np.int16); out = []
    for p, sz in chunks:
        used = decode_frame(buf, d[p:p + sz], w, h)
        out.append(buf.copy())
    return w, h, pal, out


if __name__ == '__main__':
    from PIL import Image
    sys.path.insert(0, HERE); import disc
    name = sys.argv[1]
    d = disc.read(1, 'SOUND/%s.VID' % name)
    w, h, pal, fs = frames(d)
    od = os.path.join(ROOT, 'work', 'vid', name); os.makedirs(od, exist_ok=True)
    for k, f in enumerate(fs):
        Image.fromarray(pal[np.clip(f, 0, 239)]).save(os.path.join(od, '%03d.png' % k))
    print(name, w, h, len(fs), '프레임 →', od)


# ── 다시 쌓기(인코더) ─────────────────────────────────────────────────────
def encode_frame(buf, tgt, w, h):
    """buf(앞 프레임, 제자리에서 고쳐짐) → tgt 가 되게 하는 vdat 데이터. 욕심쟁이: 건너뜀·앞 픽셀 반복·이웃 복사 중 가장 긴 것, 아니면 픽셀 하나"""
    b = buf.reshape(-1); t = tgt.reshape(-1); out = bytearray()
    for y in range(h):
        base = y * w; x = 0
        while x < w:
            k = base + x; rem = w - x
            best = (1, None)
            n = 0
            while n < rem and n < 257 and b[k + n] == t[k + n]:
                n += 1
            if n >= 2: best = (n, 0)
            if x > 0:
                v = b[k - 1]; n = 0
                while n < rem and n < 257 and t[k + n] == v:
                    n += 1
                if n > best[0]: best = (n, 8)
            for op in range(1, 8):
                dx, dy = NB[op], NY[op]
                if not (0 <= y + dy < h): continue
                n = 0
                while n < rem and n < 257:
                    sx = x + n + dx
                    if not (0 <= sx < w): break
                    s = base + x + n + dx + dy * w
                    # 복사 중 원본이 이미 바뀐 칸일 수 있음(같은 줄 x+1·윗줄) — 시뮬레이션: 앞서 쓴 값
                    sv = t[s] if (s < k + n and s >= base - w * 0) and s < k + n else b[s]
                    if s < k + n:
                        sv = t[s]
                    if sv != t[k + n]: break
                    n += 1
                if n > best[0]: best = (n, op)
            n, op = best
            if op is None or n < 2:
                c = int(t[k]); assert c <= 0xEF
                out.append(c); b[k] = c; x += 1; continue
            if op == 0:
                out += bytes([0xF9 + n - 2]) if n <= 5 else bytes([0xF0, n - 2])
            elif op == 8:
                out += bytes([0xFD + n - 2]) if n <= 4 else bytes([0xF8, n - 2])
            else:
                out += bytes([0xF0 + op, n - 2])
            b[k:k + n] = t[k:k + n]; x += n
    return bytes(out)


def rebuild(d, targets):
    """원본 VID 바이트 + 프레임별 목표(팔레트 번호 h×w) → 새 VID(덩어리 틀·vblt·끝 그대로, vdat 크기만 새로)"""
    w, h, nf, pal, chunks = parse(d)
    assert len(targets) == len(chunks)
    out = bytearray(d[:chunks[0][0] - 16]); buf = np.full((h, w), -1, np.int16)   # ⛔시작 버퍼 = 모름(앞 화면 찌꺼기) — 첫 프레임은 전 픽셀을 써야 함(원본 그대로, 2026-10-07 스태프롤 깨짐)
    for k, (p, sz) in enumerate(chunks):
        data = encode_frame(buf, targets[k].astype(np.int16), w, h)
        data += bytes(-len(data) % 4)                          # ⛔4 배수로 0 채움(원본 그대로) — 안 하면 다음 덩어리 머리 u32 읽기가 주소 오류(스태프롤 크래시, 2026-10-07)
        out += d[p - 16:p - 8] + struct.pack('>I', len(data)) + d[p - 4:p] + data
        nxt = chunks[k + 1][0] - 16 if k + 1 < len(chunks) else len(d)
        out += d[p + sz:nxt]                                   # vblt 등 덩어리 사이
    return bytes(out)
