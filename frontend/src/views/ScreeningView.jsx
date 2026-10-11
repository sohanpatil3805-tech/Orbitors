import React, { useState } from 'react';
import { RISK_TIERS } from '../data/satellites';
import { api, useApi } from '../api';
import { ACTION_LABEL, formatDistance, formatPc, formatUtc, liveEvent, tierOf } from '../lib/format';
import { ApiErrorBox, Badge, Loading, Notice, PageHeader, Stat } from '../components/ui';
import { PAGE_STYLE, buttonStyle, inputStyle } from '../lib/styles';
import { Radar, Search, FlaskConical, RefreshCw } from 'lucide-react';

const STATUSES = ['ALL', 'DANGER', 'REVIEW', 'MITIGATED', 'SAFE'];

// Inject / clear a simulated threat (POST /api/scenario) to exercise alert → plan → decision end to end
function ScenarioPanel({ satellites, scenario, onChanged }) {
  const [spec, setSpec] = useState({ primary_id: 25544, hours_to_tca: 18, miss_m: 25, crossing_deg: 70, kind: 'debris' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const send = async (enabled) => {
    setBusy(true);
    setError(null);
    try {
      await api('/scenario', { method: 'POST', body: { enabled, ...spec } });
      onChanged();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  const field = (label, key, props) => (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: 10, color: '#94a3b8' }}>
      {label}
      <input type="number" value={spec[key]} onChange={(e) => setSpec({ ...spec, [key]: Number(e.target.value) })}
        style={{ ...inputStyle, width: 90 }} {...props} />
    </label>
  );
  return (
    <div className="glass-panel" style={{ padding: '12px 18px', marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <FlaskConical size={16} color="#a855f7" />
        <span style={{ fontSize: 13, fontWeight: 700 }}>Test scenario</span>
        <span style={{ fontSize: 11, color: '#94a3b8' }}>
          Inject a simulated object on a known collision course — the satellite turns red, a burn is planned, and you know the right answer. Real data is not changed.
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 12, flexWrap: 'wrap' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: 10, color: '#94a3b8' }}>
          Satellite
          <select value={spec.primary_id} onChange={(e) => setSpec({ ...spec, primary_id: Number(e.target.value) })} style={inputStyle}>
            {(satellites || []).map((s) => <option key={s.norad_id} value={s.norad_id}>{s.name}</option>)}
          </select>
        </label>
        {field('Hours to TCA', 'hours_to_tca', { min: 3, max: 60, step: 1 })}
        {field('Miss (m)', 'miss_m', { min: 0, max: 2000, step: 5 })}
        {field('Crossing (°)', 'crossing_deg', { min: 10, max: 170, step: 5 })}
        <label style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: 10, color: '#94a3b8' }}>
          Threat
          <select value={spec.kind} onChange={(e) => setSpec({ ...spec, kind: e.target.value })} style={inputStyle}>
            <option value="debris">Debris (cannot move)</option>
            <option value="satellite">Working satellite (can move)</option>
          </select>
        </label>
        <button disabled={busy || !satellites?.length} onClick={() => send(true)} style={buttonStyle('primary')}>
          {scenario?.enabled ? 'Update threat' : 'Inject threat'}
        </button>
        {scenario?.enabled && <button disabled={busy} onClick={() => send(false)} style={buttonStyle()}>Clear</button>}
        {scenario?.enabled && (
          <Badge color="#c084fc" border="rgba(168,85,247,0.4)" bg="rgba(168,85,247,0.12)">
            ACTIVE: {scenario.threat.kind} → NORAD {scenario.threat.primary_id}, {scenario.threat.miss_m} m in {scenario.threat.hours_to_tca} h
          </Badge>
        )}
      </div>
      {error && <div style={{ marginTop: 8 }}><ApiErrorBox error={error} what="scenario" /></div>}
    </div>
  );
}

