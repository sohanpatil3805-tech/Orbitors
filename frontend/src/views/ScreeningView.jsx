import React, { useState } from 'react';
import { RISK_TIERS, SATELLITES_DATA } from '../data/satellites';
import { 
  Radar, 
  Search, 
  Filter, 
  AlertTriangle, 
  ShieldCheck, 
  ArrowUpRight, 
  Activity, 
  Flame, 
  ExternalLink 
} from 'lucide-react';

export default function ScreeningView({ onSelectSatelliteForAnalysis, onSelectSatelliteForManeuver }) {
  const [selectedSatelliteId, setSelectedSatelliteId] = useState(25544); // Default to ISS
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const activeSat = SATELLITES_DATA.find(s => s.id === selectedSatelliteId) || SATELLITES_DATA[0];

  // Conjunction events list
  const conjunctionEvents = [
    {
      id: "CONJ-25544-33758",
      primaryName: "ISS (ZARYA)",
      primaryId: 25544,
      secondaryName: "COSMOS 2251 DEBRIS (#142)",
      secondaryId: 33758,
      tcaUtc: "2026-10-14 02:18:00 UTC",
      timeToTcaHours: 36.2,
      missDistanceM: 142.0,
      relativeVelocityKmS: 14.7,
      radialMissM: 38.5,
      rawPoc: "3.20E-04",
      calibratedPoc: "2.84E-04",
      risk: "EXTREME",
      decision: "MANEUVER_RECOMMENDED"
    },
    {
      id: "CONJ-48274-41203",
      primaryName: "TIANGONG (CSS)",
      primaryId: 48274,
      secondaryName: "IRIDIUM 33 DEBRIS (#89)",
      secondaryId: 41203,
      tcaUtc: "2026-10-13 21:00:00 UTC",
      timeToTcaHours: 31.0,
      missDistanceM: 290.0,
      relativeVelocityKmS: 12.1,
      radialMissM: 88.0,
      rawPoc: "8.50E-05",
      calibratedPoc: "1.42E-04",
      risk: "EXTREME",
      decision: "MANEUVER_RECOMMENDED"
    },
    {
      id: "CONJ-44713-40992",
      primaryName: "STARLINK-1007",
      primaryId: 44713,
      secondaryName: "SL-16 UPPER STAGE",
      secondaryId: 40992,
      tcaUtc: "2026-10-14 14:30:00 UTC",
      timeToTcaHours: 48.4,
      missDistanceM: 420.0,
      relativeVelocityKmS: 13.8,
      radialMissM: 110.0,
      rawPoc: "4.50E-05",
      calibratedPoc: "4.05E-05",
      risk: "HIGH",
      decision: "MONITOR"
    },
    {
      id: "CONJ-45145-38241",
      primaryName: "ONEWEB-0145",
      primaryId: 45145,
      secondaryName: "FENGYUN-1C FRAGMENT",
      secondaryId: 38241,
      tcaUtc: "2026-10-14 20:12:00 UTC",
      timeToTcaHours: 54.2,
      missDistanceM: 560.0,
      relativeVelocityKmS: 14.1,
      radialMissM: 145.0,
      rawPoc: "3.80E-05",
      calibratedPoc: "3.20E-05",
      risk: "HIGH",
      decision: "MONITOR"
    },
    {
      id: "CONJ-20580-28221",
      primaryName: "HUBBLE TELESCOPE",
      primaryId: 20580,
      secondaryName: "CZ-4B ROCKET BODY",
      secondaryId: 28221,
      tcaUtc: "2026-10-15 04:00:00 UTC",
      timeToTcaHours: 62.0,
      missDistanceM: 1120.0,
      relativeVelocityKmS: 10.4,
      radialMissM: 320.0,
      rawPoc: "8.20E-06",
      calibratedPoc: "7.10E-06",
      risk: "MEDIUM",
      decision: "HOLD"
    },
    {
      id: "CONJ-25994-47210",
      primaryName: "TERRA (EOS AM-1)",
      primaryId: 25994,
      secondaryName: "ENVISAT DEBRIS",
      secondaryId: 47210,
      tcaUtc: "2026-10-15 10:30:00 UTC",
      timeToTcaHours: 68.5,
      missDistanceM: 1480.0,
      relativeVelocityKmS: 11.2,
      radialMissM: 410.0,
      rawPoc: "5.10E-06",
      calibratedPoc: "4.30E-06",
      risk: "MEDIUM",
      decision: "HOLD"
    },
    {
      id: "CONJ-39634-99001",
      primaryName: "SENTINEL-1A",
      primaryId: 39634,
      secondaryName: "DELTA 4 FRAGMENT",
      secondaryId: 99001,
      tcaUtc: "2026-10-15 14:00:00 UTC",
      timeToTcaHours: 72.0,
      missDistanceM: 4800.0,
      relativeVelocityKmS: 9.8,
      radialMissM: 1200.0,
      rawPoc: "1.20E-07",
      calibratedPoc: "1.00E-07",
      risk: "LOW",
      decision: "HOLD"
    }
  ];

  // Filter list
  const filteredEvents = conjunctionEvents.filter(ev => {
    const matchesRisk = riskFilter === 'ALL' || ev.risk === riskFilter;
    const matchesSearch = ev.primaryName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          ev.secondaryName.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          ev.id.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesRisk && matchesSearch;
  });

  return (
    <div style={{ padding: '84px 28px 30px', height: '100vh', overflowY: 'auto', boxSizing: 'border-box' }}>
      
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Radar size={24} color="#38bdf8" />
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, color: '#f8fafc' }}>
              72-Hour Conjunction Screening Telemetry
            </h1>
          </div>
          <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>
            SGP4 propagation screening against 39,842 cataloged space objects across 3-day forecast window
          </p>
        </div>

        {/* Global Summary Stats */}
        <div style={{ display: 'flex', gap: 16 }}>
          <div className="glass-panel" style={{ padding: '10px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>Catalog Tracked</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#f8fafc' }} className="mono">39,842</div>
          </div>
          <div className="glass-panel" style={{ padding: '10px 16px', textAlign: 'center', borderLeft: '3px solid #dc2626' }}>
            <div style={{ fontSize: 11, color: '#f87171' }}>Critical Threats (≥ 1E-4)</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#dc2626' }} className="mono">2</div>
          </div>
          <div className="glass-panel" style={{ padding: '10px 16px', textAlign: 'center', borderLeft: '3px solid #f97316' }}>
            <div style={{ fontSize: 11, color: '#fb923c' }}>High Risk (Warning)</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#f97316' }} className="mono">2</div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div 
        className="glass-panel" 
        style={{ 
          padding: '12px 18px', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          marginBottom: 20 
        }}
      >
        {/* Search Input */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, maxWidth: 380 }}>
          <Search size={16} color="#64748b" />
          <input 
            type="text"
            placeholder="Search by satellite or debris fragment..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#f8fafc',
              fontSize: 13,
              width: '100%'
            }}
          />
        </div>

        {/* Risk Filter Buttons */}
        <div style={{ display: 'flex', gap: 8 }}>
          {['ALL', 'EXTREME', 'HIGH', 'MEDIUM', 'LOW'].map((risk) => {
            const isSelected = riskFilter === risk;
            const tier = RISK_TIERS[risk];

            return (
              <button
                key={risk}
                onClick={() => setRiskFilter(risk)}
                style={{
                  background: isSelected 
                    ? (tier ? tier.badgeBg : 'rgba(255, 255, 255, 0.15)') 
                    : 'rgba(255, 255, 255, 0.04)',
                  border: isSelected 
                    ? `1px solid ${tier ? tier.border : 'rgba(255, 255, 255, 0.3)'}` 
                    : '1px solid rgba(255, 255, 255, 0.08)',
                  color: isSelected ? '#ffffff' : '#94a3b8',
                  padding: '5px 12px',
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
              >
                {risk}
              </button>
            );
          })}
        </div>
      </div>

      {/* Conjunctions Telemetry Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
          <thead>
            <tr style={{ background: 'rgba(0,0,0,0.3)', borderBottom: '1px solid rgba(255,255,255,0.08)', color: '#94a3b8' }}>
              <th style={{ padding: '12px 16px' }}>EVENT ID</th>
              <th style={{ padding: '12px 16px' }}>PRIMARY ASSET</th>
              <th style={{ padding: '12px 16px' }}>SECONDARY OBJECT</th>
              <th style={{ padding: '12px 16px' }}>TCA (CLOSEST APPROACH)</th>
              <th style={{ padding: '12px 16px' }}>MISS DISTANCE</th>
              <th style={{ padding: '12px 16px' }}>CLOSING SPEED</th>
              <th style={{ padding: '12px 16px' }}>CALIBRATED Pc</th>
              <th style={{ padding: '12px 16px' }}>DECISION</th>
              <th style={{ padding: '12px 16px', textAlign: 'right' }}>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {filteredEvents.map((ev) => {
              const tier = RISK_TIERS[ev.risk];

              return (
                <tr 
                  key={ev.id}
                  style={{ 
                    borderBottom: '1px solid rgba(255,255,255,0.04)',
                    background: ev.risk === 'EXTREME' ? 'rgba(220, 38, 38, 0.04)' : 'transparent',
                    transition: 'background 0.15s'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = ev.risk === 'EXTREME' ? 'rgba(220, 38, 38, 0.04)' : 'transparent'}
                >
                  {/* Event ID */}
                  <td style={{ padding: '12px 16px', fontWeight: 600, color: '#f8fafc' }} className="mono">
                    {ev.id}
                  </td>

                  {/* Primary Asset */}
                  <td style={{ padding: '12px 16px', fontWeight: 700, color: '#f8fafc' }}>
                    {ev.primaryName}
                  </td>

                  {/* Secondary Debris */}
                  <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>
                    {ev.secondaryName}
                  </td>

                  {/* TCA */}
                  <td style={{ padding: '12px 16px', color: '#94a3b8' }} className="mono">
                    <div>{ev.tcaUtc}</div>
                    <div style={{ fontSize: 10, color: '#64748b' }}>T-{ev.timeToTcaHours}h</div>
                  </td>

                  {/* Miss Distance */}
                  <td style={{ padding: '12px 16px', fontWeight: 700, color: ev.missDistanceM < 200 ? '#dc2626' : '#f8fafc' }} className="mono">
                    {ev.missDistanceM < 1000 ? `${ev.missDistanceM} m` : `${(ev.missDistanceM/1000).toFixed(2)} km`}
                  </td>

                  {/* Closing Velocity */}
                  <td style={{ padding: '12px 16px', color: '#94a3b8' }} className="mono">
                    {ev.relativeVelocityKmS} km/s
                  </td>

                  {/* Calibrated Pc */}
                  <td style={{ padding: '12px 16px', fontWeight: 700, color: tier.color }} className="mono">
                    {ev.calibratedPoc}
                  </td>

                  {/* Decision */}
                  <td style={{ padding: '12px 16px' }}>
                    <span 
                      style={{
                        padding: '3px 8px',
                        borderRadius: 4,
                        fontSize: 10,
                        fontWeight: 700,
                        background: tier.badgeBg,
                        color: tier.color,
                        border: `1px solid ${tier.border}`
                      }}
                    >
                      {ev.decision}
                    </span>
                  </td>

                  {/* Actions */}
                  <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
                      <button
                        onClick={() => onSelectSatelliteForAnalysis(ev)}
                        style={{
                          background: 'rgba(255, 255, 255, 0.08)',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          color: '#f8fafc',
                          padding: '4px 8px',
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 600,
                          cursor: 'pointer'
                        }}
                      >
                        Explain (XAI)
                      </button>

                      {ev.decision === 'MANEUVER_RECOMMENDED' && (
                        <button
                          onClick={() => onSelectSatelliteForManeuver(ev)}
                          style={{
                            background: 'rgba(220, 38, 38, 0.2)',
                            border: '1px solid #dc2626',
                            color: '#f87171',
                            padding: '4px 8px',
                            borderRadius: 4,
                            fontSize: 11,
                            fontWeight: 600,
                            cursor: 'pointer'
                          }}
                        >
                          Optimize Δv
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
