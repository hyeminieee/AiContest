"""FlyWire v783 전체 뇌 데이터에서 버섯체 학습 회로만 골라내기 (회로 추출)

입력 (data/raw/, 강민혁 1명만 내려받음)
  annotations/Supplemental_file1_neuron_annotations.tsv  뉴런 13.9만 개의 이름표
  shiu/Connectivity_783.parquet                          뉴런 사이 연결 1,509만 줄
출력 (data/processed/, 저장소에 올려 팀 전체가 사용)
  mb_neurons.csv   회로에 포함한 뉴런 목록 (root_id, 역할, 세포 종류, 신경전달물질)
  mb_edges.csv     그 뉴런들 사이의 연결 (보내는 뉴런, 받는 뉴런, 시냅스 수, 흥분/억제)
  circuit_check.txt 추출 결과 요약 (문헌값과 비교할 숫자)

실행:  python src/extract_circuit.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
SIDE = "right"  # 한쪽 반구만 사용

ann = pd.read_csv(RAW / "annotations" / "Supplemental_file1_neuron_annotations.tsv", sep="\t", low_memory=False)
con = pd.read_parquet(RAW / "shiu" / "Connectivity_783.parquet")

# 1) 역할별로 뉴런 고르기 (cell_class / cell_type 값은 2026-10-27에 실제 파일에서 확인)
side = ann["side"] == SIDE
roles = {
    "PN": side & (ann["cell_class"] == "ALPN"),          # 냄새 정보를 KC로 보내는 투사뉴런
    "KC": side & (ann["cell_class"] == "Kenyon_Cell"),   # 학습이 일어나는 케년세포
    "APL": side & (ann["cell_type"] == "APL"),            # KC 전체를 억제하는 뉴런
    "MBON": side & (ann["cell_class"] == "MBON"),         # 출력 뉴런 (접근/회피)
    "DAN": side & (ann["cell_class"] == "DAN"),           # 보상/벌 신호 도파민 뉴런
}
parts = []
for role, mask in roles.items():
    df = ann.loc[mask, ["root_id", "cell_class", "cell_type", "top_nt"]].copy()
    df.insert(1, "role", role)
    parts.append(df)
neurons = pd.concat(parts, ignore_index=True)

# 2) 고른 뉴런끼리의 연결만 남기기
ids = set(neurons["root_id"])
edges = con[con["Presynaptic_ID"].isin(ids) & con["Postsynaptic_ID"].isin(ids)]
edges = edges.rename(columns={"Presynaptic_ID": "pre", "Postsynaptic_ID": "post",
                              "Connectivity": "synapses", "Excitatory": "excitatory"})
edges = edges[["pre", "post", "synapses", "excitatory"]]
role_of = dict(zip(neurons["root_id"], neurons["role"]))
edges = edges.assign(pre_role=edges["pre"].map(role_of), post_role=edges["post"].map(role_of))

OUT.mkdir(parents=True, exist_ok=True)
neurons.to_csv(OUT / "mb_neurons.csv", index=False)
edges.to_csv(OUT / "mb_edges.csv", index=False)

# 3) 문헌값과 비교할 숫자 요약
pair = lambda a, b: edges[(edges.pre_role == a) & (edges.post_role == b)]
kc_ids = set(neurons.loc[neurons.role == "KC", "root_id"])
pn_kc = pair("PN", "KC")
lines = [f"반구: {SIDE}", "[뉴런 수]"]
lines += [f"  {r}: {int((neurons.role == r).sum())}" for r in roles]
lines += [
    "[연결]",
    f"  PN→KC 연결 줄 수: {len(pn_kc)}",
    f"  PN 입력을 받는 KC: {pn_kc['post'].nunique()} / {len(kc_ids)}",
    f"  KC 1개당 PN 입력 뉴런 수(중앙값): {pn_kc.groupby('post').size().median():.0f}",
    f"  KC→APL 연결을 가진 KC: {pair('KC', 'APL')['pre'].nunique()}",
    f"  APL→KC 연결을 받는 KC: {pair('APL', 'KC')['post'].nunique()}",
    f"  KC→MBON 연결 줄 수: {len(pair('KC', 'MBON'))}",
    f"  DAN→KC 연결 줄 수: {len(pair('DAN', 'KC'))}",
    f"  APL의 신경전달물질(top_nt): {', '.join(neurons.loc[neurons.role == 'APL', 'top_nt'].astype(str))}",
    "[PN 종류 상위 10개 (자극 A·B 후보)]",
]
lines += [f"  {t}: {n}" for t, n in neurons.loc[neurons.role == "PN", "cell_type"].value_counts().head(10).items()]
report = "\n".join(lines)
(OUT / "circuit_check.txt").write_text(report, encoding="utf-8")
print(report)
print(f"\n저장: {OUT / 'mb_neurons.csv'} ({len(neurons)}개), {OUT / 'mb_edges.csv'} ({len(edges)}줄)")
