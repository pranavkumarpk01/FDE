import React, { useState } from "react";
import { api, DECISION } from "../api.js";

export default function Evals({ settings, onToggle }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => { setBusy(true); try { setData(await api.runEvals()); } finally { setBusy(false); } };
  const s = data?.summary;
  const on = settings?.enable_action_limits;

  return (
    <div className="evals">
      <section className="card eval-head">
        <div>
          <div className="card-title">Evals — the exam for the AI</div>
          <p className="muted">Each test case is a customer message plus the right answer: what the customer wants (<b>intent</b>) and
            what the agent should do (<b>decision</b>). Unsafe outcomes must be 0 before going live.</p>
        </div>
        <div className="eval-actions">
          <button className={`guard-toggle ${on ? "on" : "off"}`} onClick={onToggle}><span className="knob" />Guardrail {on ? "ON" : "OFF"}</button>
          <button className="primary" onClick={run} disabled={busy}>{busy ? "Running…" : "Run evals"}</button>
        </div>
      </section>

      {s && (
        <section className="kpis five">
          <div className="kpi"><div className={`kpi-v ${s.passed === s.total ? "good" : "warn"}`}>{s.passed}/{s.total}</div><div className="kpi-k">Cases passed</div></div>
          <div className="kpi"><div className="kpi-v">{s.intent_ok}/{s.total}</div><div className="kpi-k">Understood correctly</div></div>
          <div className="kpi"><div className="kpi-v">{s.decision_ok}/{s.total}</div><div className="kpi-k">Right decision</div></div>
          <div className="kpi"><div className={`kpi-v ${s.unsafe ? "bad" : "good"}`}>{s.unsafe}</div><div className="kpi-k">Unsafe outcomes</div></div>
          <div className="kpi"><div className={`kpi-v ${s.action_limits ? "good" : "bad"}`}>{s.action_limits ? "ON" : "OFF"}</div><div className="kpi-k">Payout guardrail</div></div>
        </section>
      )}

      {data && (
        <section className="card">
          <table>
            <thead><tr><th>Case</th><th>Customer message</th><th>Expected</th><th>Got</th><th>Result</th></tr></thead>
            <tbody>{data.rows.map((r) => (
              <tr key={r.id} className={r.passed ? "" : "row-fail"}>
                <td className="mono">{r.id}</td>
                <td className="wrap">{r.text}</td>
                <td>{r.expected_intent}<br /><span className={`badge ${DECISION[r.expected_decision].tone}`}>{DECISION[r.expected_decision].label}</span></td>
                <td>{r.got_intent}<br /><span className={`badge ${DECISION[r.got_decision].tone}`}>{DECISION[r.got_decision].label}</span></td>
                <td>{r.passed ? <span className="pass">PASS</span> : <><span className="fail">FAIL</span>
                  {r.problems.map((p, i) => <div key={i} className="problem">{p.category}: {p.detail}</div>)}</>}</td>
              </tr>))}
            </tbody>
          </table>
        </section>
      )}
      {!data && <div className="card empty">Press <b>Run evals</b>. Then switch the guardrail OFF and run again to see what breaks.</div>}
    </div>
  );
}
