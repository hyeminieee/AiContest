"""REFLEX 실험 엔진: PN(입력) -> KC(학습 부위) <-> APL(억제) -> MBON(접근/회피 출력)

회로는 두 가지를 쓸 수 있다.
  real: FlyWire v783 오른쪽 반구에서 추출한 실제 연결(기본값). 연결은 고정이고 seed는 선택 난수만 바꾼다.
  toy : 예전 시제품의 무작위 연결. seed마다 연결도 새로 만든다(비교·시연용).
실제 회로에서 쓰는 연결과 처리 방법
  PN->KC  : 입력 PN(data/processed/input_pns.csv)에서 KC로 가는 시냅스 수를 그대로 사용
  KC<->APL: 실제 시냅스 수를 방향별 평균 1로 정규화. 기본·억제 약화 조건에 같은 값을 쓰고 g_apl만 바꾼다
  KC->MBON: 실제 연결이 아니라 팀이 만든 접근·회피 두 출력(가중치 1에서 시작). DAN은 보상 계산식으로 대신한다
선택과 학습은 모두 이 파일 안에서 계산하며, 화면이나 대화 AI는 값을 바꾸지 않는다.
"""
import argparse
import csv
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
STIMULI = {"A": "DM2", "B": "DM4"}  # 우선 검증 후보(팀 확정 전). src/compare_stimuli.py 집계 근거
N_PN_TOY, N_KC_TOY = 50, 2000
CONDITIONS = {
    "baseline": {"label": "기본", "g_apl": 1.0, "eta": 0.3},
    "learning_off": {"label": "학습 끔", "g_apl": 1.0, "eta": 0.0},
    "apl_weak": {"label": "APL 억제 약화", "g_apl": 0.2, "eta": 0.3},  # 0.2는 임시값(실제 회로에서 의미 재확인)
}
DEFAULTS = {"theta": 1.0, "gain": 30.0, "decay": 0.05, "beta": 8.0,
            "initial_trials": 40, "reversal_trials": 40,
            # 주 기준(팀 확정 전 임시값): 정답 선택 확률이 crit_p 이상인 시도가 crit_k번 연속
            "crit_p": 0.8, "crit_k": 5,
            # 보조 기준: 실제 선택 window번 중 need번 이상 정답
            "window": 10, "need": 9,
            # 보상 정책(팀 확정 전): reward_punish = 정답 보상(+1)·오답 처벌(-1) / reward_only = 정답 보상(+1)·오답 결과 없음(0)
            "reward_policy": "reward_punish"}
REWARD_POLICIES = ("reward_punish", "reward_only")


def make_toy_circuit(seed):
    """예전 시제품의 무작위 회로. 같은 seed면 조건이 달라도 같은 회로·자극을 쓴다(대응 비교)."""
    rng = np.random.default_rng(seed)
    conn = rng.random((N_KC_TOY, N_PN_TOY)) < 0.13
    W_pn_kc = conn * rng.lognormal(0, 0.5, (N_KC_TOY, N_PN_TOY))
    pn_A = np.zeros(N_PN_TOY)
    pn_A[rng.choice(N_PN_TOY, 12, replace=False)] = 1
    pn_B = pn_A.copy()
    flip = rng.choice(N_PN_TOY, 8, replace=False)
    pn_B[flip] = 1 - pn_B[flip]
    return {"W_pn_kc": W_pn_kc, "w_kc_apl": np.ones(N_KC_TOY), "w_apl_kc": np.ones(N_KC_TOY),
            "pn": {"A": pn_A, "B": pn_B}, "show": np.arange(N_KC_TOY),
            "source": "toy (무작위 연결)", "inputs": None, "normalization": None}


