"""자극 A·B 후보 쌍 찾기

자극 = 한 사구체(glomerulus)의 PN 묶음. PN 종류 이름의 앞부분(DM1_lPN → DM1)이 사구체 이름이다.
여러 사구체에서 오는 PN(이름이 M_ 로 시작)은 제외한다.

기준
  1. 입력받는 KC가 100개 이상인 사구체만 사용
  2. 두 자극이 입력하는 KC 수의 비가 1.25 이하 (연결을 받는 KC 수가 비교적 비슷한 후보를 선정)
  3. 겹침(Jaccard) 큰 쌍 = 연결된 KC 집합의 겹침이 큰 입력 경로 후보, 작은 쌍 = 겹침이 작은 입력 경로 후보

주의: 여기서 겹침은 '입력을 받는 KC' 기준이다. 실제로 켜지는 KC는 모델의 문턱값과 APL 억제에 따라
달라지므로, 고른 후보는 예비 실행에서 실제 반응 비율과 겹침을 다시 확인한다.

실행:  python src/choose_stimuli.py
"""
import itertools
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
n = pd.read_csv(ROOT / "data" / "processed" / "mb_neurons.csv")
e = pd.read_csv(ROOT / "data" / "processed" / "mb_edges.csv")

pn = n[(n.role == "PN") & ~n.cell_type.str.startswith("M_")].copy()
pn["glom"] = pn.cell_type.str.split("_").str[0]
pk = e[(e.pre_role == "PN") & (e.post_role == "KC")].merge(pn[["root_id", "glom"]], left_on="pre", right_on="root_id")

kcs = pk.groupby("glom")["post"].apply(set)
summary = pd.DataFrame({"PN수": pn.groupby("glom").size(), "입력받는KC": kcs.apply(len)}).dropna()
big = summary[summary["입력받는KC"] >= 100].index

rows = []
for a, b in itertools.combinations(big, 2):
    A, B = kcs[a], kcs[b]
    rows.append({"A": a, "B": b, "KC_A": len(A), "KC_B": len(B), "겹침KC": len(A & B),
                 "Jaccard": round(len(A & B) / len(A | B), 3),
                 "크기비": round(max(len(A), len(B)) / min(len(A), len(B)), 2)})
pairs = pd.DataFrame(rows)
fair = pairs[pairs["크기비"] <= 1.25]

out = ROOT / "data" / "processed" / "stimulus_pairs.csv"
fair.sort_values("Jaccard", ascending=False).to_csv(out, index=False, encoding="utf-8-sig")
print(f"사구체 {len(big)}개, 전체 쌍 {len(pairs)}개 중 크기 기준 통과 {len(fair)}개 → {out.name}")
print("\n[연결된 KC 겹침이 큰 입력 경로 후보]")
print(fair.sort_values("Jaccard", ascending=False).head(8).to_string(index=False))
print("\n[연결된 KC 겹침이 작은 입력 경로 후보]")
print(fair.sort_values("Jaccard").head(8).to_string(index=False))
