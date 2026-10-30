import React from "react";

const TABS = [
  ["demo", "Live demo"],
  ["ops", "Ops console"],
  ["evals", "Evals"],
  ["db", "Database"],
];

export default function TopBar({ tab, setTab, settings, onToggle, onReset }) {
  const on = settings?.enable_action_limits;
  return (
    <header className="topbar">
      <div className="brand">
        <div className="logo">P</div>
        <div>
          <div className="brand-name">ParcelPe</div>
          <div className="brand-sub">AI Support Desk · built the FDE way</div>
        </div>
      </div>

      <nav className="tabs">
        {TABS.map(([id, label]) => (
          <button key={id} className={`tab ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}>{label}</button>
        ))}
      </nav>

      <div className="status">
        <span className="pill"><i className="dot blue" />LLM <b>{settings?.llm ?? "…"}</b></span>
        <span className="pill"><i className={`dot ${settings?.database === "mongodb" ? "green" : "amber"}`} />DB <b>{settings?.database ?? "…"}</b></span>
        <span className="pill"><i className="dot amber" />Mode <b>{settings?.mode ?? "…"}</b></span>
        <button className={`guard-toggle ${on ? "on" : "off"}`} onClick={onToggle} disabled={!settings}
          title="Payouts above the limit need a human">
          <span className="knob" />₹{settings?.refund_auto_limit_inr?.toLocaleString("en-IN") ?? "2,000"} guardrail {on ? "ON" : "OFF"}
        </button>
        <button className="ghost" onClick={onReset}>Reset demo</button>
      </div>
    </header>
  );
}
