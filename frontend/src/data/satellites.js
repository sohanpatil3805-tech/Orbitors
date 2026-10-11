export const RISK_TIERS = {
  EXTREME: {
    key: "EXTREME",
    label: "Extreme Risk",
    color: "#dc2626", // Deep warning red
    glowColor: "rgba(0, 0, 0, 0.4)",
    badgeBg: "rgba(220, 38, 38, 0.12)",
    border: "rgba(220, 38, 38, 0.3)",
    description: "Collision probability Pc ≥ 1E-4. Immediate operator maneuver decision required."
  },
  HIGH: {
    key: "HIGH",
    label: "High Risk",
    color: "#f97316", // Amber / Flame
    glowColor: "rgba(0, 0, 0, 0.4)",
    badgeBg: "rgba(249, 115, 22, 0.12)",
    border: "rgba(249, 115, 22, 0.3)",
    description: "Close pass (300-600m). Radial covariance narrowing. Prepare contingency burn."
  },
  MEDIUM: {
    key: "MEDIUM",
    label: "Medium Risk",
    color: "#eab308", // Yellow / Warning
    glowColor: "rgba(0, 0, 0, 0.4)",
    badgeBg: "rgba(234, 179, 8, 0.12)",
    border: "rgba(234, 179, 8, 0.3)",
    description: "Pass clearance 1-2 km. Track radar updates on next orbit pass."
  },
  LOW: {
    key: "LOW",
    label: "Low Risk",
    color: "#10b981", // Emerald green
    glowColor: "rgba(0, 0, 0, 0.4)",
    badgeBg: "rgba(16, 185, 129, 0.12)",
    border: "rgba(16, 185, 129, 0.3)",
    description: "Clearance > 4 km. Nominal trajectory with zero threat of conjunction."
  }
};

export const SATELLITES_DATA = [
  // 1. EXTREME RISK (Dark Red)
  {
    id: 25544,
    name: "ISS (ZARYA)",
    operator: "NASA / International",
    intlDesignator: "1998-067A",
    risk: "EXTREME",
    altitudeKm: 418,
    inclinationDeg: 51.64,
    velocityKmS: 7.66,
    closestDebris: "COSMOS 2251 DEBRIS (#142)",
    missDistanceM: 142.0,
    poc: "2.84E-04",
    timeToTcaHours: 36.2,
    maneuverRequired: true,
    suggestedBurn: "+0.52 m/s Along-Track",
    orbitRadiusScale: 1.15, // Relative scale for 3D view
    orbitSpeed: 0.0018
  },
  {
    id: 48274,
    name: "TIANGONG (CSS)",
    operator: "CNSA (China)",
    intlDesignator: "2021-035A",
    risk: "EXTREME",
    altitudeKm: 390,
    inclinationDeg: 41.47,
    velocityKmS: 7.68,
    closestDebris: "IRIDIUM 33 DEBRIS (#89)",
    missDistanceM: 290.0,
    poc: "1.42E-04",
    timeToTcaHours: 31.0,
    maneuverRequired: true,
    suggestedBurn: "+0.45 m/s Retrograde",
    orbitRadiusScale: 1.12,
    orbitSpeed: 0.002
  },

  // 2. HIGH RISK (Orange)
  {
    id: 44713,
    name: "STARLINK-1007",
    operator: "SpaceX",
    intlDesignator: "2019-074A",
    risk: "HIGH",
    altitudeKm: 550,
    inclinationDeg: 53.05,
    velocityKmS: 7.59,
    closestDebris: "SL-16 UPPER STAGE",
    missDistanceM: 420.0,
    poc: "4.50E-05",
    timeToTcaHours: 48.4,
    maneuverRequired: false,
    suggestedBurn: "Contingency Standby",
    orbitRadiusScale: 1.25,
    orbitSpeed: 0.0015
  },
  {
    id: 45145,
    name: "ONEWEB-0145",
    operator: "Eutelsat OneWeb",
    intlDesignator: "2020-008B",
    risk: "HIGH",
    altitudeKm: 1200,
    inclinationDeg: 87.9,
    velocityKmS: 7.26,
    closestDebris: "FENGYUN-1C FRAGMENT",
    missDistanceM: 560.0,
    poc: "3.80E-05",
    timeToTcaHours: 54.2,
    maneuverRequired: false,
    suggestedBurn: "Radar Tracking Active",
    orbitRadiusScale: 1.45,
    orbitSpeed: 0.0011
  },

  // 3. MEDIUM RISK (Yellow)
  {
    id: 20580,
    name: "HUBBLE TELESCOPE",
    operator: "NASA / ESA",
    intlDesignator: "1990-037B",
    risk: "MEDIUM",
    altitudeKm: 535,
    inclinationDeg: 28.47,
    velocityKmS: 7.59,
    closestDebris: "CZ-4B ROCKET BODY",
    missDistanceM: 1120.0,
    poc: "8.20E-06",
    timeToTcaHours: 62.0,
    maneuverRequired: false,
    suggestedBurn: "None (Hold)",
    orbitRadiusScale: 1.22,
    orbitSpeed: 0.0016
  },
  {
    id: 25994,
    name: "TERRA (EOS AM-1)",
    operator: "NASA",
    intlDesignator: "1999-068A",
    risk: "MEDIUM",
    altitudeKm: 705,
    inclinationDeg: 98.2,
    velocityKmS: 7.51,
    closestDebris: "ENVISAT DEBRIS",
    missDistanceM: 1480.0,
    poc: "5.10E-06",
    timeToTcaHours: 68.5,
    maneuverRequired: false,
    suggestedBurn: "None (Hold)",
    orbitRadiusScale: 1.32,
    orbitSpeed: 0.0013
  },

  // 4. LOW RISK (Emerald Green)
  {
    id: 39634,
    name: "SENTINEL-1A",
    operator: "ESA (Copernicus)",
    intlDesignator: "2014-016A",
    risk: "LOW",
    altitudeKm: 693,
    inclinationDeg: 98.18,
    velocityKmS: 7.51,
    closestDebris: "NONE (Corridor Safe)",
    missDistanceM: 4800.0,
    poc: "1.20E-07",
    timeToTcaHours: 72.0,
    maneuverRequired: false,
    suggestedBurn: "None (Nominal Science)",
    orbitRadiusScale: 1.3,
    orbitSpeed: 0.0014
  },
  {
    id: 49260,
    name: "LANDSAT-9",
    operator: "USGS / NASA",
    intlDesignator: "2021-088A",
    risk: "LOW",
    altitudeKm: 705,
    inclinationDeg: 98.2,
    velocityKmS: 7.50,
    closestDebris: "NONE (Corridor Safe)",
    missDistanceM: 6200.0,
    poc: "< 1.0E-08",
    timeToTcaHours: 72.0,
    maneuverRequired: false,
    suggestedBurn: "None (Nominal Science)",
    orbitRadiusScale: 1.31,
    orbitSpeed: 0.0013
  },
  {
    id: 43013,
    name: "NOAA-20 (JPSS-1)",
    operator: "NOAA",
    intlDesignator: "2017-073A",
    risk: "LOW",
    altitudeKm: 824,
    inclinationDeg: 98.7,
    velocityKmS: 7.44,
    closestDebris: "NONE (Corridor Safe)",
    missDistanceM: 8500.0,
    poc: "< 1.0E-08",
    timeToTcaHours: 72.0,
    maneuverRequired: false,
    suggestedBurn: "None (Nominal Science)",
    orbitRadiusScale: 1.36,
    orbitSpeed: 0.0012
  }
];
