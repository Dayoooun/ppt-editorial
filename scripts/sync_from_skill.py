# -*- coding: utf-8 -*-
"""스킬 원본 → 공개 저장소 동기화 (2026-08-01)

## 왜 필요한가
복사와 익명화가 분리돼 있어 **같은 사고가 두 번 났다.**

1. 스킬 원본을 `cp`로 저장소에 복사
2. 익명화를 **따로** 실행해야 함
3. 2를 잊으면 고객 실명이 public 저장소로 나간다

두 번째 사고는 `doc_consistency.py`를 푸시하던 중,
README를 복사하자마자 익명화가 풀려 발생했다. pre-push 훅이 막았지만
훅이 없었으면 그대로 나갔다.

**복사와 익명화를 한 동작으로 묶으면 잊을 수가 없다.**

## 사용
    python scripts/sync_from_skill.py           # 동기화 + 익명화 + 검사
    python scripts/sync_from_skill.py --dry     # 무엇이 바뀌는지만
"""
import os, shutil, subprocess, sys, hashlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.expanduser(r"~\.claude\skills\ppt-editorial")

# 복사 대상은 디렉터리에서 자동 수집한다 — 목록을 손으로 관리하면 반드시 샌다.
# 실측: 하드코딩 목록에서 5개(assemble_pptx/chrome/index_chrome/salvage_cache/
# screenshot_frame)가 빠져 있었다.
ALWAYS = [
    "SKILL.md",
    "scripts/scene-deck/README.md",
    "scripts/scene-deck/_deprecated/README.md",
]


def pairs():
    """(스킬 상대경로, 저장소 상대경로) 목록을 자동 생성"""
    import glob as _g
    rels = list(ALWAYS)
    for pat in ("scripts/*.py", "scripts/scene-deck/*.py"):
        for p in sorted(_g.glob(os.path.join(SKILL, pat))):
            rels.append(os.path.relpath(p, SKILL).replace(os.sep, "/"))
    # 저장소 경로는 동일 구조
    seen, out = set(), []
    for r in rels:
        if r in seen:
            continue
        seen.add(r)
        out.append((r, r))
    return out


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()[:8] if os.path.exists(p) else "-"


def main():
    dry = "--dry" in sys.argv
    changed = []

    for src_rel, dst_rel in pairs():
        src = os.path.join(SKILL, src_rel)
        dst = os.path.join(REPO, dst_rel)
        if not os.path.exists(src):
            print("  ! 원본 없음: %s" % src_rel)
            continue
        if md5(src) == md5(dst):
            continue
        changed.append(dst_rel)
        if not dry:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    if not changed:
        print("동기화 대상 없음 — 이미 최신")
    else:
        print("%s %d파일:" % ("변경 예정" if dry else "복사 완료", len(changed)))
        for c in changed:
            print("   ", c)

    if dry:
        return 0

    # ★ 복사 직후 반드시 익명화 — 이 순서가 핵심이다
    print("\n[익명화]")
    subprocess.run([sys.executable, os.path.join(REPO, "scripts", "anonymize_check.py"),
                    "--fix"], cwd=REPO)

    print("\n[검사]")
    rc1 = subprocess.run([sys.executable, "scripts/anonymize_check.py"], cwd=REPO).returncode
    rc2 = subprocess.run([sys.executable, "scripts/doc_consistency.py"], cwd=REPO).returncode
    if rc1 or rc2:
        print("\n★ 검사 실패 — 커밋하지 마라")
        return 1
    print("\n동기화 완료 — 커밋 가능")
    return 0


if __name__ == "__main__":
    sys.exit(main())
