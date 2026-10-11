import React, { useState } from 'react';
import { 
  Rocket, 
  Fuel, 
  ShieldCheck, 
  TrendingDown, 
  ArrowRight, 
  Sliders, 
  DollarSign, 
  Sparkles, 
  Crosshair 
} from 'lucide-react';

export default function ManeuverView({ event }) {
  const currentEvent = event || {
    id: "ESA-KELVINS-2016-0421",
    primaryName: "ISS (ZARYA)",
    secondaryName: "COSMOS 2251 DEBRIS (#142)",
    missDistanceM: 142.0,
    currentPoc: 0.000284
  };

  const [burnDeltaV, setBurnDeltaV] = useState(0.52); // Default to sweet spot

  // Tradeoff curve points (Slide 12 Scatter Plot)
  const tradeoffPoints = [
    { dv: 0.0, risk: 2.84e-4, missM: 142.0, fuelG: 0, isSweetSpot: false },
    { dv: 0.1, risk: 1.48e-4, missM: 237.0, fuelG: 17, isSweetSpot: false },
    { dv: 0.25, risk: 5.70e-5, missM: 379.5, fuelG: 42, isSweetSpot: false },
    { dv: 0.40, risk: 2.20e-5, missM: 522.0, fuelG: 68, isSweetSpot: false },
    { dv: 0.52, risk: 1.05e-6, missM: 636.0, fuelG: 88, isSweetSpot: true },
    { dv: 0.75, risk: 2.10e-7, missM: 854.5, fuelG: 127, isSweetSpot: false },
    { dv: 1.00, risk: 1.00e-7, missM: 1092.0, fuelG: 170, isSweetSpot: false },
    { dv: 1.50, risk: 1.00e-7, missM: 1567.0, fuelG: 255, isSweetSpot: false },
    { dv: 2.00, risk: 1.00e-7, missM: 2042.0, fuelG: 340, isSweetSpot: false }
  ];

  // Dynamic calculations based on slider
  const separationGainM = burnDeltaV * 950.0;
  const newMissM = currentEvent.missDistanceM + separationGainM;
  const residualRisk = burnDeltaV === 0 
    ? currentEvent.currentPoc 
    : Math.max(1e-7, currentEvent.currentPoc * Math.exp(-separationGainM / 150.0));
  const fuelBurnedGrams = Math.round(500 * (1.0 - Math.exp(-burnDeltaV / (9.80665 * 300))) * 1000);
  const isSafe = residualRisk < 1e-5;

  return (
    <div style={{ padding: '84px 28px 30px', height: '100vh', overflowY: 'auto', boxSizing: 'border-box' }}>
      
      {/* Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Rocket size={24} color="#f97316" />
            <h1 style={{ fontSize: 24, fontWeight: 800, margin: 0, color: '#f8fafc' }}>
              Collision Avoidance Maneuver (CAM) Optimization
            </h1>
          </div>
          <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 4 }}>
            Action optimization balancing residual collision risk vs. minimal propellant expenditure (Slide 12)
          </p>
        </div>

        {/* Optimal Sweet Spot Indicator */}
        <div 
          className="glass-panel" 
          style={{ 
            padding: '10px 18px', 
            borderLeft: '4px solid #f97316',
            display: 'flex',
            alignItems: 'center',
            gap: 12
          }}
        >
          <Sparkles size={22} color="#f97316" />
          <div>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>OPTIMAL SWEET SPOT</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#f8fafc' }}>
              +0.52 m/s <span style={{ fontSize: 12, fontWeight: 500, color: '#38bdf8' }}>(88g Fuel)</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2-Column Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 20, marginBottom: 20 }}>
        
        {/* Left: Action Optimization Scatter Plot Canvas */}
        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div>
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                Action Optimization Scatter Curve
              </h3>
              <p style={{ fontSize: 11, color: '#94a3b8', margin: '2px 0 0' }}>
                Residual Collision Risk (Log scale) vs. Delta-V Cost (m/s)
              </p>
            </div>
            <span 
              style={{
                fontSize: 10,
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: 4,
                background: 'rgba(249, 115, 22, 0.2)',
                color: '#fb923c',
                border: '1px solid rgba(249, 115, 22, 0.4)'
              }}
            >
              SWEET SPOT HIGHLIGHTED
            </span>
          </div>

          {/* SVG Scatter Plot */}
          <div style={{ width: '100%', height: 260, position: 'relative', background: 'rgba(0,0,0,0.3)', borderRadius: 8, padding: 10, boxSizing: 'border-box' }}>
            <svg width="100%" height="100%" viewBox="0 0 500 240">
              {/* Grid Lines */}
              <line x1="50" y1="20" x2="480" y2="20" stroke="rgba(255,255,255,0.06)" />
              <line x1="50" y1="60" x2="480" y2="60" stroke="rgba(255,255,255,0.06)" />
              <line x1="50" y1="100" x2="480" y2="100" stroke="rgba(255,255,255,0.06)" />
              <line x1="50" y1="140" x2="480" y2="140" stroke="rgba(255,255,255,0.06)" />
              <line x1="50" y1="180" x2="480" y2="180" stroke="rgba(255,255,255,0.06)" />
              <line x1="50" y1="210" x2="480" y2="210" stroke="rgba(255,255,255,0.15)" />
              <line x1="50" y1="20" x2="50" y2="210" stroke="rgba(255,255,255,0.15)" />

              {/* Threshold Red Line (1E-4) */}
              <line x1="50" y1="80" x2="480" y2="80" stroke="#dc2626" strokeDasharray="4 4" strokeWidth="1.5" />
              <text x="55" y="75" fill="#f87171" fontSize="10" fontFamily="JetBrains Mono">1E-4 Safety Limit</text>

              {/* Target Safe Zone Green Line (1E-5) */}
              <line x1="50" y1="130" x2="480" y2="130" stroke="#10b981" strokeDasharray="4 4" strokeWidth="1" />
              <text x="55" y="125" fill="#34d399" fontSize="10" fontFamily="JetBrains Mono">1E-5 Target Safe Zone</text>

              {/* Sweet Spot Box */}
              <rect x="145" y="120" width="70" height="90" fill="rgba(249, 115, 22, 0.15)" stroke="#f97316" strokeDasharray="2 2" rx="4" />
              <text x="150" y="200" fill="#fb923c" fontSize="9" fontWeight="bold">SWEET SPOT</text>

              {/* Scatter Points */}
              {tradeoffPoints.map((pt, i) => {
                const cx = 50 + (pt.dv / 2.0) * 400;
                // Log scale mapping for Y
                const logVal = Math.log10(pt.risk);
                const cy = 20 + ((logVal - (-3.0)) / (-7.0 - (-3.0))) * 180;

                return (
                  <g key={i}>
                    <circle 
                      cx={cx} 
                      cy={cy} 
                      r={pt.isSweetSpot ? 7 : 4} 
                      fill={pt.isSweetSpot ? "#f97316" : (pt.risk < 1e-5 ? "#10b981" : "#dc2626")}
                      stroke="#ffffff"
                      strokeWidth={pt.isSweetSpot ? 2 : 1}
                    />
                  </g>
                );
              })}

              {/* Axis Labels */}
              <text x="230" y="235" fill="#94a3b8" fontSize="11" textAnchor="middle">Delta-V Burn (m/s)</text>
              <text x="15" y="115" fill="#94a3b8" fontSize="11" textAnchor="middle" transform="rotate(-90 15,115)">Residual Risk</text>
            </svg>
          </div>

          {/* Key Takeaways */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 16 }}>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>Optimal Fuel Burn</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#38bdf8', marginTop: 2 }} className="mono">0.52 m/s</div>
              <div style={{ fontSize: 10, color: '#64748b' }}>~88 grams propellant</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>Expanded Clearance</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#10b981', marginTop: 2 }} className="mono">+494 meters</div>
              <div style={{ fontSize: 10, color: '#64748b' }}>636m final separation</div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.25)', padding: 12, borderRadius: 8 }}>
              <div style={{ fontSize: 11, color: '#94a3b8' }}>Risk Suppression</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#fb923c', marginTop: 2 }} className="mono">99.6% Reduction</div>
              <div style={{ fontSize: 10, color: '#64748b' }}>Drops to 1.05E-06</div>
            </div>
          </div>
        </div>

        {/* Right: Interactive Burn Simulator */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="glass-panel" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              <Crosshair size={18} color="#38bdf8" />
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                Interactive Burn Simulator
              </h3>
            </div>

            {/* Slider */}
            <div style={{ marginBottom: 18 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}>
                <span style={{ color: '#94a3b8' }}>Applied Along-Track Δv:</span>
                <span style={{ fontWeight: 800, color: '#38bdf8' }} className="mono">
                  +{burnDeltaV.toFixed(2)} m/s
                </span>
              </div>
              <input 
                type="range"
                min="0.0"
                max="2.0"
                step="0.02"
                value={burnDeltaV}
                onChange={(e) => setBurnDeltaV(parseFloat(e.target.value))}
                style={{ width: '100%', accentColor: '#38bdf8' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#64748b', marginTop: 4 }}>
                <span>0.0 m/s (Hold)</span>
                <span>0.52 m/s (Sweet Spot)</span>
                <span>2.0 m/s (Max)</span>
              </div>
            </div>

            {/* Simulation Results */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: 12, borderRadius: 8 }}>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>Projected Miss Distance</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: '#f8fafc', marginTop: 2 }} className="mono">
                  {newMissM.toFixed(1)} meters
                </div>
                <div style={{ fontSize: 10, color: '#10b981' }}>
                  +{separationGainM.toFixed(0)}m expansion gain
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: 12, borderRadius: 8 }}>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>Residual Collision Probability</div>
                <div style={{ fontSize: 18, fontWeight: 800, color: isSafe ? '#10b981' : '#dc2626', marginTop: 2 }} className="mono">
                  {residualRisk.toExponential(2)}
                </div>
                <div style={{ fontSize: 10, color: isSafe ? '#10b981' : '#f87171' }}>
                  {isSafe ? '✓ Safely within 1E-5 clearance zone' : '⚠ Above critical 1E-4 safety limit'}
                </div>
              </div>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: 12, borderRadius: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Fuel size={14} color="#f97316" />
                  <span style={{ fontSize: 11, color: '#94a3b8' }}>Propellant Consumed</span>
                </div>
                <div style={{ fontSize: 18, fontWeight: 800, color: '#f8fafc', marginTop: 2 }} className="mono">
                  {fuelBurnedGrams} grams
                </div>
                <div style={{ fontSize: 10, color: '#64748b' }}>
                  Tsiolkovsky hydrazine Isp=300s
                </div>
              </div>
            </div>

            {/* Burn Direction Instruction */}
            <div 
              style={{ 
                marginTop: 16, 
                padding: '10px 12px', 
                borderRadius: 8, 
                background: 'rgba(6, 182, 212, 0.1)', 
                border: '1px solid rgba(6, 182, 212, 0.3)',
                fontSize: 11,
                color: '#7dd3fc'
              }}
            >
              <strong>Maneuver Execution Vector:</strong> +Along-track prograde impulse scheduled for T-24h to avoid orbital congestion corridor.
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
