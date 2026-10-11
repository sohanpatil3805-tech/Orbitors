import React from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';



export function PageHeader({ icon: Icon, iconColor = '#38bdf8', title, subtitle, children }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 20, flexWrap: 'wrap' }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Icon size={24} color={iconColor} />
          <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, color: '#f8fafc' }}>{title}</h1>
        </div>
        {subtitle && <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>{subtitle}</p>}
      </div>
      {children && <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>{children}</div>}
    </div>
  );
}

export function Stat({ label, value, sub, color = '#f8fafc', accent }) {
  return (
    <div className="glass-panel" style={{ padding: '10px 16px', textAlign: 'center', borderLeft: accent ? `3px solid ${accent}` : undefined }}>
      <div style={{ fontSize: 11, color: accent || '#94a3b8' }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800, color }} className="mono">{value}</div>
      {sub && <div style={{ fontSize: 10, color: '#64748b' }}>{sub}</div>}
    </div>
  );
}

export function Metric({ label, value, sub, color = '#f8fafc' }) {
  return (
    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: '#64748b' }}>{label}</div>
      <div style={{ fontSize: 14, fontWeight: 700, color, marginTop: 1 }} className="mono">{value}</div>
      {sub && <div style={{ fontSize: 10, color: '#64748b', marginTop: 1 }}>{sub}</div>}
    </div>
  );
}

export function Badge({ children, color, bg, border }) {
  return (
    <span style={{ padding: '3px 8px', borderRadius: 4, fontSize: 10, fontWeight: 700, background: bg || 'rgba(255,255,255,0.06)',
      color: color || '#cbd5e1', border: `1px solid ${border || 'rgba(255,255,255,0.15)'}`, whiteSpace: 'nowrap' }}>
      {children}
    </span>
  );
}

export function Notice({ tone = 'info', children }) {
  const tones = {
    info: ['rgba(56, 189, 248, 0.08)', 'rgba(56, 189, 248, 0.25)', '#7dd3fc'],
    warn: ['rgba(234, 179, 8, 0.08)', 'rgba(234, 179, 8, 0.3)', '#fde047'],
    error: ['rgba(220, 38, 38, 0.1)', 'rgba(220, 38, 38, 0.35)', '#fca5a5'],
    ok: ['rgba(16, 185, 129, 0.1)', 'rgba(16, 185, 129, 0.3)', '#6ee7b7'],
  }[tone];
  return (
    <div style={{ background: tones[0], border: `1px solid ${tones[1]}`, color: tones[2], padding: '10px 14px', borderRadius: 8, fontSize: 12, lineHeight: 1.5 }}>
      {children}
    </div>
  );
}

export function Loading({ children = 'Loading…' }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#94a3b8', fontSize: 13, padding: 16 }}>
      <Loader2 size={16} className="radar-sweep" />
      <span>{children}</span>
    </div>
  );
}

export function ApiErrorBox({ error, what = 'data' }) {
  if (!error) return null;
  const notReady = error.status === 503;
  return (
    <Notice tone={notReady ? 'warn' : 'error'}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, marginBottom: 2 }}>
        <AlertTriangle size={14} />
        {notReady ? `Live ${what} not ready yet` : `Could not load ${what}`}
      </div>
      {error.message}
    </Notice>
  );
}