@lru_cache(maxsize=4)
def make_real_circuit(glom_a=STIMULI["A"], glom_b=STIMULI["B"]):
    """FlyWire v783 오른쪽 반구 버섯체 회로. 연결은 고정이라 seed와 무관하다."""
    import pandas as pd
    n = pd.read_csv(PROC / "mb_neurons.csv")
    e = pd.read_csv(PROC / "mb_edges.csv")
    inp = pd.read_csv(PROC / "input_pns.csv")
    kc_ids = n.loc[n.role == "KC", "root_id"].to_numpy()
    kc_idx = {k: i for i, k in enumerate(kc_ids)}
    pn_idx = {p: i for i, p in enumerate(inp.root_id)}

    pk = e[(e.pre_role == "PN") & (e.post_role == "KC") & e.pre.isin(pn_idx)]
    W = np.zeros((len(kc_ids), len(pn_idx)))
    W[pk.post.map(kc_idx).to_numpy(), pk.pre.map(pn_idx).to_numpy()] = pk.synapses.to_numpy()

    apl = n.loc[n.role == "APL", "root_id"]
    assert len(apl) == 1, "APL이 1개가 아님"
    apl = apl.iloc[0]
    k2a = e[(e.pre_role == "KC") & (e.post == apl)].groupby("pre").synapses.sum().reindex(kc_ids, fill_value=0)
    a2k = e[(e.pre == apl) & (e.post_role == "KC")].groupby("post").synapses.sum().reindex(kc_ids, fill_value=0)
    k2a, a2k = k2a.to_numpy(float), a2k.to_numpy(float)

    pn = {}
    for s, g in (("A", glom_a), ("B", glom_b)):
        v = (inp.glom == g).to_numpy(float)
        assert v.sum() > 0, f"입력 PN이 없는 사구체: {g}"
        pn[s] = v
    connected = (W @ pn["A"] > 0) | (W @ pn["B"] > 0)
    return {"W_pn_kc": W, "w_kc_apl": k2a / k2a.mean(), "w_apl_kc": a2k / a2k.mean(),
            "pn": pn, "show": np.flatnonzero(connected),
            "source": "FlyWire v783 오른쪽 반구 (data/processed)",
            "inputs": {"A": glom_a, "B": glom_b, "n_pn_A": int(pn["A"].sum()), "n_pn_B": int(pn["B"].sum())},
            "normalization": "PN->KC 시냅스 수 그대로, KC<->APL 시냅스 수를 방향별 평균 1로 정규화"}


def kc_response(pn, c, g_apl, theta, gain):
    """KC 활동과 APL 억제가 맞물린 안정 상태를 이분탐색으로 구한다. 반환: (KC 활동, APL 억제량, 식의 오차)

    억제량 I는 I = F(I)를 만족한다. F는 I가 커질수록 줄어들므로 I - F(I)는 증가 함수이고,
    I=0에서 음수가 아니면 0이 해다. 탐색 상한 안에 해가 있는지 먼저 확인하고, 없으면 상한을 넓힌다.
    """
    drive = c["W_pn_kc"] @ pn
    f = lambda I: np.maximum(drive - theta - c["w_apl_kc"] * I, 0)
    F = lambda I: g_apl * gain * (c["w_kc_apl"] @ f(I)) / len(drive)
    lo, hi = 0.0, max(float(drive.max()), 1.0)
    for _ in range(200):
        if hi - F(hi) >= 0:
            break
        hi *= 2
    else:
        raise RuntimeError("APL 억제량의 탐색 범위를 찾지 못함")
    for _ in range(200):
        I = (lo + hi) / 2
        if F(I) > I:
            lo = I
        else:
            hi = I
    I = (lo + hi) / 2
    resid = F(I) - I
    if abs(resid) > 1e-6 * (1 + I):
        raise RuntimeError(f"APL 억제량 계산 오차가 큼: {resid:.3g}")
    return f(I), I, resid


