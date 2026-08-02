# ppt-editorial

레퍼런스 품질의 16:9 슬라이드 덱을 **image generation(codex/GPT Image)**으로 제작하는 범용 하네스.
모든 텍스트·도식·아이콘을 이미지 안에 직접 렌더한다. 도메인 무관(컨설팅·핀테크·의료·교육·제품 등).

> A domain-agnostic harness for producing reference-quality 16:9 slide decks via image generation.
> Text, diagrams and icons are rendered inside the image. Four-stage multi-agent pipeline.

## 핵심 구조 — 4단계 멀티 에이전트 파이프라인

| 단계 | 주체 | 산출 |
|------|------|------|
| 1. 입력 | 사용자 | 슬라이드별 내용 + 레퍼런스 이미지 + 취향/톤 |
| 2. 디자인 디렉터 | Agent (`prompts/director.md`) | 슬라이드별 codex 프롬프트 = `jobs.json` |
| 3. codex 병렬 생성 | `scripts/codex_parallel_gen.py` | 슬라이드 이미지 N장 |
| 4. 디자인 크리틱 | Agent (`prompts/critic.md`) | 슬라이드별 PASS/FIX + 수정지침 |

루프: 크리틱이 FIX한 슬라이드만 2단계로 되돌려 재생성 → 전체 PASS까지. **오케스트레이터는 미적 판단을 하지 않고 크리틱에 위임.**

## 5대 철칙 (어기면 깨짐)

1. **PIL 드로잉 금지** — codex가 PIL로 그리면 한글이 "???"로 깨짐. 프롬프트 말미에 "이미지 생성만" 강제.
2. **레퍼런스 앵커 필수** — 원하는 룩의 완성 슬라이드를 `-i`로 먹여야 리치하게 재현.
3. **콘텐츠는 모델, 고정 크롬(로고·푸터)은 PIL** — 결정적 합성. 완성형 = **SAFE ZONE 방식**(본문은 상하 15% 비우고 생성 → 크롬을 코드로 스탬프).
4. **실사진은 codex에 전달해 슬라이드 안에 함께 그리게 한다** — 코드로 후합성하면 레이아웃이 겉돌고 여백이 남는다.
5. **납품 후 수정 요청은 재생성이 아니라 image-to-image EDIT** — 승인된 덱은 픽셀이 자산이다. base 슬라이드를 주고 "바뀌는 것만, 나머지 픽셀은 EXACTLY 유지"로 지시한다. 전면 재생성하면 레이아웃이 바뀌고 없던 내용이 생겨 반려된다.

## 품질 게이트 (조립 전 필수)

| 도구 | 검출 |
|------|------|
| `scripts/deck_qc.py <슬라이드폴더>` | 종횡비 불일치 · 좌우 여백 소실 · SAFE ZONE 침범 (FAIL 시 exit 1) |
| 우측 1/3 확대 크롭 육안 검수 | 패널 안 텍스트 잘림 (콘택트시트로는 안 보임) |
| 원본 파일 대조 | 레퍼런스/GPTs가 만든 환각 수치 |

## 개정(수정 요청) 처리

`scripts/safezone/revise_{spec,chrome,build}_template.py` — `ORDER` 매핑 dict 하나로 순서 재배열·섹션 제목·카피·요약·쪽번호를 동시 해결. 소스 우선순위 체인으로 재생성분만 갈아끼운다.

- 상단 카피·하단 요약·순서·제목 변경 → **재생성 불필요**(크롬에서 처리)
- 사진·수치·도식·레이아웃 변경 → 해당 장만 EDIT

세대별 raw가 쌓이면 **어느 것이 납품본인지 픽셀 MAE로 판정**한다(기억에 의존하면 반드시 틀림).

## 스타일 프로파일

- **에디토리얼**: 페이퍼화이트 · 명조 · 미니멀 · 강조 1색.
- **모던 플랫**: Pretendard 고딕 · 3D 클레이 일러스트 · 소프트 카드/알약 · 큰 볼드 숫자. **아키타입 12종 갤러리**(`references/modern-flat/gallery/` + `CATALOG.md`).
- 강조색·서체·스타일은 **매 덱 사용자 확인**(고정 금지).
- 기본값: **정제된 작은 스케일** + **은은한 의미데코**(주제 연결).

## 하이브리드 보고서 모드

결과보고처럼 **실제 화면(대시보드·표·시트·앱 스크린샷)**을 넣어야 하는 대형 덱은 codex 전용으로 안 됨(codex는 실제 화면을 못 그림).
→ **[C] codex 내러티브 + [S] 스크린샷 프레임** 혼합. `scripts/screenshot_frame.py`가 실제 스크린샷을 모던플랫 프레임(제목·라운드 카드·그림자·캡션·데코, **강조색 파라미터**)에 임베드.

```bash
python scripts/screenshot_frame.py spec.json OUT_DIR --accent 503020
# spec = [{num, tab, eyebrow, title, images:[png], caption, layout:"one"|"two"}]
```

## 구조

