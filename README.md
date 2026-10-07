# 디자이어 한글 패치 (Desire, 세가 새턴 일본판)

- 대상: Desire (Japan) 2장 — 각 장 트랙 1에 xdelta 패치 (트랙 2 오디오는 그대로)
- 내려받기: 릴리즈의 `Desire_KR_beta.zip` — 안의 readme.txt 에 원본·패치 md5 와 적용 방법

| 디스크 | 원본 md5 (트랙 1) | 패치 md5 |
|---|---|---|
| Disc 1 | `5B7A90E8931A61733E970B578AD51E6D` | `D3E4D4D5B43FE411F2EA94629F4DF98A` |
| Disc 2 (2M) | `061B3D54D7E326F17230CA7D9EBC2DF3` | `C7820A22CD6BC0D0BAAC0FBD8A39D2EA` |

## 바뀌는 것 (beta)
- 본편 대사 전부(두 장), 화자 이름, 선택지·메뉴
- 오프닝 문구, 타이틀, 오프닝 스태프 자막
- 인물 소개 카드 12장, 저장 안내·디스크 교체 안내 그림

## 저장소
- `tools/` 빌더(`dsbuild.py`)·그림 도구(`b1.py` `tvid.py` `b1text.py` `vidtext.py`)·배포(`make_dist.py`)
- `work/text/desire.tsv` 원문 목록 · `work/text/desire_ko.tsv` 번역 · `work/text/fixes/` 교정
- `docs/` 조사·작업 기록