export default function ScreeningView({ onSelectSatelliteForAnalysis, onSelectSatelliteForManeuver }) {
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [satFilter, setSatFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const { data: status, reload: reloadStatus } = useApi('/status', { intervalMs: 10000 });
  const ready = status?.phase === 'ready';
  const version = status?.updated_at || '';
  const { data: screen, error, loading, reload } = useApi(ready ? `/conjunctions/screen?limit=1000&v=${version}` : null,
    { intervalMs: status?.refreshing ? 8000 : 30000 });
  const { data: satellites } = useApi(ready ? `/conjunctions/satellites?v=${version}` : null);
  const { data: scenario, reload: reloadScenario } = useApi('/scenario');

  const events = screen?.conjunctions || [];
  const filteredEvents = events.filter((ev) => {
    const term = searchTerm.toLowerCase();
    const matchesSearch = !term || ev.primary_name.toLowerCase().includes(term) || ev.secondary_name.toLowerCase().includes(term)
      || ev.key.toLowerCase().includes(term);
    const level = tierOf(ev.risk_level).key;
    return matchesSearch && (statusFilter === 'ALL' || ev.status === statusFilter)
      && (riskFilter === 'ALL' || level === riskFilter) && (!satFilter || String(ev.primary_norad_id) === satFilter);
  });
  const count = (fn) => events.filter(fn).length;

  return (
    <div style={PAGE_STYLE}>
      <PageHeader icon={Radar} title="72-Hour Conjunction Screening Telemetry"
        subtitle={ready
          ? `SGP4 screening of ${status.watchlist_size} watchlist satellites against ${status.objects_tracked.toLocaleString()} catalogued objects (${status.catalogue_source}) · screened ${formatUtc(status.screened_at)}`
          : 'SGP4 screening of the watchlist against the public orbit catalogue for the next 72 hours'}>
        <Stat label="Catalog Tracked" value={ready ? status.objects_tracked.toLocaleString() : '—'} />
        <Stat label="Critical (Pc ≥ 1E-3)" value={count((e) => e.risk_level === 'CRITICAL')} color="#dc2626" accent="#dc2626" />
        <Stat label="High (Pc ≥ 3.2E-5)" value={count((e) => e.risk_level === 'HIGH')} color="#f97316" accent="#f97316" />
        <Stat label="Close approaches < 10 km" value={events.length} />
        <button onClick={async () => { await api('/refresh', { method: 'POST' }); reloadStatus(); }} style={buttonStyle()} title="Fetch new orbit data now">
          <RefreshCw size={12} style={{ verticalAlign: -2 }} /> Refresh
        </button>
      </PageHeader>

      {!ready && (
        <div style={{ marginBottom: 16 }}>
          {status?.phase === 'error'
            ? <Notice tone="error"><strong>Live screening failed:</strong> {status.error}</Notice>
            : status ? <Loading>{status.message}</Loading> : <ApiErrorBox error={{ message: 'Backend unreachable — start it with: cd backend && python run.py' }} what="screening" />}
        </div>
      )}
      {ready && status.error && <div style={{ marginBottom: 16 }}><Notice tone="warn">Latest refresh failed ({status.error}); showing the previous result.</Notice></div>}

      <ScenarioPanel satellites={satellites} scenario={scenario} onChanged={() => { reloadScenario(); reloadStatus(); setTimeout(reload, 1500); }} />

      {/* Filter and Search Bar */}
      <div className="glass-panel" style={{ padding: '12px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 240, maxWidth: 380 }}>
          <Search size={16} color="#64748b" />
          <input type="text" placeholder="Search by satellite, object or event key..." value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ background: 'transparent', border: 'none', outline: 'none', color: '#f8fafc', fontSize: 13, width: '100%' }} />
        </div>
        <select value={satFilter} onChange={(e) => setSatFilter(e.target.value)} style={inputStyle}>
          <option value="">All watchlist satellites</option>
          {(satellites || []).map((s) => <option key={s.norad_id} value={s.norad_id}>{s.name} ({s.conjunctions})</option>)}
        </select>
        <div style={{ display: 'flex', gap: 6 }}>
          {STATUSES.map((st) => (
            <button key={st} onClick={() => setStatusFilter(st)} style={buttonStyle('default', statusFilter === st)}>{st}</button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((risk) => {
            const isSelected = riskFilter === risk;
            const tier = RISK_TIERS[risk];
            return (
              <button key={risk} onClick={() => setRiskFilter(risk)}
                style={{ background: isSelected ? (tier ? tier.badgeBg : 'rgba(255, 255, 255, 0.15)') : 'rgba(255, 255, 255, 0.04)',
                  border: isSelected ? `1px solid ${tier ? tier.border : 'rgba(255, 255, 255, 0.3)'}` : '1px solid rgba(255, 255, 255, 0.08)',
                  color: isSelected ? '#ffffff' : '#94a3b8', padding: '5px 12px', borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: 'pointer' }}>
                {risk}
              </button>
            );
          })}
        </div>
      </div>

      <ApiErrorBox error={error} what="conjunctions" />

      {/* Conjunctions Telemetry Table */}
      <div className="glass-panel" style={{ overflow: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'rgba(0,0,0,0.3)', borderBottom: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8' }}>
              {['EVENT KEY', 'PRIMARY ASSET', 'SECONDARY OBJECT', 'TCA (CLOSEST APPROACH)', 'MISS DISTANCE', 'CLOSING SPEED', 'COLLISION PROB. (Pc)', 'STATUS / DECISION'].map((h) => (
                <th key={h} style={{ padding: '12px 16px' }}>{h}</th>
              ))}
              <th style={{ padding: '12px 16px', textAlign: 'right' }}>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.map((ev) => {
              const tier = tierOf(ev.risk_level, ev.status);
              const hot = ev.status === 'DANGER';
              return (
                <tr key={ev.key} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: hot ? 'rgba(220, 38, 38, 0.04)' : 'transparent' }}>
                  <td style={{ padding: '12px 16px', fontWeight: 600, color: '#f8fafc', fontSize: 11 }} className="mono">{ev.key}</td>
                  <td style={{ padding: '12px 16px', fontWeight: 700, color: '#f8fafc' }}>{ev.primary_name}</td>
                  <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>
                    <div>{ev.secondary_name}</div>
                    <div style={{ fontSize: 10, color: '#64748b' }}>
                      {ev.secondary_type} · NORAD {ev.secondary_norad_id}{ev.simulated ? ' · simulated test threat' : ''}
                    </div>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#94a3b8' }} className="mono">
                    <div>{formatUtc(ev.tca_utc)}</div>
                    <div style={{ fontSize: 10, color: '#64748b' }}>T-{ev.time_to_tca_hours.toFixed(1)}h</div>
                  </td>
                  <td style={{ padding: '12px 16px', fontWeight: 700, color: ev.miss_distance_m < 1000 ? '#f87171' : '#f8fafc' }} className="mono">
                    {formatDistance(ev.miss_distance_m)}
                  </td>
                  <td style={{ padding: '12px 16px', color: '#94a3b8' }} className="mono">{ev.relative_velocity_km_s.toFixed(2)} km/s</td>
                  <td style={{ padding: '12px 16px', fontWeight: 700, color: tier.color }} className="mono">
                    <div>{formatPc(ev.log_pc)}</div>
                    <div style={{ fontSize: 9, color: '#64748b', fontWeight: 400 }}>{ev.pc_source}</div>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    <Badge color={tier.color} bg={tier.badgeBg} border={tier.border}>{ev.status} · {ACTION_LABEL[ev.recommended_action]}</Badge>
                  </td>
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
                      <button onClick={() => onSelectSatelliteForAnalysis(liveEvent(ev))} style={buttonStyle()}>Explain (XAI)</button>
                      {(ev.status === 'DANGER' || ev.status === 'MITIGATED' || ev.status === 'REVIEW') && (
                        <button onClick={() => onSelectSatelliteForManeuver(liveEvent(ev))} style={buttonStyle(ev.status === 'DANGER' ? 'danger' : 'default')}>
                          {ev.status === 'MITIGATED' ? 'View burn' : 'Optimize Δv'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {ready && !loading && !filteredEvents.length && (
          <div style={{ padding: 18, color: '#94a3b8', fontSize: 12 }}>
            {events.length ? 'No close approaches match these filters.' : 'No close approaches under 10 km in the screening window.'}
          </div>
        )}
      </div>
    </div>
  );
}
