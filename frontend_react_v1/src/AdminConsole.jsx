import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";

const V2 = "http://localhost:8000/api/economics/v2";
const V1A = "http://localhost:8000/api/video-economics/admin";

const styles = `
.icx-root{--blue:#185FA5;--green:#0F6E56;--red:#A32D2D;--yellow:#92620A;--bg:#F8F9FA;--card:#fff;--border:#DEE2E6;--text:#1A1A2E;--muted:#6C757D;--radius:8px;
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
.icx-btn{padding:6px 14px;border-radius:6px;font-size:12px;cursor:pointer;border:1px solid var(--border);background:#fff;color:var(--text)}
.icx-btn:hover{border-color:var(--blue);color:var(--blue)}
.icx-btn.primary{background:var(--blue);color:#fff;border-color:var(--blue)}
.icx-btn.danger{background:var(--red);color:#fff;border-color:var(--red)}
.icx-field{margin-bottom:12px}
.icx-field label{display:block;font-size:12px;font-weight:500;color:var(--muted);margin-bottom:4px}
.icx-field input,.icx-field select,.icx-field textarea{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;font-family:inherit}
.icx-field textarea{min-height:100px;font-family:monospace;font-size:12px}
.icx-msg{padding:10px 14px;border-radius:6px;font-size:13px;margin-top:10px}
.icx-msg.ok{background:#E1F5EE;color:var(--green)}
.icx-msg.err{background:#FCEBEB;color:var(--red)}
.icx-grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.icx-kv{background:#F4F6F8;border:1px solid var(--border);padding:12px 14px;border-radius:6px;font-family:monospace;font-size:12px;white-space:pre-wrap;overflow:auto;max-height:320px}
.icx-event-row{padding:9px 0;border-bottom:1px solid var(--border);display:flex;gap:12px;font-size:12px}
.icx-event-type{font-weight:500;color:var(--blue);min-width:300px}
.icx-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:500}
.icx-badge.active-b{background:#E1F5EE;color:var(--green)}
.icx-badge.inactive-b{background:#FCEBEB;color:var(--red)}
.icx-badge.staged-b{background:#FFF3CD;color:var(--yellow)}
.icx-alert-card{padding:10px 0;border-bottom:1px solid var(--border)}
.icx-alert-title{font-weight:500;font-size:13px;margin-bottom:3px}
.icx-alert-desc{font-size:12px;color:var(--muted)}
.icx-sev-high{color:var(--red)}
.icx-sev-critical{color:var(--red);font-weight:700}
.icx-sev-medium{color:var(--yellow)}
.icx-sev-low{color:var(--muted)}
.icx-input{padding:7px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px}
`;

