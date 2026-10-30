import React, { useEffect, useState } from "react";
import { api, DECISION, inr } from "../api.js";

export default function OpsConsole() {
  const [m, setM] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [msgs, setMsgs] = useState([]);
  const [refunds, setRefunds] = useState([]);

  const load = async () => {
    const [a, b, c, d] = await Promise.all([api.metrics(), api.tickets(), api.messages(), api.refunds()]);
    setM(a); setTickets(b); setMsgs(c); setRefunds(d);
  };
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);

  const act = async (id, approve) => { approve ? await api.approve(id) : await api.reject(id); load(); };

  const kpis = m ? [
    ["Messages handled", m.messages],
    ["Fully automated", Math.round(m.automation_rate * 100) + "%"],
    ["Guardrail stops", m.guardrail_blocks],
    ["Open tickets", m.open_tickets],
    ["Refunds paid by AI", inr(m.refunds_auto_inr)],
    ["Refunds approved by humans", inr(m.refunds_human_inr)],
    ["LLM cost", inr(m.llm_cost_inr)],
    ["Same work by humans", inr(m.human_cost_inr)],
  ] : [];

  return (
    <div className="ops">
      <section className="kpis">
        {kpis.map(([k, v]) => <div key={k} className="kpi"><div className="kpi-v">{v}</div><div className="kpi-k">{k}</div></div>)}
      </section>

      <section className="card">
        <div className="card-title">Human review queue <span className="count">{tickets.filter((t) => t.status === "open").length} open</span></div>
        {tickets.length === 0 ? <div className="empty">No tickets yet. Run scenario 01 or 04 in the live demo.</div> : (
          <table>
            <thead><tr><th>Ticket</th><th>Customer said</th><th>Why a human</th><th>Amount</th><th>Status</th><th /></tr></thead>
            <tbody>{tickets.map((t) => (
              <tr key={t.ticket_id}>
                <td className="mono">{t.ticket_id}</td>
                <td className="wrap">{t.customer_text}</td>
                <td className="wrap">{t.reason}</td>
                <td>{t.amount_inr ? inr(t.amount_inr) : "—"}</td>
                <td><span className={`status-chip ${t.status}`}>{t.status}</span></td>
                <td className="actions">{t.status === "open" && <>
                  <button className="approve" onClick={() => act(t.ticket_id, true)}>Approve</button>
                  <button className="ghost" onClick={() => act(t.ticket_id, false)}>Reject</button></>}</td>
              </tr>))}
            </tbody>
          </table>)}
      </section>

      <div className="two">
        <section className="card">
          <div className="card-title">Audit trail <span className="count">messages collection</span></div>
          {msgs.length === 0 ? <div className="empty">Nothing logged yet.</div> : (
            <table>
              <thead><tr><th>Time</th><th>Customer said</th><th>Intent</th><th>Decision</th><th>Reason</th></tr></thead>
              <tbody>{msgs.map((r) => (
                <tr key={r.message_id + r.logged_at}>
                  <td className="mono">{new Date(r.logged_at).toLocaleTimeString()}</td>
                  <td className="wrap">{r.customer_text}</td>
                  <td>{r.intent}</td>
                  <td><span className={`badge ${DECISION[r.decision].tone}`}>{DECISION[r.decision].label}</span></td>
                  <td className="wrap">{r.reason}</td>
                </tr>))}
              </tbody>
            </table>)}
        </section>
        <section className="card">
          <div className="card-title">Refunds <span className="count">refunds collection</span></div>
          {refunds.length === 0 ? <div className="empty">No payouts yet.</div> : (
            <table>
              <thead><tr><th>Parcel</th><th>Amount</th><th>Approved by</th></tr></thead>
              <tbody>{refunds.map((r) => (
                <tr key={r.message_id + r.paid_at}>
                  <td className="mono">{r.tracking_id}</td><td>{inr(r.amount_inr)}</td>
                  <td><span className={`badge ${r.approved_by === "ai" ? "ok" : "info"}`}>{r.approved_by === "ai" ? "AI (under limit)" : r.approved_by}</span></td>
                </tr>))}
              </tbody>
            </table>)}
        </section>
      </div>
    </div>
  );
}