class Session:
    """한 마리 펫(한 번의 실행). 화면과 실험 실행기가 같은 클래스를 쓴다."""

    def __init__(self, condition="baseline", seed=0, circuit="real", **overrides):
        self.condition = condition
        self.seed = seed
        self.circuit_kind = circuit
        self.p = {**DEFAULTS, **CONDITIONS[condition], **overrides}
        if self.p["reward_policy"] not in REWARD_POLICIES:
            raise ValueError(f"보상 정책은 {REWARD_POLICIES} 중 하나")
        self.circuit = make_real_circuit() if circuit == "real" else make_toy_circuit(seed)
        self.rng = np.random.default_rng(10_000 + seed)  # 선택 난수. 실제 회로에서는 seed가 바꾸는 유일한 값
        self.kc, self.apl, self.apl_resid = {}, {}, {}
        for s in ("A", "B"):
            self.kc[s], self.apl[s], self.apl_resid[s] = kc_response(
                self.circuit["pn"][s], self.circuit, self.p["g_apl"], self.p["theta"], self.p["gain"])
        self.W = np.ones((2, len(self.kc["A"])))  # 0: KC->접근 MBON, 1: KC->회피 MBON
        self.good = "A"
        self.reversals = 0  # 규칙을 바꾼 횟수. 시도 기록의 단계(phase)는 이 값으로 정한다
        self.trial = 0
        self.history = []

    # ---- 측정값 ----
    def mbon(self, s):
        return {"approach": float(self.W[0] @ self.kc[s]), "avoid": float(self.W[1] @ self.kc[s])}

    def value(self, s):
        m = self.mbon(s)
        return (m["approach"] - m["avoid"]) / max(self.kc[s].sum(), 1e-9)

    def p_choose_A(self):
        return float(1 / (1 + np.exp(-self.p["beta"] * (self.value("A") - self.value("B")))))

    def sparseness(self, s):
        return float((self.kc[s] > 0).mean())

    def overlap(self):
        a, b = self.kc["A"] > 0, self.kc["B"] > 0
        return float((a & b).sum() / max((a | b).sum(), 1))

    def weight_summary(self, s):
        """자극 s에 반응한 KC들의 접근·회피 가중치 평균(연결 강도 변화 기록용)"""
        active = self.kc[s] > 0
        if not active.any():
            return {"approach": None, "avoid": None}
        return {"approach": float(self.W[0, active].mean()), "avoid": float(self.W[1, active].mean())}

    # ---- 조작 ----
    def learn(self, s, outcome):
        """outcome=+1(좋은 결과): 활성 KC->회피 MBON 약화 / -1(좋지 않은 결과): 활성 KC->접근 MBON 약화
        / 0(결과 없음): 보상·처벌에 따른 약화는 없고 회복 규칙만 적용된다.
        어느 경우든 모든 가중치가 초기값 쪽으로 decay만큼 회복된다(추가한 가정)."""
        if outcome not in (-1, 0, 1):
            raise ValueError("outcome은 -1, 0, 1 중 하나")
        if outcome != 0:
            active = self.kc[s] > 0
            row = 1 if outcome > 0 else 0
            self.W[row] -= self.p["eta"] * self.W[row] * active
        self.W += self.p["decay"] * (1.0 - self.W)

    def step(self, outcome_override=None):
        """시도 1회: 모델이 A/B를 고르고, 현재 규칙(또는 사람이 준 결과)으로 학습한다."""
        pA = self.p_choose_A()
        vA, vB = self.value("A"), self.value("B")
        choice = "A" if self.rng.random() < pA else "B"
        wrong = -1 if self.p["reward_policy"] == "reward_punish" else 0
        outcome = outcome_override if outcome_override is not None else (1 if choice == self.good else wrong)
        self.learn(choice, outcome)
        wA, wB = self.weight_summary("A"), self.weight_summary("B")
        rec = {"trial": self.trial, "phase": phase_name(self.reversals),
               "good": self.good, "choice": choice, "pA": pA, "p_correct": pA if self.good == "A" else 1 - pA,
               "value_A": vA, "value_B": vB, "outcome": outcome, "correct": choice == self.good,
               "wA_approach": wA["approach"], "wA_avoid": wA["avoid"],
               "wB_approach": wB["approach"], "wB_avoid": wB["avoid"]}
        self.history.append(rec)
        self.trial += 1
        return rec

    def reverse(self):
        self.good = "B" if self.good == "A" else "A"
        self.reversals += 1

    def state(self):
        last = self.history[-1] if self.history else None
        return {
            "condition": self.condition, "label": self.p["label"], "seed": self.seed,
            "trial": self.trial, "good": self.good, "pA": round(self.p_choose_A(), 3),
            "last_choice": last["choice"] if last else None,
            "last_outcome": ({1: "좋은 결과", -1: "좋지 않은 결과", 0: "결과 없음"}[last["outcome"]]) if last else None,
            "kc_active_A": round(self.sparseness("A"), 3), "kc_active_B": round(self.sparseness("B"), 3),
            "overlap_AB": round(self.overlap(), 3), "apl_inhibition_A": round(self.apl["A"], 3),
            "mbon_A": {k: round(v, 1) for k, v in self.mbon("A").items()},
            "mbon_B": {k: round(v, 1) for k, v in self.mbon("B").items()},
            "recent": [f'{r["choice"]}-{ {1: "좋음", -1: "나쁨", 0: "없음"}[r["outcome"]] }' for r in self.history[-5:]],
        }


def phase_name(reversals):
    return "initial" if reversals == 0 else "reversal" if reversals == 1 else f"reversal{reversals}"


