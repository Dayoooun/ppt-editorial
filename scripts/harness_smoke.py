# -*- coding: utf-8 -*-
"""하네스 스모크 테스트 (2026-08-02)

## 왜 필요한가
`doc_consistency`는 문서를, `deck_qc`는 산출 이미지를 검사한다.
**코드 자체가 도는지**는 아무도 안 본다.

이 세션에서 실제로 있었던 일:
- `typo()` 시그니처 불일치로 `NameError` — 렌더까지 가서야 발견
- `Deck.save()` 미호출로 `FileNotFoundError` — 재로드 시점에 터짐
- `Image.getdata()` deprecation — 씬 생성 때마다 경고

전부 "import는 되는데 실행하면 죽는" 부류다. import 확인만으로는 못 잡는다.

## 사용
    python scripts/harness_smoke.py           # 조립까지 (수초)
    python scripts/harness_smoke.py --quiet   # 실패만 출력
"""
import os, sys, glob, json, warnings, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SD = os.path.join(HERE, "scene-deck")
sys.path.insert(0, SD)
sys.path.insert(0, HERE)

CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


@check("모듈 import")
def _import():
    import fonts, presets, layout_engine, photos, revise, deck  # noqa
    return "6모듈"


@check("프리셋 전종")
def _presets():
    import presets
    bad = []
    for k in presets.PRESETS:
        p = presets.preset(k)
        if not p.get("palette", {}).get("hero") or not p.get("fonts", {}).get("head"):
            bad.append(k)
        if len(presets.style_block(k)) < 400:
            bad.append(k + "(style_block 짧음)")
    if bad:
        raise AssertionError("불완전: %s" % bad)
    return "%d종" % len(presets.PRESETS)


@check("구도 함수 시그니처")
def _layouts():
    """실제 렌더는 씬 파일이 필요하므로 시그니처와 등록만 확인한다."""
    import layout_engine as LE
    import inspect
    bad = []
    for name, fn in LE.LAY.items():
        params = list(inspect.signature(fn).parameters)
        # 전 구도가 (im, d, s) 3인자 규약을 지켜야 조립기가 호출할 수 있다
        if len(params) < 3:
            bad.append("%s%s" % (name, params))
    if bad:
        raise AssertionError("시그니처 불일치: %s" % bad)
    for need in ("L", "S", "W", "C", "A", "F", "T", "COVER", "AGENDA", "CLOSING"):
        if need not in LE.LAY:
            raise AssertionError("구도 %s 누락" % need)
    return "%d종" % len(LE.LAY)


@check("revise 명령")
def _revise():
    import revise
    spec = {"domain": "it", "foot": "x", "slides": [
        {"lay": "L", "eyebrow": "A", "scene": "s%02d" % i,
         "head": ["h%d" % i], "sub": ["s"]} for i in range(1, 6)]}
    d = revise.Deck(json.loads(json.dumps(spec)))
    cmds = ["3번 헤드라인을 새 제목 로", "2번 구도를 W로", "1번 씬 다시",
            "5번을 2번으로 이동", "색을 navy로"]
    fail = [c for c in cmds if revise.apply_command(d, c) is None]
    if fail:
        raise AssertionError("파싱 실패: %s" % fail)
    if not d.dirty_scenes:
        raise AssertionError("씬 재생성이 집계되지 않음")
    return "%d종" % len(cmds)


@check("Deck 조립+출력")
def _deck():
    from deck import Deck
    outs = sorted(glob.glob(os.path.join(
        os.path.expanduser("~"), "..", "..", "**", "showcase", "*", "spec.json")))
    # 검증 덱이 없으면 최소 스펙으로 조립만
    tmp = tempfile.mkdtemp()
    try:
        d = Deck(domain="it", foot="스모크", title="smoke", out_dir=tmp)
        d.cover("SMOKE", ["표지"], ["서브"], issuer="테스트", scene="a test cover")
        d.slide("L", "TEST", ["헤드라인"], ["서브"], scene="a simple test scene")
        d.save()
        sp = os.path.join(tmp, "spec.json")
        if not os.path.exists(sp):
            raise AssertionError("spec.json 미생성")
        d2 = Deck.load(sp)
        if len(d2.slides) != 2:
            raise AssertionError("load 후 슬라이드 %d개 (2 기대)" % len(d2.slides))
        # jobs 생성까지 — 프롬프트 조립 경로 확인
        jobs = d2.jobs()
        if len(jobs) != 2 or not jobs[0].get("prompt"):
            raise AssertionError("jobs 생성 실패")
        return "save/load/jobs OK"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    quiet = "--quiet" in sys.argv
    fails = []
    # deprecation을 오류로 승격 — import는 되는데 실행하면 죽는 부류를 잡는다
    warnings.simplefilter("error", DeprecationWarning)
    warnings.simplefilter("error", PendingDeprecationWarning)

    for name, fn in CHECKS:
        try:
            got = fn()
            if not quiet:
                print("  %-16s OK  %s" % (name, got))
        except Exception as e:
            fails.append((name, "%s: %s" % (type(e).__name__, str(e)[:70])))
            print("  %-16s ★ %s: %s" % (name, type(e).__name__, str(e)[:70]))

    if fails:
        print("\n실패 %d/%d" % (len(fails), len(CHECKS)))
        return 1
    if not quiet:
        print("\n전 %d항목 통과 (deprecation 승격 상태)" % len(CHECKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
