import React, { useState } from 'react';
import SolarSystem3D from '../components/SolarSystem3D';
import { SOLAR_SYSTEM_DATA } from '../data/solarSystemData';
import { 
  Orbit, 
  Eye, 
  EyeOff, 
  Compass, 
  RotateCcw, 
  Pause, 
  X, 
  ChevronRight, 
  Sparkles, 
  Rocket, 
  Globe2,
  Thermometer
} from 'lucide-react';

export default function SolarSystemView({ onNavigateToEarthFleet }) {
  const [selectedBody, setSelectedBody] = useState(SOLAR_SYSTEM_DATA[3]); // Default to Earth
  const [simSpeed, setSimSpeed] = useState(1);
  const [showOrbits, setShowOrbits] = useState(true);
  const [showAsteroidBelt, setShowAsteroidBelt] = useState(true);
  const [showPanel, setShowPanel] = useState(true);

  const handleSelectBody = (body) => {
    setSelectedBody(body);
    setShowPanel(true);
  };

  const handleResetOverview = () => {
    // Select Sun or null to reset camera
    setSelectedBody(SOLAR_SYSTEM_DATA[0]);
  };

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden', background: '#020617' }}>
      
      {/* 3D WebGL Solar System Canvas */}
      <div style={{ position: 'absolute', inset: 0, zIndex: 1 }}>
        <SolarSystem3D 
          selectedBody={selectedBody}
          onSelectBody={handleSelectBody}
          simSpeed={simSpeed}
          showOrbits={showOrbits}
          showAsteroidBelt={showAsteroidBelt}
        />
      </div>

      {/* Top Planetary Quick-Selection Ribbon */}
      <div 
        style={{
          position: 'absolute',
          top: 76,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 40,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '6px 14px',
          background: 'rgba(8, 14, 28, 0.88)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: 12,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6)',
          maxWidth: '92vw',
          overflowX: 'auto'
        }}
      >
        <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', marginRight: 4, whiteSpace: 'nowrap' }}>
          SOLAR ORRERY:
        </span>

        {SOLAR_SYSTEM_DATA.map((body) => {
          const isSelected = selectedBody && selectedBody.id === body.id;
          const displayName = body.id === 'sun' ? 'Sun' : body.id === 'moon' ? 'Moon' : body.name.split(' ')[0];
          return (
            <button
              key={body.id}
              onClick={() => handleSelectBody(body)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                background: isSelected ? 'rgba(255, 255, 255, 0.14)' : 'rgba(255, 255, 255, 0.03)',
                border: isSelected ? `1px solid ${body.visualColor}` : '1px solid rgba(255, 255, 255, 0.08)',
                color: isSelected ? '#ffffff' : '#94a3b8',
                padding: '4px 8px',
                borderRadius: 6,
                fontSize: 10,
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease'
              }}
            >
              <span 
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  backgroundColor: body.visualColor,
                  boxShadow: isSelected ? `0 0 6px ${body.visualColor}` : 'none'
                }}
              />
              <span>{displayName}</span>
            </button>
          );
        })}
      </div>

      {/* Floating Detailed Planetary Inspection Card (Right Side) */}
      {selectedBody && showPanel && (
        <div 
          className="glass-panel"
          style={{
            position: 'absolute',
            top: 92,
            right: 20,
            width: 360,
            maxHeight: 'calc(100vh - 170px)',
            zIndex: 45,
            padding: 20,
            overflowY: 'auto',
            borderTop: `4px solid ${selectedBody.visualColor}`,
            boxShadow: '0 20px 45px rgba(0, 0, 0, 0.75)'
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: '#f8fafc', margin: 0 }}>
                  {selectedBody.name}
                </h3>
              </div>
              <span style={{ fontSize: 11, color: '#94a3b8', marginTop: 2, display: 'block' }}>
                {selectedBody.type}
              </span>
            </div>
            <button
              onClick={() => setShowPanel(false)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#64748b',
                cursor: 'pointer',
                padding: 4
              }}
            >
              <X size={16} />
            </button>
          </div>

          {/* Overview summary */}
          <p style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.5, marginBottom: 14 }}>
            {selectedBody.overview}
          </p>

          {/* Core Metrics Grid */}
          <div 
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 8,
              marginBottom: 14
            }}
          >
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
              <div style={{ fontSize: 10, color: '#64748b' }}>Mean Radius</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                {selectedBody.radiusKm.toLocaleString()} km
              </div>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
              <div style={{ fontSize: 10, color: '#64748b' }}>Distance from Sun</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                {selectedBody.orbitDistanceAU > 0 ? `${selectedBody.orbitDistanceAU} AU` : '0 AU (Star)'}
              </div>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
              <div style={{ fontSize: 10, color: '#64748b' }}>Orbital Period</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                {selectedBody.orbitalPeriod}
              </div>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
              <div style={{ fontSize: 10, color: '#64748b' }}>Rotation Period</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                {selectedBody.rotationPeriod}
              </div>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
              <div style={{ fontSize: 10, color: '#64748b' }}>Surface Gravity</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                {selectedBody.gravity}
              </div>
            </div>

            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
              <div style={{ fontSize: 10, color: '#64748b' }}>Axial Tilt</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                {selectedBody.axialTilt}°
              </div>
            </div>
          </div>

          {/* Temperature & Atmosphere Banner */}
          <div 
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: 8,
              padding: 10,
              marginBottom: 12
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <Thermometer size={13} color="#f59e0b" />
              <span style={{ fontSize: 11, fontWeight: 700, color: '#f8fafc' }}>
                Thermal Profile:
              </span>
              <span style={{ fontSize: 11, color: '#94a3b8' }} className="mono">
                {selectedBody.surfaceTemp}
              </span>
            </div>

            <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6, lineHeight: 1.4 }}>
              <strong style={{ color: '#cbd5e1' }}>Atmosphere:</strong> {selectedBody.atmosphere}
            </div>
          </div>

          {/* Moons Count */}
          <div 
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: 'rgba(0,0,0,0.25)',
              padding: '8px 12px',
              borderRadius: 6,
              marginBottom: 12
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Globe2 size={13} color="#38bdf8" />
              <span style={{ fontSize: 11, fontWeight: 600, color: '#cbd5e1' }}>Confirmed Moons:</span>
            </div>
            <span style={{ fontSize: 12, fontWeight: 800, color: '#f8fafc' }} className="mono">
              {selectedBody.moonsCount}
            </span>
          </div>

          {/* Space Exploration Missions */}
          {selectedBody.missions && selectedBody.missions.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <Rocket size={13} color="#38bdf8" />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#f8fafc' }}>
                  Historic & Active Space Missions:
                </span>
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>
                {selectedBody.missions.map((m, idx) => (
                  <li key={idx} style={{ marginBottom: 3 }}>
                    {m}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Deep Facts */}
          {selectedBody.facts && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <Sparkles size={13} color="#facc15" />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#f8fafc' }}>
                  Key Astronomical Findings:
                </span>
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>
                {selectedBody.facts.map((fact, idx) => (
                  <li key={idx} style={{ marginBottom: 4 }}>
                    {fact}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Fast Switch to Earth Fleet (If Earth or Moon is selected) */}
          {(selectedBody.id === 'earth' || selectedBody.id === 'moon') && onNavigateToEarthFleet && (
            <button
              onClick={onNavigateToEarthFleet}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                background: 'rgba(56, 189, 248, 0.12)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                color: '#38bdf8',
                padding: '10px 14px',
                borderRadius: 8,
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <Orbit size={15} />
              <span>Launch Earth Fleet Conjunction Console</span>
              <ChevronRight size={14} />
            </button>
          )}

        </div>
      )}

      {/* Bottom Control Dock */}
      <div 
        className="glass-panel"
        style={{
          position: 'absolute',
          bottom: 20,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 30,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '8px 18px'
        }}
      >
        {/* Speed Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 10, color: '#64748b', marginRight: 4 }}>SPEED:</span>
          
          <button
            onClick={() => setSimSpeed(0)}
            style={{
              padding: '4px 8px',
              borderRadius: 5,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              background: simSpeed === 0 ? 'rgba(255, 255, 255, 0.18)' : 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: simSpeed === 0 ? '#ffffff' : '#94a3b8'
            }}
            title="Pause Simulation"
          >
            <Pause size={11} />
          </button>

          <button
            onClick={() => setSimSpeed(1)}
            style={{
              padding: '4px 8px',
              borderRadius: 5,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              background: simSpeed === 1 ? 'rgba(255, 255, 255, 0.18)' : 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: simSpeed === 1 ? '#ffffff' : '#94a3b8'
            }}
          >
            1x
          </button>

          <button
            onClick={() => setSimSpeed(5)}
            style={{
              padding: '4px 8px',
              borderRadius: 5,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              background: simSpeed === 5 ? 'rgba(255, 255, 255, 0.18)' : 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: simSpeed === 5 ? '#ffffff' : '#94a3b8'
            }}
          >
            5x
          </button>

          <button
            onClick={() => setSimSpeed(25)}
            style={{
              padding: '4px 8px',
              borderRadius: 5,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              background: simSpeed === 25 ? 'rgba(255, 255, 255, 0.18)' : 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              color: simSpeed === 25 ? '#ffffff' : '#94a3b8'
            }}
          >
            25x
          </button>
        </div>

        <span style={{ width: 1, height: 16, background: 'rgba(255, 255, 255, 0.1)' }} />

        {/* Orbit Lines Toggle */}
        <button
          onClick={() => setShowOrbits(!showOrbits)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: showOrbits ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            color: showOrbits ? '#f8fafc' : '#94a3b8',
            padding: '5px 10px',
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          {showOrbits ? <Eye size={12} /> : <EyeOff size={12} />}
          <span>{showOrbits ? 'Orbits On' : 'Orbits Off'}</span>
        </button>

        {/* Asteroid Belt Toggle */}
        <button
          onClick={() => setShowAsteroidBelt(!showAsteroidBelt)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: showAsteroidBelt ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            color: showAsteroidBelt ? '#f8fafc' : '#94a3b8',
            padding: '5px 10px',
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          <Sparkles size={12} />
          <span>Asteroid Belt</span>
        </button>

        {/* Reset Camera Overview */}
        <button
          onClick={handleResetOverview}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            color: '#94a3b8',
            padding: '5px 10px',
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            cursor: 'pointer'
          }}
          title="Reset to Sun Center"
        >
          <RotateCcw size={12} />
          <span>Overview</span>
        </button>

        <span style={{ width: 1, height: 16, background: 'rgba(255, 255, 255, 0.1)' }} />

        {/* Interaction hints */}
        <div style={{ fontSize: 11, color: '#64748b', display: 'flex', alignItems: 'center', gap: 5 }}>
          <Compass size={12} />
          <span>Click planet to inspect • Drag to rotate • Scroll to zoom</span>
        </div>
      </div>

    </div>
  );
}