/** Simple SVG line chart. series: [{ name, color, points: [{x, y}], dashed }] */
export function LineChart({ series, xLabel, yLabel, height = 220, xReversed = false, hLines = [], vLines = [], yMin, yMax, formatX = (v) => v.toFixed(1), formatY = (v) => v.toFixed(0) }) {
  const W = 520, H = height, L = 48, R = 12, T = 26, B = 34;   // T leaves a row for the legend
  const all = series.flatMap((s) => s.points).filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
  if (!all.length) return <div style={{ color: '#64748b', fontSize: 12 }}>No data</div>;
  let x0 = Math.min(...all.map((p) => p.x)), x1 = Math.max(...all.map((p) => p.x));
  let y0 = yMin ?? Math.min(...all.map((p) => p.y), ...hLines.map((h) => h.y)), y1 = yMax ?? Math.max(...all.map((p) => p.y), ...hLines.map((h) => h.y));
  if (x0 === x1) { x0 -= 1; x1 += 1; }
  if (y0 === y1) { y0 -= 1; y1 += 1; }
  const sx = (x) => L + ((xReversed ? x1 - x : x - x0) / (x1 - x0)) * (W - L - R);
  const sy = (y) => T + ((y1 - Math.min(Math.max(y, y0), y1)) / (y1 - y0)) * (H - T - B);
  const ticks = (a, b, n) => Array.from({ length: n + 1 }, (_, i) => a + ((b - a) * i) / n);
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: 'block' }}>
      {ticks(y0, y1, 4).map((y, i) => (
        <g key={`y${i}`}>
          <line x1={L} x2={W - R} y1={sy(y)} y2={sy(y)} stroke="rgba(255,255,255,0.06)" />
          <text x={L - 6} y={sy(y) + 3} fill="#64748b" fontSize="9" textAnchor="end" fontFamily="JetBrains Mono">{formatY(y)}</text>
        </g>
      ))}
      {ticks(x0, x1, 5).map((x, i) => (
        <text key={`x${i}`} x={sx(x)} y={H - B + 13} fill="#64748b" fontSize="9" textAnchor="middle" fontFamily="JetBrains Mono">{formatX(x)}</text>
      ))}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke="rgba(255,255,255,0.15)" />
      <line x1={L} x2={L} y1={T} y2={H - B} stroke="rgba(255,255,255,0.15)" />
      {hLines.map((h, i) => (
        <g key={`h${i}`}>
          <line x1={L} x2={W - R} y1={sy(h.y)} y2={sy(h.y)} stroke={h.color} strokeDasharray="4 4" strokeWidth="1.2" />
          <text x={W - R - 4} y={sy(h.y) - 4} fill={h.color} fontSize="9" textAnchor="end" fontFamily="JetBrains Mono">{h.label}</text>
        </g>
      ))}
      {vLines.map((v, i) => (
        <line key={`v${i}`} x1={sx(v.x)} x2={sx(v.x)} y1={T} y2={H - B} stroke={v.color} strokeDasharray="3 3" strokeWidth="1" />
      ))}
      {series.map((s) => {
        const pts = s.points.filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));
        return (
          <g key={s.name}>
            <polyline fill="none" stroke={s.color} strokeWidth="2" strokeDasharray={s.dashed ? '5 4' : undefined}
              points={pts.map((p) => `${sx(p.x)},${sy(p.y)}`).join(' ')} />
            {pts.map((p, i) => (
              <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={p.highlight ? 6 : 2.6} fill={p.highlight ? '#f97316' : s.color}
                stroke={p.highlight ? '#ffffff' : 'none'} strokeWidth={p.highlight ? 2 : 0}>
                {p.label && <title>{p.label}</title>}
              </circle>
            ))}
          </g>
        );
      })}
      <text x={(L + W - R) / 2} y={H - 4} fill="#94a3b8" fontSize="10" textAnchor="middle">{xLabel}</text>
      <text x={12} y={(T + H - B) / 2} fill="#94a3b8" fontSize="10" textAnchor="middle" transform={`rotate(-90 12,${(T + H - B) / 2})`}>{yLabel}</text>
      <g>
        {series.map((s, i) => (
          <g key={`lg${s.name}`} transform={`translate(${L + i * Math.min(120, (W - L - R) / series.length)}, 4)`}>
            <line x1={0} x2={16} y1={4} y2={4} stroke={s.color} strokeWidth="2" strokeDasharray={s.dashed ? '5 4' : undefined} />
            <text x={20} y={7} fill="#cbd5e1" fontSize="9">{s.name}</text>
          </g>
        ))}
      </g>
    </svg>
  );
}
