"""서버 없이 더블클릭으로 여는 PoC 파일(REFLEX_PoC.html) 만들기

화면(static/)과 브라우저용 엔진(static/local_engine.js)에, 파이썬 엔진의 실제 회로 데이터와
seed별 선택 난수를 넣어 파일 하나로 묶는다. 엔진이나 회로 데이터를 바꾸면 다시 실행한다.

실행:  python poc/build_html.py      → poc/REFLEX_PoC.html
확인:  python poc/check_html.py      → 브라우저용 엔진이 파이썬 엔진과 같은 결과를 내는지 검사
"""
import json
from pathlib import Path

import numpy as np

import engine

HERE = Path(__file__).parent
STATIC = HERE / "static"
OUT = HERE / "REFLEX_PoC.html"
N_SEEDS, N_DRAWS = 50, 400  # 화면의 반복 실험은 seed 0~49, 한 실행당 선택 난수 400개까지 파이썬과 같다


def export_data():
    c = engine.make_real_circuit()
    show = c["show"]
    return {
        "n_kc": int(c["W_pn_kc"].shape[0]), "n_pn": int(c["W_pn_kc"].shape[1]),
        "pn": {s: np.flatnonzero(c["pn"][s]).tolist() for s in ("A", "B")},
        "drive": {s: (c["W_pn_kc"] @ c["pn"][s])[show].tolist() for s in ("A", "B")},
        "w_kc_apl": c["w_kc_apl"][show].tolist(), "w_apl_kc": c["w_apl_kc"][show].tolist(),
        "source": c["source"], "inputs": c["inputs"], "normalization": c["normalization"],
        "defaults": engine.DEFAULTS, "conditions": engine.CONDITIONS,
        "uniforms": {str(s): np.random.default_rng(10_000 + s).random(N_DRAWS).tolist() for s in range(N_SEEDS)},
    }


def data_js(data):
    return "window.REFLEX_DATA = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"


def build():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    css = (STATIC / "style.css").read_text(encoding="utf-8")
    scripts = [data_js(export_data()), (STATIC / "local_engine.js").read_text(encoding="utf-8"),
               (STATIC / "app.js").read_text(encoding="utf-8")]
    assert all("</script" not in s for s in scripts)
    link, tag = '<link rel="stylesheet" href="style.css">', '<script src="app.js"></script>'
    assert html.count(link) == 1 and html.count(tag) == 1
    html = html.replace(link, f"<style>\n{css}\n</style>")
    html = html.replace(tag, "\n".join(f"<script>\n{s}\n</script>" for s in scripts))
    OUT.write_text(html, encoding="utf-8")
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"저장: {p} ({p.stat().st_size / 1024:.0f} KB) — 파일을 더블클릭해서 브라우저로 엽니다")
