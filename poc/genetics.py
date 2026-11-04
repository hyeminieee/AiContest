"""가상 성향 유전과 교배 (engine.py 위에 얹는 층)

팀이 정한 **가상 유전 규칙**이다. 실제 초파리나 사람의 유전을 재현하지 않는다.
  - 성향 코드: 256비트(16진수 64자리)를 16비트 칸 16개로 나눈다.
  - 물려주는 것: 성향 설정(억제 강도 g_apl, 회복 속도 decay)만. 학습된 연결·기록은 물려주지 않는다.
  - 교배: 성향마다 독립적으로 부모 중 한쪽의 칸을 50% 확률로 받는다. 돌연변이 없음, 부모–새끼 2세대.
값과 대응표는 모두 팀 확정 전 임시값이다(docs/실험_확정표.md).

실행:  python poc/genetics.py --demo      (임시값으로 작은 시범 실행, 결과는 poc/results/)
검사:  python poc/test_genetics.py
"""
import argparse
import csv
import itertools
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

import engine

N_SLOTS, SLOT_BITS = 16, 16
HIGH, LOW = 0xFFFF, 0x0000
# 성향 대응표(팀 확정 전 임시값). 칸 번호, 칸 값별 설정값, 화면 표시
TRAITS = {
    "g_apl": {"slot": 0, "values": {HIGH: 1.0, LOW: 0.2}, "labels": {HIGH: "억제 강함", LOW: "억제 약함"}},
    # decay는 값이 작을수록 경험 유지가 강함 → 칸 값 HIGH(유지 강함) = 작은 decay
    "decay": {"slot": 1, "values": {HIGH: 0.017, LOW: 0.067}, "labels": {HIGH: "경험 유지 강함", LOW: "경험 유지 약함"}},
}
LEVELS = {"high": HIGH, "low": LOW}


# ---- 256비트 코드 ----
def slot_get(code, slot):
    return (code >> (slot * SLOT_BITS)) & 0xFFFF


def slot_set(code, slot, value):
    mask = 0xFFFF << (slot * SLOT_BITS)
    return (code & ~mask) | ((value & 0xFFFF) << (slot * SLOT_BITS))


def encode(levels):
    """{"g_apl": "high", "decay": "low"} → 256비트 정수"""
    if set(levels) != set(TRAITS):
        raise ValueError(f"성향은 {sorted(TRAITS)} 모두 필요")
    code = 0
    for t, lv in levels.items():
        code = slot_set(code, TRAITS[t]["slot"], LEVELS[lv])
    return code


def validate(code):
    """팀이 정한 유효 코드인지: 256비트 이내, 쓰는 칸은 HIGH/LOW, 쓰지 않는 칸은 0"""
    if not (0 <= code < 1 << (N_SLOTS * SLOT_BITS)):
        raise ValueError("256비트 범위를 벗어남")
    used = {v["slot"] for v in TRAITS.values()}
    for s in range(N_SLOTS):
        v = slot_get(code, s)
        if s in used and v not in (HIGH, LOW):
            raise ValueError(f"{s}번 칸 값 {v:#06x}는 정해진 값이 아님")
        if s not in used and v != 0:
            raise ValueError(f"사용하지 않는 {s}번 칸이 0이 아님")
    return code


def decode(code):
    """코드 → (단계, 설정값, 화면 표시)"""
    validate(code)
    levels, settings, labels = {}, {}, {}
    for t, spec in TRAITS.items():
        v = slot_get(code, spec["slot"])
        levels[t] = "high" if v == HIGH else "low"
        settings[t] = spec["values"][v]
        labels[t] = spec["labels"][v]
    return levels, settings, labels


def to_hex(code):
    return f"{code:064x}"


def from_hex(text):
    return validate(int(text, 16))


# ---- 펫과 교배 ----
@dataclass(frozen=True)
class Pet:
    pet_id: str
    code: int
    generation: int = 1
    family_id: str = ""
    parents: tuple = ()
    origin: str = "founder"          # founder / random_cross / controlled
    inherited_from: dict = field(default_factory=dict)  # 성향별로 어느 부모에게서 받았는지

    @property
    def levels(self):
        return decode(self.code)[0]

    @property
    def settings(self):
        return decode(self.code)[1]

    @property
    def labels(self):
        return decode(self.code)[2]

    def row(self):
        d = asdict(self)
        d.update(code=to_hex(self.code), parents=",".join(self.parents),
                 inherited_from=json.dumps(self.inherited_from, ensure_ascii=False),
                 **{f"{t}_level": lv for t, lv in self.levels.items()}, **self.settings)
        return d