async function get(url) {
  try {
    const r = await fetch(url);
    return await r.json();
  } catch {
    return null;
  }
}
async function post(url, body) {
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return await r.json();
  } catch {
    return null;
  }
}
async function patch(url, body) {
  try {
    const r = await fetch(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
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
  ["economics.v2.variance.detected", "variance.detected"],
  ["economics.v2.config.profile.activated", "config.activated"],
];

const PROVIDERS = ["openai", "runway", "fal", "replicate", "piapi"];

export default function AdminConsole() {
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

  const [actualProvider, setActualProvider] = useState("openai");
  const [actualAmount, setActualAmount] = useState("");
  const [actualEstimateId, setActualEstimateId] = useState("");
  const [actualNotes, setActualNotes] = useState("");
  const [actualMsg, setActualMsg] = useState(null);
  const [varianceReport, setVarianceReport] = useState(null);
  const [unmapped, setUnmapped] = useState(null);

  const [analyticsSummary, setAnalyticsSummary] = useState(null);
  const [eventFilter, setEventFilter] = useState("");
  const [events, setEvents] = useState(null);

  const [forecastWs, setForecastWs] = useState("");
  const [forecastDays, setForecastDays] = useState(30);
  const [forecastBudget, setForecastBudget] = useState("");
  const [forecastResult, setForecastResult] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [anomalies, setAnomalies] = useState(null);

  const loadProviders = useCallback(async () => {
    const data = await get(`${V2}/providers/pricing/active`);
    if (!data) {
      setProviderError(true);
      setProviders(null);
      return;
    }
    setProviderError(false);
    setProviders(data.providers || []);
  }, []);

  const loadThresholds = useCallback(async () => {
    const data = await get(`${V1A}/thresholds`);
    if (data) {
      setNearBudget(data.near_budget_threshold);
      setAsyncSavings(data.async_savings_threshold);
    }
  }, []);

  const loadAnalyticsSummary = useCallback(async () => {
    const data = await get(`${V2}/analytics/summary`);
    if (data) setAnalyticsSummary(data);
  }, []);

  const loadEvents = useCallback(async () => {
    const url = eventFilter
      ? `${V2}/analytics/events?event_type=${encodeURIComponent(eventFilter)}&limit=30`
      : `${V2}/analytics/events?limit=30`;
    const data = await get(url);
    setEvents(data && data.events ? data.events : []);
  }, [eventFilter]);

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  useEffect(() => {
    if (tab === "providers") loadProviders();
    if (tab === "thresholds") loadThresholds();
    if (tab === "analytics") {
      loadAnalyticsSummary();
      loadEvents();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function previewImpact(pk) {
    if (!approveVersion) {
      alert("Enter a version number first.");
      return;
    }
    const data = await get(`${V2}/providers/${pk}/pricing/impact/${approveVersion}`);
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
    const result = await post(`${V2}/providers/${stageProvider}/pricing/stage`, {
      profile_data: { ...json, provider_key: stageProvider },
      created_by: "admin",
    });
    if (result && result.staged_version) {
      setStageMsg({ ok: true, text: `Staged v${result.staged_version}. Validate then approve to activate.` });
      loadProviders();
    } else {
      setStageMsg({ ok: false, text: result?.detail || "Stage failed." });
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
    const result = await post(`${V2}/providers/${stageProvider}/pricing/validate`, {
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
    const result = await post(
      `${V2}/providers/${stageProvider}/pricing/approve?version=${approveVersion}&approved_by=admin`,
      {}
    );
    if (result && result.activated_version) {
      setApproveMsg({ ok: true, text: `v${result.activated_version} activated.` });
      loadProviders();
    } else {
      setApproveMsg({ ok: false, text: result?.detail || "Approval failed." });
    }
  }

  async function handleRollback() {
    if (!stageProvider) {
      setStageMsg({ ok: false, text: "Select a provider." });
      return;
    }
    const result = await post(`${V2}/providers/${stageProvider}/pricing/rollback`, {});
    if (result && result.rolled_back_to) {
      setStageMsg({ ok: true, text: `Rolled back to v${result.rolled_back_to}.` });
      loadProviders();
    } else {
      setStageMsg({ ok: false, text: result?.detail || "Rollback failed." });
    }
  }

  async function handleSaveThresholds() {
    const payload = {
      near_budget_threshold: parseFloat(nearBudget),
      async_savings_threshold: parseFloat(asyncSavings),
    };
    const result = await patch(`${V1A}/thresholds`, payload);
    setThresholdMsg(result ? { ok: true, text: "Thresholds saved." } : { ok: false, text: "Save failed." });
  }

  async function handleLoadLedger() {
    const url = ledgerWs ? `${V2}/ledger/summary?workspace_id=${ledgerWs}` : `${V2}/ledger/summary`;
    const summary = await get(url);
    const entryUrl = ledgerWs
      ? `${V2}/ledger/entries?workspace_id=${ledgerWs}&limit=20`
      : `${V2}/ledger/entries?limit=20`;
    const entries = await get(entryUrl);
    setLedgerLoaded(true);
    if (summary) setLedgerSummary(summary);
    if (entries) setLedgerEntries(entries.entries || []);
  }

  async function handleImportActual() {
    if (!actualAmount) {
      setActualMsg({ ok: false, text: "Enter actual amount." });
      return;
    }
    const payload = {
      provider_key: actualProvider,
      actual_amount: parseFloat(actualAmount),
      currency: "USD",
      import_source: "manual",
      notes: actualNotes || null,
      estimate_id: actualEstimateId || null,
    };
    const result = await post(`${V2}/actuals/import`, payload);
    if (result && result.actual_cost_id) {
      setActualMsg({ ok: true, text: `Imported. Map status: ${result.map_status}.` });
    } else {
      setActualMsg({ ok: false, text: "Import failed." });
    }
  }

  async function handleLoadVariances() {
    const data = await get(`${V2}/actuals/variance`);
    if (data) setVarianceReport(data);
  }

  async function handleLoadUnmapped() {
    const data = await get(`${V2}/actuals/unmapped`);
    setUnmapped(data && data.unmapped ? data.unmapped : []);
  }

  async function handleForecast() {
    let url = `${V2}/analytics/forecast?days_ahead=${forecastDays || 30}`;
    if (forecastWs) url += `&workspace_id=${forecastWs}`;
    if (forecastBudget) url += `&monthly_budget=${forecastBudget}`;
    const data = await get(url);
    if (data) setForecastResult(data);
  }

  async function handleLoadAlerts() {
    const data = await get(`${V2}/analytics/alerts`);
    setAlerts(data && data.alerts ? data.alerts : []);
  }

  async function handleRunAnomalies() {
    const data = await get(`${V2}/analytics/anomalies`);
    setAnomalies(data && data.anomalies ? data.anomalies : []);
  }

  return (
    <div className="icx-root">
      <style>{styles}</style>

      <header className="icx-header">
        <h1>IncuBrix - Admin Console</h1>
        <div>
          <Link to="/simulation">Simulation UI</Link>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">API Docs ↗</a>
        </div>
      </header>

      <div className="icx-tabs">
        {["providers", "thresholds", "ledger", "actuals", "analytics", "forecast"].map((name) => (
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
                  <th>Source</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {providerError && (
                  <tr>
                    <td colSpan={6} style={{ color: "var(--red)" }}>Cannot connect to API. Is the server running?</td>
                  </tr>
                )}
                {!providerError && providers === null && (
                  <tr>
                    <td colSpan={6} style={{ color: "var(--muted)" }}>Loading...</td>
                  </tr>
                )}
                {!providerError &&
                  providers &&
                  providers.map((p, i) => (
                    <tr key={i}>
                      <td><strong>{p.provider_key}</strong></td>
                      <td style={{ color: "var(--muted)" }}>{p.model_key || "default"}</td>
                      <td>v{p.profile_version}</td>
                      <td><span className="icx-badge active-b">{p.approval_status}</span></td>
                      <td style={{ color: "var(--muted)" }}>{p.source_type || "manual"}</td>
                      <td>
                        <button className="icx-btn" onClick={() => previewImpact(p.provider_key)}>
                          Impact Preview
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          <div className="icx-card">
            <h2>Manage Profile Version</h2>
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
                  <label>Profile JSON (fields to update)</label>
                  <textarea
                    value={stageJson}
                    onChange={(e) => setStageJson(e.target.value)}
                    placeholder='{"rate_cards":[{"model_key":"default","unit_type":"per_second","unit_rate":0.025,"quality_class":"high","currency":"USD"}]}'
                  />
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button className="icx-btn primary" onClick={handleStage}>Stage New Version</button>
                  <button className="icx-btn" onClick={handleValidate}>Validate</button>
                  <button className="icx-btn danger" onClick={handleRollback}>Rollback</button>
                </div>
                {stageMsg && <div className={`icx-msg ${stageMsg.ok ? "ok" : "err"}`}>{stageMsg.text}</div>}
              </div>
              <div>
                <div className="icx-field">
                  <label>Approve Version Number</label>
                  <input
                    type="number"
                    min={1}
                    placeholder="e.g. 2"
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
          <div className="icx-card" style={{ maxWidth: 480 }}>
            <h2>Policy Thresholds</h2>
            <div className="icx-field">
              <label>Near-Budget Warning Threshold (0.0 – 1.0)</label>
              <input
                type="number"
                step="0.01"
                min={0}
                max={1}
                placeholder="default: 0.85"
                value={nearBudget}
                onChange={(e) => setNearBudget(e.target.value)}
              />
              <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 3 }}>
                Routes where high cost {">="} this % of cap get a warning.
              </div>
            </div>
            <div className="icx-field">
              <label>Async Savings Threshold (0.0 – 1.0)</label>
              <input
                type="number"
                step="0.01"
                min={0}
                max={1}
                placeholder="default: 0.15"
                value={asyncSavings}
                onChange={(e) => setAsyncSavings(e.target.value)}
              />
              <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 3 }}>
                Async recommended when savings exceed this %.
              </div>
            </div>
            <button className="icx-btn primary" onClick={handleSaveThresholds}>Save Thresholds</button>
            {thresholdMsg && <div className={`icx-msg ${thresholdMsg.ok ? "ok" : "err"}`}>{thresholdMsg.text}</div>}
          </div>
        </div>
      )}

      {tab === "ledger" && (
        <div className="icx-section">
          <div className="icx-card">
            <h2>Ledger Summary</h2>
            <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
              <input
                className="icx-input"
                placeholder="workspace_id (optional)"
                style={{ width: 220 }}
                value={ledgerWs}
                onChange={(e) => setLedgerWs(e.target.value)}
              />
              <button className="icx-btn primary" onClick={handleLoadLedger}>Load Summary</button>
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
                  <th>Campaign</th>
                  <th>Notes</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {!ledgerLoaded && (
                  <tr>
                    <td colSpan={6} style={{ color: "var(--muted)" }}>Click Load Summary above.</td>
                  </tr>
                )}
                {ledgerLoaded && ledgerEntries.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ color: "var(--muted)" }}>No entries.</td>
                  </tr>
                )}
                {ledgerLoaded &&
                  ledgerEntries.map((e, i) => (
                    <tr key={i}>
                      <td>{e.entry_type}</td>
                      <td>${parseFloat(e.amount).toFixed(4)}</td>
                      <td>{e.provider_key || "-"}</td>
                      <td>{e.campaign_id || "-"}</td>
                      <td style={{ color: "var(--muted)" }}>{e.notes || ""}</td>
                      <td style={{ color: "var(--muted)" }}>{e.created_at?.slice(0, 19)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "actuals" && (
        <div className="icx-section">
          <div className="icx-card">
            <h2>Import Actual Cost</h2>
            <div className="icx-grid2">
              <div>
                <div className="icx-field">
                  <label>Provider</label>
                  <select value={actualProvider} onChange={(e) => setActualProvider(e.target.value)}>
                    {PROVIDERS.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  <div className="icx-field">
                    <label>Actual Amount ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="e.g. 12.50"
                      value={actualAmount}
                      onChange={(e) => setActualAmount(e.target.value)}
                    />
                  </div>
                  <div className="icx-field">
                    <label>Estimate ID (optional)</label>
                    <input
                      type="text"
                      placeholder="link to estimate"
                      value={actualEstimateId}
                      onChange={(e) => setActualEstimateId(e.target.value)}
                    />
                  </div>
                </div>
                <div className="icx-field">
                  <label>Notes</label>
                  <input
                    type="text"
                    placeholder="e.g. Invoice #123"
                    value={actualNotes}
                    onChange={(e) => setActualNotes(e.target.value)}
                  />
                </div>
                <button className="icx-btn primary" onClick={handleImportActual}>Import</button>
                {actualMsg && <div className={`icx-msg ${actualMsg.ok ? "ok" : "err"}`}>{actualMsg.text}</div>}
              </div>
              <div>
                <button className="icx-btn" onClick={handleLoadVariances} style={{ marginBottom: 12 }}>
                  Load Variance Report
                </button>
                {varianceReport && (
                  <div className="icx-kv" style={{ maxHeight: 260 }}>
                    {JSON.stringify(varianceReport, null, 2)}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="icx-card">
            <h2>Unmapped Actuals</h2>
            <button className="icx-btn" onClick={handleLoadUnmapped} style={{ marginBottom: 12 }}>
              Load Unmapped
            </button>
            <table className="icx-table">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Amount</th>
                  <th>Source</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {unmapped === null && (
                  <tr>
                    <td colSpan={4} style={{ color: "var(--muted)" }}>Click Load Unmapped.</td>
                  </tr>
                )}
                {unmapped && unmapped.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ color: "var(--muted)" }}>No unmapped actuals.</td>
                  </tr>
                )}
                {unmapped &&
                  unmapped.map((r, i) => (
                    <tr key={i}>
                      <td>{r.provider_key}</td>
                      <td>${parseFloat(r.actual_amount).toFixed(4)}</td>
                      <td>{r.import_source}</td>
                      <td style={{ color: "var(--muted)" }}>{r.created_at?.slice(0, 19)}</td>
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
            <h2>Events</h2>
            <div style={{ display: "flex", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
              <select
                className="icx-input"
                value={eventFilter}
                onChange={(e) => setEventFilter(e.target.value)}
              >
                {EVENT_TYPES.map(([val, label]) => (
                  <option key={val} value={val}>{label}</option>
                ))}
              </select>
              <button className="icx-btn" onClick={loadEvents}>Refresh</button>
            </div>
            <div>
              {events === null && <div style={{ color: "var(--muted)", fontSize: 13 }}>Loading...</div>}
              {events && events.length === 0 && (
                <div style={{ color: "var(--muted)", fontSize: 13 }}>No events yet. Run an estimate first.</div>
              )}
              {events &&
                events.map((e, i) => (
                  <div className="icx-event-row" key={i}>
                    <div className="icx-event-type">{e.event_type}</div>
                    <div style={{ color: "var(--muted)", minWidth: 160 }}>{e.created_at?.slice(0, 19)}</div>
                    <div style={{ fontFamily: "monospace", fontSize: 11, color: "var(--muted)" }}>
                      {JSON.stringify(e.properties || {}).slice(0, 140)}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {tab === "forecast" && (
        <div className="icx-section">
          <div className="icx-card" style={{ maxWidth: 520 }}>
            <h2>Spend Forecast</h2>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
              <input
                className="icx-input"
                placeholder="workspace_id (optional)"
                style={{ flex: 1, minWidth: 160 }}
                value={forecastWs}
                onChange={(e) => setForecastWs(e.target.value)}
              />
              <input
                className="icx-input"
                type="number"
                min={1}
                placeholder="days ahead"
                style={{ width: 100 }}
                value={forecastDays}
                onChange={(e) => setForecastDays(e.target.value)}
              />
              <input
                className="icx-input"
                type="number"
                step="0.01"
                placeholder="monthly budget $"
                style={{ width: 150 }}
                value={forecastBudget}
                onChange={(e) => setForecastBudget(e.target.value)}
              />
            </div>
            <button className="icx-btn primary" onClick={handleForecast}>Run Forecast</button>
            {forecastResult && (
              <div className="icx-kv" style={{ marginTop: 12 }}>
                {JSON.stringify(forecastResult, null, 2)}
              </div>
            )}
          </div>

          <div className="icx-card">
            <h2>Active Alerts</h2>
            <button className="icx-btn" onClick={handleLoadAlerts} style={{ marginBottom: 12 }}>
              Load Alerts
            </button>
            {alerts === null && <div style={{ color: "var(--muted)", fontSize: 13 }}>Click Load Alerts.</div>}
            {alerts && alerts.length === 0 && (
              <div style={{ color: "var(--muted)", fontSize: 13 }}>No active alerts.</div>
            )}
            {alerts &&
              alerts.map((a, i) => (
                <div className="icx-alert-card" key={i}>
                  <div className="icx-alert-title">
                    {a.title}{" "}
                    <span className={`icx-badge icx-sev-${a.severity}`} style={{ marginLeft: 6 }}>
                      {a.severity}
                    </span>
                  </div>
                  <div className="icx-alert-desc">{a.description || ""}</div>
                </div>
              ))}
          </div>

          <div className="icx-card">
            <h2>Anomaly Detection</h2>
            <button className="icx-btn primary" onClick={handleRunAnomalies}>Run Detection</button>
            <div style={{ marginTop: 12, fontSize: 13, color: "var(--muted)" }}>
              {anomalies === null && ""}
              {anomalies && anomalies.length === 0 && "No anomalies detected."}
              {anomalies &&
                anomalies.length > 0 &&
                anomalies.map((a, i) => (
                  <div
                    key={i}
                    style={{ padding: "6px 0", borderBottom: "1px solid var(--border)" }}
                  >
                    <strong style={{ color: "var(--text)" }}>{a.provider_key}</strong> — variance{" "}
                    {a.variance_percent?.toFixed(1)}%{" "}
                    <span className={`icx-badge icx-sev-${a.severity}`} style={{ marginLeft: 4 }}>
                      {a.severity}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
