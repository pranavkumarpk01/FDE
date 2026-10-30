import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import TopBar from "./components/TopBar.jsx";
import LiveDemo from "./components/LiveDemo.jsx";
import OpsConsole from "./components/OpsConsole.jsx";
import Evals from "./components/Evals.jsx";
import Database from "./components/Database.jsx";

export default function App() {
  const [tab, setTab] = useState("demo");
  const [settings, setSettings] = useState(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0); // bump to refresh other tabs after a reset

  const loadSettings = () =>
    api.settings().then((s) => { setSettings(s); setError(""); })
      .catch(() => setError("Can't reach the backend on port 8000. Is it running?"));

  useEffect(() => { loadSettings(); }, []);

  const toggleGuardrail = async () => {
    setSettings(await api.saveSettings({ enable_action_limits: !settings.enable_action_limits }));
  };
  const reset = async () => { await api.reset(); setVersion((v) => v + 1); };

  return (
    <div className="app">
      <div className="bg-grid" />
      <TopBar tab={tab} setTab={setTab} settings={settings} onToggle={toggleGuardrail} onReset={reset} />
      {error && <div className="error-banner">{error}</div>}
      <main key={version}>
        {tab === "demo" && <LiveDemo settings={settings} />}
        {tab === "ops" && <OpsConsole />}
        {tab === "evals" && <Evals settings={settings} onToggle={toggleGuardrail} />}
        {tab === "db" && <Database settings={settings} />}
      </main>
    </div>
  );
}
