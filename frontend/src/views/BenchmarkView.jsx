import React, { useState } from 'react';
import { useApi } from '../api';
import { formatPc, tierOf } from '../lib/format';
import { ApiErrorBox, Badge, LineChart, Loading, Metric, PageHeader } from '../components/ui';
import { PAGE_STYLE, buttonStyle } from '../lib/styles';
import { ArrowRight, Award, CheckCircle2, CircleSlash, History, XCircle } from 'lucide-react';

const pct = (x, d = 1) => (x === null || x === undefined ? '—' : `${(x * 100).toFixed(d)}%`);
const CATEGORY_COLORS = { HIGH_RISK: '#dc2626', FALSE_ALARM: '#10b981', LATE_RISE: '#f97316', SPACE_WEATHER: '#a855f7', NEGLIGIBLE: '#38bdf8' };

function Kpi({ label, value, sub, color }) {
  return (
    <div className="glass-panel" style={{ padding: 16, borderTop: `4px solid ${color}` }}>
      <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color }} className="mono">{value}</div>
      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function Replay({ events, onOpenEvent }) {
  const [selected, setSelected] = useState(0);
  const active = events[selected];
  const { data, error, loading } = useApi(active ? `/predict/esa-replay/${active.event_id}` : null);
  return (
    <div className="glass-panel" style={{ padding: 22, marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <History size={20} color="#38bdf8" />
          <h3 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Real ESA Event Replay</h3>
        </div>
        <span style={{ fontSize: 11, color: '#94a3b8' }}>{active?.source}</span>
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        {events.map((e, i) => {
          const color = CATEGORY_COLORS[e.category] || '#94a3b8';
          return (
            <button key={e.event_id} onClick={() => setSelected(i)}
              style={{ flex: 1, minWidth: 170, padding: '10px 14px', borderRadius: 8, textAlign: 'left', cursor: 'pointer', color: '#f8fafc',
                background: selected === i ? `${color}33` : 'rgba(255,255,255,0.04)', border: selected === i ? `1px solid ${color}` : '1px solid rgba(255,255,255,0.08)' }}>
              <div style={{ fontSize: 10, color, fontWeight: 700 }}>{e.category.replace('_', ' ')} · EVENT {e.event_id}</div>
              <div style={{ fontSize: 13, fontWeight: 700, marginTop: 2 }}>{e.title}</div>
            </button>
          );
        })}
      </div>
      {active && (
        <div style={{ background: 'rgba(0,0,0,0.3)', padding: 18, borderRadius: 10, border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12, gap: 12 }}>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800 }}>{active.title}</div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>{active.description}</div>
            </div>
            <Badge color="#ffffff" bg={tierOf(active.final_level).color} border={tierOf(active.final_level).color}>FINAL: {active.final_level}</Badge>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, margin: '14px 0' }}>
            <Metric label="CDMs in the event" value={active.n_cdms} sub={`mission ${active.mission_id} vs ${active.other_object_type}`} />
            <Metric label={`ESA risk ${active.decision_tca_days.toFixed(1)} d out`} value={formatPc(active.decision_risk)} sub={`model: ${formatPc(active.decision_pred)}`} />
            <Metric label={`ESA risk ${active.final_tca_days.toFixed(2)} d out (final)`} value={formatPc(active.final_risk)} sub={`model: ${formatPc(active.final_pred)}`} />
            <Metric label="Max geomagnetic Ap" value={active.max_ap ?? '—'} sub={`F10.7 ${active.f10?.toFixed(0) ?? '—'}`} />
          </div>
          {loading && <Loading>Loading the CDM sequence…</Loading>}
          <ApiErrorBox error={error} what="replay" />
          {data && (
            <LineChart xReversed xLabel="Days before closest approach" yLabel="log₁₀ Pc" height={230}
              series={[{ name: 'ESA risk', color: '#f8fafc', points: data.series.map((p) => ({ x: p.time_to_tca_days, y: Math.max(p.esa_risk, -30) })) },
                { name: 'CDM model', color: '#38bdf8', dashed: true, points: data.series.map((p) => ({ x: p.time_to_tca_days, y: Math.max(p.model_risk, -30) })) }]}
              hLines={[{ y: -4.5, color: '#f97316', label: 'alert line (−4.5)' }]} vLines={[{ x: 2, color: 'rgba(255,255,255,0.25)' }]}
              formatX={(v) => v.toFixed(1)} formatY={(v) => v.toFixed(0)} />
          )}
          <button onClick={() => onOpenEvent({ source: 'esa', event_id: active.event_id })} style={{ ...buttonStyle('primary'), marginTop: 10, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            Explain this event with SHAP <ArrowRight size={13} />
          </button>
        </div>
      )}
    </div>
  );
}

