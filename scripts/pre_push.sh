#!/bin/sh
# pre-push 게이트 (2026-08-02)
#
# 훅 본체를 저장소에 두고 .git/hooks/pre-push는 이 파일을 부르게 한다.
# .git/hooks는 클론되지 않으므로 로직이 저장소에 없으면 유실된다.
#
# 설치:
#   printf '#!/bin/sh\nexec "$(git rev-parse --show-toplevel)/scripts/pre_push.sh"\n' \
#     > .git/hooks/pre-push && chmod +x .git/hooks/pre-push

set -e
cd "$(git rev-parse --show-toplevel)"

# 1) 고객 실명·이메일·전화 — public 저장소라 필수
python scripts/anonymize_check.py || exit 1

# 2) 문서-코드 정합 (수치 / 명령표 실동작 / 예제 API)
python scripts/doc_consistency.py || exit 1

# 3) 검사기 자체를 고쳤으면 자체 회귀까지 돌린다.
#    ★ 검사기를 수정하면서 검사를 무력화한 사고가 실제로 있었다
#      (검사 5가 정규식 불일치로 아무것도 안 잡고 있었음).
if git diff --cached --name-only 2>/dev/null | grep -q "doc_consistency.py" ||
   git diff --name-only HEAD~1 2>/dev/null | grep -q "doc_consistency.py"; then
    echo "[pre-push] doc_consistency.py 변경 감지 — 자체 회귀 실행"
    python scripts/doc_consistency.py --selftest || exit 1
fi

# 4) 하네스 스모크 — 코드가 실제로 도는지 (deprecation 승격 상태)
#    문서·이미지 검사만으로는 "import는 되는데 실행하면 죽는" 부류를 못 잡는다.
python scripts/harness_smoke.py --quiet || exit 1

# 스모크 자체를 고쳤으면 인메모리 자체 회귀까지 (파일을 건드리지 않으므로 안전)
if git diff --cached --name-only 2>/dev/null | grep -q "harness_smoke.py" ||
   git diff --name-only HEAD~1 2>/dev/null | grep -q "harness_smoke.py"; then
    echo "[pre-push] harness_smoke.py 변경 감지 — 자체 회귀 실행"
    python scripts/harness_smoke.py --selftest || exit 1
fi

echo "[pre-push] 전 게이트 통과"
