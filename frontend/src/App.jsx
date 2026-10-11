import React, { useState, useEffect } from 'react';
import Globe3D from './components/Globe3D';
import ScreeningView from './views/ScreeningView';
import AnalysisView from './views/AnalysisView';
import ManeuverView from './views/ManeuverView';
import BenchmarkView from './views/BenchmarkView';
import { RISK_TIERS, SATELLITES_DATA } from './data/satellites';
import { 
  ShieldAlert, 
  Satellite, 
  RotateCw, 
  Eye, 
  EyeOff, 
  Compass, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  X, 
  ChevronLeft, 
  ChevronRight,
  Globe,
  Radar,
  BrainCircuit,
  Rocket,
  Award
} from 'lucide-react';

export default function App() {
  // Navigation tabs: 'HOME' (3D Globe), 'SCREENING', 'ANALYSIS', 'MANEUVER', 'BENCHMARK'
  const [currentView, setCurrentView] = useState('HOME');

  // Shared event for analysis/maneuver
  const [activeAnalysisEvent, setActiveAnalysisEvent] = useState(null);

  // Home Page State (Strictly Preserved!)
  const [selectedSat, setSelectedSat] = useState(SATELLITES_DATA[0]); // Default to ISS
  const [filterRisk, setFilterRisk] = useState('ALL');
  const [showOrbits, setShowOrbits] = useState(true);
  const [autoRotate, setAutoRotate] = useState(true);
  const [utcTime, setUtcTime] = useState('');
  const [showLeftPanel, setShowLeftPanel] = useState(true);

  // Live UTC Mission Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Filtered satellite list for Home Page
  const filteredSatellites = SATELLITES_DATA.filter((sat) => {
    if (filterRisk === 'ALL') return true;
    return sat.risk === filterRisk;
  });

  const riskCounts = {
    EXTREME: SATELLITES_DATA.filter(s => s.risk === 'EXTREME').length,
    HIGH: SATELLITES_DATA.filter(s => s.risk === 'HIGH').length,
    MEDIUM: SATELLITES_DATA.filter(s => s.risk === 'MEDIUM').length,
    LOW: SATELLITES_DATA.filter(s => s.risk === 'LOW').length
  };

  // Navigation handlers
  const handleSelectSatelliteForAnalysis = (event) => {
    setActiveAnalysisEvent(event);
    setCurrentView('ANALYSIS');
  };

  const handleSelectSatelliteForManeuver = (event) => {
    setActiveAnalysisEvent(event);
    setCurrentView('MANEUVER');
  };

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', overflow: 'hidden', background: '#030712' }}>
      
      {/* ============================================================== */}
      {/* GLOBAL TOP NAVIGATION HEADER                                   */}
      {/* ============================================================== */}
      <header 
        style={{
          position: 'absolute',
          top: 14,
          left: 20,
          right: 20,
          zIndex: 50,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '10px 20px',
          background: 'rgba(8, 14, 28, 0.88)',
          backdropFilter: 'blur(16px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: 14,
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5)'
        }}
      >
        {/* Brand */}
        <div 
          onClick={() => setCurrentView('HOME')}
          style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}
        >
          <div 
            style={{
              width: 36,
              height: 36,
              borderRadius: 9,
              background: '#0f172a',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
            }}
          >
            <Satellite size={20} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 17, fontWeight: 800, letterSpacing: '0.08em', color: '#f8fafc' }}>
                ORBITGUARD<span style={{ color: '#38bdf8' }}>.AI</span>
              </span>
              <span 
                style={{
                  fontSize: 9,
                  fontWeight: 700,
                  padding: '2px 5px',
                  borderRadius: 4,
                  background: 'rgba(255, 255, 255, 0.06)',
                  color: '#94a3b8',
                  border: '1px solid rgba(255, 255, 255, 0.12)'
                }}
              >
                MISSION CONTROL
              </span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          
          {/* TAB 1: 3D Fleet Globe (Home Page) */}
          <button
            onClick={() => setCurrentView('HOME')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: currentView === 'HOME' ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
              border: currentView === 'HOME' ? '1px solid rgba(255, 255, 255, 0.22)' : '1px solid transparent',
              color: currentView === 'HOME' ? '#f8fafc' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
          >
            <Globe size={14} />
            <span>3D Fleet Globe</span>
          </button>

          {/* TAB 2: Screening */}
          <button
            onClick={() => setCurrentView('SCREENING')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: currentView === 'SCREENING' ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
              border: currentView === 'SCREENING' ? '1px solid rgba(255, 255, 255, 0.22)' : '1px solid transparent',
              color: currentView === 'SCREENING' ? '#f8fafc' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
          >
            <Radar size={14} />
            <span>72h Screening</span>
          </button>

          {/* TAB 3: ML Analysis & XAI */}
          <button
            onClick={() => setCurrentView('ANALYSIS')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: currentView === 'ANALYSIS' ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
              border: currentView === 'ANALYSIS' ? '1px solid rgba(255, 255, 255, 0.22)' : '1px solid transparent',
              color: currentView === 'ANALYSIS' ? '#f8fafc' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
          >
            <BrainCircuit size={14} />
            <span>ML & SHAP (XAI)</span>
          </button>

          {/* TAB 4: Maneuver Optimizer */}
          <button
            onClick={() => setCurrentView('MANEUVER')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: currentView === 'MANEUVER' ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
              border: currentView === 'MANEUVER' ? '1px solid rgba(255, 255, 255, 0.22)' : '1px solid transparent',
              color: currentView === 'MANEUVER' ? '#f8fafc' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
          >
            <Rocket size={14} />
            <span>Δv Maneuver</span>
          </button>

          {/* TAB 5: ESA Benchmarks */}
          <button
            onClick={() => setCurrentView('BENCHMARK')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: currentView === 'BENCHMARK' ? 'rgba(255, 255, 255, 0.12)' : 'transparent',
              border: currentView === 'BENCHMARK' ? '1px solid rgba(255, 255, 255, 0.22)' : '1px solid transparent',
              color: currentView === 'BENCHMARK' ? '#f8fafc' : '#94a3b8',
              padding: '6px 12px',
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
          >
            <Award size={14} />
            <span>ESA Replay & KPIs</span>
          </button>
        </div>

        {/* UTC Mission Clock */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#94a3b8', fontSize: 11 }} className="mono">
          <Clock size={13} color="#94a3b8" />
          <span>{utcTime || 'UTC 00:00:00'}</span>
        </div>
      </header>

      {/* ============================================================== */}
      {/* VIEW 1: HOME PAGE (STRICTLY PRESERVED AS REQUESTED!)           */}
      {/* ============================================================== */}
      {currentView === 'HOME' && (
        <div style={{ position: 'relative', width: '100%', height: '100%' }}>
          
          {/* Centered 3D NASA Blue Marble Earth Globe */}
          <div 
            style={{ 
              position: 'absolute', 
              inset: 0, 
              zIndex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Globe3D 
              selectedSatellite={selectedSat}
              onSelectSatellite={(sat) => setSelectedSat(sat)}
              filterRisk={filterRisk}
              showOrbits={showOrbits}
              autoRotate={autoRotate}
            />
          </div>

          {/* 4-Tier Interactive Risk Filter Bar (Sub-bar right beneath header on Home) */}
          <div 
            style={{
              position: 'absolute',
              top: 76,
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 40,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 14px',
              background: 'rgba(8, 14, 28, 0.82)',
              backdropFilter: 'blur(12px)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: 10
            }}
          >
            <button
              onClick={() => setFilterRisk('ALL')}
              style={{
                background: filterRisk === 'ALL' ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                border: filterRisk === 'ALL' ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.08)',
                color: filterRisk === 'ALL' ? '#f8fafc' : '#94a3b8',
                padding: '4px 10px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              All ({SATELLITES_DATA.length})
            </button>

            {/* EXTREME */}
            <button
              onClick={() => setFilterRisk('EXTREME')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                background: filterRisk === 'EXTREME' ? RISK_TIERS.EXTREME.badgeBg : 'rgba(220, 38, 38, 0.08)',
                border: `1px solid ${filterRisk === 'EXTREME' ? RISK_TIERS.EXTREME.border : 'rgba(220, 38, 38, 0.25)'}`,
                color: '#f87171',
                padding: '4px 10px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: RISK_TIERS.EXTREME.color }} />
              Extreme ({riskCounts.EXTREME})
            </button>

            {/* HIGH */}
            <button
              onClick={() => setFilterRisk('HIGH')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                background: filterRisk === 'HIGH' ? RISK_TIERS.HIGH.badgeBg : 'rgba(249, 115, 22, 0.08)',
                border: `1px solid ${filterRisk === 'HIGH' ? RISK_TIERS.HIGH.border : 'rgba(249, 115, 22, 0.25)'}`,
                color: '#fb923c',
                padding: '4px 10px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: RISK_TIERS.HIGH.color }} />
              High ({riskCounts.HIGH})
            </button>

            {/* MEDIUM */}
            <button
              onClick={() => setFilterRisk('MEDIUM')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                background: filterRisk === 'MEDIUM' ? RISK_TIERS.MEDIUM.badgeBg : 'rgba(234, 179, 8, 0.08)',
                border: `1px solid ${filterRisk === 'MEDIUM' ? RISK_TIERS.MEDIUM.border : 'rgba(234, 179, 8, 0.25)'}`,
                color: '#facc15',
                padding: '4px 10px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: RISK_TIERS.MEDIUM.color }} />
              Medium ({riskCounts.MEDIUM})
            </button>

            {/* LOW */}
            <button
              onClick={() => setFilterRisk('LOW')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                background: filterRisk === 'LOW' ? RISK_TIERS.LOW.badgeBg : 'rgba(16, 185, 129, 0.08)',
                border: `1px solid ${filterRisk === 'LOW' ? RISK_TIERS.LOW.border : 'rgba(16, 185, 129, 0.25)'}`,
                color: '#34d399',
                padding: '4px 10px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <span style={{ width: 7, height: 7, borderRadius: '50%', background: RISK_TIERS.LOW.color }} />
              Low ({riskCounts.LOW})
            </button>
          </div>

          {/* Left Panel Toggle Button */}
          <button
            onClick={() => setShowLeftPanel(!showLeftPanel)}
            style={{
              position: 'absolute',
              top: 92,
              left: showLeftPanel ? 336 : 20,
              zIndex: 35,
              background: 'rgba(8, 14, 28, 0.9)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#94a3b8',
              width: 32,
              height: 32,
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.3s ease'
            }}
            title={showLeftPanel ? 'Collapse Fleet Panel' : 'Expand Fleet Panel'}
          >
            {showLeftPanel ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
          </button>

          {/* Left Floating Fleet Console */}
          <div 
            style={{
              position: 'absolute',
              top: 92,
              left: 20,
              width: 300,
              maxHeight: 'calc(100vh - 170px)',
              zIndex: 30,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
              overflowY: 'auto',
              transform: showLeftPanel ? 'translateX(0)' : 'translateX(-340px)',
              opacity: showLeftPanel ? 1 : 0,
              transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
              pointerEvents: showLeftPanel ? 'auto' : 'none'
            }}
          >
            {/* Global Fleet Status */}
            <div 
              className="glass-panel" 
              style={{ 
                padding: 16,
                borderLeft: '4px solid #dc2626'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.05em', color: '#94a3b8' }}>
                  GLOBAL FLEET STATUS
                </span>
                <span 
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: '2px 6px',
                    borderRadius: 4,
                    background: 'rgba(220, 38, 38, 0.2)',
                    color: '#f87171',
                    border: '1px solid rgba(220, 38, 38, 0.4)'
                  }}
                >
                  RED ALERT
                </span>
              </div>
              <div>
                <div style={{ fontSize: 22, fontWeight: 800, color: '#f8fafc' }}>
                  2 <span style={{ fontSize: 13, fontWeight: 500, color: '#dc2626' }}>Critical Conjunctions</span>
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                  ISS & Tiangong crossing 1E-4 safety limit
                </div>
              </div>
            </div>

            {/* Monitored Satellites List */}
            <div className="glass-panel" style={{ padding: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, padding: '0 4px' }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8' }}>
                  MONITORED SATELLITES ({filteredSatellites.length})
                </span>
                <span style={{ fontSize: 10, color: '#64748b' }}>Click to focus</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {filteredSatellites.map((sat) => {
                  const isSelected = selectedSat && selectedSat.id === sat.id;
                  const tier = RISK_TIERS[sat.risk];

                  return (
                    <div
                      key={sat.id}
                      onClick={() => setSelectedSat(sat)}
                      className="glass-panel-interactive"
                      style={{
                        padding: '8px 10px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        borderColor: isSelected ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.08)',
                        background: isSelected ? 'rgba(255, 255, 255, 0.08)' : 'rgba(13, 22, 42, 0.65)',
                        boxShadow: 'none'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span 
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            backgroundColor: tier.color
                          }}
                          className={sat.risk === 'EXTREME' ? 'pulse-extreme' : ''}
                        />
                        <div>
                          <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>
                            {sat.name}
                          </div>
                          <div style={{ fontSize: 10, color: '#94a3b8' }}>
                            #{sat.id} • {sat.altitudeKm} km
                          </div>
                        </div>
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <span 
                          style={{
                            fontSize: 9,
                            fontWeight: 700,
                            padding: '2px 5px',
                            borderRadius: 3,
                            color: tier.color,
                            background: 'rgba(0, 0, 0, 0.3)',
                            border: `1px solid ${tier.border}`
                          }}
                        >
                          {sat.risk}
                        </span>
                        <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }} className="mono">
                          {sat.missDistanceM < 1000 ? `${sat.missDistanceM}m` : `${(sat.missDistanceM/1000).toFixed(1)}km`}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Floating Detailed Telemetry Inspection Panel */}
          {selectedSat && (
            <div 
              className="glass-panel"
              style={{
                position: 'absolute',
                top: 92,
                right: 20,
                width: 330,
                zIndex: 30,
                padding: 18,
                borderTop: `4px solid ${RISK_TIERS[selectedSat.risk].color}`,
                boxShadow: `0 15px 35px rgba(0, 0, 0, 0.6)`
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <h3 style={{ fontSize: 16, fontWeight: 800, color: '#f8fafc', margin: 0 }}>
                      {selectedSat.name}
                    </h3>
                    <span 
                      style={{
                        fontSize: 9,
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: 4,
                        color: '#ffffff',
                        background: RISK_TIERS[selectedSat.risk].color
                      }}
                    >
                      {selectedSat.risk}
                    </span>
                  </div>
                  <p style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
                    {selectedSat.operator} • NORAD #{selectedSat.id}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedSat(null)}
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

              {/* Quick Metrics */}
              <div 
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(2, 1fr)',
                  gap: 8,
                  marginBottom: 12
                }}
              >
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Orbital Altitude</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                    {selectedSat.altitudeKm} km
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Inclination</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                    {selectedSat.inclinationDeg}°
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Velocity</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                    {selectedSat.velocityKmS} km/s
                  </div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px 10px', borderRadius: 6 }}>
                  <div style={{ fontSize: 10, color: '#64748b' }}>Time to TCA</div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc', marginTop: 1 }} className="mono">
                    T-{selectedSat.timeToTcaHours}h
                  </div>
                </div>
              </div>

              {/* Threat Box */}
              <div 
                style={{
                  background: RISK_TIERS[selectedSat.risk].badgeBg,
                  border: `1px solid ${RISK_TIERS[selectedSat.risk].border}`,
                  borderRadius: 8,
                  padding: 12,
                  marginBottom: 12
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <AlertTriangle size={14} color={RISK_TIERS[selectedSat.risk].color} />
                  <span style={{ fontSize: 10, fontWeight: 700, color: RISK_TIERS[selectedSat.risk].color }}>
                    APPROACHING THREAT
                  </span>
                </div>
                <div style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>
                  {selectedSat.closestDebris}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 11 }}>
                  <span style={{ color: '#94a3b8' }}>Miss Distance:</span>
                  <span style={{ fontWeight: 700, color: '#f8fafc' }} className="mono">
                    {selectedSat.missDistanceM} meters
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3, fontSize: 11 }}>
                  <span style={{ color: '#94a3b8' }}>Collision Prob (Pc):</span>
                  <span style={{ fontWeight: 700, color: RISK_TIERS[selectedSat.risk].color }} className="mono">
                    {selectedSat.poc}
                  </span>
                </div>
              </div>

              {/* Decision */}
              <div style={{ background: 'rgba(0,0,0,0.25)', borderRadius: 8, padding: 12 }}>
                <div style={{ fontSize: 10, color: '#64748b', marginBottom: 4 }}>
                  DECISION ENGINE (THRESHOLD 1E-4)
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  {selectedSat.maneuverRequired ? (
                    <>
                      <ShieldAlert size={16} color="#dc2626" />
                      <span style={{ fontSize: 12, fontWeight: 800, color: '#f87171' }}>
                        MANEUVER RECOMMENDED
                      </span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={16} color="#10b981" />
                      <span style={{ fontSize: 12, fontWeight: 800, color: '#34d399' }}>
                        HOLD (ZERO ACTION)
                      </span>
                    </>
                  )}
                </div>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>
                  <strong>Prescribed Burn:</strong> {selectedSat.suggestedBurn}
                </div>
              </div>

              {/* Quick Actions to Switch Views */}
              <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <button
                  onClick={() => {
                    setActiveAnalysisEvent(selectedSat);
                    setCurrentView('ANALYSIS');
                  }}
                  style={{
                    flex: 1,
                    background: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid rgba(255, 255, 255, 0.18)',
                    color: '#f8fafc',
                    padding: '8px 10px',
                    borderRadius: 6,
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  Inspect XAI & SHAP
                </button>
                {selectedSat.maneuverRequired && (
                  <button
                    onClick={() => {
                      setActiveAnalysisEvent(selectedSat);
                      setCurrentView('MANEUVER');
                    }}
                    style={{
                      flex: 1,
                      background: 'rgba(220, 38, 38, 0.2)',
                      border: '1px solid #dc2626',
                      color: '#f87171',
                      padding: '8px 10px',
                      borderRadius: 6,
                      fontSize: 11,
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    Optimize Δv
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Bottom Dock Controls */}
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
              gap: 14,
              padding: '8px 18px'
            }}
          >
            <button
              onClick={() => setAutoRotate(!autoRotate)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: autoRotate ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.04)',
                border: autoRotate ? '1px solid rgba(255, 255, 255, 0.25)' : '1px solid rgba(255, 255, 255, 0.08)',
                color: autoRotate ? '#f8fafc' : '#94a3b8',
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <RotateCw size={13} />
              {autoRotate ? 'Auto-Rotate ON' : 'Paused'}
            </button>

            <button
              onClick={() => setShowOrbits(!showOrbits)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: showOrbits ? 'rgba(255, 255, 255, 0.12)' : 'rgba(255, 255, 255, 0.04)',
                border: showOrbits ? '1px solid rgba(255, 255, 255, 0.25)' : '1px solid rgba(255, 255, 255, 0.08)',
                color: showOrbits ? '#f8fafc' : '#94a3b8',
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {showOrbits ? <Eye size={13} /> : <EyeOff size={13} />}
              {showOrbits ? 'Orbits Visible' : 'Orbits Hidden'}
            </button>

            <span style={{ width: 1, height: 16, background: 'rgba(255, 255, 255, 0.1)' }} />

            <div style={{ fontSize: 11, color: '#64748b', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Compass size={12} />
              Drag to rotate • Scroll to zoom • Click satellite to inspect
            </div>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* VIEW 2: 72-HOUR SCREENING VIEW                                 */}
      {/* ============================================================== */}
      {currentView === 'SCREENING' && (
        <ScreeningView 
          onSelectSatelliteForAnalysis={handleSelectSatelliteForAnalysis}
          onSelectSatelliteForManeuver={handleSelectSatelliteForManeuver}
        />
      )}

      {/* ============================================================== */}
      {/* VIEW 3: ML RISK & SHAP XAI ANALYSIS VIEW                       */}
      {/* ============================================================== */}
      {currentView === 'ANALYSIS' && (
        <AnalysisView 
          event={activeAnalysisEvent}
          onNavigateToManeuver={handleSelectSatelliteForManeuver}
        />
      )}

      {/* ============================================================== */}
      {/* VIEW 4: COLLISION AVOIDANCE MANEUVER (CAM) VIEW                */}
      {/* ============================================================== */}
      {currentView === 'MANEUVER' && (
        <ManeuverView 
          event={activeAnalysisEvent}
        />
      )}

      {/* ============================================================== */}
      {/* VIEW 5: ESA KELVINS BENCHMARK VALIDATION VIEW                  */}
      {/* ============================================================== */}
      {currentView === 'BENCHMARK' && (
        <BenchmarkView />
      )}

    </div>
  );
}
