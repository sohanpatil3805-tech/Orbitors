import React, { useEffect, useState } from 'react';
import { api, useApi } from '../api';
import { formatDistance, formatPc, formatUtc, liveEvent, tierOf } from '../lib/format';
import { ApiErrorBox, Badge, LineChart, Loading, Metric, Notice, PageHeader } from '../components/ui';
import { PAGE_STYLE, buttonStyle, inputStyle } from '../lib/styles';
import { CheckCircle2, Crosshair, Fuel, Rocket, Sparkles, XCircle } from 'lucide-react';

const cms = (dv) => `${(dv * 100).toFixed(2)} cm/s`;

function OptionsTable({ options, selected, setSelected }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, textAlign: 'left' }}>
        <thead>
          <tr style={{ color: '#94a3b8', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
            {['', 'Option', 'Who moves', 'Burn time (UTC)', 'Lead', 'Direction', 'ΔV', 'Fuel', 'Altitude Δ', 'New miss', 'New Pc', 'New conflicts'].map((h) => (
              <th key={h} style={{ padding: '6px 8px' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {options.map((o, i) => (
            <tr key={i} onClick={() => setSelected(i)} style={{ cursor: 'pointer', background: selected === i ? 'rgba(56,189,248,0.1)' : 'transparent', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
              <td style={{ padding: '6px 8px' }}><input type="radio" readOnly checked={selected === i} /></td>
              <td style={{ padding: '6px 8px', fontWeight: 700, color: o.label === 'Recommended' ? '#fb923c' : '#f8fafc' }}>{o.label}</td>
              <td style={{ padding: '6px 8px' }}>{o.mover_name}<div style={{ fontSize: 9, color: '#64748b' }}>{o.role === 'primary' ? 'this satellite' : 'other operator'}</div></td>
              <td style={{ padding: '6px 8px' }} className="mono">{formatUtc(o.burn_time_utc)}</td>
              <td style={{ padding: '6px 8px' }} className="mono">{o.lead_orbits} orb ({o.lead_hours.toFixed(1)} h)</td>
              <td style={{ padding: '6px 8px' }}>{o.direction}</td>
              <td style={{ padding: '6px 8px', fontWeight: 700 }} className="mono">{cms(o.dv_ms)}</td>
              <td style={{ padding: '6px 8px' }} className="mono">{(o.fuel_kg * 1000).toFixed(1)} g</td>
              <td style={{ padding: '6px 8px' }} className="mono">{o.altitude_change_m.toFixed(0)} m</td>
              <td style={{ padding: '6px 8px' }} className="mono">{o.new_miss_km.toFixed(2)} km</td>
              <td style={{ padding: '6px 8px', color: tierOf(o.new_level).color }} className="mono">{formatPc(o.new_log_pc)}</td>
              <td style={{ padding: '6px 8px' }}>{o.conflict_checked ? (o.conflicts.length ? `${o.conflicts.length} high-risk` : 'none') : 'not checked'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LivePlan({ eventKey }) {
  const [selected, setSelected] = useState(0);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);
  const { data: plan, error, reload } = useApi(`/maneuver/plan/${encodeURIComponent(eventKey)}`);
  const { data: history, reload: reloadHistory } = useApi('/maneuver/decisions');
  const pending = plan && (plan.status === 'queued' || plan.status === 'computing');
  useEffect(() => {
    if (!pending) return undefined;
    const id = setInterval(reload, 3000);   // the planner runs in the background — poll until ready
    return () => clearInterval(id);
  }, [pending, reload]);

  if (error) return <ApiErrorBox error={error} what="manoeuvre plan" />;
  if (!plan) return <Loading>Loading plan…</Loading>;
  const c = plan.conjunction;
  const decide = async (decision) => {
    setBusy(true);
    setActionError(null);
    try {
      await api('/maneuver/decision', { method: 'POST', body: { key: eventKey, decision, option_index: plan.options?.length ? selected : null, note } });
      reload();
      reloadHistory();
    } catch (e) {
      setActionError(e);
    } finally {
      setBusy(false);
    }
  };

  const header = (
    <div className="glass-panel" style={{ padding: '12px 18px', marginBottom: 18, borderLeft: `4px solid ${tierOf(c.risk_level, c.status).color}` }}>
      <div style={{ fontSize: 14, fontWeight: 800 }}>{c.primary_name} vs {c.secondary_name} <span style={{ fontWeight: 400, color: '#94a3b8' }}>({c.secondary_type})</span></div>
      <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }} className="mono">
        {c.status} · {c.risk_level} · TCA {formatUtc(c.tca_utc)} · miss {formatDistance(c.miss_distance_m)} · Pc {formatPc(c.log_pc)} · {c.relative_velocity_km_s.toFixed(1)} km/s
      </div>
    </div>
  );
  if (pending) {
    return (
      <>
        {header}
        <Loading>{plan.status === 'queued' ? `Queued for the manoeuvre planner (${plan.queue_position} waiting)…` : 'Searching burns (6 directions × 5 lead times), verifying with full J2 propagation and screening the new path against the catalogue…'}</Loading>
      </>
    );
  }
  if (plan.status === 'error') return <>{header}<Notice tone="error">Planning failed: {plan.error}</Notice></>;

  const options = plan.options || [];
  const opt = options[selected];
  const curve = plan.tradeoff_curve || [];
  const target = plan.target;
  const optionPoint = curve.find((p) => p.is_option);
  return (
    <>
      {header}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 20, marginBottom: 20 }}>
        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>ΔV vs residual collision risk</h3>
              <p style={{ fontSize: 11, color: '#94a3b8', margin: '2px 0 0' }}>
                Recommended mover, burn time and direction; linear J2 burn model (validated to &lt; 2% against full propagation)
              </p>
            </div>
            <Badge color="#fb923c" bg="rgba(249, 115, 22, 0.2)" border="rgba(249, 115, 22, 0.4)">RECOMMENDED BURN HIGHLIGHTED</Badge>
          </div>
          {curve.length ? (
            <LineChart xLabel="ΔV (cm/s)" yLabel="log₁₀ Pc at closest approach" height={260} yMin={Math.max(-30, Math.min(...curve.map((p) => p.log_pc)))}
              series={[{ name: 'Residual risk', color: '#38bdf8', points: curve.map((p) => ({ x: p.dv_ms * 100, y: p.log_pc, highlight: p.is_option, label: `${cms(p.dv_ms)} → Pc ${formatPc(p.log_pc)}, miss ${p.miss_km.toFixed(2)} km` })) }]}
              hLines={[{ y: -4.5, color: '#dc2626', label: 'HIGH (−4.5)' }, { y: target.log_pc, color: '#10b981', label: `target (${target.log_pc})` }]}
              formatX={(v) => v.toFixed(1)} formatY={(v) => v.toFixed(0)} />
          ) : <Notice tone="warn">No burn met the target, so there is no trade-off curve.</Notice>}
          {optionPoint && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 12 }}>
              <Metric label="Recommended ΔV" value={cms(optionPoint.dv_ms)} sub={`${(optionPoint.fuel_kg * 1000).toFixed(1)} g propellant`} color="#38bdf8" />
              <Metric label="New miss distance" value={`${optionPoint.miss_km.toFixed(2)} km`} sub={`was ${formatDistance(c.miss_distance_m)}`} color="#10b981" />
              <Metric label="Risk after the burn" value={formatPc(optionPoint.log_pc)} sub={`was ${formatPc(c.log_pc)}`} color="#fb923c" />
            </div>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="glass-panel" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <Sparkles size={18} color="#f97316" />
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Suggestion</h3>
            </div>
            <div style={{ fontSize: 13, color: '#f8fafc', marginBottom: 10 }}>{plan.summary}</div>
            {plan.notes?.map((n, i) => <div key={i} style={{ fontSize: 11, color: '#94a3b8', marginBottom: 6 }}>ℹ️ {n}</div>)}
            {opt && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
                <Metric label="Selected burn" value={`${opt.direction} ${cms(opt.dv_ms)}`} sub={formatUtc(opt.burn_time_utc)} />
                <Metric label="Burn duration" value={`${opt.burn_duration_s.toFixed(1)} s`} sub={`${plan.spacecraft.thrust_n} N thruster`} />
                <Metric label="Propellant" value={`${(opt.fuel_kg * 1000).toFixed(1)} g`} sub={`${plan.spacecraft.mass_kg} kg, Isp ${plan.spacecraft.isp_s} s`} />
                <Metric label="Verified result" value={`${opt.new_miss_km.toFixed(2)} km`} sub={`Pc ${formatPc(opt.new_log_pc)} (${opt.verified ? 'full J2 check' : 'linear model'})`} />
              </div>
            )}
          </div>
          <div className="glass-panel" style={{ padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <Crosshair size={16} color="#38bdf8" />
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>Operator decision</h3>
            </div>
            {plan.decision && (
              <div style={{ marginBottom: 10 }}>
                <Notice tone={plan.decision.decision === 'ACCEPTED' ? 'ok' : 'warn'}>
                  {plan.decision.decision} at {plan.decision.time}
                  {plan.decision.option ? ` — ${plan.decision.option.direction} ${cms(plan.decision.option.dv_ms)}` : ''}
                  {plan.decision.note ? ` · “${plan.decision.note}”` : ''}
                </Notice>
              </div>
            )}
            <input placeholder="Operator note (optional)" value={note} onChange={(e) => setNote(e.target.value)} style={{ ...inputStyle, width: '100%', marginBottom: 10 }} />
            <div style={{ display: 'flex', gap: 8 }}>
              <button disabled={busy || !opt} onClick={() => decide('ACCEPTED')} style={{ ...buttonStyle('ok'), flex: 1 }}><CheckCircle2 size={12} style={{ verticalAlign: -2 }} /> Accept selected burn</button>
              <button disabled={busy} onClick={() => decide('DECLINED')} style={{ ...buttonStyle('danger'), flex: 1 }}><XCircle size={12} style={{ verticalAlign: -2 }} /> Decline</button>
            </div>
            <ApiErrorBox error={actionError} what="decision" />
            <div style={{ fontSize: 10, color: '#64748b', marginTop: 8 }}>Logged to logs/manoeuvre_decisions.jsonl (shared with the Streamlit dashboard). Accepted burns mark the conjunction MITIGATED.</div>
          </div>
        </div>
      </div>
      {options.length > 0 && (
        <div className="glass-panel" style={{ padding: 18, marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 10px' }}>Options (click to select)</h3>
          <OptionsTable options={options} selected={selected} setSelected={setSelected} />
          {opt?.conflicts?.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <Notice tone="warn">This burn would create new high-risk approaches: {opt.conflicts.map((x) => `${x.object_name} (${x.level}, ${x.miss_km.toFixed(2)} km)`).join(', ')}</Notice>
            </div>
          )}
        </div>
      )}
      {history?.length > 0 && (
        <div className="glass-panel" style={{ padding: 18 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 10px' }}>Decision log</h3>
          {history.slice(0, 8).map((h, i) => (
            <div key={i} style={{ fontSize: 11, color: '#cbd5e1', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }} className="mono">
              {h.time} · {h.decision} · {h.primary} vs {h.secondary}{h.option ? ` · ${h.option.mover_name} ${h.option.direction} ${cms(h.option.dv_ms)}` : ''}{h.note ? ` · ${h.note}` : ''}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

const DIRECTION_COLORS = { prograde: '#38bdf8', retrograde: '#0ea5e9', 'radial-out': '#a855f7', 'radial-in': '#c084fc', normal: '#10b981', 'anti-normal': '#34d399' };

function EsaEstimate({ eventId }) {
  const [mass, setMass] = useState(500);
  const [isp, setIsp] = useState(220);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      api('/maneuver/optimize', { method: 'POST', signal: ctrl.signal, body: { event_id: eventId, satellite_mass_kg: mass, isp_s: isp } })
        .then((r) => { setResult(r); setError(null); })
        .catch((e) => { if (e.name !== 'AbortError') setError(e); });
    }, 300);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [eventId, mass, isp]);
  if (error) return <ApiErrorBox error={error} what="manoeuvre estimate" />;
  if (!result) return <Loading>Estimating burns for ESA event {eventId}…</Loading>;
  const best = result.best;
  // The analytic model treats opposite directions alike, so merge curves that are identical
  const merged = [];
  Object.entries(result.curves).forEach(([dir, pts]) => {
    const sig = pts.map((p) => p.residual_log_pc.toFixed(6)).join(',');
    const same = merged.find((m) => m.sig === sig);
    if (same) same.dirs.push(dir);
    else merged.push({ sig, dirs: [dir], pts });
  });
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 20 }}>
      <div className="glass-panel" style={{ padding: 20 }}>
        <h3 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 4px' }}>Residual risk by burn direction</h3>
        <p style={{ fontSize: 11, color: '#94a3b8', margin: '0 0 10px' }}>{result.method}</p>
        <LineChart xLabel="ΔV (m/s, log scale)" yLabel="log₁₀ Pc" height={260}
          series={merged.map(({ dirs, pts }) => ({ name: dirs.join(' / '), color: DIRECTION_COLORS[dirs[0]] || '#94a3b8',
            points: pts.map((p) => ({ x: Math.log10(p.dv_ms), y: p.residual_log_pc, highlight: best && p.dv_ms === best.dv_ms && dirs.includes(best.direction), label: `${dirs.join(' / ')} ${p.dv_ms} m/s → ${formatPc(p.residual_log_pc)}` })) }))}
          hLines={[{ y: result.target_log_pc, color: '#10b981', label: `target (${result.target_log_pc})` }]}
          formatX={(v) => (10 ** v).toPrecision(1)} formatY={(v) => v.toFixed(0)} />
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <Fuel size={16} color="#f97316" />
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Cheapest burn meeting the target</h3>
          </div>
          {best ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <Metric label="Burn" value={`${best.direction} ${best.dv_ms} m/s`} color="#38bdf8" />
              <Metric label="Propellant" value={`${(best.fuel_kg * 1000).toFixed(1)} g`} />
              <Metric label="New miss" value={`${best.new_miss_km.toFixed(2)} km`} sub={`was ${result.original_miss_km.toFixed(2)} km`} />
              <Metric label="Residual Pc" value={formatPc(best.residual_log_pc)} sub={best.meets_target ? 'meets the target' : 'best available — misses the target'} />
            </div>
          ) : <Notice>No burn evaluated.</Notice>}
          {result.no_manoeuvre_justified && <div style={{ marginTop: 10 }}><Notice tone="ok">Risk is already below 1E-7 — no manoeuvre is justified.</Notice></div>}
          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 10 }}>Original risk {formatPc(result.original_log_pc)}, {result.time_to_tca_hours.toFixed(1)} h before closest approach.</div>
        </div>
        <div className="glass-panel" style={{ padding: 18 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 10px' }}>Spacecraft</h3>
          <div style={{ display: 'flex', gap: 10 }}>
            <label style={{ fontSize: 11, color: '#94a3b8' }}>Mass (kg)<br /><input type="number" min="10" value={mass} onChange={(e) => setMass(Number(e.target.value) || 500)} style={{ ...inputStyle, width: 100 }} /></label>
            <label style={{ fontSize: 11, color: '#94a3b8' }}>Isp (s)<br /><input type="number" min="50" value={isp} onChange={(e) => setIsp(Number(e.target.value) || 220)} style={{ ...inputStyle, width: 100 }} /></label>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ManeuverView({ event }) {
  const [picked, setPicked] = useState(null);
  const { data: status } = useApi('/status');
  const { data: danger } = useApi(status?.phase === 'ready' ? '/conjunctions/screen?status=DANGER&status=MITIGATED&limit=50' : null);
  const options = danger?.conjunctions || [];
  const current = picked || event || (options[0] ? liveEvent(options[0]) : null);

  return (
    <div style={PAGE_STYLE}>
      <PageHeader icon={Rocket} iconColor="#f97316" title="Collision Avoidance Maneuver (CAM) Optimization"
        subtitle="Smallest burn that brings the risk below 1E-7 and the miss above 2 km, verified with full propagation and screened against the whole catalogue">
        {options.length > 0 && (
          <select value={current?.source === 'live' ? current.key : ''} onChange={(e) => setPicked(liveEvent(options.find((c) => c.key === e.target.value)))} style={{ ...inputStyle, maxWidth: 420 }}>
            {current?.source !== 'live' && <option value="">Choose a live high-risk conjunction…</option>}
            {current?.source === 'live' && !options.some((c) => c.key === current.key) && <option value={current.key}>{current.primary_name} vs {current.secondary_name}</option>}
            {options.map((c) => <option key={c.key} value={c.key}>{c.status} · {c.primary_name} vs {c.secondary_name} · Pc {formatPc(c.log_pc)}</option>)}
          </select>
        )}
      </PageHeader>
      {current?.source === 'live' && <LivePlan key={current.key} eventKey={current.key} />}
      {current?.source === 'esa' && <EsaEstimate key={current.event_id} eventId={current.event_id} />}
      {!current && (
        <Notice tone="ok">
          {status?.phase === 'ready'
            ? 'No HIGH or CRITICAL conjunctions in the screening window — no manoeuvre needed. Inject a test threat on the 72h Screening page to see the planner work.'
            : status ? `Live screening: ${status.message}` : 'Backend unreachable — start it with: cd backend && python run.py'}
        </Notice>
      )}
    </div>
  );
}
