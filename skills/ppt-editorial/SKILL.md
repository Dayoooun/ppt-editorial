---
name: ppt-editorial
description: "Reference-quality 16:9 slide deck harness. Use for result reports, proposals, pitch decks, lecture decks, and presentation redesigns where every text/diagram/icon must be rendered inside a generated image, visual consistency matters, and real screenshots may need to be embedded."
---

# PPT Editorial

이 스킬은 `ppt-editorial` 하네스의 **설치형 엔트리포인트**입니다.
전체 워크플로는 저장소 루트의 `SKILL.md`를 정식 운영 가이드로 사용하세요.
아래는 플러그인 설치 시 지켜야 할 **최소 행동 계약**입니다.

## 최소 행동 계약

1. **역할 분리** — 오케스트레이터는 미적 판단을 하지 않는다.
   디자인 디렉터 에이전트(`prompts/director.md`)가 슬라이드별 프롬프트를 쓰고,
   디자인 크리틱 에이전트(`prompts/critic.md`)가 PASS/FIX를 판정한다. FIX만 재생성 루프.

2. **3대 철칙**
   - PIL/코드 드로잉 금지 → 이미지 생성만(한글 깨짐 방지).
   - 원하는 룩의 견본을 `-i` 스타일 앵커로 반드시 먹인다.
   - 콘텐츠는 모델, 고정 크롬(로고·푸터)은 결정적 합성(PIL).

3. **매 덱 사용자 확인** — 스타일 프로파일 · 강조색 · 서체는 **고정 금지**, 시작 시 질문한다.

4. **기본값** — 정제된 작은 스케일(작은 글자·넓은 여백) + 은은한 의미데코(슬라이드 주제와 연결, 1~2개, 저대비). 무의미한 기하 필러 금지.

5. **아키타입 선택** — `references/modern-flat/CATALOG.md`에서 슬라이드 내용에 맞는 아키타입을 골라 그 견본을 앵커로 사용한다.

6. **하이브리드 보고서** — 실제 화면(대시보드·표·시트·앱)이 필요한 덱은 codex 전용으로 만들지 않는다.
   내러티브는 생성, 실증 화면은 `scripts/screenshot_frame.py`로 프레임 임베드 후 순서 병합.

7. **정직성** — 표시 텍스트·수치는 원본 대조. 창작·추정 금지.

## 스크립트

| 스크립트 | 용도 |
|---------|------|
| `scripts/codex_parallel_gen.py` | 격리홈 병렬 이미지 생성 + 재시도 루프 |
| `scripts/screenshot_frame.py` | 실제 스크린샷을 모던플랫 프레임에 임베드(강조색 파라미터) |
| `scripts/chrome.py` | 균일 크롬(로고·푸터) 합성 |
