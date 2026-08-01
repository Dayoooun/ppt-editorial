# 씬 덱 (Scene Deck) — 고품질 프로파일 ★기본

> 2026-08-01 확정. 실제 납품 승인본(고객 G 기술해자·고객 B 결과보고) 수준을 재현하는 표준.
> **고객 납품·피칭·제안 덱은 이 프로파일로 시작한다.**

## 1. 이게 왜 기본인가

이전 시도들이 반려된 이유를 그대로 뒤집은 것이다.

| 반려된 접근 | 이 프로파일 |
|---|---|
| 아이콘 10개 만들어 카드에 나열 | **씬 일러스트 1장이 슬라이드를 지배** |
| 카드 3~4개 균등 배치 | 좌 대형타이포 / 우 씬 **2단 그리드** |
| 파란 풀블리드 밴드 | **미니멀 크롬** — 대시+영문라벨 / 얇은 하단 라인 |
| 5장 전부 같은 구도 | **내용이 구도를 결정** (L/W/S/C) |

### ★ 아이콘 ≠ 일러스트 ≠ 씬
- **아이콘**: 80px 타일. 카드 안 보조 요소. 키우면 "커진 아이콘"으로 보여 싸구려가 된다.
- **씬**: 메시지를 담은 한 장면. 갈라진 플랫폼, 다리를 건너는 사람, 교집합에 선 사람.
  **슬라이드 하나당 씬 하나**가 원칙.

## 2. 씬 프롬프트 규격

`scene_prompts.py`의 `BASE_STYLE`을 그대로 쓴다. 핵심 3요소:

```
RENDER STYLE — High-end 3D render, soft studio lighting, matte surfaces,
  rounded tactile geometry, soft contact shadows, subtle depth of field.
  NOT flat vector, NOT cartoon, NOT clay-toy, NOT line icons.
  Apple-keynote / fintech quality.

PALETTE — primary #2B6EF2 · lighter #6FA0FA · pale #DCE7FD
  white · grey #F1F3F6 · ink #161D2B   (blue is the hero)

BACKGROUND — pure white, generous empty space.
```

### ★ 씬 안에 라벨을 박아라
기준 덱은 그림 안에 한글 라벨이 들어간다(빙산의 `원고/조판/품질검증`, 벤의 `둘 다`).
라벨 없는 씬은 정보량이 부족하다.

```
TEXT LABELS rendered in the image (bold Korean gothic, ink colour, small):
  above the left platform:  "경영"
  above the right platform: "기술"
```

## 3. 구도 4종 — 내용이 결정한다

`layout_engine.py`의 `LAY` dict. 슬라이드 성격에 맞춰 고른다.

| 코드 | 구도 | 언제 쓰나 | 실측 예 |
|---|---|---|---|
| **L** | 좌 텍스트 / 우 씬 | 개념 설명. 텍스트가 주도 | 문제 제기, 제품 소개 |
| **W** | 상단 텍스트 / 하단 와이드 씬 | **순서·프로세스**. 가로로 흘러야 읽힘 | 4단계 공정 |
| **S** | 좌 씬 / 우 텍스트 (L 반전) | **리듬 전환**. 수직 축적형 씬 | 실적 스택 |
| **C** | 중앙 대칭 | **비교·교집합**. 대칭이라야 의미가 산다 | 벤다이어그램 |

**연속 3장 이상 같은 구도를 쓰지 말 것.** L→W→S→C→L 처럼 교차한다.

## 4. 실행 순서

```bash
# 1) 씬 스펙 작성 (슬라이드별 구도 + 씬 내용 + 라벨)
#    scene_prompts.py 의 SCENES 를 프로젝트에 맞게 수정
python scene_prompts.py                      # → jobs_v3.json

# 2) 씬 생성 (--effort high 필수, 품질 차이가 크다)
python ../codex_parallel_gen.py jobs_v3.json --cap 5 --retry 1 --loop 2 \
       --timeout 900 --effort high

# 3) 조립 (구도별 레이아웃 + 미니멀 크롬 + PDF)
#    layout_engine.py 의 SLIDES 를 수정 후
python layout_engine.py                      # → v3_out/*.png + PDF
```

## 5. 그리드 규격 (실측 기반)

캔버스 **2560×1440**, 좌우 여백 `M = W*0.030`

| 요소 | 위치 |
|---|---|
| 상단 크롬 (대시+영문라벨 / 쪽번호) | `y = H*0.062` |
| 헤드라인 시작 | `y = H*0.245` (L/S), `H*0.16` (W), `H*0.155` (C) |
| 헤드라인 크기 | **112px** (L/S) · 96px (W/C) — 화면을 지배해야 함 |
| 서브 텍스트 | 38px, grey `#7A8494`, 행간 1.52 |
| 하단 구분선 | `y = H*0.889`, 1px `#E4E7EC` |
| 씬 영역 | 폭 `W*0.40~0.42`, 높이 `H*0.60` |

## 6. 함정

- **`trim_white()` 필수** — 씬 PNG는 흰 여백을 잔뜩 물고 온다. 그대로 붙이면 작아 보인다.
- **`--effort high` 없으면 품질이 무너진다.** 씬은 렌더 난이도가 높아 기본 effort로는 평면적으로 나온다.
- **씬 비율을 용도에 맞게 요청** — W 구도용은 `16:9 wide`, 나머지는 `4:3 landscape`.
- 헤드라인 2줄이 기본. 1줄이면 허전하고 3줄이면 씬이 눌린다.
