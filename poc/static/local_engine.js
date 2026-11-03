// REFLEX 브라우저용 엔진: poc/engine.py와 poc/command.py를 그대로 옮긴 것(서버 없이 HTML 파일만으로 실행).
// 연구 결과의 기준은 파이썬 엔진이다. 이 파일은 시연·작업용이며 check_html.py로 파이썬 결과와 일치하는지 확인한다.
// 데이터(window.REFLEX_DATA)는 build_html.py가 파이썬 엔진의 실제 회로에서 만들어 넣는다.
(function () {
  const D = window.REFLEX_DATA;
  const sum = (a) => a.reduce((x, y) => x + y, 0);
  const phaseName = (k) => (k === 0 ? "initial" : k === 1 ? "reversal" : `reversal${k}`);

  // 선택 난수: seed별로 파이썬(numpy default_rng(10000+seed))이 뽑은 값을 그대로 쓴다. 모자라면 대체 난수를 쓰고 표시한다.
  function mulberry32(a) {
    return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  function makeRng(seed) {
    const list = D.uniforms[String(seed)] || [];
    const fallback = mulberry32(10000 + seed);
    let i = 0;
    const rng = () => (i < list.length ? list[i++] : (rng.fallbackUsed = true, fallback()));
    rng.fallbackUsed = false;
    return rng;
  }

  // ---- 회로 ----
  // 입력 A·B와 연결된 KC만 담는다. 연결 없는 KC는 입력이 0이라 늘 꺼져 있으므로 계산 결과가 같다.
  // 단, 억제량 식의 분모와 반응 비율의 분모는 전체 KC 수(D.n_kc)를 쓴다(파이썬과 같음).
  function kcResponse(drive, g, theta, gain) {
    const f = (I) => drive.map((d, j) => Math.max(d - theta - D.w_apl_kc[j] * I, 0));
    const F = (I) => { const fi = f(I); let s = 0; for (let j = 0; j < fi.length; j++) s += D.w_kc_apl[j] * fi[j]; return g * gain * s / D.n_kc; };
    let lo = 0, hi = Math.max(Math.max(...drive), 1), ok = false;
    for (let k = 0; k < 200; k++) { if (hi - F(hi) >= 0) { ok = true; break; } hi *= 2; }
    if (!ok) throw new Error("APL 억제량의 탐색 범위를 찾지 못함");
    for (let k = 0; k < 200; k++) { const I = (lo + hi) / 2; if (F(I) > I) lo = I; else hi = I; }
    const I = (lo + hi) / 2, resid = F(I) - I;
    if (Math.abs(resid) > 1e-6 * (1 + I)) throw new Error("APL 억제량 계산 오차가 큼: " + resid);
    return [f(I), I, resid];
  }

  class Session {
    constructor(condition = "baseline", seed = 0, overrides = {}) {
      this.condition = condition; this.seed = seed;
      this.p = { ...D.defaults, ...D.conditions[condition], ...overrides };
      this.rng = makeRng(seed);
      this.kc = {}; this.apl = {}; this.apl_resid = {};
      for (const s of ["A", "B"]) [this.kc[s], this.apl[s], this.apl_resid[s]] = kcResponse(D.drive[s], this.p.g_apl, this.p.theta, this.p.gain);
      const m = D.drive.A.length;
      this.W = [new Array(m).fill(1), new Array(m).fill(1)];
      this.good = "A"; this.reversals = 0; this.trial = 0; this.history = [];
    }
    mbon(s) { const k = this.kc[s]; let a = 0, v = 0; for (let j = 0; j < k.length; j++) { a += this.W[0][j] * k[j]; v += this.W[1][j] * k[j]; } return { approach: a, avoid: v }; }
    value(s) { const m = this.mbon(s); return (m.approach - m.avoid) / Math.max(sum(this.kc[s]), 1e-9); }
    p_choose_A() { return 1 / (1 + Math.exp(-this.p.beta * (this.value("A") - this.value("B")))); }
    sparseness(s) { return this.kc[s].filter((x) => x > 0).length / D.n_kc; }
    overlap() { let and = 0, or = 0; for (let j = 0; j < this.kc.A.length; j++) { const a = this.kc.A[j] > 0, b = this.kc.B[j] > 0; if (a && b) and++; if (a || b) or++; } return and / Math.max(or, 1); }
    weight_summary(s) {
      const idx = []; this.kc[s].forEach((x, j) => { if (x > 0) idx.push(j); });
      if (!idx.length) return { approach: null, avoid: null };
      return { approach: sum(idx.map((j) => this.W[0][j])) / idx.length, avoid: sum(idx.map((j) => this.W[1][j])) / idx.length };
    }
    learn(s, outcome) {
      if (![-1, 0, 1].includes(outcome)) throw new Error("outcome은 -1, 0, 1 중 하나");
      if (outcome !== 0) { const row = outcome > 0 ? 1 : 0, k = this.kc[s];
        for (let j = 0; j < k.length; j++) if (k[j] > 0) this.W[row][j] -= this.p.eta * this.W[row][j]; }
      for (const r of this.W) for (let j = 0; j < r.length; j++) r[j] += this.p.decay * (1 - r[j]);
    }
    step(outcomeOverride = null) {
      const pA = this.p_choose_A(), vA = this.value("A"), vB = this.value("B");
      const choice = this.rng() < pA ? "A" : "B";
      const outcome = outcomeOverride != null ? outcomeOverride : choice === this.good ? 1 : -1;
      this.learn(choice, outcome);
      const wA = this.weight_summary("A"), wB = this.weight_summary("B");
      const rec = { trial: this.trial, phase: phaseName(this.reversals),
        good: this.good, choice, pA, p_correct: this.good === "A" ? pA : 1 - pA, value_A: vA, value_B: vB,
        outcome, correct: choice === this.good, wA_approach: wA.approach, wA_avoid: wA.avoid, wB_approach: wB.approach, wB_avoid: wB.avoid };
      this.history.push(rec); this.trial++;
      return rec;
    }
    reverse() { this.good = this.good === "A" ? "B" : "A"; this.reversals++; }
    state() {
      const r3 = (x) => Math.round(x * 1000) / 1000, r1 = (x) => Math.round(x * 10) / 10;
      const last = this.history.length ? this.history[this.history.length - 1] : null;
      const OUT = { 1: "좋은 결과", "-1": "좋지 않은 결과", 0: "결과 없음" }, SHORT = { 1: "좋음", "-1": "나쁨", 0: "없음" };
      const mb = (s) => { const m = this.mbon(s); return { approach: r1(m.approach), avoid: r1(m.avoid) }; };
      return { condition: this.condition, label: this.p.label, seed: this.seed, trial: this.trial, good: this.good,
        pA: r3(this.p_choose_A()), last_choice: last ? last.choice : null, last_outcome: last ? OUT[last.outcome] : null,
        kc_active_A: r3(this.sparseness("A")), kc_active_B: r3(this.sparseness("B")), overlap_AB: r3(this.overlap()),
        apl_inhibition_A: r3(this.apl.A), mbon_A: mb("A"), mbon_B: mb("B"),
        recent: this.history.slice(-5).map((r) => `${r.choice}-${SHORT[r.outcome]}`) };
    }
  }

  // ---- 판정: 그 단계로 기록된 시도 중 정해진 횟수까지만 (정식 절차에서는 history[:n0], history[n0:n0+n1]) ----
  const phaseSlice = (h, p, ph) => h.filter((r) => r.phase === ph).slice(0, ph === "initial" ? p.initial_trials : p.reversal_trials);
  function reachPrimary(seq, cp, ck) { let run = 0; for (let i = 0; i < seq.length; i++) { run = seq[i].p_correct >= cp ? run + 1 : 0; if (run >= ck) return i + 1; } return null; }
  function reachSecondary(seq, w, need) { const c = seq.map((r) => r.correct); for (let i = 0; i + w <= c.length; i++) if (c.slice(i, i + w).filter(Boolean).length >= need) return i + w; return null; }

  function runOne(condition, seed) {
    const s = new Session(condition, seed);
    for (let i = 0; i < s.p.initial_trials; i++) s.step();
    s.reverse();
    for (let i = 0; i < s.p.reversal_trials; i++) s.step();
    const out = { condition, seed, kc_active: s.sparseness("A"), kc_active_B: s.sparseness("B"), overlap: s.overlap(),
      apl_resid: Math.max(...Object.values(s.apl_resid).map(Math.abs)), history: s.history, fallback: s.rng.fallbackUsed };
    for (const ph of ["initial", "reversal"]) { const seq = phaseSlice(s.history, s.p, ph);
      out[ph] = reachPrimary(seq, s.p.crit_p, s.p.crit_k); out[ph + "_secondary"] = reachSecondary(seq, s.p.window, s.p.need); }
    return out;
  }

  // 순열검정의 난수는 numpy와 같을 수 없어 p값은 파이썬과 조금 다를 수 있다(참고값).
  function pairedSignflipP(x, y, nPerm = 20000) {
    const d = x.map((v, i) => v - y[i]).filter((v) => v !== 0);
    if (!d.length) return 1;
    const obs = Math.abs(sum(d) / d.length), rnd = mulberry32(0);
    let hit = 0;
    for (let k = 0; k < nPerm; k++) { let s = 0; for (const v of d) s += rnd() < 0.5 ? -v : v; if (Math.abs(s / d.length) >= obs) hit++; }
    return (hit + 1) / (nPerm + 1);
  }
  const median = (xs) => { const a = [...xs].sort((p, q) => p - q), n = a.length; return n % 2 ? a[(n - 1) / 2] : (a[n / 2 - 1] + a[n / 2]) / 2; };
  const cumulative = (vals, n, runs) => Array.from({ length: n }, (_, t) => Math.round((vals.filter((v) => v != null && v <= t + 1).length / runs) * 1000) / 1000);
  const meanCurve = (rs, key) => rs[0].history.map((_, t) => Math.round((sum(rs.map((r) => r.history[t][key])) / rs.length) * 1000) / 1000);

  function runBatch(nSeeds = 30, seedStart = 0) {
    const seeds = Array.from({ length: nSeeds }, (_, i) => seedStart + i), params = { ...D.defaults };
    const runs = {}, summary = {};
    for (const c of Object.keys(D.conditions)) runs[c] = seeds.map((s) => runOne(c, s));
    for (const [c, rs] of Object.entries(runs)) {
      const row = { label: D.conditions[c].label, n_runs: rs.length,
        kc_active: Math.round((sum(rs.map((r) => r.kc_active)) / rs.length) * 1000) / 1000,
        overlap: Math.round((sum(rs.map((r) => r.overlap)) / rs.length) * 1000) / 1000,
        curve: meanCurve(rs, "pA"), curve_p_correct: meanCurve(rs, "p_correct") };
      for (const [ph, nPh] of [["initial", params.initial_trials], ["reversal", params.reversal_trials]]) {
        for (const kind of ["", "_secondary"]) {
          const vals = rs.map((r) => r[ph + kind]), reached = vals.filter((v) => v != null);
          row[ph + kind] = vals; row[`reached_${ph}${kind}`] = reached.length;
          row[`median_reached_${ph}${kind}`] = reached.length ? median(reached) : null;
          row[`cumulative_${ph}${kind}`] = cumulative(vals, nPh, rs.length);
        }
        row[`fail_${ph}`] = row.n_runs - row[`reached_${ph}`];
      }
      row.initial_reached_runs = rs.filter((r) => r.initial != null).length;
      row.reversal_given_initial = rs.filter((r) => r.initial != null && r.reversal != null).length;
      summary[c] = row;
    }
    const pen = (c, k) => summary[c][k].map((v) => (v != null ? v : params[k + "_trials"] + 1));
    const tests = {}; for (const k of ["initial", "reversal"]) tests[k] = pairedSignflipP(pen("apl_weak", k), pen("baseline", k));
    const condition_params = Object.fromEntries(Object.keys(D.conditions).map((c) => [c, { ...D.defaults, ...D.conditions[c] }]));
    return { n_seeds: nSeeds, seeds, params, condition_params, conditions: summary, criteria_note: "주 기준 crit_p·crit_k와 보조 기준 window·need는 팀 확정 전 임시값",
      p_apl_vs_baseline: tests, p_method: "미도달을 단계 시도 수+1로 둔 벌점 점수의 대응 부호 뒤집기 순열검정(참고용, 브라우저 난수)",
      circuit_source: D.source, circuit_inputs: D.inputs, circuit_normalization: D.normalization,
      fallback_rng_used: Object.values(runs).some((rs) => rs.some((r) => r.fallback)) };
  }

  // ---- 명령 해석 (command.py의 규칙 기반 해석기. 브라우저에서는 LLM을 쓰지 않는다) ----
  const ALLOWED = new Set(["present_stimulus", "run_trials", "give_reward", "give_punishment", "reverse_rule", "query_status", "unknown"]);
  const REFUSAL = "그건 실험에서 허용되지 않은 명령이에요. 자극 A/B 보여주기, 시도하기, 보상, 벌, 규칙 바꾸기, 상태 묻기 중에서 말해 주세요.";
  const INJECTION_HINTS = ["무시", "ignore", "시스템", "system", "프롬프트", "prompt", "점수", "학습률", "코드", "관리자", "admin"];
  const UNKNOWN = () => ({ command: "unknown", stimulus: "none", n: 0 });
  const has = (t, ks) => ks.some((k) => t.includes(k));
  // 파이썬 정규식의 \b는 한글도 글자로 보므로 같은 의미가 되도록 유니코드 글자 경계를 쓴다
  const W = "[\\p{L}\\p{N}_]";
  function ruleParse(text) {
    const t = text.trim().toLowerCase();
    if (has(t, INJECTION_HINTS)) return UNKNOWN();
    const m = t.match(/(\d+)\s*(번|회)/);
    if (has(t, ["시도", "해봐", "연습", "골라"])) return { command: "run_trials", stimulus: "none", n: m ? parseInt(m[1], 10) : 1 };
    if (has(t, ["규칙", "바꿔", "반대"])) return { command: "reverse_rule", stimulus: "none", n: 0 };
    if (has(t, ["잘했", "칭찬", "간식", "보상", "먹이"])) return { command: "give_reward", stimulus: "none", n: 0 };
    if (has(t, ["혼", "벌", "안돼", "나빠"])) return { command: "give_punishment", stimulus: "none", n: 0 };
    if (has(t, ["상태", "기분", "기억", "어때", "뭐 배웠"])) return { command: "query_status", stimulus: "none", n: 0 };
    const stim = new RegExp(`(?<!${W})a(?!${W})|에이`, "u").test(t) ? "A" : new RegExp(`(?<!${W})b(?!${W})|비(?!${W})`, "u").test(t) ? "B" : null;
    if (stim && has(t, ["보여", "맡", "냄새", "자극", "줘"])) return { command: "present_stimulus", stimulus: stim, n: 0 };
    return UNKNOWN();
  }
  function validate(cmd) {
    if (!cmd || !ALLOWED.has(cmd.command)) return [UNKNOWN(), "허용목록에 없는 명령 → unknown"];
    if (cmd.command === "present_stimulus" && !["A", "B"].includes(cmd.stimulus)) return [UNKNOWN(), "자극이 A/B가 아님 → unknown"];
    const n = cmd.n ?? 0;
    if (cmd.command === "run_trials" && !(Number.isInteger(n) && n >= 1 && n <= 40))
      return [{ ...cmd, n: Math.max(1, Math.min(40, Number.isInteger(n) ? n : 1)) }, "시도 횟수를 1~40으로 제한"];
    if (cmd.command === "unknown") return [cmd, "허용된 명령이 아님 → 실행 차단"];
    return [cmd, "통과"];
  }
  function parse(text) {
    if (text.length > 200) return [UNKNOWN(), "rule", "입력이 너무 김(200자 초과) → unknown"];
    const [cmd, note] = validate(ruleParse(text));
    return [cmd, "규칙 기반 (브라우저 오프라인 모드)", note];
  }
  function explain(state, text) {
    const nums = (s) => new Set(s.match(/\d+(?:\.\d+)?/g) || []);
    const allowed = nums(JSON.stringify(state)), used = [...nums(text)];
    if (used.every((u) => allowed.has(u))) return [text, "근거 일치"];
    return [`(자동 안내) 시도 ${state.trial}회, A를 고를 확률 ${state.pA}입니다.`, `근거 없는 숫자 ${JSON.stringify(used.filter((u) => !allowed.has(u)).sort())} → 안내문으로 교체`];
  }
  function describe(state) {
    if (state.trial === 0) return "아직 아무 경험이 없어요. A와 B 중 어느 쪽이 좋은지 몰라요.";
    const lean = state.pA >= 0.5 ? "A" : "B";
    return `지금까지 ${state.trial}번 골라 봤고, 최근 선택은 ${state.last_choice}(${state.last_outcome})예요. 지금은 ${lean} 쪽으로 갈 확률이 더 높아요 (A를 고를 확률 ${state.pA}).`;
  }

  // ---- server.py의 handle()과 같은 응답 ----
  const sessions = {}, batchCache = {};
  const kcSample = (s, n = 240) => ({ A: s.kc.A.slice(0, n).map((x) => (x > 0 ? 1 : 0)), B: s.kc.B.slice(0, n).map((x) => (x > 0 ? 1 : 0)) });
  const pnVec = (s) => { const v = new Array(D.n_pn).fill(0); D.pn[s].forEach((i) => (v[i] = 1)); return v; };
  function handle(path, body = {}) {
    const sid = body.sid || "main";
    if (path === "/api/reset") {
      const cond = body.condition || "baseline";
      if (!(cond in D.conditions)) return { error: "unknown condition" };
      const s = (sessions[sid] = new Session(cond, parseInt(body.seed || 0, 10)));
      return { state: s.state(), kc: kcSample(s), n_pn: D.n_pn, n_kc: D.n_kc, inputs: D.inputs,
        pn: { A: pnVec("A"), B: pnVec("B") }, source: D.source + " · 브라우저 실행", params: s.p };
    }
    const s = sessions[sid];
    if (!s) return { error: "reset first" };
    if (path === "/api/step") { const n = Math.max(1, Math.min(80, parseInt(body.n || 1, 10))); const recs = []; for (let i = 0; i < n; i++) recs.push(s.step()); return { records: recs, state: s.state() }; }
    if (path === "/api/reverse") { s.reverse(); return { state: s.state() }; }
    if (path === "/api/command") {
      const text = String(body.text || "").slice(0, 500);
      let [cmd, parser, note] = parse(text), result = "", records = [];
      const c = cmd.command;
      if (c === "present_stimulus") { const st = cmd.stimulus, m = s.mbon(st);
        result = `자극 ${st}: KC ${(s.sparseness(st) * 100).toFixed(1)}%가 반응, 접근 MBON ${m.approach.toFixed(1)} / 회피 MBON ${m.avoid.toFixed(1)}`; }
      else if (c === "run_trials") { for (let i = 0; i < cmd.n; i++) records.push(s.step()); result = `${cmd.n}번 시도했어요.`; }
      else if (c === "give_reward" || c === "give_punishment") {
        if (!s.history.length) result = "아직 고른 적이 없어서 보상/벌을 줄 수 없어요.";
        else { const last = s.history[s.history.length - 1].choice; s.learn(last, c === "give_reward" ? 1 : -1);
          result = `방금 고른 ${last}에 ${c === "give_reward" ? "좋은" : "좋지 않은"} 결과를 주었어요.`; } }
      else if (c === "reverse_rule") { s.reverse(); result = `이제 정답 자극은 ${s.good}입니다.`; }
      else if (c === "query_status") { const st = s.state(); const [t, check] = explain(st, describe(st)); result = t; note = `${note} / 설명 검사: ${check}`; }
      else result = REFUSAL;
      return { parsed: cmd, parser, check: note, reply: result, records, state: s.state() };
    }
    if (path === "/api/batch") { const n = Math.max(5, Math.min(50, parseInt(body.n || 30, 10))); if (!batchCache[n]) batchCache[n] = runBatch(n); return batchCache[n]; }
    return { error: "unknown path" };
  }

  window.ReflexLocal = { handle, Session, runOne, runBatch, ruleParse, validate, explain, describe };
})();
