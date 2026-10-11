import React, { useEffect, useState } from 'react';
import { api, useApi } from '../api';
import { formatDistance, formatNumber, formatPc, formatUtc, liveEvent, tierOf } from '../lib/format';
import { ApiErrorBox, Badge, LineChart, Loading, Metric, Notice, PageHeader } from '../components/ui';
import { PAGE_STYLE, buttonStyle, inputStyle } from '../lib/styles';
import { ArrowRight, BrainCircuit, CheckCircle2, Gauge, ShieldAlert, Sliders } from 'lucide-react';

const SIGMA_NAMES = { r: 'radial', t: 'along-track', n: 'cross-track' };

function ShapBars({ features, valueKey = 'shap_value', format = (v) => v.toFixed(2), unit = '' }) {
  const max = Math.max(...features.map((f) => Math.abs(f[valueKey])), 1e-9);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {features.map((f) => {
        const up = f[valueKey] > 0;
        return (
          <div key={f.feature} style={{ background: 'rgba(0,0,0,0.25)', padding: '10px 14px', borderRadius: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>{f.label}</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: up ? '#f87171' : '#34d399' }} className="mono">
                {up ? '+' : ''}{format(f[valueKey])}{unit}
              </span>
            </div>
            <div style={{ width: '100%', height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden', marginBottom: 6 }}>
              <div style={{ width: `${(Math.abs(f[valueKey]) / max) * 100}%`, height: '100%', borderRadius: 3,
                background: up ? 'linear-gradient(90deg, #f97316, #dc2626)' : 'linear-gradient(90deg, #38bdf8, #10b981)' }} />
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8' }} className="mono">
              value = {typeof f.value === 'number' ? Number(f.value.toPrecision(4)) : String(f.value)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Slider({ label, value, setValue, min, max, step, format }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: '#94a3b8' }}>{label}</span>
        <span style={{ fontWeight: 700, color: '#f8fafc' }} className="mono">{format(value)}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => setValue(parseFloat(e.target.value))}
        style={{ width: '100%', accentColor: '#38bdf8' }} />
    </div>
  );
}

// Re-runs the real Pc engine (POST /api/predict/what-if) as the sliders move. Scales are log10 on the slider.
function WhatIfTuner({ source, id }) {
  const [miss, setMiss] = useState(0);
  const [sigma, setSigma] = useState(0);
  const [hbr, setHbr] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      api('/predict/what-if', { method: 'POST', signal: ctrl.signal,
        body: { source, id: String(id), miss_scale: 10 ** miss, sigma_scale: 10 ** sigma, hbr_scale: 10 ** hbr } })
        .then((r) => { setResult(r); setError(null); })
        .catch((e) => { if (e.name !== 'AbortError') setError(e); });
    }, 250);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [source, id, miss, sigma, hbr]);
  const factor = (v) => `×${(10 ** v).toPrecision(2)}`;
  const mod = result?.modified, base = result?.baseline;
  return (
    <div className="glass-panel" style={{ padding: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Sliders size={16} color="#38bdf8" />
        <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: '#f8fafc' }}>What-if: recompute with the Pc engine</h3>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Slider label="Miss distance" value={miss} setValue={setMiss} min={-1} max={2} step={0.05} format={factor} />
        <Slider label="Position uncertainty (σ)" value={sigma} setValue={setSigma} min={-2} max={2} step={0.05} format={factor} />
        <Slider label="Hard-body radius (object size)" value={hbr} setValue={setHbr} min={-1} max={1} step={0.05} format={factor} />
      </div>
      <ApiErrorBox error={error} what="what-if result" />
      {mod && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 14 }}>
          <Metric label="Baseline Pc" value={formatPc(base.log_pc)} sub={`${base.risk_level} · ${formatDistance(base.miss_distance_m)}`} color={tierOf(base.risk_level).color} />
          <Metric label="What-if Pc" value={formatPc(mod.log_pc)} sub={`${mod.risk_level} · ${formatDistance(mod.miss_distance_m)}`} color={tierOf(mod.risk_level).color} />
        </div>
      )}
      <div style={{ fontSize: 10, color: '#64748b', marginTop: 8 }}>
        Same 2D encounter-plane integral as the screening (validated against ESA's own risk values).
      </div>
    </div>
  );
}

function DecisionBadge({ danger, label }) {
  return (
    <div className="glass-panel" style={{ padding: '10px 18px', borderLeft: `4px solid ${danger ? '#dc2626' : '#10b981'}`, display: 'flex', alignItems: 'center', gap: 12 }}>
      {danger ? <ShieldAlert size={24} color="#dc2626" /> : <CheckCircle2 size={24} color="#10b981" />}
      <div>
        <div style={{ fontSize: 11, color: '#94a3b8' }}>OPERATOR DECISION</div>
        <div style={{ fontSize: 16, fontWeight: 800, color: danger ? '#f87171' : '#34d399' }}>{label}</div>
      </div>
    </div>
  );
}

