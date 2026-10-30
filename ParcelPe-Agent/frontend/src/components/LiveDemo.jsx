import React, { useEffect, useRef, useState } from "react";
import { api, SCENARIOS, DECISION, inr } from "../api.js";

// The 7 fixed stages of the agent loop (matches backend/app/agent.py)
const STAGES = [
  { n: 1, name: "Input guardrail", kind: "guard", hint: "Hide personal data · catch prompt injection" },
  { n: 2, name: "Understand", kind: "ai", hint: "LLM reads intent, tracking ID, confidence" },
  { n: 3, name: "Act · tools", kind: "tool", hint: "Tracking · refund policy · photo check · address" },
  { n: 4, name: "Action guardrail", kind: "guard", hint: "Payout > limit or flagged → human" },
  { n: 5, name: "Draft reply", kind: "ai", hint: "LLM writes from verified facts only" },
  { n: 6, name: "Output guardrail", kind: "guard", hint: "No unapproved promises · no personal data" },
  { n: 7, name: "Audit trail", kind: "log", hint: "Everything saved to MongoDB" },
];

export default function LiveDemo() {
  const [chat, setChat] = useState([
    { from: "bot", text: "Hi! I'm ParcelPe's assistant. Ask me about your parcel 📦" },
  ]);
  const [text, setText] = useState("");
  const [image, setImage] = useState(null); // { base64, mime, name, preview }
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [revealed, setRevealed] = useState(0);
  const [error, setError] = useState("");
  const fileRef = useRef(null);
  const chatRef = useRef(null);

  useEffect(() => { chatRef.current?.scrollTo(0, chatRef.current.scrollHeight); }, [chat]);

  // Light up the stages one by one
  useEffect(() => {
    if (!result) return;
    setRevealed(0);
    const timers = STAGES.map((_, i) => setTimeout(() => setRevealed(i + 1), 450 * (i + 1)));
    return () => timers.forEach(clearTimeout);
  }, [result]);

  const pickImage = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const url = reader.result;
      setImage({ base64: url.split(",")[1], mime: file.type, name: file.name, preview: url });
    };
    reader.readAsDataURL(file);
  };

  const send = async () => {
    if (!text.trim()) { setError("Type a message first"); return; }
    setError(""); setBusy(true); setResult(null);
    setChat((c) => [...c, { from: "me", text, image: image?.preview }]);
    try {
      const r = await api.send({ text, image_base64: image?.base64, image_mime: image?.mime });
      setResult(r);
      setTimeout(() => setChat((c) => [...c, { from: "bot", text: r.reply, decision: r.decision }]), 450 * 5);
    } catch (e) {
      setError("Backend error: " + e.message);
    } finally {
      setBusy(false); setText(""); setImage(null);
    }
  };

  const stepsFor = (n) => (result?.steps || []).filter((s) => s.n === n);
  const verdict = result && DECISION[result.decision];

  return (
    <div className="demo">
      {/* Scenario launcher */}
      <section className="scenarios">
        {SCENARIOS.map((s) => (
          <button key={s.n} className="scenario" onClick={() => { setText(s.text); setError(""); }}>
            <span className="sc-n">{s.n}</span>
            <span className="sc-title">{s.title}</span>
            <span className="sc-tag">{s.tag}</span>
          </button>
        ))}
      </section>

      <div className="demo-grid">
        {/* Customer phone */}
        <section className="phone">
          <div className="phone-head">
            <div className="avatar">P</div>
            <div><b>ParcelPe Support</b><small>WhatsApp · online</small></div>
          </div>
          <div className="chat" ref={chatRef}>
            {chat.map((m, i) => (
              <div key={i} className={`bubble ${m.from}`}>
                {m.image && <img src={m.image} alt="Customer photo" />}
                {m.text}
                {m.decision && <span className={`mini ${DECISION[m.decision].tone}`}>{DECISION[m.decision].label}</span>}
              </div>
            ))}
            {busy && <div className="bubble bot typing"><i /><i /><i /></div>}
          </div>
          {image && (
            <div className="attach-preview">
              <img src={image.preview} alt="" /> {image.name}
              <button className="link" onClick={() => setImage(null)}>remove</button>
            </div>
          )}
          <div className="composer">
            <button className="icon" title="Attach a photo" onClick={() => fileRef.current.click()}>＋</button>
            <input ref={fileRef} type="file" accept="image/*" hidden onChange={pickImage} />
            <textarea value={text} rows={2} placeholder="Type as the customer…"
              onChange={(e) => { setText(e.target.value); setError(""); }}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
            <button className="send" onClick={send} disabled={busy}>➤</button>
          </div>
          {error && <div className="field-error">{error}</div>}
        </section>

        {/* Agent pipeline */}
        <section className="pipeline card">
          <div className="card-title">Inside the agent <span className="legend">
            <i className="lg guard" />Guardrail <i className="lg ai" />AI <i className="lg tool" />Tool <i className="lg log" />Log</span></div>

          {result && revealed >= STAGES.length && verdict && (
            <div className={`verdict ${verdict.tone}`}>
              <div className="v-label">{verdict.label}</div>
              <div className="v-reason">
                {result.refund_issued ? `${inr(result.refund_amount_inr)} refunded automatically · ` : ""}{result.reason}
              </div>
            </div>
          )}

          <div className="stages">
            {STAGES.map((st, i) => {
              const items = stepsFor(st.n);
              const shown = result && revealed > i;
              const status = !shown ? "idle" : items.length === 0 ? "skipped"
                : items.some((x) => x.status === "blocked") ? "blocked"
                : items.some((x) => x.status === "warn") ? "warn" : "ok";
              return (
                <div key={st.n} className={`stage ${st.kind} ${status}`}>
                  <div className="st-num">{st.n}</div>
                  <div className="st-body">
                    <div className="st-name">{st.name}<span className="st-status">{
                      { idle: "", skipped: "skipped", ok: "passed", warn: "acted", blocked: "stopped" }[status]}</span></div>
                    {!shown && <div className="st-hint">{st.hint}</div>}
                    {shown && items.length === 0 && <div className="st-hint">Not needed for this message</div>}
                    {shown && items.map((x, k) => (
                      <div key={k} className="st-detail">
                        {x.step.startsWith("Tool") && <b>{x.step.replace("Tool · ", "")}: </b>}{x.detail}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* What got saved */}
        <section className="card saved">
          <div className="card-title">Saved in the database</div>
          {!result ? (
            <div className="empty">Pick a scenario above, then hit send. The record stored in the <code>messages</code> collection appears here.</div>
          ) : (
            <>
              <pre className="json">{JSON.stringify({
                message_id: result.message_id,
                customer_text: result.customer_text,
                has_image: result.has_image,
                intent: result.intent,
                tracking_id: result.tracking_id,
                decision: result.decision,
                reason: result.reason,
                ticket_id: result.ticket_id,
                refund_amount_inr: result.refund_amount_inr,
                llm: result.llm,
                tokens: result.tokens,
                cost_inr: result.cost_inr,
                latency_ms: result.latency_ms,
              }, null, 2)}</pre>
              <div className="note">Notice <code>customer_text</code>: personal data is masked <b>before</b> storage. The raw number is never saved.</div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
