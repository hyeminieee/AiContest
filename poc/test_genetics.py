"""보상 정책·유전·교배 구현 검사 (docs/실험_확정표.md 6-1항)

실행:  python poc/test_genetics.py      (git이 필요: 기준 커밋의 엔진과 비교)
"""
import copy
import importlib.util
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

import engine
import genetics as G

HERE = Path(__file__).parent
BASE_COMMIT = "34a20e1"
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'통과' if ok else '실패'}] {name}" + (f" — {detail}" if detail else ""))


def old_engine():
    """기준 커밋의 engine.py를 임시 폴더에서 불러온다(데이터 경로는 지금 저장소로 맞춤)."""
    src = subprocess.run(["git", "show", f"{BASE_COMMIT}:poc/engine.py"], cwd=HERE, capture_output=True,
                         text=True, encoding="utf-8", check=True).stdout
    d = Path(tempfile.mkdtemp())
    (d / "engine_base.py").write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("engine_base", d / "engine_base.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.PROC = engine.PROC
    return m


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    # 1. 기본 모드 회귀 검사: 보상+처벌의 선택·확률·판정이 기준 커밋과 같은지
    old, worst, bad = old_engine(), 0.0, 0
    for c in engine.CONDITIONS:
        for s in range(30):
            a, b = old.run_one(c, s), engine.run_one(c, s)
            worst = max(worst, max(abs(x["pA"] - y["pA"]) for x, y in zip(a["history"], b["history"])))
            same = [x["choice"] for x in a["history"]] == [y["choice"] for y in b["history"]] and all(
                a[k] == b[k] for k in ("initial", "reversal", "initial_secondary", "reversal_secondary"))
            bad += not same
    check("기본 모드(보상+처벌)가 기준 커밋과 같음", bad == 0 and worst == 0.0, f"3조건 × seed 30, 불일치 {bad}, 확률 최대 차이 {worst}")

    # 2. 보상만: 오답에 결과 없음(0), 처벌(-1) 없음
    r = engine.run_one("baseline", 0, reward_policy="reward_only")
    outs = Counter(h["outcome"] for h in r["history"])
    check("보상만 정책에서 오답은 0, 처벌 없음", -1 not in outs and all(
        (h["outcome"] == 1) == h["correct"] for h in r["history"]), dict(outs))
    try:
        engine.Session("baseline", 0, reward_policy="잘못된값")
        check("잘못된 보상 정책을 거부", False)
    except ValueError:
        check("잘못된 보상 정책을 거부", True)

    # 3. 코드 왕복 변환(유효 코드)과 잘못된 코드 거부
    ok = all(G.encode(G.decode(G.encode(c))[0]) == G.encode(c) and G.from_hex(G.to_hex(G.encode(c))) == G.encode(c)
             for c in G.all_combinations())
    check("유효 코드 4개의 왕복 변환", ok, f"예: {G.to_hex(G.encode({'g_apl': 'high', 'decay': 'low'}))}")
    rejected = 0
    for code in (G.slot_set(0, 5, 1), G.slot_set(G.encode({"g_apl": "high", "decay": "low"}), 0, 0x1234), 1 << 256):
        try:
            G.validate(code)
        except ValueError:
            rejected += 1
    check("잘못된 코드 거부(안 쓰는 칸, 정해지지 않은 값, 256비트 초과)", rejected == 3)

    # 4. 상속 비율: 두 성향이 모두 다른 부모 → 네 조합 각 약 25%, 한 성향이 같으면 두 조합만
    p1, p2 = G.founder("P1", {"g_apl": "high", "decay": "low"}), G.founder("P2", {"g_apl": "low", "decay": "high"})
    kids = G.breed(p1, p2, 20000, breed_seed=1, family_id="T")
    freq = Counter(tuple(k.levels.values()) for k in kids)
    share = {k: v / len(kids) for k, v in freq.items()}
    check("두 성향이 모두 다른 부모: 네 조합이 각 약 25%", len(freq) == 4 and all(abs(v - 0.25) < 0.015 for v in share.values()),
          {"/".join(k): round(v, 3) for k, v in sorted(share.items())})
    p3 = G.founder("P3", {"g_apl": "high", "decay": "high"})
    freq2 = Counter(tuple(k.levels.values()) for k in G.breed(p1, p3, 2000, breed_seed=2, family_id="U"))
    check("한 성향(억제)이 같은 부모: 가능한 조합 2개", len(freq2) == 2 and all(k[0] == "high" for k in freq2), dict(freq2))

    # 5. 새끼 초기화와 부모 불변
    parent_before = copy.deepcopy((p1, p2))
    ps = G.session_for(p1, 0)
    for _ in range(80):
        ps.step()
    child = G.breed(p1, p2, 1, breed_seed=3, family_id="V")[0]
    cs = G.session_for(child, 0)
    check("새끼 세션이 학습 전 상태(가중치 1, 기록 없음, 규칙 변경 0)",
          np.all(cs.W == 1) and cs.history == [] and cs.reversals == 0 and cs.good == "A" and cs.trial == 0)
    check("교배 후 부모 성향 코드가 그대로", (p1, p2) == parent_before and len(ps.history) == 80)
    check("새끼 기록에 부모·가족·받은 출처가 남음", child.parents == ("P1", "P2") and child.family_id == "V"
          and set(child.inherited_from) == set(G.TRAITS))

    # 6. 학습 끔 유지: 성향 설정을 적용해도 학습률 0
    w_ok = True
    for c in G.all_combinations():
        s = G.session_for(G.Pet("x", G.encode(c)), 0, "learning_off")
        for _ in range(80):
            s.step()
        w_ok &= s.p["eta"] == 0 and np.all(s.W == 1)
    check("학습 끔 조건에서 네 조합 모두 학습률 0, 가중치 불변", bool(w_ok))
    try:
        G.session_for(p1, 0, eta=0.5)
        check("성향 실험에서 학습률 덮어쓰기 거부", False)
    except ValueError:
        check("성향 실험에서 학습률 덮어쓰기 거부", True)
    try:
        G.session_for(p1, 0, "apl_weak")
        check("성향 실험에서 apl_weak 조건 거부(억제는 코드로 정함)", False)
    except ValueError:
        check("성향 실험에서 apl_weak 조건 거부(억제는 코드로 정함)", True)

    # 7. 성향 설정이 실제로 적용되는지
    s = G.session_for(G.Pet("y", G.encode({"g_apl": "low", "decay": "high"})), 0)
    check("코드의 설정이 세션에 적용됨", s.p["g_apl"] == 0.2 and s.p["decay"] == 0.017, f"g_apl {s.p['g_apl']}, decay {s.p['decay']}")

    print(f"\n결과: {sum(results)}/{len(results)} 통과")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