def founder(pet_id, levels):
    return Pet(pet_id, encode(levels))


def cross(a, b, rng, child_id, family_id):
    """성향마다 독립적으로 부모 a 또는 b의 칸을 50% 확률로 받는다. 부모 객체는 바꾸지 않는다."""
    code, src = 0, {}
    for t, spec in TRAITS.items():
        p = a if rng.random() < 0.5 else b
        code = slot_set(code, spec["slot"], slot_get(p.code, spec["slot"]))
        src[t] = p.pet_id
    return Pet(child_id, validate(code), max(a.generation, b.generation) + 1, family_id,
               (a.pet_id, b.pet_id), "random_cross", src)


def breed(a, b, n_children, breed_seed, family_id):
    """무작위 교배: 교배 난수(breed_seed)는 학습용 선택 seed와 따로 쓰고 기록한다."""
    rng = np.random.default_rng(breed_seed)
    return [cross(a, b, rng, f"{family_id}-c{i + 1}", family_id) for i in range(n_children)]


# ---- 훈련 ----
def session_for(pet, seed, condition="baseline", **overrides):
    """펫의 성향 설정을 적용한 새 세션(학습 전 상태). 학습 끔 조건의 학습률은 덮어쓰지 않는다."""
    if condition not in ("baseline", "learning_off"):
        raise ValueError("펫 실험에서는 baseline 또는 learning_off만 씀(억제 강도는 성향 코드로 정함)")
    if set(overrides) & set(TRAITS) or "eta" in overrides:
        raise ValueError("성향 설정과 학습률은 overrides로 바꾸지 않음")
    s = engine.Session(condition, seed, "real", **pet.settings, **overrides)
    assert s.p["eta"] == engine.CONDITIONS[condition]["eta"]
    return s


def train(pet, seed, condition="baseline", **overrides):
    """정식 절차(첫 학습 → 규칙 변경 → 재학습) 한 번. engine.run_one과 같은 판정을 쓴다."""
    session_for(pet, seed, condition, **overrides)  # 조건 검사
    r = engine.run_one(condition, seed, "real", **pet.settings, **overrides)
    return {"pet_id": pet.pet_id, "family_id": pet.family_id, "origin": pet.origin, "condition": condition,
            "seed": seed, **{f"{t}_level": lv for t, lv in pet.levels.items()}, **pet.settings,
            "initial": r["initial"], "reversal": r["reversal"],
            "initial_secondary": r["initial_secondary"], "reversal_secondary": r["reversal_secondary"],
            "kc_active": r["kc_active"], "overlap": r["overlap"], "history": r["history"]}


# ---- 실험 실행기 ----
def all_combinations():
    """두 성향 × 두 단계 = 네 조합 (통제 비교용)"""
    return [dict(zip(TRAITS, lv)) for lv in itertools.product(("high", "low"), repeat=len(TRAITS))]


def controlled_comparison(seeds, include_learning_off=True, **overrides):
    """통제 비교: 네 조합에 같은 seed 범위를 쓴다. 무작위 교배 결과와 구분해 origin='controlled'로 기록"""
    pets = [Pet(f"combo-{'-'.join(f'{t}_{lv}' for t, lv in c.items())}", encode(c), origin="controlled")
            for c in all_combinations()]
    conds = ["baseline"] + (["learning_off"] if include_learning_off else [])
    runs = [train(p, s, c, **overrides) for p in pets for c in conds for s in seeds]
    return pets, runs


