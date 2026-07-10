import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000/api/economics/v2";
const THRESHOLDS_URL = "http://localhost:8000/api/video-economics/admin/thresholds";

const styles = `
.icx-root{--blue:#185FA5;--green:#0F6E56;--red:#A32D2D;--bg:#F8F9FA;--card:#fff;--border:#DEE2E6;--text:#1A1A2E;--muted:#6C757D;--radius:8px;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.icx-root *{box-sizing:border-box}
.icx-header{background:var(--blue);color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between}
.icx-header h1{font-size:17px;font-weight:600;margin:0}
.icx-header a{color:rgba(255,255,255,.8);font-size:12px;text-decoration:none;margin-left:16px;cursor:pointer}
.icx-tabs{display:flex;gap:2px;background:var(--border);padding:2px;border-radius:var(--radius);margin:18px 28px 0;width:fit-content}
.icx-tab{padding:8px 18px;border-radius:6px;font-size:13px;cursor:pointer;border:none;background:transparent;color:var(--muted)}
.icx-tab.active{background:#fff;color:var(--blue);font-weight:500}
.icx-section{padding:18px 28px}
.icx-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:18px;margin-bottom:14px}
.icx-card h2{font-size:13px;font-weight:600;color:var(--blue);text-transform:uppercase;letter-spacing:.04em;margin:0 0 14px}
.icx-table{width:100%;border-collapse:collapse;font-size:13px}
.icx-table th{text-align:left;padding:8px 10px;background:var(--blue);color:#fff;font-weight:500;font-size:12px}
.icx-table td{padding:8px 10px;border-bottom:1px solid var(--border)}
.icx-table tr:nth-child(even) td{background:#F8F9FA}
.icx-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:500}
.icx-badge.active-badge{background:#E1F5EE;color:var(--green)}
.icx-badge.inactive-badge{background:#FCEBEB;color:var(--red)}
.icx-badge.staged-badge{background:#FFF3CD;color:#92620A}
.icx-btn{padding:6px 14px;border-radius:6px;font-size:12px;cursor:pointer;border:1px solid var(--border);background:#fff;color:var(--text)}
.icx-btn:hover{border-color:var(--blue);color:var(--blue)}
.icx-btn.primary{background:var(--blue);color:#fff;border-color:var(--blue)}
.icx-field{margin-bottom:12px}
.icx-field label{display:block;font-size:12px;font-weight:500;color:var(--muted);margin-bottom:4px}
.icx-field input,.icx-field select,.icx-field textarea{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;font-family:inherit}
.icx-field textarea{min-height:80px;font-family:monospace;font-size:12px}
.icx-msg{padding:10px 14px;border-radius:6px;font-size:13px;margin-top:10px}
.icx-msg.ok{background:#E1F5EE;color:var(--green)}
.icx-msg.err{background:#FCEBEB;color:var(--red)}
.icx-grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.icx-event-row{padding:8px 0;border-bottom:1px solid var(--border);font-size:12px;display:flex;gap:12px}
.icx-event-type{font-weight:500;color:var(--blue);min-width:280px}
.icx-kv{background:#F4F6F8;border:1px solid var(--border);padding:10px 14px;border-radius:6px;font-family:monospace;font-size:12px;margin-top:8px;white-space:pre-wrap}
.icx-input{padding:7px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px}
`;

async function callApi(path, method = "GET", body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  try {
    const r = await fetch(`${API_BASE}${path}`, opts);
    return await r.json();
  } catch {
    return null;
  }
}

const EVENT_TYPES = [
  ["", "All events"],
  ["economics.v2.estimate.created", "estimate.created"],
  ["economics.v2.budget.blocked", "budget.blocked"],
  ["economics.v2.budget.reserved", "budget.reserved"],
  ["economics.v2.batch.savings_recommended", "batch.savings"],
  ["economics.v2.decision.overridden", "decision.overridden"],
  ["economics.v2.actual.imported", "actual.imported"],
];

