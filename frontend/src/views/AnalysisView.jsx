import React, { useState } from 'react';
import { RISK_TIERS } from '../data/satellites';
import { 
  BrainCircuit, 
  ShieldAlert, 
  Sliders, 
  HelpCircle, 
  ArrowRight, 
  Sun, 
  Activity, 
  CheckCircle2, 
  Gauge, 
  Flame 
} from 'lucide-react';

export default function AnalysisView({ event, onNavigateToManeuver }) {
  // Default sample event if none selected from table
  const defaultEvent = {
    id: "ESA-KELVINS-2016-0421",
    primaryName: "ISS (ZARYA)",
    secondaryName: "COSMOS 2251 DEBRIS (#142)",
    tcaUtc: "2026-10-14 02:18:00 UTC",
    timeToTcaHours: 36.2,
    missDistanceM: 142.0,
    relativeVelocityKmS: 14.7,
    radialCovarianceM: 120.0,
    solarFluxF107: 162.0,
    rawPoc: "3.20E-04",
    calibratedPoc: "2.84E-04"
  };

  const currentEvent = event || defaultEvent;

  // Interactive tuner state
  const [missDist, setMissDist] = useState(currentEvent.missDistanceM || 142.0);
  const [radialCov, setRadialCov] = useState(currentEvent.radialCovarianceM || 120.0);
  const [solarFlux, setSolarFlux] = useState(currentEvent.solarFluxF107 || 162.0);

  // Dynamic simulation of calibrated PoC and SHAP
  const isHighRisk = missDist < 250 && radialCov < 300;
  const simulatedPoc = isHighRisk ? (2.84e-4 * (180 / Math.max(50, missDist))).toExponential(2) : (3.5e-6).toExponential(2);
  const isCritical = parseFloat(simulatedPoc) >= 1e-4;

  const shapFeatures = [
    {
      feature: "miss_distance_m",
      label: "Miss Distance",
      impact: missDist < 200 ? -0.45 : -0.15,
      direction: missDist < 300 ? "INCREASES_RISK" : "REDUCES_RISK",
      percentage: 35,
      explanation: `Close approach distance of ${missDist.toFixed(1)}m is ${missDist < 200 ? 'critically within 200m safety envelope' : 'providing moderate clearance'}.`
    },
    {
      feature: "radial_position_covariance",
      label: "Radial Position Covariance",
      impact: radialCov < 300 ? 0.38 : -0.25,
      direction: radialCov < 300 ? "INCREASES_RISK" : "REDUCES_RISK",
      percentage: 28,
      explanation: `Orbital tracking uncertainty is ${radialCov < 300 ? 'tight (120m, high radar confidence)' : 'diffuse (uncertain pass)'}.`
    },
    {
      feature: "time_to_tca_hours",
      label: "Time to TCA (Lead Time)",
      impact: 0.22,
      direction: "INCREASES_RISK",
      percentage: 18,
      explanation: `36.2h remaining until TCA narrows collision avoidance burn planning window.`
    },
    {
      feature: "relative_velocity_km_s",
      label: "Closing Velocity",
      impact: 0.14,
      direction: "INCREASES_RISK",
      percentage: 12,
      explanation: `Hypersonic encounter velocity of 14.7 km/s yields catastrophic kinetic lethality.`
    },
    {
      feature: "solar_flux_f10_7",
      label: "Solar Drag (F10.7 Radio Flux)",
      impact: solarFlux > 150 ? 0.09 : 0.02,
      direction: solarFlux > 150 ? "INCREASES_RISK" : "REDUCES_RISK",
      percentage: 7,
      explanation: `Solar flux F10.7=${solarFlux.toFixed(0)} indicates ${solarFlux > 150 ? 'active thermospheric density swelling causing orbit decay' : 'nominal solar quiet conditions'}.`
    }
  ];

  return (
    <div style={{ padding: '84px 28px 30px', height: '100vh', overflowY: 'auto', boxSizing: 'border-box' }}>
      
      {/* Page Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <BrainCircuit size={24} color="#38bdf8" />
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, color: '#f8fafc' }}>
              Explainable AI (XAI) & Conjunction Risk Calibration
            </h1>
          </div>
          <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>
            TreeSHAP feature attributions and calibrated collision probability against 1E-4 industry threshold
          </p>
        </div>

        {/* Go/No-Go Decision Status Badge */}
        <div 
          className="glass-panel" 
          style={{ 
            padding: '10px 18px', 
            borderLeft: `4px solid ${isCritical ? '#dc2626' : '#10b981'}`,
            display: 'flex',
            alignItems: 'center',
            gap: 12
          }}
        >
          {isCritical ? <ShieldAlert size={24} color="#dc2626" /> : <CheckCircle2 size={24} color="#10b981" />}
          <div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>OPERATOR DECISION</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: isCritical ? '#f87171' : '#34d399' }}>
              {isCritical ? 'MANEUVER RECOMMENDED' : 'HOLD (NOMINAL)'}
            </div>
          </div>
        </div>
      </div>

      {/* Main 2-Column Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 20, marginBottom: 20 }}>
        
        {/* Left Column: SHAP Feature Attributions */}
        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Gauge size={18} color="#38bdf8" />
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                SHAP Driving Factor Attribution
              </h3>
            </div>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Game-Theoretic XAI (Lundberg & Lee)</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {shapFeatures.map((feat, idx) => {
              const isRiskIncrease = feat.direction === 'INCREASES_RISK';

              return (
                <div key={idx} style={{ background: 'rgba(0,0,0,0.25)', padding: '12px 14px', borderRadius: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc' }}>
                      {feat.label}
                    </span>
                    <span 
                      style={{ 
                        fontSize: 12, 
                        fontWeight: 700, 
                        color: isRiskIncrease ? '#f87171' : '#34d399' 
                      }} 
                      className="mono"
                    >
                      {isRiskIncrease ? `+${feat.percentage}% Risk` : `-${feat.percentage}% Risk`}
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div style={{ width: '100%', height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden', marginBottom: 8 }}>
                    <div 
                      style={{
                        width: `${feat.percentage * 2.5}%`,
                        height: '100%',
                        background: isRiskIncrease ? 'linear-gradient(90deg, #f97316, #dc2626)' : 'linear-gradient(90deg, #38bdf8, #10b981)',
                        borderRadius: 3
                      }}
                    />
                  </div>

                  <p style={{ fontSize: 11, color: '#94a3b8', margin: 0 }}>
                    {feat.explanation}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Event Readout & Interactive Tuner */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          
          {/* Mission Telemetry Readout (Slide 13 of Problem Statement) */}
          <div className="glass-panel" style={{ padding: 18, borderLeft: '4px solid #38bdf8' }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 10px', color: '#f8fafc' }}>
              OPERATIONAL TELEMETRY READOUT
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
              <div style={{ background: 'rgba(220, 38, 38, 0.1)', padding: 10, borderRadius: 6, border: '1px solid rgba(220,38,38,0.3)', color: '#fca5a5' }}>
                <strong>[ALERT]:</strong> Calibrated PoC ({simulatedPoc}) {isCritical ? 'crosses 1E-4 critical limit.' : 'remains below critical threshold.'} Miss distance: {missDist.toFixed(1)}m.
              </div>
              <div style={{ background: 'rgba(56, 189, 248, 0.08)', padding: 10, borderRadius: 6, border: '1px solid rgba(56, 189, 248, 0.25)', color: '#7dd3fc' }}>
                <strong>[DIAGNOSTIC]:</strong> Radial uncertainty narrowed to {radialCov.toFixed(0)}m. Solar weather F10.7={solarFlux.toFixed(0)}.
              </div>
              <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: 10, borderRadius: 6, border: '1px solid rgba(16,185,129,0.3)', color: '#6ee7b7' }}>
                <strong>[ACTION]:</strong> {isCritical ? 'Recommend +0.52 m/s along-track burn at T-24h to raise radial separation by +450m.' : 'HOLD. Continue tracking radar passes.'}
              </div>
            </div>
          </div>

          {/* Interactive Feature Tuner */}
          <div className="glass-panel" style={{ padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <Sliders size={16} color="#38bdf8" />
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                Live Conjunction Feature Tuner
              </h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Miss Distance Slider */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                  <span style={{ color: '#94a3b8' }}>Miss Distance:</span>
                  <span style={{ fontWeight: 700, color: '#f8fafc' }} className="mono">{missDist} m</span>
                </div>
                <input 
                  type="range"
                  min="50"
                  max="1500"
                  step="10"
                  value={missDist}
                  onChange={(e) => setMissDist(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#38bdf8' }}
                />
              </div>

              {/* Covariance Slider */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                  <span style={{ color: '#94a3b8' }}>Radial Covariance (Uncertainty):</span>
                  <span style={{ fontWeight: 700, color: '#f8fafc' }} className="mono">{radialCov} m</span>
                </div>
                <input 
                  type="range"
                  min="50"
                  max="1000"
                  step="10"
                  value={radialCov}
                  onChange={(e) => setRadialCov(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#f97316' }}
                />
              </div>

              {/* Solar Weather Slider */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                  <span style={{ color: '#94a3b8' }}>Solar Radio Flux (F10.7):</span>
                  <span style={{ fontWeight: 700, color: '#f8fafc' }} className="mono">{solarFlux}</span>
                </div>
                <input 
                  type="range"
                  min="100"
                  max="250"
                  step="5"
                  value={solarFlux}
                  onChange={(e) => setSolarFlux(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: '#eab308' }}
                />
              </div>
            </div>

            {/* Maneuver CTA Button */}
            <button
              onClick={() => onNavigateToManeuver && onNavigateToManeuver(currentEvent)}
              style={{
                width: '100%',
                marginTop: 16,
                background: 'linear-gradient(135deg, #dc2626, #ea580c)',
                border: 'none',
                color: '#ffffff',
                padding: '10px 16px',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                boxShadow: '0 4px 15px rgba(220, 38, 38, 0.4)'
              }}
            >
              <span>Proceed to Δv Maneuver Optimization</span>
              <ArrowRight size={16} />
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
