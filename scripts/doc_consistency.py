# -*- coding: utf-8 -*-
"""문서-코드 정합 검사 (2026-08-01)

## 왜 필요한가
한 세션에서 문서 모순을 **6건** 수작업으로 찾았다. 전부 같은 원인이다 —
같은 사실을 CLAUDE.md / SKILL.md / README.md 세 곳에 적어두고
코드를 고칠 때 한두 곳만 갱신했다.

발견된 모순:
1. README §2·§4가 격리된 `scene_prompts.py`를 쓰라고 안내
2. README §3 "구도 4종" vs §9 "구도 7종" vs 실제 10종
3. README §4 그리드 규격이 구버전 수치(112px)
4. README §1 표가 초기 표기 `(L/W/S/C)`
5. CLAUDE.md 헤드라인 112px + PPTX 누락
6. CLAUDE.md "구도 10종"이라 써놓고 나열은 4종

**코드에서 실제 값을 읽어 문서와 대조**하면 자동으로 잡힌다.

## 사용
    python scripts/doc_consistency.py

## pre-commit 훅
    printf '#!/bin/sh\\npython scripts/doc_consistency.py || exit 1\\n' \\
      > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
SD = os.path.join(HERE, "scene-deck")
sys.path.insert(0, SD)

DOCS = {
    "CLAUDE.md": os.path.expanduser("~/.claude/CLAUDE.md"),
    "SKILL.md":  os.path.join(SKILL_DIR, "SKILL.md"),
    "README.md": os.path.join(SD, "README.md"),
}

# 문서에 남아 있으면 안 되는 구버전 패턴
STALE = [
    (r"구도 [1-9]종",        "구도 개수"),
    (r"\(L/W/S/C\)",         "구도 나열(구버전 4종)"),
    # 헤드라인 크기는 STALE로 잡지 않는다 — 실측값과 대조하는 규칙(4)이 담당.
    # 정규식으로 잡으면 정상값 115px까지 오탐한다(실측).
    (r"scene_prompts",       "격리된 모듈"),
    (r"jobs_v3",             "구버전 산출물명"),
    (r"15~25분",             "정정된 성능 수치"),
    (r"(?<!\d)4배(?!\w)",    "정정된 성능 배수"),
]


def code_facts():
    """코드에서 실제 값을 읽는다"""
    import layout_engine as LE
    import presets, fonts, photos, deck
    return {
        "구도_개수": len(LE.LAY),
        "구도_코드": sorted(LE.LAY),
        "도메인_개수": len(presets.PRESETS),
        "헤드라인_px": fonts.TYPE_SCALE["headline"],
        "표지_px": fonts.TYPE_SCALE["display"],
        "사진_모드": len(photos.ARRANGE),
        "Deck_메서드": [m for m in ("cover", "agenda", "closing", "slide",
                                   "photos", "generate", "build", "pdf",
                                   "pptx", "revise", "load")
                       if hasattr(deck.Deck, m)],
    }


def check():
    f = code_facts()
    problems = []

    for name, path in DOCS.items():
        if not os.path.exists(path):
            problems.append((name, "-", "파일 없음"))
            continue
        text = open(path, encoding="utf-8").read()

        # PPT 섹션만 보는 문서
        if name == "CLAUDE.md":
            i = text.find("Auto-Trigger: PPT")
            text = text[i:i + 3000] if i > 0 else text

        # 1) 구버전 패턴
        for pat, why in STALE:
            for m in re.finditer(pat, text):
                ln = text[:m.start()].count("\n") + 1
                problems.append((name, "%d행" % ln, "%s: '%s'" % (why, m.group())))

        # 2) 구도 개수 주장 vs 실제
        for m in re.finditer(r"구도\s*(\d+)\s*종", text):
            if int(m.group(1)) != f["구도_개수"]:
                problems.append((name, "%d행" % (text[:m.start()].count("\n") + 1),
                                 "구도 %s종 주장 ≠ 실제 %d종" % (m.group(1), f["구도_개수"])))

        # 3) 구도 개수를 언급했다면 전 코드가 나열돼야 함
        if re.search(r"구도\s*\d+\s*종", text):
            # 단일 문자 코드(L/S/W/C/A/F/T)는 일반 단어에 묻히므로
            # 백틱·괄호·굵게 표시 안에 있을 때만 '나열됨'으로 본다.
            def listed(c):
                if len(c) == 1:
                    return re.search(r"[`*(\s]%s[`*)\s(,·/]" % c, text) is not None
                return c in text
            missing = [c for c in f["구도_코드"] if not listed(c)]
            if missing:
                problems.append((name, "-", "구도 나열 누락: %s" % ", ".join(missing)))

        # 4) 헤드라인 px 주장 vs 실제
        for m in re.finditer(r"헤드라인\s*\*{0,2}(\d+)px", text):
            if int(m.group(1)) != f["헤드라인_px"]:
                problems.append((name, "%d행" % (text[:m.start()].count("\n") + 1),
                                 "헤드라인 %spx 주장 ≠ 실제 %dpx" % (m.group(1), f["헤드라인_px"])))

        # 5) 도메인 개수
        for m in re.finditer(r"도메인\s*(?:프리셋\s*)?(\d+)\s*종", text):
            if int(m.group(1)) != f["도메인_개수"]:
                problems.append((name, "%d행" % (text[:m.start()].count("\n") + 1),
                                 "도메인 %s종 주장 ≠ 실제 %d종" % (m.group(1), f["도메인_개수"])))

    return f, problems


if __name__ == "__main__":
    facts, probs = check()
    print("=== 코드 실측 ===")
    for k, v in facts.items():
        print("  %-12s %s" % (k, v if not isinstance(v, list) else " ".join(map(str, v))))
    print("\n=== 문서 정합 ===")
    if probs:
        for doc, loc, msg in probs:
            print("  ★ %-11s %-7s %s" % (doc, loc, msg))
        print("\n  모순 %d건 — 문서를 코드에 맞춰 갱신하라" % len(probs))
        sys.exit(1)
    print("  모순 0건 — CLAUDE.md / SKILL.md / README.md 전건 정합")