function LiveAnalysis({ eventKey, onNavigateToManeuver }) {
  const { data, error, loading } = useApi(`/conjunctions/detail/${encodeURIComponent(eventKey)}`);
  const [role, setRole] = useState('secondary');
  const [axis, setAxis] = useState('t');
  if (loading) return <Loading>Computing the physics breakdown and SHAP explanations…</Loading>;
  if (error) return <ApiErrorBox error={error} what="conjunction" />;
  const c = data.conjunction, enc = data.encounter;
  const tier = tierOf(c.risk_level, c.status);
  const obj = data.objects.find((o) => o.role === role);
  const ml = obj.ml_explanation?.[axis];
  const danger = c.status === 'DANGER';
  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800 }}>{c.primary_name} vs {c.secondary_name}</div>
          <div style={{ fontSize: 12, color: '#94a3b8' }}>TCA {formatUtc(c.tca_utc)} (T-{c.time_to_tca_hours.toFixed(1)} h) · {c.secondary_type}{c.simulated ? ' · simulated test threat' : ''}</div>
        </div>
        <DecisionBadge danger={danger} label={{ DANGER: 'MANEUVER RECOMMENDED', REVIEW: 'MONITOR (REVIEW)', MITIGATED: 'BURN ACCEPTED', SAFE: 'HOLD (NOMINAL)' }[c.status]} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 20 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className="glass-panel" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 12px' }}>Encounter physics</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
              <Metric label="Miss distance" value={formatDistance(c.miss_distance_m)} sub={`R ${formatNumber(enc.miss_vector_rtn_m.r, 0)} · T ${formatNumber(enc.miss_vector_rtn_m.t, 0)} · N ${formatNumber(enc.miss_vector_rtn_m.n, 0)} m`} />
              <Metric label="Closing speed" value={`${c.relative_velocity_km_s.toFixed(2)} km/s`} />
              <Metric label="Uncertainty ellipse (1σ)" value={`${formatDistance(enc.sigma_major_m)} × ${formatDistance(enc.sigma_minor_m)}`} sub="combined, encounter plane" />
              <Metric label="Mahalanobis distance" value={enc.mahalanobis_distance.toFixed(2)} sub="miss in σ units" />
              <Metric label="Hard-body radius" value={`${enc.hard_body_radius_m.toFixed(1)} m`} />
              <Metric label="Pc (OrbitGuard)" value={formatPc(enc.log_pc_ours)} color={tier.color} sub={c.risk_level} />
              <Metric label="Worst-case Pc" value={formatPc(enc.log_pc_max)} sub="least favourable σ size" />
              <Metric label="Pc used" value={formatPc(enc.log_pc_used)} sub={enc.pc_source} />
            </div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 10 }}>{enc.model}</div>
          </div>

          <div className="glass-panel" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 8, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Gauge size={18} color="#38bdf8" />
                <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>SHAP: why the orbit uncertainty is this large</h3>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                {data.objects.map((o) => <button key={o.role} onClick={() => setRole(o.role)} style={buttonStyle('default', role === o.role)}>{o.name}</button>)}
                {Object.keys(SIGMA_NAMES).map((a) => <button key={a} onClick={() => setAxis(a)} style={buttonStyle('default', axis === a)}>{SIGMA_NAMES[a]}</button>)}
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
              <Metric label={`Total ${SIGMA_NAMES[axis]} σ`} value={formatDistance(obj.sigma_total_m[axis])} />
              <Metric label="Assumed TLE error" value={formatDistance(obj.sigma_tle_m[axis])} sub={`orbit data ${obj.epoch_age_days.toFixed(1)} days old`} />
              <Metric label="ML-predicted σ" value={obj.sigma_ml_m ? formatDistance(obj.sigma_ml_m[axis]) : '—'} sub="trained on ESA CDMs" />
            </div>
            {ml ? (
              <>
                <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>
                  Each input multiplies the model's typical σ ({formatDistance(10 ** ml.base_log10_m)}) by the factor shown; together they give {formatDistance(10 ** ml.predicted_log10_m)}.
                </div>
                <ShapBars features={ml.features.slice(0, 6)} valueKey="shap_log10" format={(v) => `${v.toFixed(2)} dex (×${(10 ** v).toPrecision(2)})`} />
              </>
            ) : <Notice tone="warn">The ML uncertainty model is not loaded, so only the assumed TLE error is used.</Notice>}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className="glass-panel" style={{ padding: 18, borderLeft: '4px solid #38bdf8' }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 10px' }}>OPERATIONAL TELEMETRY READOUT</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
              <Notice tone={danger ? 'error' : 'ok'}>
                <strong>[ALERT]:</strong> Pc {formatPc(c.log_pc)} ({c.risk_level}) at {formatDistance(c.miss_distance_m)} miss, {c.relative_velocity_km_s.toFixed(1)} km/s, in {c.time_to_tca_hours.toFixed(1)} h.
              </Notice>
              <Notice>
                <strong>[DIAGNOSTIC]:</strong> The miss is {enc.mahalanobis_distance.toFixed(2)}σ inside a {formatDistance(enc.sigma_major_m)} × {formatDistance(enc.sigma_minor_m)} uncertainty ellipse
                {enc.mahalanobis_distance < 1 ? ' — the objects could plausibly touch.' : '.'}
              </Notice>
              <Notice tone="ok">
                <strong>[ACTION]:</strong> {danger ? 'Plan an avoidance burn — the J2 manoeuvre planner computes the smallest verified option.'
                  : c.status === 'MITIGATED' ? 'Avoidance burn accepted by the operator.' : 'HOLD. Keep monitoring new orbit data.'}
              </Notice>
            </div>
          </div>
          <WhatIfTuner source="live" id={c.key} />
          <button onClick={() => onNavigateToManeuver && onNavigateToManeuver(liveEvent(c))}
            style={{ ...buttonStyle(danger ? 'danger' : 'default'), padding: '10px 16px', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <span>{danger ? 'Proceed to Δv Maneuver Optimization' : 'Open the manoeuvre planner'}</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </>
  );
}

function EsaAnalysis({ eventId, onNavigateToManeuver }) {
  const { data, error, loading } = useApi(`/predict/esa-replay/${eventId}`);
  if (loading) return <Loading>Running the CDM model and TreeSHAP on every CDM of event {eventId}…</Loading>;
  if (error) return <ApiErrorBox error={error} what="ESA event" />;
  const d = data.decision_cdm;
  const tier = tierOf(d.risk_level);
  const danger = d.status === 'DANGER';
  const pts = (key) => data.series.map((p) => ({ x: p.time_to_tca_days, y: Math.max(p[key] ?? NaN, -30), highlight: key === 'esa_risk' && p.is_decision_cdm, label: `${p.time_to_tca_days.toFixed(2)} d: ${p[key]?.toFixed(2)}` }));
  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 800 }}>ESA event {data.event_id} · mission {data.mission_id} vs {data.other_object_type}</div>
          <div style={{ fontSize: 12, color: '#94a3b8' }}>{data.n_cdms} CDMs · {data.source}</div>
        </div>
        <DecisionBadge danger={danger} label={danger ? 'MANEUVER RECOMMENDED' : d.status === 'REVIEW' ? 'MONITOR (REVIEW)' : 'HOLD (NOMINAL)'} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 20 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className="glass-panel" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Gauge size={18} color="#38bdf8" />
                <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>SHAP Driving Factor Attribution</h3>
              </div>
              <span style={{ fontSize: 11, color: '#94a3b8' }}>TreeSHAP on the decision CDM ({d.time_to_tca_days.toFixed(2)} days before TCA)</span>
            </div>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>
              Starting from the model's average of {data.shap.base_value.toFixed(2)} log₁₀ Pc, these inputs move it to {data.shap.prediction.toFixed(2)} (red raises the risk, green lowers it).
            </div>
            <ShapBars features={data.shap.features.slice(0, 8)} format={(v) => `${v.toFixed(2)} log₁₀ Pc`} />
          </div>
          <div className="glass-panel" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 6px' }}>Risk evolution over the CDM sequence</h3>
            <LineChart xReversed xLabel="Days before closest approach" yLabel="log₁₀ Pc"
              series={[{ name: 'ESA risk', color: '#f8fafc', points: pts('esa_risk') },
                { name: 'CDM model', color: '#38bdf8', points: pts('model_risk'), dashed: true },
                { name: 'Physics engine', color: '#a855f7', points: pts('physics_risk'), dashed: true }]}
              hLines={[{ y: -4.5, color: '#f97316', label: 'HIGH (−4.5)' }, { y: -3, color: '#dc2626', label: 'CRITICAL (−3)' }]}
              vLines={[{ x: 2, color: 'rgba(255,255,255,0.25)' }]} formatX={(v) => v.toFixed(1)} formatY={(v) => v.toFixed(0)} />
            <div style={{ fontSize: 10, color: '#64748b' }}>The orange dot is the decision CDM (latest one at least 2 days before TCA). {data.model_note}</div>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className="glass-panel" style={{ padding: 18, borderLeft: '4px solid #38bdf8' }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 10px' }}>DECISION CDM</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <Metric label="ESA risk" value={formatPc(d.esa_risk)} color={tierOf(d.risk_level).color} />
              <Metric label="Model prediction" value={formatPc(d.model_risk)} color={tier.color} sub={d.risk_level} />
              <Metric label="Physics recomputation" value={formatPc(d.physics_risk)} />
              <Metric label="Final CDM (ESA)" value={formatPc(data.final_cdm.esa_risk)} sub={`${data.final_cdm.time_to_tca_days.toFixed(2)} d before TCA`} />
              <Metric label="Miss distance" value={formatDistance(d.miss_distance_m)} sub={`R ${formatNumber(d.radial_miss_m, 0)} · T ${formatNumber(d.along_track_miss_m, 0)} · N ${formatNumber(d.cross_track_miss_m, 0)} m`} />
              <Metric label="Relative speed" value={`${(d.relative_speed_m_s / 1000).toFixed(2)} km/s`} />
              <Metric label="Solar flux F10.7" value={formatNumber(d.space_weather.F10, 0)} sub={`81-day mean ${formatNumber(d.space_weather.F3M, 0)}`} />
              <Metric label="Geomagnetic Ap" value={formatNumber(d.space_weather.AP, 0)} />
            </div>
          </div>
          {d.physics_risk !== null && <WhatIfTuner source="esa" id={data.event_id} />}
          <button onClick={() => onNavigateToManeuver && onNavigateToManeuver({ source: 'esa', event_id: data.event_id })}
            style={{ ...buttonStyle(danger ? 'danger' : 'default'), padding: '10px 16px', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <span>CDM-only Δv estimate for this event</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </>
  );
}

export default function AnalysisView({ event, onNavigateToManeuver }) {
  const [picked, setPicked] = useState(null);
  const { data: status } = useApi('/status');
  const { data: open } = useApi(status?.phase === 'ready' ? '/conjunctions/screen?status=DANGER&status=REVIEW&status=MITIGATED&limit=25' : null);
  const { data: esaEvents, error: esaError } = useApi('/predict/esa-events');

  const liveOptions = open?.conjunctions || [];
  const fallback = liveOptions[0] ? liveEvent(liveOptions[0]) : esaEvents?.[0] ? { source: 'esa', event_id: esaEvents[0].event_id } : null;
  const current = picked || event || fallback;
  const value = current ? (current.source === 'live' ? `live:${current.key}` : `esa:${current.event_id}`) : '';

  const choose = (v) => {
    const [src, id] = [v.slice(0, v.indexOf(':')), v.slice(v.indexOf(':') + 1)];
    if (src === 'live') setPicked(liveEvent(liveOptions.find((c) => c.key === id) || { key: id }));
    else setPicked({ source: 'esa', event_id: Number(id) });
  };

  return (
    <div style={PAGE_STYLE}>
      <PageHeader icon={BrainCircuit} title="Explainable AI (XAI) & Conjunction Risk"
        subtitle="Live conjunctions: physics breakdown + SHAP of the ML uncertainty model · ESA events: TreeSHAP of the trained CDM risk model">
        <select value={value} onChange={(e) => choose(e.target.value)} style={{ ...inputStyle, maxWidth: 420 }}>
          {current?.source === 'live' && !liveOptions.some((c) => c.key === current.key) && <option value={value}>{current.primary_name} vs {current.secondary_name}</option>}
          {liveOptions.length > 0 && (
            <optgroup label="Live conjunctions (danger / review / mitigated)">
              {liveOptions.map((c) => <option key={c.key} value={`live:${c.key}`}>{c.status} · {c.primary_name} vs {c.secondary_name} · Pc {formatPc(c.log_pc)}</option>)}
            </optgroup>
          )}
          {esaEvents?.length > 0 && (
            <optgroup label="ESA dataset events">
              {esaEvents.map((e) => <option key={e.event_id} value={`esa:${e.event_id}`}>{e.title} · event {e.event_id}</option>)}
            </optgroup>
          )}
        </select>
      </PageHeader>
      {!current && (esaError ? <ApiErrorBox error={esaError} what="events" /> : <Loading>Loading events…</Loading>)}
      {current?.source === 'live' && <LiveAnalysis key={current.key} eventKey={current.key} onNavigateToManeuver={onNavigateToManeuver} />}
      {current?.source === 'esa' && <EsaAnalysis key={current.event_id} eventId={current.event_id} onNavigateToManeuver={onNavigateToManeuver} />}
      {current?.source === 'live' && <div style={{ marginTop: 10 }}><Badge>Live conjunction · {current.key}</Badge></div>}
    </div>
  );
}
