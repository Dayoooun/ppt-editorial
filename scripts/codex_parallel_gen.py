# -*- coding: utf-8 -*-
"""codex 병렬 이미지 생성 하네스 (v3) — ima2 병렬 개념을 codex로 복제 + 상태격리 + 재귀개선 루프.

ima2 서버·OAuth 로그인 없이, 이미 인증된 codex(GPT Image)로 여러 슬라이드를 동시 생성한다.

핵심 설계(전부 실전 사고의 교훈 내장):
  1) 세션당 base_dir 하위 ASCII 격리 폴더 — %TEMP% 금지(codex Windows 샌드박스 split-root 거부)
  2) ★★ 잡별 CODEX_HOME 격리 — codex 세션이 ~/.codex 공유 상태(cap_sid 등)로 서로 내용을 섞는
     "고병렬 오염" 방지. auth.json+config.toml만 격리홈에 복사 → 고병렬에서도 안전
  3) codex 경로 shutil.which로 .cmd 셰임 해석
  4) 검증: 파일<100KB=PIL폴백/깨짐 WARN + ★중복 헤드라인 해시=내용오염 검출
  5) ★재귀 개선 루프(--loop N): 실패/오염 잡만 재생성, 전부 통과할 때까지 반복
  6) 고품질: --effort(reasoning) / --model / 프롬프트 고해상도 지시

사용:
  python codex_parallel_gen.py jobs.json --cap 10 --retry 1 --loop 4 --effort high
  jobs.json = [{"label","refs":[...],"out","prompt"}]  (경로는 jobs.json 기준 상대/절대)
"""
import sys, os, json, shutil, subprocess, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

CODEX = shutil.which("codex") or "codex"
BASE_FLAGS = ["exec", "-s", "workspace-write", "--skip-git-repo-check"]
USER_CODEX_HOME = os.path.join(os.path.expanduser("~"), ".codex")


def _ascii_id(job, idx):
    stem = os.path.splitext(os.path.basename(job.get("out", f"job{idx}")))[0]
    slug = "".join(c if (c.isascii() and (c.isalnum() or c in "_-")) else "" for c in stem)
    return slug or f"job{idx}"


def _iso_home(work):
    """잡별 격리 CODEX_HOME 생성 — 공유 세션상태 오염 차단. auth+config만 복사."""
    home = os.path.join(work, ".codexhome")
    os.makedirs(home, exist_ok=True)
    for fn in ("auth.json", "config.toml"):
        src = os.path.join(USER_CODEX_HOME, fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(home, fn))
    return home


