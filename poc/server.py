"""REFLEX PoC 시연 서버 (Python 표준 라이브러리 + numpy만 사용)

실행:  python server.py        → 브라우저에서 http://localhost:8765
"""
import csv
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

import command
import engine

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
RESULTS = ROOT / "results"
PORT = int(os.environ.get("PORT", "8765"))
sessions = {}
batch_cache = {}


def kc_sample(sess, n=240):
    """화면에 그릴 KC 일부의 활성 여부. 실제 계산값 그대로다.
    실제 회로에서는 A·B 입력과 연결된 KC 중 앞쪽 n개를 고른다(연결 없는 KC는 늘 꺼져 있음)."""
    idx = sess.circuit["show"][:n]
    return {s: (sess.kc[s][idx] > 0).astype(int).tolist() for s in ("A", "B")}


def save_batch(out):
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "batch_summary.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["condition", "seed", "trials_initial", "trials_reversal"])
        for c, s in out["conditions"].items():
            for seed, (a, b) in enumerate(zip(s["initial"], s["reversal"])):
                w.writerow([c, seed, a if a is not None else "fail", b if b is not None else "fail"])


def handle(path, body):
    sid = body.get("sid", "main")
    if path == "/api/reset":
        cond = body.get("condition", "baseline")
        if cond not in engine.CONDITIONS:
            return {"error": "unknown condition"}
        sessions[sid] = engine.Session(cond, int(body.get("seed", 0)))
        s = sessions[sid]
        return {"state": s.state(), "kc": kc_sample(s), "n_pn": s.circuit["W_pn_kc"].shape[1],
                "n_kc": s.circuit["W_pn_kc"].shape[0], "inputs": s.circuit["inputs"],
                "pn": {k: v.astype(int).tolist() for k, v in s.circuit["pn"].items()},
                "source": s.circuit["source"], "params": s.p}
    s = sessions.get(sid)
    if s is None:
        return {"error": "reset first"}
    if path == "/api/step":
        recs = [s.step() for _ in range(max(1, min(80, int(body.get("n", 1)))))]
        return {"records": recs, "state": s.state()}
    if path == "/api/reverse":
        s.reverse()
        return {"state": s.state()}
    if path == "/api/command":
        text = str(body.get("text", ""))[:500]
        cmd, parser, note = command.parse(text)
        result, records = "", []
        c = cmd["command"]
        if c == "present_stimulus":
            st = cmd["stimulus"]
            result = (f"자극 {st}: KC {s.sparseness(st) * 100:.1f}%가 반응, "
                      f"접근 MBON {s.mbon(st)['approach']:.1f} / 회피 MBON {s.mbon(st)['avoid']:.1f}")
        elif c == "run_trials":
            records = [s.step() for _ in range(cmd["n"])]
            result = f"{cmd['n']}번 시도했어요."
        elif c in ("give_reward", "give_punishment"):
            if not s.history:
                result = "아직 고른 적이 없어서 보상/벌을 줄 수 없어요."
            else:
                last = s.history[-1]["choice"]
                s.learn(last, 1 if c == "give_reward" else -1)
                result = f"방금 고른 {last}에 {'좋은' if c == 'give_reward' else '좋지 않은'} 결과를 주었어요."
        elif c == "reverse_rule":
            s.reverse()
            result = f"이제 정답 자극은 {s.good}입니다."
        elif c == "query_status":
            result = s.state()
            text_out, check = command.explain(result, command.describe(result))
            result = text_out
            note = f"{note} / 설명 검사: {check}"
        else:
            result = command.REFUSAL
        return {"parsed": cmd, "parser": parser, "check": note, "reply": result,
                "records": records, "state": s.state()}
    if path == "/api/batch":
        n = max(5, min(50, int(body.get("n", 30))))
        if n not in batch_cache:
            out = engine.run_batch(n)
            engine.save_results(out, f"batch_n{n}")
            out.pop("_runs")  # 시도별 원자료는 파일로만 저장하고 화면에는 요약만 보낸다
            batch_cache[n] = out
            save_batch(out)
        return batch_cache[n]
    return {"error": "unknown path"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(STATIC), **kw)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            out = handle(self.path, body)
        except Exception as e:
            out = {"error": f"{type(e).__name__}: {e}"}
        data = json.dumps(out, ensure_ascii=False, default=lambda o: o.item() if isinstance(o, np.generic) else str(o)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write("[REFLEX] " + fmt % args + "\n")


if __name__ == "__main__":
    print(f"REFLEX PoC: http://localhost:{PORT}  (종료: Ctrl+C)")
    print("해석기:", "LLM" if command._llm_available() else "규칙 기반(오프라인 데모 모드)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
