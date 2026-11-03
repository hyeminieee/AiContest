"""자극 A·B 입력 경로 후보를 같은 기준으로 비교하기

입력 경로 = 한 사구체(glomerulus, 더듬이의 냄새 신호가 모이는 구역)에서 KC로 신호를 보내는 PN 묶음.
choose_stimuli.py보다 기준을 좁혔다.
  - FlyWire 이름표의 cell_sub_class가 uniglomerular(한 사구체 담당)인 PN만 사용
  - 흥분성(acetylcholine) PN만 사용. GABA PN은 KC를 억제하므로 '입력 신호'와 성격이 다름
  - 연결 기준(시냅스 수 문턱)을 PN 1개 → KC 1개의 '뉴런 쌍' 단위로 적용, 1개 이상과 5개 이상을 모두 계산

분석 기준 (AI가 제안한 값, 팀 결정 전. 생물학적 사실이 아님)
  MIN_KC    = 연결된 KC가 100개 이상인 사구체만 후보
  MAX_RATIO = 두 입력의 KC 수 비, 시냅스 합 비가 모두 1.25 이하

입력:  data/processed/mb_neurons.csv, mb_edges.csv (extract_circuit.py 결과)
       data/raw/annotations/Supplemental_file1_neuron_annotations.tsv (cell_sub_class 확인용)
출력:  data/processed/stimulus_glomeruli.csv (사구체별 집계)
       data/processed/stimulus_candidates.csv (후보 쌍 비교)
       data/processed/input_pns.csv (위 기준을 통과한 입력 PN 목록, 엔진이 사용)
실행:  python src/compare_stimuli.py
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
MIN_KC, MAX_RATIO, THRESHOLDS = 100, 1.25, (1, 5)

n = pd.read_csv(PROC / "mb_neurons.csv")
e = pd.read_csv(PROC / "mb_edges.csv")
ann = pd.read_csv(ROOT / "data" / "raw" / "annotations" / "Supplemental_file1_neuron_annotations.tsv",
                  sep="\t", usecols=["root_id", "cell_sub_class"], low_memory=False)

pn = n[n.role == "PN"].merge(ann, on="root_id", how="left")
pn["glom"] = pn.cell_type.str.split("_").str[0]
uni = pn[(pn.cell_sub_class == "uniglomerular") & (pn.top_nt == "acetylcholine")]
kc_type = n[n.role == "KC"].set_index("root_id").cell_type
kc_group = kc_type.str.extract(r"^KC(g|ab|apbp|a'b')")[0].map({"g": "γ", "ab": "αβ", "apbp": "α'β'", "a'b'": "α'β'"})

pk = e[(e.pre_role == "PN") & (e.post_role == "KC")].merge(uni[["root_id", "glom"]], left_on="pre", right_on="root_id")

rows, kc_sets, kc_vecs = [], {}, {}
for g, sub in pk.groupby("glom"):
    row = {"사구체": g, "PN수": int((uni.glom == g).sum()),
           "PN종류": ",".join(sorted(uni.loc[uni.glom == g, "cell_type"].unique())),
           "VP계열": g.startswith("VP")}
    for t in THRESHOLDS:
        s = sub[sub.synapses >= t]  # 뉴런 쌍(PN 1개 → KC 1개) 단위 문턱
        kcs = set(s.post)
        kc_sets[g, t] = kcs
        kc_vecs[g, t] = s.groupby("post").synapses.sum()
        row[f"KC수_{t}"] = len(kcs)
        row[f"시냅스합_{t}"] = int(s.synapses.sum())
        if t == 1:
            comp = kc_group.reindex(list(kcs)).value_counts(normalize=True)
            row["KC구성(γ/αβ/α'β')"] = "/".join(f"{comp.get(k, 0):.2f}" for k in ("γ", "αβ", "α'β'"))
            row["KC당시냅스_평균"] = round(s.groupby("post").synapses.sum().mean(), 1)
    rows.append(row)
glom = pd.DataFrame(rows).sort_values("KC수_1", ascending=False)
glom.to_csv(PROC / "stimulus_glomeruli.csv", index=False, encoding="utf-8-sig")
# 엔진(poc/engine.py)이 원본 이름표 없이 입력 PN을 고를 수 있도록 같은 기준의 PN 목록을 남긴다
uni[["root_id", "cell_type", "glom", "top_nt", "cell_sub_class"]].to_csv(PROC / "input_pns.csv", index=False)

big = glom[(glom["KC수_1"] >= MIN_KC)].set_index("사구체")
pairs = []
for a, b in itertools.combinations(big.index, 2):
    r = {"A": a, "B": b, "VP포함": bool(big.at[a, "VP계열"] or big.at[b, "VP계열"]),
         "PN수": f"{big.at[a, 'PN수']}/{big.at[b, 'PN수']}"}
    ok = True
    for t in THRESHOLDS:
        A, B = kc_sets[a, t], kc_sets[b, t]
        va, vb = kc_vecs[a, t], kc_vecs[b, t]
        idx = va.index.union(vb.index)
        x, y = va.reindex(idx, fill_value=0).values, vb.reindex(idx, fill_value=0).values
        sa, sb = big.at[a, f"시냅스합_{t}"], big.at[b, f"시냅스합_{t}"]
        kc_ratio = max(len(A), len(B)) / min(len(A), len(B))
        syn_ratio = max(sa, sb) / min(sa, sb)
        ok = ok and kc_ratio <= MAX_RATIO and syn_ratio <= MAX_RATIO and min(len(A), len(B)) >= MIN_KC
        r.update({f"KC_A_{t}": len(A), f"KC_B_{t}": len(B), f"공통KC_{t}": len(A & B),
                  f"Jaccard_{t}": round(len(A & B) / len(A | B), 3),
                  f"겹침계수_{t}": round(len(A & B) / min(len(A), len(B)), 3),
                  f"코사인_{t}": round(float(x @ y / np.linalg.norm(x) / np.linalg.norm(y)), 3),
                  f"KC비_{t}": round(kc_ratio, 2),  # 표시용 반올림. 판정은 반올림 전 값으로 한다
                  f"시냅스비_{t}": round(syn_ratio, 2)})
    r["기준통과"] = ok and not r["VP포함"]
    pairs.append(r)
pairs = pd.DataFrame(pairs).sort_values("Jaccard_1", ascending=False)
pairs.to_csv(PROC / "stimulus_candidates.csv", index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"흥분성 단일 사구체 PN {len(uni)}개, 사구체 {glom.shape[0]}개 중 KC {MIN_KC}개 이상 {len(big)}개")
    print(f"후보 쌍 {len(pairs)}개 중 기준 통과 {int(pairs['기준통과'].sum())}개")
    print(f"저장: {PROC / 'stimulus_glomeruli.csv'}, {PROC / 'stimulus_candidates.csv'}")