export default function BenchmarkView({ onOpenEvent = () => {} }) {
  const { data: m, error, loading } = useApi('/benchmark/metrics');
  const { data: events, error: eventsError } = useApi('/predict/esa-events');

  return (
    <div style={PAGE_STYLE}>
      <PageHeader icon={Award} iconColor="#facc15" title="ESA Benchmark Validation & Replay Mode"
        subtitle={m ? `${m.model_name} · ${m.test_dataset} · alert = log₁₀ Pc ≥ ${m.alert_threshold_log10_pc}` : 'Saved evaluation of the trained models on the ESA Collision Avoidance Challenge dataset'}>
        <div className="glass-panel" style={{ padding: '8px 14px', fontSize: 11, color: '#94a3b8' }}>
          Dataset: <strong>ESA Spacecraft Collision Avoidance Challenge</strong>
        </div>
      </PageHeader>
      {loading && <Loading>Loading evaluation results…</Loading>}
      <ApiErrorBox error={error} what="benchmark metrics" />
      {m && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
            <Kpi label="F2 SCORE (ALERTS, TEST SET)" value={m.kpis.alert_f2?.toFixed(3) ?? '—'} color="#10b981" sub="recall-weighted alert score (the Kelvins challenge metric)" />
            <Kpi label="HIGH-RISK RECALL" value={pct(m.kpis.alert_recall)} color="#38bdf8" sub="share of ESA high-risk CDMs the model also flags" />
            <Kpi label="HIGH-RISK PRECISION" value={pct(m.kpis.alert_precision)} color="#a855f7" sub="share of the model's alerts that ESA rates high-risk" />
            <Kpi label="TEST R² (log₁₀ Pc)" value={m.kpis.test_r2?.toFixed(4) ?? '—'} color="#f97316" sub={`mean abs error ${m.kpis.test_mae?.toFixed(3)} log₁₀ units`} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 20, marginBottom: 20 }}>
            <div className="glass-panel" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 12px' }}>CDM risk model — train / validation / test</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ color: '#94a3b8', textAlign: 'left' }}>
                    {['Split', 'Rows', 'R²', 'MAE', 'Precision', 'Recall', 'F2', 'Alerts (ESA / model)'].map((h) => <th key={h} style={{ padding: '6px 8px' }}>{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {m.splits.map((s) => (
                    <tr key={s.split} style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }} className="mono">
                      <td style={{ padding: '6px 8px', fontFamily: 'Inter', fontWeight: 700 }}>{s.split}</td>
                      <td style={{ padding: '6px 8px' }}>{s.rows?.toLocaleString()}</td>
                      <td style={{ padding: '6px 8px' }}>{s.r2?.toFixed(4)}</td>
                      <td style={{ padding: '6px 8px' }}>{s.mae?.toFixed(3)}</td>
                      <td style={{ padding: '6px 8px' }}>{s.alert_precision?.toFixed(3)}</td>
                      <td style={{ padding: '6px 8px' }}>{s.alert_recall?.toFixed(3)}</td>
                      <td style={{ padding: '6px 8px' }}>{s.alert_f2?.toFixed(3)}</td>
                      <td style={{ padding: '6px 8px' }}>{s.alerts_true} / {s.alerts_predicted}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 10 }}>
                {m.training.trees} trees, {m.training.features} features, trained on {m.training.device} in {m.training.training_time_s?.toFixed(1)} s. Validation rows are split by event. {m.conclusion}
              </div>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: '18px 0 10px' }}>Live uncertainty model vs baseline</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                {m.uncertainty_model.errors.map((u) => (
                  <Metric key={u.quantity} label={u.quantity} value={`${u.ml_error_factor.toFixed(2)}×`} sub={`baseline ${u.baseline_error_factor.toFixed(2)}× (typical error factor)`} color="#10b981" />
                ))}
              </div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 8 }}>
                Trained on {m.uncertainty_model.rows_trained?.toLocaleString()} object-states from ESA CDMs, tested on {m.uncertainty_model.rows_tested?.toLocaleString()}. Baseline = per-object-type median.
              </div>
            </div>

            <div className="glass-panel" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 4px' }}>Validation report</h3>
              {m.validation ? (
                <>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 10 }}>
                    {m.validation.passed} passed · {m.validation.failed} failed · {m.validation.skipped} skipped · {m.validation.generated_at}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 420, overflowY: 'auto' }}>
                    {m.validation.checks.map((c) => (
                      <div key={c.name} style={{ background: 'rgba(0,0,0,0.25)', padding: '8px 10px', borderRadius: 6 }} title={c.what}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700 }}>
                          {c.passed === true ? <CheckCircle2 size={13} color="#10b981" /> : c.passed === false ? <XCircle size={13} color="#dc2626" /> : <CircleSlash size={13} color="#64748b" />}
                          {c.name}
                        </div>
                        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{c.result}</div>
                      </div>
                    ))}
                  </div>
                </>
              ) : <div style={{ fontSize: 12, color: '#94a3b8' }}>No report yet — run <code>python validate.py</code>.</div>}
            </div>
          </div>

          <div className="glass-panel" style={{ padding: 20, marginBottom: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 12px' }}>Top features (XGBoost gain)</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 24px' }}>
              {m.feature_importance.map((f) => (
                <div key={f.feature} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
                  <span style={{ width: 190, color: '#cbd5e1' }} className="mono">{f.feature}</span>
                  <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.06)', borderRadius: 3 }}>
                    <div style={{ width: `${(f.share / m.feature_importance[0].share) * 100}%`, height: '100%', background: '#38bdf8', borderRadius: 3 }} />
                  </div>
                  <span style={{ width: 44, textAlign: 'right', color: '#94a3b8' }} className="mono">{pct(f.share)}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
      <ApiErrorBox error={eventsError} what="ESA events" />
      {events?.length > 0 && <Replay events={events} onOpenEvent={onOpenEvent} />}
    </div>
  );
}