def _run_one(job, base_dir, retry, idx=0, effort=None, model=None, timeout=590):
    """단일 codex 생성 잡 (격리 폴더 + 격리 CODEX_HOME에서 실행)."""
    prompt = job["prompt"]
    refs = [os.path.join(base_dir, r) if not os.path.isabs(r) else r for r in job.get("refs", [])]
    out = job["out"] if os.path.isabs(job["out"]) else os.path.join(base_dir, job["out"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    aid = _ascii_id(job, idx)
    label = job.get("label", aid)

    for attempt in range(retry + 1):
        work = os.path.join(base_dir, ".cxwork", f"{aid}_{attempt}")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        try:
            local_refs = []
            for r in refs:
                dst = os.path.join(work, os.path.basename(r))
                shutil.copy(r, dst)
                local_refs.append(os.path.basename(r))
            result_name = "__out.png"
            cmd = [CODEX] + BASE_FLAGS
            if effort:
                cmd += ["-c", f'model_reasoning_effort="{effort}"']
            if model:
                cmd += ["-m", model]
            for lr in local_refs:
                cmd += ["-i", lr]
            full_prompt = prompt + f"\n\n결과를 반드시 {result_name} (파일명 정확히) 로 저장하고 크기를 출력하라."
            env = dict(os.environ, CODEX_HOME=_iso_home(work))  # ★상태 격리
            # ★★ 캐시 즉시 반환 (2026-07-14): 이미지가 나타나는 순간 회수하고 codex 트리 강제종료.
            #    codex는 생성 후 후처리/요약에 수백 초 매달림 — 블로킹 대기는 순수 낭비 (검증: ppt-image-first bubu_genAB)
            import glob as _glob
            import time as _time
            proc = subprocess.Popen(cmd, cwd=work, stdin=subprocess.PIPE,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    text=True, encoding="utf-8", errors="replace", env=env)
            try:
                proc.stdin.write(full_prompt)
                proc.stdin.close()
            except OSError:
                pass
            result_path = os.path.join(work, result_name)
            cache_pat = os.path.join(work, ".codexhome", "generated_images", "**", "*.png")
            deadline = _time.time() + timeout
            produced = None
            _last = {}
            cache_stable_at = None
            while _time.time() < deadline:
                if os.path.exists(result_path):          # 정식 산출물(정확한 크기) 최우선
                    produced = result_path
                    break
                cands = _glob.glob(cache_pat, recursive=True)
                if cands:
                    newest = max(cands, key=os.path.getmtime)
                    sz = os.path.getsize(newest)
                    if sz > 100_000 and _last.get(newest) == sz:  # 크기 2연속 동일 = 쓰기 완료
                        if cache_stable_at is None:
                            cache_stable_at = _time.time()
                        # 캐시 확보 후 __out.png(리사이즈본)를 최대 45초만 더 기다림
                        if _time.time() - cache_stable_at > 45:
                            produced = newest
                            break
                    _last[newest] = sz
                if proc.poll() is not None:              # codex 자연 종료 → 마지막 스캔
                    if os.path.exists(result_path):
                        produced = result_path
                    elif cands:
                        produced = max(cands, key=os.path.getmtime)
                    break
                _time.sleep(3)
            # codex 트리 강제 종료 (매달림 제거) — 이미 죽었으면 무해
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
            if produced is None:
                produced = os.path.join(work, result_name)
            if not os.path.exists(produced):
                pngs = [os.path.join(work, f) for f in os.listdir(work)
                        if f.lower().endswith(".png") and f not in [os.path.basename(x) for x in local_refs]]
                if pngs:
                    produced = max(pngs, key=os.path.getmtime)
            if not os.path.exists(produced):
                # ★ no-output 플레이키 회수: codex가 저장은 건너뛰어도 격리홈 캐시엔 생성본이 남는다
                import glob as _glob
                cache = _glob.glob(os.path.join(work, ".codexhome", "generated_images", "**", "*.png"), recursive=True)
                if cache:
                    produced = max(cache, key=os.path.getmtime)
            if os.path.exists(produced):
                shutil.copy(produced, out)
                size_kb = os.path.getsize(out) // 1024
                # 30KB 미만만 PIL폴백/한글깨짐 의심 (표지·클로징 등 여백 많은 정상 슬라이드는 50~90KB로 정상)
                status = "WARN(PIL폴백의심<30KB)" if size_kb < 30 else "OK"
                return {"label": label, "status": status, "out": out, "size_kb": size_kb, "attempt": attempt + 1}
        except subprocess.TimeoutExpired:
            if attempt == retry:
                return {"label": label, "status": "FAIL(timeout)", "out": out}
        except Exception as e:
            if attempt == retry:
                return {"label": label, "status": f"FAIL({type(e).__name__})", "out": out}
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return {"label": label, "status": "FAIL(no-output)", "out": out}


def _ahash_head(path, hsize=16):
    """슬라이드 상단(헤드라인) 영역 average-hash — 중복(내용오염) 검출용."""
    try:
        from PIL import Image
        im = Image.open(path).convert("L")
        W, H = im.size
        strip = im.crop((0, 0, W, int(H * 0.22))).resize((hsize, hsize))
        px = list(strip.getdata())
        avg = sum(px) / len(px)
        return sum(1 << i for i, p in enumerate(px) if p > avg)
    except Exception:
        return None


def _hamming(a, b):
    return bin(a ^ b).count("1") if (a is not None and b is not None) else 999


def verify(jobs, base_dir, dup_check=False):
    """실패/오염 잡 라벨 반환. 크기<30KB(PIL폴백/깨짐) 검출.
    ⚠️ dup-headline은 기본 OFF: CODEX_HOME 격리가 내용오염을 이미 차단하므로 중복. 게다가
    에디토리얼 덱은 상단 여백+헤드라인 위치가 유사해 avg-hash가 닮아 '오염'으로 오탐 → 불필요 재생성.
    옛 draft-anchor 파이프라인(격리 없이 고병렬)에서만 --dup-check로 켤 것.
    ★ 어느 검사도 '한글 글자 깨짐'은 못 잡는다 → 반드시 사람 눈/비전으로 컨택트시트 검수."""
    bad = {}
    hashes = {}
    for j in jobs:
        out = j["out"] if os.path.isabs(j["out"]) else os.path.join(base_dir, j["out"])
        lbl = j.get("label", out)
        if not os.path.exists(out):
            bad[lbl] = "missing"; continue
        if os.path.getsize(out) < 30 * 1024:
            bad[lbl] = "small(<30KB)"; continue
        hashes[lbl] = _ahash_head(out)
    if dup_check:
        labels = list(hashes)
        for i in range(len(labels)):
            for k in range(i + 1, len(labels)):
                if _hamming(hashes[labels[i]], hashes[labels[k]]) <= 6:
                    bad.setdefault(labels[i], "dup-headline(오염)")
                    bad.setdefault(labels[k], "dup-headline(오염)")
    return bad


def run_round(jobs, base_dir, cap, retry, effort, model, timeout=590):
    results = []
    with ThreadPoolExecutor(max_workers=cap) as ex:
        futs = {ex.submit(_run_one, j, base_dir, retry, i, effort, model, timeout): j.get("label", i)
                for i, j in enumerate(jobs)}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            mark = "✓" if r["status"] == "OK" else ("!" if r["status"].startswith("WARN") else "✗")
            extra = f" {r.get('size_kb')}KB" if r.get("size_kb") else ""
            print(f"  {mark} {r['label']:20} {r['status']}{extra}", flush=True)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs_json")
    ap.add_argument("--cap", type=int, default=5, help="동시 실행 캡 (기본 5, 격리홈 있으면 고병렬 안전)")
    ap.add_argument("--retry", type=int, default=1, help="잡별 재시도 (기본 1)")
    ap.add_argument("--loop", type=int, default=3, help="재귀 개선 라운드 상한 (기본 3) — 전부 통과 시 조기 종료")
    ap.add_argument("--effort", default=None, help="reasoning effort (low/medium/high/xhigh)")
    ap.add_argument("--model", default=None, help="codex 모델 (gpt-5.5 최강 / gpt-5.4 균형)")
    ap.add_argument("--timeout", type=int, default=590, help="잡당 codex 타임아웃(초)")
    ap.add_argument("--dup-check", action="store_true",
                    help="중복 헤드라인(오염) 검사 켜기 — 격리 없는 옛 파이프라인에서만. 에디토리얼 덱은 오탐 유발하니 OFF 권장")
    args = ap.parse_args()

    with open(args.jobs_json, encoding="utf-8") as f:
        all_jobs = json.load(f)
    base_dir = os.path.dirname(os.path.abspath(args.jobs_json))

    # 선검증: 이미 정상인 슬라이드는 재생성하지 않음 (기존 결과 재활용)
    pre = verify(all_jobs, base_dir, args.dup_check)
    if not pre:
        print(f"[선검증] 전 {len(all_jobs)}장 이미 정상 — 생성 생략", flush=True)
        json.dump({"rounds": 0, "clean": True}, open(os.path.join(base_dir, "_gen_result.json"), "w"))
        return
    if pre and len(pre) < len(all_jobs):
        pending = [j for j in all_jobs if j.get("label") in pre]
        print(f"[선검증] 정상 {len(all_jobs)-len(pending)}장 유지, 불량 {len(pending)}장만 재생성 대상: "
              + ", ".join(f"{k}[{v}]" for k, v in pre.items()), flush=True)
    else:
        pending = all_jobs
    for rnd in range(1, args.loop + 1):
        print(f"[라운드 {rnd}/{args.loop}] {len(pending)}개 잡 · 동시성 {args.cap} · 재시도 {args.retry} · 격리홈 ON", flush=True)
        run_round(pending, base_dir, args.cap, args.retry, args.effort, args.model, args.timeout)
        bad = verify(all_jobs, base_dir, args.dup_check)
        if not bad:
            print(f"\n결과: 전 {len(all_jobs)}장 통과 (크기·중복 검증 clean) — 라운드 {rnd}에서 완료", flush=True)
            json.dump({"rounds": rnd, "clean": True}, open(os.path.join(base_dir, "_gen_result.json"), "w"))
            return
        print(f"  재생성 대상 {len(bad)}: " + ", ".join(f"{k}[{v}]" for k, v in bad.items()), flush=True)
        pending = [j for j in all_jobs if j.get("label") in bad]
    # 루프 소진
    bad = verify(all_jobs, base_dir)
    print(f"\n결과: 루프 {args.loop}회 소진, 잔여 {len(bad)}장: " + ", ".join(bad), flush=True)
    json.dump({"rounds": args.loop, "clean": False, "remaining": list(bad)},
              open(os.path.join(base_dir, "_gen_result.json"), "w"), ensure_ascii=False)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