```
SKILL.md                     # 하네스 전체 방법론
prompts/director.md          # 2단계 디자인 디렉터 템플릿
prompts/critic.md            # 4단계 디자인 크리틱 템플릿
scripts/codex_parallel_gen.py  # 격리홈 병렬 codex 생성 + 루프
scripts/screenshot_frame.py    # [S] 스크린샷 임베드 렌더러 (범용)
scripts/chrome.py              # 균일 크롬(로고·푸터) 합성
references/modern-flat/
 ├ CATALOG.md                # 아키타입 12종 카탈로그
 └ gallery/                  # 아키타입 12종 견본(중립)
```

## 요구 사항

- **codex CLI** (GPT Image 이미지 생성)
- Python 3 + `pillow`, `pymupdf`(fitz), `python-pptx`

## 설치 (플러그인)

`.codex-plugin/plugin.json` + `skills/ppt-editorial/SKILL.md` 구조를 갖춘 설치형 플러그인입니다.
설치 후에는 `skills/ppt-editorial/SKILL.md`가 엔트리포인트(최소 행동 계약)이고, 루트 `SKILL.md`가 정식 운영 가이드입니다.

```bash
git clone https://github.com/Dayoooun/ppt-editorial.git
```

## 라이선스

MIT — `LICENSE` 참조.


---

## ★ 씬 덱 (Scene Deck) — 기본 프로파일

고객 납품·피칭·제안은 여기서 시작한다. 상세는 `scripts/scene-deck/README.md`(19절).

```python
import sys, os
sys.path.insert(0, "scripts/scene-deck")
from deck import Deck

d = Deck(domain="제조", foot="OO정밀", title="제안서")
d.cover("PROPOSAL", ["헤드라인", "2줄"], ["서브"], issuer="(주)OO정밀",
        meta=["2026"], scene="영문 씬 서술")
d.agenda(["배경", "과제", "계획"], scene="...")
d.slide("L", "SECTION", ["헤드라인"], ["서브"], scene="...", labels=["라벨"])
d.slide("C", "RESULT", ["결과"], ["..."], scene="...",
        num=["42", "%", "캡션"], chips=["키워드1", "키워드2"])
d.photos(["a.jpg", "b.jpg"], "ON SITE", ["현장"], ["..."])
d.closing(["감사합니다"], issuer="(주)OO정밀", scene="...")

d.generate()                    # 씬 생성 (있으면 생략)
d.build(pdf=True, pptx=True)    # 조립 + 출력
```

`domain` 한 줄로 팔레트·폰트·씬모티프·톤이 잡힌다.

### 구성

| 파일 | 역할 |
|---|---|
| `scripts/scene-deck/deck.py` | **진입점** — build.py를 새로 쓰지 마라 |
| `scripts/scene-deck/presets.py` | 도메인 9종 (it/food/manufacturing/education/welfare/culture/public/medical/retail) |
| `scripts/scene-deck/layout_engine.py` | 구도 10종 + 강조요소 + 오버플로우 방어 |
| `scripts/scene-deck/fonts.py` | 폰트 풀 11종 + 황금비 스케일 |
| `scripts/scene-deck/revise.py` | 수정 인터페이스 (자연어 + API) |
| `scripts/scene-deck/photos.py` | 실사진 4모드 |

### 구도 10종

본문 `L`(좌텍/우씬) `S`(반전) `W`(프로세스) `C`(비교·교집합)
`A`(비대칭대형) `F`(전면) `T`(3분할) / 실무 `COVER` `AGENDA` `CLOSING`

**연속 3장 이상 같은 구도 금지.**

---

## 저장소 관리 도구

| 도구 | 용도 |
|---|---|
| `scripts/sync_from_skill.py` | 스킬 원본 → 이 저장소 **복사 + 익명화 + 검사** |
| `scripts/anonymize_check.py` | 고객 실명·이메일·전화 검사 |
| `scripts/doc_consistency.py` | **코드 실측값 vs 문서 주장** 대조 |
| `scripts/harness_smoke.py` | **코드가 실제로 도는지** (수초, deprecation 승격) |

```bash
python scripts/sync_from_skill.py --dry   # 변경분 확인
python scripts/sync_from_skill.py         # 복사 + 익명화 + 검사
```

⚠️ **`cp`를 직접 쓰지 마라.** 익명화를 잊어 실명이 공개된 사고가 2번 났다.
### pre-push 게이트

```bash
# 설치 (재클론 후 1회)
printf '#!/bin/sh\nexec "$(git rev-parse --show-toplevel)/scripts/pre_push.sh"\n' \
  > .git/hooks/pre-push && chmod +x .git/hooks/pre-push
```

`scripts/pre_push.sh`가 순차 실행한다:
1. `anonymize_check` — 고객 실명·이메일·전화
2. `doc_consistency` — 문서-코드 정합
3. `doc_consistency.py`를 고쳤으면 `--selftest`까지

⚠️ **로직은 `.git/hooks`가 아니라 저장소에 있다.** `.git/hooks`는 클론되지 않으므로
훅 안에 검사를 쓰면 재클론 시 게이트가 통째로 사라진다.
