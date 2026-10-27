"""REFLEX 실험 엔진: PN(입력) -> KC(학습 부위) <-> APL(억제) -> MBON(접근/회피 출력)

현재 연결은 무작위로 만든 장난감(toy) 연결이다. FlyWire v783 회로를 추출하면
make_circuit()만 실제 시냅스 수 행렬로 바꾸고 나머지 코드는 그대로 쓴다.
선택과 학습은 모두 이 파일 안에서 계산하며, 화면이나 대화 AI는 값을 바꾸지 않는다.
"""
import numpy as np

N_PN, N_KC = 50, 2000
CONDITIONS = {
    "baseline": {"label": "기본", "g_apl": 1.0, "eta": 0.3},
    "learning_off": {"label": "학습 끔", "g_apl": 1.0, "eta": 0.0},
    "apl_weak": {"label": "APL 억제 약화", "g_apl": 0.2, "eta": 0.3},
}
DEFAULTS = {"theta": 1.0, "gain": 30.0, "decay": 0.05, "beta": 8.0,
            "initial_trials": 40, "reversal_trials": 40, "window": 10, "need": 9}


def make_circuit(seed):
    """회로와 자극 A·B를 만든다. 같은 seed면 조건이 달라도 같은 회로·자극을 쓴다(대응 비교)."""
    rng = np.random.default_rng(seed)
    conn = rng.random((N_KC, N_PN)) < 0.13
    W_pn_kc = conn * rng.lognormal(0, 0.5, (N_KC, N_PN))
    pn_A = np.zeros(N_PN)
    pn_A[rng.choice(N_PN, 12, replace=False)] = 1
    pn_B = pn_A.copy()
    flip = rng.choice(N_PN, 8, replace=False)
    pn_B[flip] = 1 - pn_B[flip]
    return {"W_pn_kc": W_pn_kc, "w_kc_apl": np.ones(N_KC), "w_apl_kc": np.ones(N_KC),
            "pn": {"A": pn_A, "B": pn_B}, "source": "toy (무작위 연결, FlyWire 교체 예정)"}


def kc_response(pn, c, g_apl, theta, gain):
    """KC 활동과 APL 억제가 맞물린 안정 상태를 이분탐색으로 구한다. 반환: (KC 활동, APL 억제량)"""
    drive = c["W_pn_kc"] @ pn
    f = lambda I: np.maximum(drive - theta - c["w_apl_kc"] * I, 0)
    lo, hi = 0.0, float(drive.max())
    for _ in range(60):
        I = (lo + hi) / 2
        if g_apl * gain * (c["w_kc_apl"] @ f(I)) / len(drive) > I:
            lo = I
        else:
            hi = I
    I = (lo + hi) / 2
    return f(I), I


class Session:
    """한 마리 펫(한 번의 실행). 화면과 실험 실행기가 같은 클래스를 쓴다."""

    def __init__(self, condition="baseline", seed=0, **overrides):
        self.condition = condition
        self.seed = seed
        self.p = {**DEFAULTS, **CONDITIONS[condition], **overrides}
        self.circuit = make_circuit(seed)
        self.rng = np.random.default_rng(10_000 + seed)
        self.kc, self.apl = {}, {}
        for s in ("A", "B"):
            self.kc[s], self.apl[s] = kc_response(self.circuit["pn"][s], self.circuit,
                                                  self.p["g_apl"], self.p["theta"], self.p["gain"])
        self.W = np.ones((2, N_KC))  # 0: KC->접근 MBON, 1: KC->회피 MBON
        self.good = "A"
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

    # ---- 조작 ----
    def learn(self, s, outcome):
        """outcome=+1(좋은 결과): 활성 KC->회피 MBON 약화 / -1(좋지 않은 결과): 활성 KC->접근 MBON 약화"""
        active = self.kc[s] > 0
        row = 1 if outcome > 0 else 0
        self.W[row] -= self.p["eta"] * self.W[row] * active
        self.W += self.p["decay"] * (1.0 - self.W)  # 서서히 원래 값으로 회복(망각)

    def step(self, outcome_override=None):
        """시도 1회: 모델이 A/B를 고르고, 현재 규칙(또는 사람이 준 보상/벌)으로 학습한다."""
        pA = self.p_choose_A()
        choice = "A" if self.rng.random() < pA else "B"
        outcome = outcome_override if outcome_override is not None else (1 if choice == self.good else -1)
        self.learn(choice, outcome)
        rec = {"trial": self.trial, "good": self.good, "choice": choice, "pA": round(pA, 4),
               "outcome": outcome, "correct": choice == self.good}
        self.history.append(rec)
        self.trial += 1
        return rec

    def reverse(self):
        self.good = "B" if self.good == "A" else "A"

    def state(self):
        last = self.history[-1] if self.history else None
        return {
            "condition": self.condition, "label": self.p["label"], "seed": self.seed,
            "trial": self.trial, "good": self.good, "pA": round(self.p_choose_A(), 3),
            "last_choice": last["choice"] if last else None,
            "last_outcome": ("좋은 결과" if last["outcome"] > 0 else "좋지 않은 결과") if last else None,
            "kc_active_A": round(self.sparseness("A"), 3), "kc_active_B": round(self.sparseness("B"), 3),
            "overlap_AB": round(self.overlap(), 3), "apl_inhibition_A": round(self.apl["A"], 3),
            "mbon_A": {k: round(v, 1) for k, v in self.mbon("A").items()},
            "mbon_B": {k: round(v, 1) for k, v in self.mbon("B").items()},
            "recent": [f'{r["choice"]}-{"좋음" if r["outcome"] > 0 else "나쁨"}' for r in self.history[-5:]],
        }