def summarize(runs, key=("g_apl_level", "decay_level", "condition"), n_trials=None):
    n_trials = n_trials or {"initial": engine.DEFAULTS["initial_trials"], "reversal": engine.DEFAULTS["reversal_trials"]}
    out = {}
    for r in runs:
        out.setdefault(tuple(r[k] for k in key), []).append(r)
    rows = []
    for k, rs in sorted(out.items()):
        row = dict(zip(key, k), n_runs=len(rs))
        for ph in ("initial", "reversal"):
            vals = [r[ph] for r in rs]
            reached = [v for v in vals if v is not None]
            row[f"reached_{ph}"] = len(reached)
            row[f"median_reached_{ph}"] = float(np.median(reached)) if reached else None
            row[f"cumulative_{ph}"] = engine.cumulative_reach(vals, n_trials[ph], len(rs))
        rows.append(row)
    return rows


def save(tag, pets, runs, meta):
    d = Path(__file__).parent / "results"
    d.mkdir(exist_ok=True)
    with open(d / f"{tag}_pets.csv", "w", newline="", encoding="utf-8-sig") as f:
        rows = [p.row() for p in pets]
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(d / f"{tag}_runs.csv", "w", newline="", encoding="utf-8-sig") as f:
        cols = [k for k in runs[0] if k != "history"]
        w = csv.writer(f)
        w.writerow(cols)
        for r in runs:
            w.writerow(["미도달" if r[c] is None and c in ("initial", "reversal", "initial_secondary", "reversal_secondary") else r[c] for c in cols])
    with open(d / f"{tag}_trials.csv", "w", newline="", encoding="utf-8-sig") as f:
        keys = list(runs[0]["history"][0])
        w = csv.writer(f)
        w.writerow(["pet_id", "condition", "seed"] + keys)
        for r in runs:
            for h in r["history"]:
                w.writerow([r["pet_id"], r["condition"], r["seed"]] + [h[k] for k in keys])
    meta = {**meta, "traits": {t: {"slot": s["slot"], "values": {f"{k:#06x}": v for k, v in s["values"].items()},
                                   "labels": {f"{k:#06x}": v for k, v in s["labels"].items()}} for t, s in TRAITS.items()},
            "engine_defaults": engine.DEFAULTS, "note": "성향 값·대응표·보상 정책·판정 기준은 팀 확정 전 임시값"}
    (d / f"{tag}_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="가상 성향 교배 시범 실행(임시값)")
    ap.add_argument("--demo", action="store_true", help="작은 시범 실행: 통제 비교 4조합 × seed 5개 + 무작위 교배 1가족")
    ap.add_argument("--reward", choices=engine.REWARD_POLICIES, default=engine.DEFAULTS["reward_policy"])
    a = ap.parse_args()
    if not a.demo:
        ap.error("지금은 --demo만 지원합니다. 본 실험은 팀이 값을 확정한 뒤 실행합니다.")
    seeds = list(range(5))  # 예비 범위(0–29) 안의 시범 seed. 본 실험 seed(1000–)는 쓰지 않음
    pets, runs = controlled_comparison(seeds, reward_policy=a.reward)
    p1 = founder("P1", {"g_apl": "high", "decay": "low"})
    p2 = founder("P2", {"g_apl": "low", "decay": "high"})
    kids = breed(p1, p2, 8, breed_seed=7, family_id="F1")
    runs += [train(k, 100 + i, reward_policy=a.reward) for i, k in enumerate(kids)]
    tag = f"genetics_demo_{a.reward}"
    save(tag, [*pets, p1, p2, *kids], runs, {"reward_policy": a.reward, "train_seeds": seeds, "breed_seed": 7,
                                             "kind": "시범 실행(설계 점검용, 결론 아님)"})
    print(f"[시범 실행 · 임시값 · 보상 정책 {a.reward}]")
    for r in summarize([r for r in runs if r["origin"] == "controlled"]):
        print(f"  {r['g_apl_level']:>4}/{r['decay_level']:>4} {r['condition']:<12} 첫학습 {r['reached_initial']}/{r['n_runs']}"
              f" 재학습 {r['reached_reversal']}/{r['n_runs']} (중앙값 {r['median_reached_reversal']})")
    print("  무작위 교배 F1(P1 억제강함·유지약함 × P2 억제약함·유지강함) 새끼 8마리:",
          {lab: sum(1 for k in kids if tuple(k.labels.values()) == lab) for lab in {tuple(k.labels.values()) for k in kids}})
    print("저장:", Path(__file__).parent / "results" / f"{tag}_*")
