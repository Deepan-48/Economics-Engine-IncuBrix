import { useState } from "react";
import { Link } from "react-router-dom";

const API = "http://localhost:8000";

const styles = `
.sim-root{--blue:#185FA5;--green:#0F6E56;--red:#A32D2D;--yellow:#92620A;--bg:#F8F9FA;--card:#fff;--border:#DEE2E6;--text:#1A1A2E;--muted:#6C757D;--radius:8px;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.sim-root *{box-sizing:border-box}
.sim-header{background:var(--blue);color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between}
.sim-header h1{font-size:17px;font-weight:600;margin:0}
.sim-header a{color:rgba(255,255,255,.8);font-size:12px;text-decoration:none;margin-left:16px;cursor:pointer}
.sim-layout{display:grid;grid-template-columns:360px 1fr;gap:20px;padding:20px 28px;max-width:1300px;margin:0 auto}
.sim-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:18px;margin-bottom:14px}
.sim-card h2{font-size:13px;font-weight:600;color:var(--blue);text-transform:uppercase;letter-spacing:.04em;margin:0 0 14px}
.sim-field{margin-bottom:12px}
.sim-field label{display:block;font-size:12px;font-weight:500;color:var(--muted);margin-bottom:4px}
.sim-field select,.sim-field input{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px}
.sim-field-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.sim-run{width:100%;padding:11px;background:var(--blue);color:#fff;border:none;border-radius:var(--radius);font-size:14px;font-weight:600;cursor:pointer;margin-top:6px}
.sim-run:hover{background:#145490}
.sim-run:disabled{background:var(--muted);cursor:not-allowed}
.sim-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;text-transform:uppercase}
.sim-badge.safe{background:#E1F5EE;color:var(--green)}
.sim-badge.warn_near_cap,.sim-badge.warning{background:#FFF3CD;color:var(--yellow)}
.sim-badge.blocked_hard_cap,.sim-badge.blocked{background:#FCEBEB;color:var(--red)}
.sim-badge.completed{background:#E6F1FB;color:var(--blue)}
.sim-route-card{border:1.5px solid var(--border);border-radius:var(--radius);padding:14px;margin-bottom:10px}
.sim-route-card.rec{border-color:var(--blue);background:#F0F6FF}
.sim-route-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px}
.sim-route-name{font-size:15px;font-weight:600;text-transform:capitalize}
.sim-cost-row{display:flex;gap:18px;margin-bottom:8px;flex-wrap:wrap}
.sim-cost-item .val{font-size:18px;font-weight:600;color:var(--blue)}
.sim-cost-item .lbl{font-size:10px;color:var(--muted)}
.sim-explanation{font-size:12px;color:var(--muted);line-height:1.5;border-top:1px solid var(--border);padding-top:8px;margin-top:6px}
.sim-meta-chip{font-size:10px;padding:2px 7px;border-radius:10px;background:var(--bg);border:1px solid var(--border);color:var(--muted);margin-right:4px}
.sim-empty{text-align:center;padding:48px;color:var(--muted);font-size:14px}
.sim-loading{text-align:center;padding:32px}
.sim-spinner{width:28px;height:28px;border:3px solid var(--border);border-top-color:var(--blue);border-radius:50%;animation:sim-spin .8s linear infinite;margin:0 auto 12px}
@keyframes sim-spin{to{transform:rotate(360deg)}}
.sim-info-box{background:#F8F9FA;border:1px solid var(--border);border-radius:6px;padding:10px 14px;margin-top:10px;font-size:12px;color:var(--muted)}
.sim-section-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin:14px 0 8px}
.sim-blocked-msg{background:#FCEBEB;border:1px solid #F5C6CB;border-radius:var(--radius);padding:14px;color:var(--red);font-size:13px;margin-bottom:14px}
.sim-tab-bar{display:flex;gap:2px;background:var(--border);padding:2px;border-radius:var(--radius);margin-bottom:14px;width:fit-content}
.sim-tab{padding:7px 16px;border-radius:6px;font-size:12px;cursor:pointer;border:none;background:transparent;color:var(--muted)}
.sim-tab.active{background:#fff;color:var(--blue);font-weight:500}
.sim-components-table{width:100%;border-collapse:collapse;font-size:11px;margin-top:8px}
.sim-components-table th{background:#E6F1FB;color:var(--blue);padding:4px 8px;text-align:left}
.sim-components-table td{padding:4px 8px;border-bottom:1px solid var(--border)}
.sim-preset-btn{padding:8px;border:1px solid var(--border);border-radius:6px;background:#fff;cursor:pointer;font-size:12px;text-align:left}
`;

