import { RISK_TIERS } from '../data/satellites';

const STATUS_ORDER = { DANGER: 3, REVIEW: 2, MITIGATED: 1, SAFE: 0 };

/** Backend risk level (+ status) → frontend tier key. Accepted manoeuvres show as LOW (green). */
export function tierKey(level, status) {
  if (status === 'MITIGATED') return 'LOW';
  return { CRITICAL: 'CRITICAL', HIGH: 'HIGH', MEDIUM: 'MEDIUM' }[level] || 'LOW';
}

export const tierOf = (level, status) => RISK_TIERS[tierKey(level, status)];

/** log10 Pc → "2.84E-04" */
export function formatPc(logPc) {
  if (logPc === null || logPc === undefined || Number.isNaN(logPc)) return '—';
  if (logPc <= -29.9) return '< 1E-30';
  return Math.pow(10, logPc).toExponential(2).toUpperCase().replace(/E([+-])(\d)$/, 'E$10$2');
}

export function formatDistance(m) {
  if (m === null || m === undefined) return '—';
  return m < 1000 ? `${m.toFixed(0)} m` : `${(m / 1000).toFixed(2)} km`;
}

export function formatUtc(iso) {
  if (!iso) return '—';
  return new Date(iso).toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
}

export const formatNumber = (x, digits = 2) => (x === null || x === undefined ? '—' : Number(x).toFixed(digits));

export const ACTION_LABEL = {
  MANEUVER_RECOMMENDED: 'MANEUVER RECOMMENDED',
  MONITOR: 'MONITOR',
  HOLD: 'HOLD',
  MANEUVER_ACCEPTED: 'MANEUVER ACCEPTED',
};

/** A live conjunction from the API, tagged so views know where it came from. */
export const liveEvent = (conj) => (conj ? { source: 'live', ...conj } : null);

/** GET /api/conjunctions/satellites row → the shape Globe3D and the fleet panels use. */
export function toGlobeSatellite(s) {
  const w = s.worst_conjunction;
  const burn = {
    DANGER: w?.plan_status === 'ready' ? 'Suggestion ready — open Δv Maneuver' : 'Planner computing the smallest safe burn…',
    REVIEW: 'Monitor (review the close pass)',
    MITIGATED: 'Accepted avoidance burn',
    SAFE: 'None (hold)',
  }[s.status];
  return {
    id: s.norad_id,
    name: s.name,
    operator: s.owner || s.object_type || '—',
    risk: tierKey(s.risk_level, s.status),
    riskLevel: s.risk_level,
    status: s.status,
    altitudeKm: Math.round(s.altitude_km),
    inclinationDeg: Number(s.inclination_deg.toFixed(2)),
    velocityKmS: s.velocity_km_s ? Number(s.velocity_km_s.toFixed(2)) : null,
    periodMin: s.period_min,
    raanDeg: s.raan_deg,
    argLatitudeDeg: s.arg_latitude_deg,
    orbitSpeed: 0.0018 * (92.9 / s.period_min),   // stylised: ISS ≈ 0.0018 rad / frame
    conjunctions: s.conjunctions,
    closestDebris: w ? w.secondary_name : 'No close approach in the window',
    missDistanceM: w ? Math.round(w.miss_distance_m) : null,
    poc: w ? formatPc(w.log_pc) : '—',
    timeToTcaHours: w ? Number(w.time_to_tca_hours.toFixed(1)) : null,
    maneuverRequired: s.status === 'DANGER',
    suggestedBurn: burn,
    worst: w,
  };
}

/** Most urgent first: status, then worst collision probability. */
export function sortFleet(fleet) {
  return [...fleet].sort((a, b) => (STATUS_ORDER[b.status] ?? 0) - (STATUS_ORDER[a.status] ?? 0)
    || (b.worst?.log_pc ?? -99) - (a.worst?.log_pc ?? -99));
}
