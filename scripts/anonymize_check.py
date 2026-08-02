# -*- coding: utf-8 -*-
"""공개 저장소 실명 노출 검사 (2026-08-01)

## 왜 필요한가
커밋마다 익명화 스크립트를 돌렸는데도 실명이 원격에 올라갔다.
원인: 나중에 스킬 원본을 다시 복사하면서 익명화를 건너뛴 커밋이 있었다.
`git push` 전에 이 검사를 통과해야 한다.

## 사용
    python scripts/anonymize_check.py          # 검사만
    python scripts/anonymize_check.py --fix    # 검사 후 자동 치환

## pre-push 훅으로 걸기
    printf '#!/bin/sh\\npython scripts/anonymize_check.py || exit 1\\n' \\
      > .git/hooks/pre-push && chmod +x .git/hooks/pre-push
"""
import os, re, subprocess, sys

# 고객·작성자 실명 → 대체어
MAP = [
    ("고객 A", "고객 A"), ("고객 E", "고객 E"), ("고객 C", "고객 C"),
    ("고객 D", "고객 D"), ("고객 F", "고객 F"), ("고객 B", "고객 B"),
    ("작성자", "작성자"), ("고객 G", "고객 G"), ("고객 H", "고객 H"),
    ("OO협동조합", "OO협동조합"),
    ("업사이클", "업사이클"), ("스마트멀티탭", "스마트멀티탭"),
]

TEXT_EXT = (".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".cfg", ".sh")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"01[016789][-\s]?\d{3,4}[-\s]?\d{4}")


SELF = os.path.basename(__file__)

# 치환 규칙이나 치환 결과값을 코드에 담는 것이 정상인 파일 —
# 검사하면 항상 실패한다(실측: sync_from_skill.py의 '010-0000-0000' 오탐).
EXEMPT = {SELF, "sync_from_skill.py", "sync_harness.py", "secret_check.py"}


def tracked_text_files():
    """트래킹된 텍스트 파일. 치환 도구 자신들은 제외한다."""
    out = subprocess.run(["git", "ls-files"], capture_output=True).stdout.decode()
    return [f for f in out.split()
            if f.lower().endswith(TEXT_EXT) and os.path.exists(f)
            and os.path.basename(f) not in EXEMPT]


def scan():
    """반환: {파일: (실명목록, 이메일목록, 전화목록)}"""
    hits = {}
    for f in tracked_text_files():
        t = open(f, encoding="utf-8", errors="ignore").read()
        names = [a for a, _ in MAP if a in t]
        mails = [e for e in EMAIL.findall(t) if "example.com" not in e]
        phones = PHONE.findall(t)
        if names or mails or phones:
            hits[f] = (names, mails, phones)
    return hits


def fix():
    n = 0
    for f in tracked_text_files():
        t = open(f, encoding="utf-8", errors="ignore").read()
        o = t
        for a, b in MAP:
            t = t.replace(a, b)
        t = EMAIL.sub("example@example.com", t)
        t = PHONE.sub("010-0000-0000", t)
        if t != o:
            open(f, "w", encoding="utf-8").write(t)
            n += 1
            print("  치환:", f)
    return n


if __name__ == "__main__":
    if "--fix" in sys.argv:
        print("=== 자동 치환 ===")
        print("  %d파일 처리\n" % fix())

    hits = scan()
    if hits:
        print("★ 실명/개인정보 노출 %d파일 — 푸시 차단" % len(hits))
        for f, (n, m, p) in hits.items():
            parts = []
            if n: parts.append("실명 " + ",".join(n))
            if m: parts.append("메일 " + ",".join(m[:2]))
            if p: parts.append("전화 " + ",".join(p[:2]))
            print("  %-46s %s" % (f[:46], " / ".join(parts)))
        print("\n  → python scripts/anonymize_check.py --fix 로 치환 후 재커밋")
        sys.exit(1)
    print("실명/개인정보 노출 없음 — 푸시 가능")
