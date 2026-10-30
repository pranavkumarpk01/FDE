import React, { useEffect, useState } from "react";
import { api, inr } from "../api.js";

const QUERIES = [
  ["Every message the AI escalated", 'db.messages.find({ decision: "ESCALATE" })'],
  ["Open tickets for humans", 'db.tickets.find({ status: "open" })'],
  ["Refunds the AI paid on its own", 'db.refunds.find({ approved_by: "ai" })'],
  ["Is any raw Aadhaar stored? (should be none)", 'db.messages.find({ customer_text: /\\d{4} \\d{4} \\d{4}/ })'],
  ["Delivered parcels", 'db.parcels.find({ status: "delivered" })'],
];

export default function Database({ settings }) {
  const [parcels, setParcels] = useState([]);
  useEffect(() => { api.parcels().then(setParcels); }, []);

  return (
    <div className="db">
      <section className="card">
        <div className="card-title">Where the data lives <span className="count">{settings?.database}</span></div>
        <div className="collections">
          {[["parcels", "The tracking system — seeded from data/parcels.json"],
            ["messages", "Audit trail — every message, step and decision"],
            ["tickets", "The human review queue"],
            ["refunds", "Every payout — by AI or by a human"]].map(([c, d]) => (
            <div key={c} className="collection"><div className="mono">{c}</div><div className="muted">{d}</div></div>))}
        </div>
        <p className="muted">Browse it live in <b>Mongo Express</b> at <a href="http://localhost:8081" target="_blank" rel="noreferrer">localhost:8081</a>,
          or run queries in <code>mongosh</code> / MongoDB Compass:</p>
        <div className="queries">
          {QUERIES.map(([k, q]) => <div key={q} className="query"><span>{k}</span><code>{q}</code></div>)}
        </div>
      </section>

      <section className="card">
        <div className="card-title">parcels collection <span className="count">{parcels.length} documents</span></div>
        <table>
          <thead><tr><th>Tracking ID</th><th>Customer</th><th>City</th><th>Status</th><th>Value</th><th>Delivered</th><th>Past claims</th></tr></thead>
          <tbody>{parcels.map((p) => (
            <tr key={p.tracking_id}>
              <td className="mono">{p.tracking_id}</td><td>{p.customer}</td><td>{p.city}</td>
              <td><span className={`status-chip ${p.status}`}>{p.status.replace(/_/g, " ")}</span></td>
              <td>{inr(p.declared_value_inr)}</td>
              <td>{p.delivered_hours_ago != null ? `${p.delivered_hours_ago} h ago` : "—"}</td>
              <td>{p.prior_claims}</td>
            </tr>))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