const PRESETS = {
  cheap: { use_case: "article_to_social", duration_class: "short", quality_bar: "acceptable", latency_mode: "async_ok", budget_mode: "cheapest", batch_size: 5, job_budget_cap: 10, workspace_budget_cap: 500 },
  breach: { use_case: "campaign_variant_generation", duration_class: "long", quality_bar: "premium", latency_mode: "async_ok", budget_mode: "cheapest", batch_size: 20, job_budget_cap: 5, workspace_budget_cap: 500 },
  premium: { use_case: "brand_marketing_post_to_promo", duration_class: "medium", quality_bar: "premium", latency_mode: "fastest", budget_mode: "premium", batch_size: 1, job_budget_cap: 50, workspace_budget_cap: 500 },
  margin: { use_case: "script_to_social_variants", duration_class: "short", quality_bar: "high", latency_mode: "async_ok", budget_mode: "balanced", batch_size: 10, job_budget_cap: 25, workspace_budget_cap: 500 },
};

function badgeClass(s) {
  return (s || "safe").replace(/\./g, "_");
}

function Badge({ status }) {
  return <span className={`sim-badge ${badgeClass(status)}`}>{(status || "safe").replace(/_/g, " ")}</span>;
}

function RouteCard({ r, isRec }) {
  const provider = r.provider || r.provider_key;
  return (
    <div className={`sim-route-card${isRec ? " rec" : ""}`}>
      <div className="sim-route-header">
        <span className="sim-route-name">🔹 {provider}</span>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          {r.is_async_batch && <span className="sim-meta-chip">async/batch</span>}
          <Badge status={r.budget_status} />
          {isRec && <span className="sim-badge completed">RECOMMENDED</span>}
        </div>
      </div>
      <div className="sim-cost-row">
        <div className="sim-cost-item"><div className="val">${r.estimated_base_cost?.toFixed(2)}</div><div className="lbl">Base</div></div>
        <div className="sim-cost-item"><div className="val" style={{ color: "var(--green)" }}>${r.estimated_low_cost?.toFixed(2)}</div><div className="lbl">Low</div></div>
        <div className="sim-cost-item"><div className="val" style={{ color: "var(--red)" }}>${r.estimated_high_cost?.toFixed(2)}</div><div className="lbl">High</div></div>
        {r.final_score != null && (
          <div className="sim-cost-item"><div className="val" style={{ color: "var(--muted)" }}>{(r.final_score * 100).toFixed(0)}</div><div className="lbl">Score</div></div>
        )}
        {r.per_output_cost != null && (
          <div className="sim-cost-item"><div className="val" style={{ fontSize: 14 }}>${r.per_output_cost?.toFixed(4)}</div><div className="lbl">Per output</div></div>
        )}
      </div>
      <div style={{ marginBottom: 6 }}>
        <span className="sim-meta-chip">cost: {r.cost_class}</span>
        <span className="sim-meta-chip">confidence: {r.confidence_class}</span>
        {r.async_savings_percent != null && <span className="sim-meta-chip">saves {r.async_savings_percent}% vs sync</span>}
        {r.retry_exposure != null && <span className="sim-meta-chip">retry exp: ${r.retry_exposure?.toFixed(3)}</span>}
      </div>
      <div className="sim-explanation">{r.explanation}</div>
      {r.cost_components?.length > 0 && (
        <table className="sim-components-table">
          <thead>
            <tr><th>Unit Type</th><th>Qty</th><th>Rate</th><th>Base</th><th>Low</th><th>High</th></tr>
          </thead>
          <tbody>
            {r.cost_components.map((c, i) => (
              <tr key={i}>
                <td>{c.unit_type}</td>
                <td>{c.unit_quantity}</td>
                <td>${c.unit_rate?.toFixed(6)}</td>
                <td>${c.base_cost?.toFixed(4)}</td>
                <td>${c.low_cost?.toFixed(4)}</td>
                <td>${c.high_cost?.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function SimulationUI() {
  const [mode, setMode] = useState("v1");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [connError, setConnError] = useState(false);

  const [form, setForm] = useState({
    use_case: "script_to_social_variants",
    duration_class: "short",
    quality_bar: "high",
    latency_mode: "async_ok",
    budget_mode: "balanced",
    batch_size: 10,
    variant_count: 1,
    job_budget_cap: 25,
    workspace_budget_cap: 500,
    markup_mode: "",
    price_to_customer: "",
    target_margin_percent: "",
  });

  function setField(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function loadPreset(name) {
    const p = PRESETS[name];
    if (!p) return;
    setForm((f) => ({ ...f, ...p }));
    if (name === "margin") {
      setMode("v2");
      setForm((f) => ({ ...f, ...p, markup_mode: "markup", price_to_customer: 60, target_margin_percent: 40 }));
    }
  }

  async function runEstimate() {
    setLoading(true);
    setData(null);
    setConnError(false);

    const payload = {
      use_case: form.use_case,
      duration_class: form.duration_class,
      quality_bar: form.quality_bar,
      latency_mode: form.latency_mode,
      budget_mode: form.budget_mode,
      batch_size: parseInt(form.batch_size),
      simulation_mode: true,
    };
    if (form.job_budget_cap) payload.job_budget_cap = parseFloat(form.job_budget_cap);
    if (form.workspace_budget_cap) payload.workspace_budget_cap = parseFloat(form.workspace_budget_cap);

    if (mode === "v2") {
      payload.variant_count = parseInt(form.variant_count) || 1;
      if (form.markup_mode) payload.markup_mode = form.markup_mode;
      if (form.price_to_customer) payload.price_to_customer = parseFloat(form.price_to_customer);
      if (form.target_margin_percent) payload.target_margin_percent = parseFloat(form.target_margin_percent);
    }

    const endpoint = mode === "v2" ? `${API}/api/economics/v2/simulate` : `${API}/api/video-economics/simulate`;

    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await resp.json();
      setData(json);
    } catch {
      setConnError(true);
    } finally {
      setLoading(false);
    }
  }

  const blockedRoutes = data?.blocked_routes?.length
    ? data.blocked_routes
    : (data?.all_routes || []).filter((r) => r.budget_status?.includes("blocked"));

  return (
    <div className="sim-root">
      <style>{styles}</style>

      <header className="sim-header">
        <h1>IncuBrix — Economics Engine</h1>
        <div>
          <Link to="/">Admin Console</Link>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">API Docs ↗</a>
        </div>
      </header>

      <div className="sim-layout">
        <div>
          <div className="sim-card">
            <h2>Job Request</h2>
            <div className="sim-tab-bar">
              <button className={`sim-tab${mode === "v1" ? " active" : ""}`} onClick={() => setMode("v1")}>v1 API</button>
              <button className={`sim-tab${mode === "v2" ? " active" : ""}`} onClick={() => setMode("v2")}>v2 API</button>
            </div>

            <div className="sim-field">
              <label>Use Case</label>
              <select value={form.use_case} onChange={(e) => setField("use_case", e.target.value)}>
                <option value="script_to_social_variants">Script → Social Variants</option>
                <option value="article_to_social">Article → Social</option>
                <option value="brand_marketing_post_to_promo">Brand Marketing → Promo</option>
                <option value="blog_product_copy_to_explainer">Blog/Product → Explainer</option>
                <option value="campaign_variant_generation">Campaign Variant Generation</option>
                <option value="short_form_social_video">Short-form Social Video</option>
              </select>
            </div>

            <div className="sim-field-row">
              <div className="sim-field">
                <label>Duration</label>
                <select value={form.duration_class} onChange={(e) => setField("duration_class", e.target.value)}>
                  <option value="short">Short (~8s)</option>
                  <option value="medium">Medium (~20s)</option>
                  <option value="long">Long (~45s)</option>
                </select>
              </div>
              <div className="sim-field">
                <label>Quality</label>
                <select value={form.quality_bar} onChange={(e) => setField("quality_bar", e.target.value)}>
                  <option value="acceptable">Acceptable</option>
                  <option value="high">High</option>
                  <option value="premium">Premium</option>
                </select>
              </div>
            </div>

            <div className="sim-field-row">
              <div className="sim-field">
                <label>Latency Mode</label>
                <select value={form.latency_mode} onChange={(e) => setField("latency_mode", e.target.value)}>
                  <option value="fastest">Fastest</option>
                  <option value="balanced">Balanced</option>
                  <option value="async_ok">Async OK</option>
                </select>
              </div>
              <div className="sim-field">
                <label>Budget Mode</label>
                <select value={form.budget_mode} onChange={(e) => setField("budget_mode", e.target.value)}>
                  <option value="cheapest">Cheapest</option>
                  <option value="balanced">Balanced</option>
                  <option value="premium">Premium</option>
                </select>
              </div>
            </div>

            <div className="sim-field-row">
              <div className="sim-field">
                <label>Batch Size</label>
                <input type="number" min={1} value={form.batch_size} onChange={(e) => setField("batch_size", e.target.value)} />
              </div>
              {mode === "v2" && (
                <div className="sim-field">
                  <label>Variant Count <span style={{ color: "var(--blue)" }}>(v2)</span></label>
                  <input type="number" min={1} value={form.variant_count} onChange={(e) => setField("variant_count", e.target.value)} />
                </div>
              )}
            </div>

            <div className="sim-field-row">
              <div className="sim-field">
                <label>Job Budget Cap (USD)</label>
                <input type="number" min={0} step="0.01" value={form.job_budget_cap} onChange={(e) => setField("job_budget_cap", e.target.value)} />
              </div>
              <div className="sim-field">
                <label>Workspace Cap (USD)</label>
                <input type="number" min={0} step="0.01" value={form.workspace_budget_cap} onChange={(e) => setField("workspace_budget_cap", e.target.value)} />
              </div>
            </div>

            {mode === "v2" && (
              <div>
                <div style={{ borderTop: "1px solid var(--border)", margin: "12px 0 10px" }} />
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--muted)", textTransform: "uppercase", marginBottom: 8 }}>
                  Margin Simulation (v2)
                </div>
                <div className="sim-field-row">
                  <div className="sim-field">
                    <label>Price to Customer ($)</label>
                    <input type="number" step="0.01" placeholder="e.g. 60.00" value={form.price_to_customer} onChange={(e) => setField("price_to_customer", e.target.value)} />
                  </div>
                  <div className="sim-field">
                    <label>Target Margin %</label>
                    <input type="number" step="1" placeholder="e.g. 40" value={form.target_margin_percent} onChange={(e) => setField("target_margin_percent", e.target.value)} />
                  </div>
                </div>
                <div className="sim-field">
                  <label>Markup Mode</label>
                  <select value={form.markup_mode} onChange={(e) => setField("markup_mode", e.target.value)}>
                    <option value="">None</option>
                    <option value="pass_through">Pass-through</option>
                    <option value="markup">Markup</option>
                    <option value="protected_margin">Protected Margin</option>
                  </select>
                </div>
              </div>
            )}

            <button className="sim-run" disabled={loading} onClick={runEstimate}>
              {loading ? "Running..." : "▶ Run Estimate"}
            </button>
          </div>

          <div className="sim-card">
            <h2>Quick Presets</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <button className="sim-preset-btn" onClick={() => loadPreset("cheap")}>💰 Cheapest — short, acceptable, async, batch=5</button>
              <button className="sim-preset-btn" onClick={() => loadPreset("breach")}>🚫 Budget Breach — long, premium, batch=20, cap=$5</button>
              <button className="sim-preset-btn" onClick={() => loadPreset("premium")}>⭐ Premium — medium, premium, fastest, batch=1</button>
              <button className="sim-preset-btn" onClick={() => loadPreset("margin")}>📊 Margin Sim (v2) — markup, price=$60</button>
            </div>
          </div>
        </div>

        <div>
          <div className="sim-card">
            <h2>{mode === "v2" ? "Result (v2)" : "Result (v1)"}</h2>

            {loading && (
              <div className="sim-loading">
                <div className="sim-spinner" />
                <div style={{ color: "var(--muted)", fontSize: 13 }}>Running economics pipeline...</div>
              </div>
            )}

            {!loading && connError && (
              <div className="sim-blocked-msg">
                ⚠️ Cannot connect to API at {API}.<br />
                Make sure the server is running: <code>uvicorn main:app --reload</code>
              </div>
            )}

            {!loading && !connError && !data && (
              <div className="sim-empty">Fill in the form and click Run Estimate.</div>
            )}

            {!loading && !connError && data && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
                  <div style={{ fontSize: 12, color: "var(--muted)" }}>
                    Request: <code>{(data.request_id || "").slice(0, 8)}...</code>
                    {data.job_fingerprint && <> | Fingerprint: <code>{data.job_fingerprint}</code></>}
                  </div>
                  <Badge status={data.request_status} />
                </div>

                {data.request_status === "blocked" && data.blocked_reason && (
                  <div className="sim-blocked-msg">🚫 <strong>Blocked.</strong><br />{data.blocked_reason}</div>
                )}

                {data.recommended_route && (
                  <>
                    <div className="sim-section-label">✅ Recommended Route</div>
                    <RouteCard r={data.recommended_route} isRec />
                  </>
                )}

                {data.alternatives?.length > 0 && (
                  <>
                    <div className="sim-section-label">Alternatives</div>
                    {data.alternatives.map((r, i) => <RouteCard key={i} r={r} />)}
                  </>
                )}

                {blockedRoutes.length > 0 && (
                  <>
                    <div className="sim-section-label">Blocked Routes</div>
                    {blockedRoutes.map((r, i) => <RouteCard key={i} r={r} />)}
                  </>
                )}

                {data.savings_delta_vs_next != null && (
                  <div className="sim-info-box">
                    💡 Savings vs next best route: <strong>${data.savings_delta_vs_next.toFixed(4)}</strong>
                  </div>
                )}

                {data.fallback_exposure && (
                  <div className="sim-info-box">
                    <strong>Fallback Exposure:</strong> Retry ${data.fallback_exposure.retry_cost?.toFixed(2)}
                    {data.fallback_exposure.fallback_provider &&
                      ` | Fallback to ${data.fallback_exposure.fallback_provider}: $${data.fallback_exposure.fallback_cost?.toFixed(2)}`}
                    {" "}| Worst-case: <strong>${data.fallback_exposure.total_worst_case?.toFixed(2)}</strong>
                  </div>
                )}

                {data.margin_simulation && (
                  <div className="sim-info-box">
                    <strong>Margin:</strong> {data.margin_simulation.markup_mode}
                    {" "}| Cost ${data.margin_simulation.base_cost?.toFixed(2)}
                    {data.margin_simulation.price_to_customer != null &&
                      ` | Price $${parseFloat(data.margin_simulation.price_to_customer).toFixed(2)}`}
                    {data.margin_simulation.gross_margin_percent != null && (
                      <> | Margin <strong>{parseFloat(data.margin_simulation.gross_margin_percent).toFixed(1)}%</strong></>
                    )}
                    {data.margin_simulation.is_margin_blocked && (
                      <span style={{ color: "var(--red)", fontWeight: 600 }}> | BLOCKED</span>
                    )}
                  </div>
                )}

                {data.batch_recommendation?.batch_recommended && (
                  <div className="sim-info-box">
                    💡 <strong>Batch savings:</strong> Async mode saves {data.batch_recommendation.savings_percent}%
                    (${data.batch_recommendation.estimated_savings?.toFixed(2)}) via {data.batch_recommendation.recommended_provider}.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