const PROVIDERS = ["openai", "runway", "fal", "replicate", "piapi"];

export default function AdminConsoleV2() {
  const [tab, setTab] = useState("providers");

  const [providers, setProviders] = useState(null);
  const [providerError, setProviderError] = useState(false);
  const [stageProvider, setStageProvider] = useState("");
  const [stageJson, setStageJson] = useState("");
  const [stageMsg, setStageMsg] = useState(null);
  const [approveVersion, setApproveVersion] = useState("");
  const [approveMsg, setApproveMsg] = useState(null);
  const [impactPreview, setImpactPreview] = useState(null);

  const [nearBudget, setNearBudget] = useState("");
  const [asyncSavings, setAsyncSavings] = useState("");
  const [thresholdMsg, setThresholdMsg] = useState(null);

  const [ledgerWs, setLedgerWs] = useState("");
  const [ledgerSummary, setLedgerSummary] = useState(null);
  const [ledgerEntries, setLedgerEntries] = useState([]);
  const [ledgerLoaded, setLedgerLoaded] = useState(false);

  const [analyticsSummary, setAnalyticsSummary] = useState(null);
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [events, setEvents] = useState(null);

  const [forecastWs, setForecastWs] = useState("");
  const [forecastDays, setForecastDays] = useState(30);
  const [forecastBudget, setForecastBudget] = useState("");
  const [forecastResult, setForecastResult] = useState(null);
  const [alerts, setAlerts] = useState(null);

  const loadProviders = useCallback(async () => {
    const data = await callApi("/providers/pricing/active");
    if (!data) {
      setProviderError(true);
      setProviders(null);
      return;
    }
    setProviderError(false);
    setProviders(data.providers || []);
  }, []);

  const loadThresholds = useCallback(async () => {
    const data = await fetch(THRESHOLDS_URL).then((r) => r.json()).catch(() => null);
    if (data) {
      setNearBudget(data.near_budget_threshold);
      setAsyncSavings(data.async_savings_threshold);
    }
  }, []);

  const loadAnalyticsSummary = useCallback(async () => {
    const data = await callApi("/analytics/summary");
    if (data) setAnalyticsSummary(data);
  }, []);

  const loadAnalytics = useCallback(async () => {
    const url = eventTypeFilter
      ? `/analytics/events?event_type=${encodeURIComponent(eventTypeFilter)}&limit=30`
      : "/analytics/events?limit=30";
    const data = await callApi(url);
    setEvents(data && data.events ? data.events : []);
  }, [eventTypeFilter]);

  const loadAlerts = useCallback(async () => {
    const data = await callApi("/analytics/alerts");
    setAlerts(data && data.alerts ? data.alerts : []);
  }, []);

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  useEffect(() => {
    if (tab === "providers") loadProviders();
    if (tab === "thresholds") loadThresholds();
    if (tab === "analytics") {
      loadAnalyticsSummary();
      loadAnalytics();
    }
    if (tab === "forecast") loadAlerts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function previewImpact(pk) {
    if (!approveVersion) {
      alert("Enter a version number first.");
      return;
    }
    const data = await callApi(`/providers/${pk}/pricing/impact/${approveVersion}`);
    if (data) setImpactPreview(data);
  }

  async function handleStage() {
    if (!stageProvider) {
      setStageMsg({ ok: false, text: "Select a provider." });
      return;
    }
    let json;
    try {
      json = JSON.parse(stageJson);
    } catch {
      setStageMsg({ ok: false, text: "Invalid JSON." });
      return;
    }
    const result = await callApi(`/providers/${stageProvider}/pricing/stage`, "POST", {
      profile_data: { ...json, provider_key: stageProvider },
      created_by: "admin",
    });
    if (result && result.staged_version) {
      setStageMsg({ ok: true, text: `Staged v${result.staged_version}. Validate then approve to activate.` });
      loadProviders();
    } else {
      setStageMsg({ ok: false, text: result?.detail || "Failed." });
    }
  }

  async function handleValidate() {
    if (!stageProvider) {
      setStageMsg({ ok: false, text: "Select a provider." });
      return;
    }
    let json;
    try {
      json = JSON.parse(stageJson);
    } catch {
      setStageMsg({ ok: false, text: "Invalid JSON." });
      return;
    }
    const result = await callApi(`/providers/${stageProvider}/pricing/validate`, "POST", {
      provider_key: stageProvider,
      draft_profile: { ...json, provider_key: stageProvider },
    });
    if (result) {
      setStageMsg({
        ok: !!result.valid,
        text: result.valid ? "Valid. Ready to approve." : "Errors: " + (result.errors || []).join(", "),
      });
    }
  }

  async function handleApprove() {
    if (!stageProvider || !approveVersion) {
      setApproveMsg({ ok: false, text: "Select provider and enter version." });
      return;
    }
    const result = await callApi(
      `/providers/${stageProvider}/pricing/approve?version=${approveVersion}&approved_by=admin`,
      "POST"
    );
    if (result && result.activated_version) {
      setApproveMsg({ ok: true, text: `v${result.activated_version} activated.` });
      loadProviders();
    } else {
      setApproveMsg({ ok: false, text: result?.detail || "Failed." });
    }
  }

  async function handleRollback() {
    if (!stageProvider) {
      setStageMsg({ ok: false, text: "Select a provider." });
      return;
    }
    const result = await callApi(`/providers/${stageProvider}/pricing/rollback`, "POST");
    if (result && result.rolled_back_to) {
      setStageMsg({ ok: true, text: `Rolled back to v${result.rolled_back_to}.` });
      loadProviders();
    } else {
      setStageMsg({ ok: false, text: result?.detail || "Failed." });
    }
  }

  async function handleSaveThresholds() {
    const payload = {
      near_budget_threshold: parseFloat(nearBudget),
      async_savings_threshold: parseFloat(asyncSavings),
    };
    const result = await fetch(THRESHOLDS_URL, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((r) => r.json())
      .catch(() => null);
    setThresholdMsg(result ? { ok: true, text: "Saved." } : { ok: false, text: "Failed." });
  }

  async function handleLoadLedger() {
    const url = ledgerWs ? `/ledger/summary?workspace_id=${ledgerWs}` : "/ledger/summary";
    const summary = await callApi(url);
    const entries = await callApi(
      ledgerWs ? `/ledger/entries?workspace_id=${ledgerWs}&limit=20` : "/ledger/entries?limit=20"
    );
    setLedgerLoaded(true);
    if (summary) setLedgerSummary(summary);
    if (entries) setLedgerEntries(entries.entries || []);
  }

  async function handleForecast() {
    let url = `/analytics/forecast?days_ahead=${forecastDays || 30}`;
    if (forecastWs) url += `&workspace_id=${forecastWs}`;
    if (forecastBudget) url += `&monthly_budget=${forecastBudget}`;
    const data = await callApi(url);
    if (data) setForecastResult(data);
  }

  return (
    <div className="icx-root">
      <style>{styles}</style>

      <header className="icx-header">
        <h1>IncuBrix - Admin Console v2</h1>
        <div>
          <a>Simulation UI</a>
          <a>API Docs ↗</a>
        </div>
      </header>

      <div className="icx-tabs">
        {["providers", "thresholds", "ledger", "analytics", "forecast"].map((name) => (
          <button
            key={name}
            className={`icx-tab${tab === name ? " active" : ""}`}
            onClick={() => setTab(name)}
          >
            {name.charAt(0).toUpperCase() + name.slice(1)}
          </button>
        ))}
      </div>

      {tab === "providers" && (
        <div className="icx-section">
          <div className="icx-card">
            <h2>Active Provider Profiles (v2)</h2>
            <table className="icx-table">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Model</th>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {providerError && (
                  <tr>
                    <td colSpan={5} style={{ color: "var(--red)" }}>Cannot connect to API.</td>
                  </tr>
                )}
                {!providerError && providers === null && (
                  <tr>
                    <td colSpan={5} style={{ color: "var(--muted)" }}>Loading...</td>
                  </tr>
                )}
                {!providerError &&
                  providers &&
                  providers.map((p, i) => (
                    <tr key={i}>
                      <td><strong>{p.provider_key}</strong></td>
                      <td style={{ color: "var(--muted)" }}>{p.model_key || "default"}</td>
                      <td>v{p.profile_version}</td>
                      <td>
                        <span className={`icx-badge ${p.is_active ? "active" : "inactive"}-badge`}>
                          {p.approval_status}
                        </span>
                      </td>
                      <td>
                        <button className="icx-btn" onClick={() => previewImpact(p.provider_key)}>
                          Preview Impact
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          <div className="icx-card">
            <h2>Stage New Profile Version</h2>
            <div className="icx-grid2">
              <div>
                <div className="icx-field">
                  <label>Provider</label>
                  <select value={stageProvider} onChange={(e) => setStageProvider(e.target.value)}>
                    <option value="">Select...</option>
                    {PROVIDERS.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
                <div className="icx-field">
                  <label>Profile Changes (JSON)</label>
                  <textarea
                    value={stageJson}
                    onChange={(e) => setStageJson(e.target.value)}
                    placeholder='{"rate_cards": [{"model_key":"default","unit_type":"per_second","unit_rate":0.025,"quality_class":"high","currency":"USD"}]}'
                  />
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="icx-btn primary" onClick={handleStage}>Stage</button>
                  <button className="icx-btn" onClick={handleValidate}>Validate</button>
                  <button className="icx-btn" onClick={handleRollback}>Rollback</button>
                </div>
                {stageMsg && <div className={`icx-msg ${stageMsg.ok ? "ok" : "err"}`}>{stageMsg.text}</div>}
              </div>
              <div>
                <div className="icx-field">
                  <label>Approve & Activate Version</label>
                  <input
                    type="number"
                    min={1}
                    placeholder="version number e.g. 2"
                    value={approveVersion}
                    onChange={(e) => setApproveVersion(e.target.value)}
                  />
                </div>
                <button className="icx-btn primary" onClick={handleApprove}>Approve & Activate</button>
                {approveMsg && <div className={`icx-msg ${approveMsg.ok ? "ok" : "err"}`}>{approveMsg.text}</div>}
                {impactPreview && (
                  <div className="icx-kv" style={{ marginTop: 12 }}>
                    {JSON.stringify(impactPreview, null, 2)}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === "thresholds" && (
        <div className="icx-section">
          <div className="icx-card" style={{ maxWidth: 460 }}>
            <h2>Policy Thresholds</h2>
            <div className="icx-field">
              <label>Near-Budget Warning (0.0–1.0)</label>
              <input
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={nearBudget}
                onChange={(e) => setNearBudget(e.target.value)}
              />
            </div>
            <div className="icx-field">
              <label>Async Savings Threshold (0.0–1.0)</label>
              <input
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={asyncSavings}
                onChange={(e) => setAsyncSavings(e.target.value)}
              />
            </div>
            <button className="icx-btn primary" onClick={handleSaveThresholds}>Save</button>
            {thresholdMsg && <div className={`icx-msg ${thresholdMsg.ok ? "ok" : "err"}`}>{thresholdMsg.text}</div>}
          </div>
        </div>
      )}

      {tab === "ledger" && (
        <div className="icx-section">
          <div className="icx-card">
            <h2>Ledger Summary</h2>
            <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
              <input
                className="icx-input"
                placeholder="workspace_id (optional)"
                style={{ width: 220 }}
                value={ledgerWs}
                onChange={(e) => setLedgerWs(e.target.value)}
              />
              <button className="icx-btn primary" onClick={handleLoadLedger}>Load</button>
            </div>
            {ledgerLoaded && ledgerSummary && (
              <div className="icx-kv">{JSON.stringify(ledgerSummary, null, 2)}</div>
            )}
          </div>

          <div className="icx-card">
            <h2>Recent Ledger Entries</h2>
            <table className="icx-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Provider</th>
                  <th>Notes</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {!ledgerLoaded && (
                  <tr>
                    <td colSpan={5} style={{ color: "var(--muted)" }}>Click Load above.</td>
                  </tr>
                )}
                {ledgerLoaded && ledgerEntries.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ color: "var(--muted)" }}>No entries.</td>
                  </tr>
                )}
                {ledgerLoaded &&
                  ledgerEntries.map((e, i) => (
                    <tr key={i}>
                      <td>{e.entry_type}</td>
                      <td>${parseFloat(e.amount).toFixed(4)}</td>
                      <td>{e.provider_key || "-"}</td>
                      <td style={{ color: "var(--muted)" }}>{e.notes || ""}</td>
                      <td style={{ color: "var(--muted)" }}>{e.created_at?.slice(0, 19)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "analytics" && (
        <div className="icx-section">
          <div className="icx-card">
            <h2>Summary</h2>
            <div className="icx-kv">
              {analyticsSummary ? JSON.stringify(analyticsSummary, null, 2) : "Loading..."}
            </div>
          </div>
          <div className="icx-card">
            <h2>Recent Events</h2>
            <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
              <select
                className="icx-input"
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
              >
                {EVENT_TYPES.map(([val, label]) => (
                  <option key={val} value={val}>{label}</option>
                ))}
              </select>
              <button className="icx-btn" onClick={loadAnalytics}>Refresh</button>
            </div>
            <div>
              {events === null && <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading...</div>}
              {events && events.length === 0 && (
                <div style={{ color: "var(--muted)", fontSize: 13 }}>No events yet.</div>
              )}
              {events &&
                events.map((e, i) => (
                  <div className="icx-event-row" key={i}>
                    <div className="icx-event-type">{e.event_type}</div>
                    <div style={{ color: "var(--muted)", minWidth: 170 }}>{e.created_at?.slice(0, 19)}</div>
                    <div style={{ color: "var(--muted)", fontSize: 11, fontFamily: "monospace" }}>
                      {JSON.stringify(e.properties || {}).slice(0, 120)}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {tab === "forecast" && (
        <div className="icx-section">
          <div className="icx-card" style={{ maxWidth: 500 }}>
            <h2>Spend Forecast</h2>
            <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
              <input
                className="icx-input"
                placeholder="workspace_id (optional)"
                style={{ flex: 1 }}
                value={forecastWs}
                onChange={(e) => setForecastWs(e.target.value)}
              />
              <input
                className="icx-input"
                type="number"
                min={1}
                placeholder="days ahead"
                style={{ width: 110 }}
                value={forecastDays}
                onChange={(e) => setForecastDays(e.target.value)}
              />
              <input
                className="icx-input"
                type="number"
                step="0.01"
                placeholder="monthly budget"
                style={{ width: 140 }}
                value={forecastBudget}
                onChange={(e) => setForecastBudget(e.target.value)}
              />
              <button className="icx-btn primary" onClick={handleForecast}>Run Forecast</button>
            </div>
            {forecastResult && <div className="icx-kv">{JSON.stringify(forecastResult, null, 2)}</div>}
          </div>

          <div className="icx-card">
            <h2>Active Alerts</h2>
            {(!alerts || alerts.length === 0) && (
              <div style={{ color: "var(--muted)", fontSize: 13 }}>No active alerts.</div>
            )}
            {alerts &&
              alerts.map((a, i) => (
                <div key={i} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                  <div style={{ fontWeight: 500, fontSize: 13 }}>
                    {a.title}{" "}
                    <span className="icx-badge" style={{ background: "#FFF3CD", color: "#92620A" }}>
                      {a.severity}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>{a.description}</div>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