# ---- 판정: 단계별 구간만 검사한다 ----
def phase_slice(history, p, phase):
    """그 단계(규칙 변경 전 = initial, 첫 변경 후 = reversal)로 기록된 시도 중 정해진 횟수까지만 쓴다.
    정식 절차(run_one)에서는 첫 학습 history[:n0], 재학습 history[n0:n0+n1]과 같다."""
    n = p["initial_trials"] if phase == "initial" else p["reversal_trials"]
    return [r for r in history if r["phase"] == phase][:n]


def reach_primary(seq, crit_p, crit_k):
    """주 기준: 정답 선택 확률(반올림 전)이 crit_p 이상인 시도가 crit_k번 연속된 마지막 시도 번호(단계 안 1부터)"""
    run = 0
    for i, r in enumerate(seq):
        run = run + 1 if r["p_correct"] >= crit_p else 0
        if run >= crit_k:
            return i + 1
    return None


def reach_secondary(seq, window, need):
    """보조 기준: 실제 선택 window번 중 need번 이상 정답인 구간이 처음 끝나는 시도 번호"""
    c = [r["correct"] for r in seq]
    for i in range(len(c) - window + 1):
        if sum(c[i:i + window]) >= need:
            return i + window
    return None


def run_one(condition, seed, circuit="real", **overrides):
    s = Session(condition, seed, circuit, **overrides)
    for _ in range(s.p["initial_trials"]):
        s.step()
    s.reverse()
    for _ in range(s.p["reversal_trials"]):
        s.step()
    out = {"condition": condition, "seed": seed, "kc_active": s.sparseness("A"), "kc_active_B": s.sparseness("B"),
           "overlap": s.overlap(), "apl_resid": max(abs(v) for v in s.apl_resid.values()), "history": s.history}
    for ph in ("initial", "reversal"):
        seq = phase_slice(s.history, s.p, ph)
        out[ph] = reach_primary(seq, s.p["crit_p"], s.p["crit_k"])
        out[ph + "_secondary"] = reach_secondary(seq, s.p["window"], s.p["need"])
    return out


def paired_signflip_p(x, y, n_perm=20000, seed=0):
    """대응 표본 부호 뒤집기 순열검정(양측). scipy 없이 Wilcoxon 대신 쓰는 간단한 방법."""
    d = np.asarray(x, float) - np.asarray(y, float)
    d = d[d != 0]
    if len(d) == 0:
        return 1.0
    obs = abs(d.mean())
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1, 1], size=(n_perm, len(d)))
    return float(((np.abs((signs * d).mean(axis=1)) >= obs).sum() + 1) / (n_perm + 1))


def cumulative_reach(values, n_trials, n_runs):
    """누적 도달 곡선: t번째 시도까지 기준에 한 번이라도 도달한 실행의 비율. 분모는 미도달을 포함한 전체 실행 수"""
    return [round(sum(v is not None and v <= t for v in values) / n_runs, 3) for t in range(1, n_trials + 1)]


