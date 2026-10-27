"""REFLEX toy mushroom-body model (PoC 1일차용, 가짜 연결로 먼저 돌려보기)
PN(입력) -> KC(학습 부위) <-> APL(억제) -> MBON(접근/회피 출력)
나중에 W_pn_kc, w_kc_apl, w_apl_kc, W_kc_mbon 을 FlyWire 실제 값으로 교체한다.
"""
import numpy as np

def make_net(rng, n_pn=50, n_kc=2000, n_mbon=2):
    # 각 KC가 PN 약 6~7개에서 입력을 받는 무작위 연결 (실제 데이터로 교체 예정)
    conn = rng.random((n_kc, n_pn)) < 0.13
    W_pn_kc = conn * rng.lognormal(0, 0.5, (n_kc, n_pn))   # 시냅스 수처럼 크기가 다른 연결
    w_kc_apl = np.ones(n_kc)            # KC -> APL
    w_apl_kc = np.ones(n_kc)            # APL -> KC
    W_kc_mbon = np.ones((n_mbon, n_kc))  # 0: 접근 MBON, 1: 회피 MBON
    return W_pn_kc, w_kc_apl, w_apl_kc, W_kc_mbon

def kc_response(pn, W_pn_kc, w_kc_apl, w_apl_kc, g_apl, theta=1.0, gain=30.0):
    """KC 활동과 APL 억제가 서로 맞물린 안정 상태(I = APL 억제량)를 이분탐색으로 구한다.
    g_apl: APL이 KC를 억제하는 강도 배율 (1.0=기본, 0.2=약화). 세포를 지우지 않고 강도만 낮춘다."""
    drive = W_pn_kc @ pn
    f = lambda I: np.maximum(drive - theta - w_apl_kc * I, 0)
    lo, hi = 0.0, float(drive.max())
    for _ in range(60):
        I = (lo + hi) / 2
        if g_apl * gain * (w_kc_apl @ f(I)) / len(drive) > I:
            lo = I
        else:
            hi = I
    return f((lo + hi) / 2)

def run(g_apl=1.0, eta=0.3, decay=0.05, beta=8.0, n_trials=80, reverse_at=40, seed=0):
    rng = np.random.default_rng(seed)
    W_pn_kc, w_kc_apl, w_apl_kc, W = make_net(rng)
    W = W.copy()
    # 자극 A, B: 일부 PN을 공유하는 비슷한 두 입력
    pn_A = np.zeros(50); pn_A[rng.choice(50, 12, replace=False)] = 1
    pn_B = pn_A.copy(); flip = rng.choice(50, 8, replace=False); pn_B[flip] = 1 - pn_B[flip]
    kcA = kc_response(pn_A, W_pn_kc, w_kc_apl, w_apl_kc, g_apl)
    kcB = kc_response(pn_B, W_pn_kc, w_kc_apl, w_apl_kc, g_apl)
    actA, actB = kcA > 0, kcB > 0
    overlap = (actA & actB).sum() / max((actA | actB).sum(), 1)
    log = []
    for t in range(n_trials):
        good = "A" if t < reverse_at else "B"     # 조건 변경(역전)
        vA = (W[0] - W[1]) @ kcA; vB = (W[0] - W[1]) @ kcB
        nA, nB = max(kcA.sum(), 1e-9), max(kcB.sum(), 1e-9)
        pA = 1 / (1 + np.exp(-beta * (vA / nA - vB / nB)))   # 두 자극의 가치 차이 -> 선택 확률
        choice = "A" if rng.random() < pA else "B"
        kc = kcA if choice == "A" else kcB
        if choice == good:   # 좋은 결과: 회피 MBON으로 가는 연결 약화
            W[1] -= eta * W[1] * (kc > 0)
        else:                # 좋지 않은 결과: 접근 MBON으로 가는 연결 약화
            W[0] -= eta * W[0] * (kc > 0)
        W += decay * (1.0 - W)   # 시간이 지나면 연결이 원래 값으로 서서히 회복(망각)
        log.append(dict(trial=t, good=good, choice=choice, pA=round(pA, 3), correct=choice == good))
    return log, actA.mean(), actB.mean(), overlap

def trials_to_criterion(log, start, window=10, need=8):
    seq = [r["correct"] for r in log[start:]]
    for i in range(len(seq) - window + 1):
        if sum(seq[i:i + window]) >= need:
            return i + window
    return None

if __name__ == "__main__":
    for name, g, eta in [("기본", 1.0, 0.3), ("학습끔", 1.0, 0.0), ("APL약화", 0.2, 0.3)]:
        first, rev, ov, sp = [], [], [], []
        for s in range(10):
            log, a, b, o = run(g_apl=g, eta=eta, seed=s)
            first.append(trials_to_criterion(log, 0)); rev.append(trials_to_criterion(log, 40)); ov.append(o); sp.append(a)
        fmt = lambda xs: [x if x is not None else "실패" for x in xs]
        print(f"{name}: 활성KC비율={np.mean(sp):.3f} 겹침={np.mean(ov):.2f} 첫학습={fmt(first)} 역전={fmt(rev)}")