def trials_to_criterion(history, start, window, need):
    seq = [r["correct"] for r in history[start:]]
    for i in range(len(seq) - window + 1):
        if sum(seq[i:i + window]) >= need:
            return i + window
    return None


def run_one(condition, seed):
    s = Session(condition, seed)
    for _ in range(s.p["initial_trials"]):
        s.step()
    s.reverse()
    for _ in range(s.p["reversal_trials"]):
        s.step()
    n0, w, need = s.p["initial_trials"], s.p["window"], s.p["need"]
    return {"condition": condition, "seed": seed,
            "initial": trials_to_criterion(s.history, 0, w, need),
            "reversal": trials_to_criterion(s.history, n0, w, need),
            "kc_active": s.sparseness("A"), "overlap": s.overlap(), "history": s.history}


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


def run_batch(n_seeds=30):
    """3개 조건 × n_seeds 반복. 기준 미달(실패)은 시도 수를 상한(=시도 수+1)으로 두고 따로 센다."""
    runs = {c: [run_one(c, s) for s in range(n_seeds)] for c in CONDITIONS}
    cap = DEFAULTS["reversal_trials"] + 1
    summary = {}
    for c, rs in runs.items():
        summary[c] = {
            "label": CONDITIONS[c]["label"],
            "initial": [r["initial"] for r in rs], "reversal": [r["reversal"] for r in rs],
            "kc_active": round(float(np.mean([r["kc_active"] for r in rs])), 3),
            "overlap": round(float(np.mean([r["overlap"] for r in rs])), 3),
            "fail_initial": sum(r["initial"] is None for r in rs),
            "fail_reversal": sum(r["reversal"] is None for r in rs),
            "curve": np.mean([[h["correct"] for h in r["history"]] for r in rs], axis=0).round(3).tolist(),
        }
    filled = lambda c, k: [v if v is not None else cap for v in summary[c][k]]
    tests = {k: paired_signflip_p(filled("apl_weak", k), filled("baseline", k)) for k in ("initial", "reversal")}
    return {"n_seeds": n_seeds, "params": DEFAULTS, "conditions": summary, "p_apl_vs_baseline": tests,
            "circuit_source": make_circuit(0)["source"]}


if __name__ == "__main__":
    out = run_batch(30)
    for c, s in out["conditions"].items():
        med = lambda xs: np.median([x for x in xs if x is not None]) if any(x is not None for x in xs) else None
        print(f'{s["label"]}: KC활성 {s["kc_active"]} 겹침 {s["overlap"]} '
              f'첫학습 중앙값 {med(s["initial"])} (실패 {s["fail_initial"]}) '
              f'역전 중앙값 {med(s["reversal"])} (실패 {s["fail_reversal"]})')
    print("APL약화 vs 기본 p:", out["p_apl_vs_baseline"])