def run_batch(n_seeds=30, seed_start=0, circuit="real", **overrides):
    """3개 조건 × n_seeds 반복. 원자료의 미도달은 None으로 남긴다."""
    seeds = list(range(seed_start, seed_start + n_seeds))
    params = {**DEFAULTS, **overrides}
    runs = {c: [run_one(c, s, circuit, **overrides) for s in seeds] for c in CONDITIONS}
    summary = {}
    for c, rs in runs.items():
        row = {"label": CONDITIONS[c]["label"], "n_runs": len(rs),
               "kc_active": round(float(np.mean([r["kc_active"] for r in rs])), 3),
               "overlap": round(float(np.mean([r["overlap"] for r in rs])), 3),
               "curve": np.mean([[h["pA"] for h in r["history"]] for r in rs], axis=0).round(3).tolist(),
               "curve_p_correct": np.mean([[h["p_correct"] for h in r["history"]] for r in rs], axis=0).round(3).tolist()}
        for ph, n_ph in (("initial", params["initial_trials"]), ("reversal", params["reversal_trials"])):
            for kind in ("", "_secondary"):
                vals = [r[ph + kind] for r in rs]
                reached = [v for v in vals if v is not None]
                row[ph + kind] = vals
                row[f"reached_{ph}{kind}"] = len(reached)
                row[f"median_reached_{ph}{kind}"] = float(np.median(reached)) if reached else None
                row[f"cumulative_{ph}{kind}"] = cumulative_reach(vals, n_ph, len(rs))
            row[f"fail_{ph}"] = row[f"n_runs"] - row[f"reached_{ph}"]
        row["reversal_given_initial"] = sum(r["reversal"] is not None for r in rs if r["initial"] is not None)
        row["initial_reached_runs"] = sum(r["initial"] is not None for r in rs)
        summary[c] = row
    # 벌점 점수(미도달 = 단계 시도 수 + 1)로 계산한 참고용 검정. 실제 41회 만에 학습했다는 뜻이 아니다
    penalty = lambda c, k, cap: [v if v is not None else cap for v in summary[c][k]]
    tests = {k: paired_signflip_p(penalty("apl_weak", k, params[k + "_trials"] + 1),
                                  penalty("baseline", k, params[k + "_trials"] + 1)) for k in ("initial", "reversal")}
    circ = make_real_circuit() if circuit == "real" else make_toy_circuit(seeds[0])
    condition_params = {c: {**DEFAULTS, **CONDITIONS[c], **overrides} for c in CONDITIONS}
    return {"n_seeds": n_seeds, "seeds": seeds, "params": params, "condition_params": condition_params, "conditions": summary,
            "criteria_note": "주 기준 crit_p·crit_k와 보조 기준 window·need는 팀 확정 전 임시값",
            "p_apl_vs_baseline": tests, "p_method": "미도달을 단계 시도 수+1로 둔 벌점 점수의 대응 부호 뒤집기 순열검정(참고용)",
            "circuit_source": circ["source"], "circuit_inputs": circ["inputs"],
            "circuit_normalization": circ["normalization"], "_runs": runs}


def save_results(out, tag):
    """원자료(시도별 기록)와 요약·설정을 poc/results/에 저장한다."""
    d = Path(__file__).parent / "results"
    d.mkdir(exist_ok=True)
    runs = out["_runs"]
    keys = list(next(iter(runs.values()))[0]["history"][0].keys())
    with open(d / f"{tag}_trials.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["condition", "seed"] + keys)
        for c, rs in runs.items():
            for r in rs:
                for h in r["history"]:
                    w.writerow([c, r["seed"]] + [h[k] for k in keys])
    with open(d / f"{tag}_runs.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        cols = ["initial", "initial_secondary", "reversal", "reversal_secondary", "kc_active", "kc_active_B", "overlap", "apl_resid"]
        w.writerow(["condition", "seed"] + cols)
        for c, rs in runs.items():
            for r in rs:
                w.writerow([c, r["seed"]] + ["미도달" if r[k] is None else r[k] for k in cols])
    summary = {k: v for k, v in out.items() if k != "_runs"}
    (d / f"{tag}_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="세 조건 반복 실행")
    ap.add_argument("--n", type=int, default=30, help="조건별 실행 수")
    ap.add_argument("--start", type=int, default=0, help="첫 seed (예비 실행과 본 실험은 다른 범위를 쓴다)")
    ap.add_argument("--circuit", choices=["real", "toy"], default="real")
    ap.add_argument("--tag", default=None, help="결과 파일 이름 앞부분 (지정하면 poc/results/에 저장)")
    a = ap.parse_args()
    out = run_batch(a.n, a.start, a.circuit)
    print(f"회로: {out['circuit_source']} / 입력: {out['circuit_inputs']} / seed {a.start}~{a.start + a.n - 1}")
    print(f"주 기준: 정답 확률 {DEFAULTS['crit_p']} 이상 {DEFAULTS['crit_k']}회 연속 (임시값) / "
          f"보조 기준: {DEFAULTS['window']}번 중 {DEFAULTS['need']}번 정답")
    for c, s in out["conditions"].items():
        print(f'{s["label"]}: KC활성 {s["kc_active"]} 활동겹침 {s["overlap"]} | '
              f'첫학습 도달 {s["reached_initial"]}/{s["n_runs"]} (중앙값 {s["median_reached_initial"]}) '
              f'재학습 도달 {s["reached_reversal"]}/{s["n_runs"]} (중앙값 {s["median_reached_reversal"]}) | '
              f'보조 첫학습 {s["reached_initial_secondary"]}/{s["n_runs"]} 재학습 {s["reached_reversal_secondary"]}/{s["n_runs"]}')
    print("참고 검정 p (APL 약화 vs 기본, 벌점 점수):", out["p_apl_vs_baseline"])
    if a.tag:
        print("저장:", save_results(out, a.tag))
