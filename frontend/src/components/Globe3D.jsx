import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RISK_TIERS } from '../data/satellites';

// ============================================================================
// Procedural Canvas Texture Generators for Solar Planets & Celestial Bodies
// ============================================================================

function createSunTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, '#f59e0b');
  grad.addColorStop(0.5, '#d97706');
  grad.addColorStop(1, '#f59e0b');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 512, 256);
  for (let i = 0; i < 1500; i++) {
    ctx.beginPath();
    ctx.arc(Math.random() * 512, Math.random() * 256, Math.random() * 6 + 1, 0, Math.PI * 2);
    ctx.fillStyle = Math.random() > 0.5 ? 'rgba(254, 240, 138, 0.4)' : 'rgba(180, 83, 9, 0.45)';
    ctx.fill();
  }
  return new THREE.CanvasTexture(canvas);
}

function createMoonTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#94a3b8';
  ctx.fillRect(0, 0, 256, 128);
  // Lunar Maria
  const maria = [{ x: 70, y: 50, r: 24 }, { x: 130, y: 45, r: 28 }, { x: 160, y: 70, r: 22 }];
  maria.forEach(m => {
    ctx.beginPath();
    ctx.arc(m.x, m.y, m.r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(30, 41, 59, 0.6)';
    ctx.fill();
  });
  for (let i = 0; i < 300; i++) {
    ctx.beginPath();
    ctx.arc(Math.random() * 256, Math.random() * 128, Math.random() * 3 + 1, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(241, 245, 249, 0.35)';
    ctx.fill();
  }
  return new THREE.CanvasTexture(canvas);
}

function createMarsTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#c2410c';
  ctx.fillRect(0, 0, 512, 256);
  for (let i = 0; i < 600; i++) {
    ctx.beginPath();
    ctx.arc(Math.random() * 512, Math.random() * 256, Math.random() * 8 + 2, 0, Math.PI * 2);
    ctx.fillStyle = Math.random() > 0.6 ? 'rgba(124, 45, 18, 0.4)' : 'rgba(234, 88, 12, 0.35)';
    ctx.fill();
  }
  // Polar Ice Caps
  ctx.fillStyle = '#f8fafc';
  ctx.fillRect(0, 0, 512, 14);
  ctx.fillRect(0, 242, 512, 14);
  return new THREE.CanvasTexture(canvas);
}

function createJupiterTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  const bands = ['#78350f', '#b45309', '#d97706', '#fef3c7', '#d97706', '#92400e', '#451a03', '#b45309', '#fef3c7', '#78350f'];
  const h = 256 / bands.length;
  bands.forEach((c, i) => {
    ctx.fillStyle = c;
    ctx.fillRect(0, i * h, 512, h);
  });
  // Great Red Spot
  ctx.beginPath();
  ctx.ellipse(160, 160, 28, 16, 0, 0, Math.PI * 2);
  ctx.fillStyle = '#b91c1c';
  ctx.fill();
  return new THREE.CanvasTexture(canvas);
}

function createSaturnTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');
  const bands = ['#ca8a04', '#eab308', '#fef08a', '#eab308', '#ca8a04'];
  const h = 128 / bands.length;
  bands.forEach((c, i) => {
    ctx.fillStyle = c;
    ctx.fillRect(0, i * h, 256, h);
  });
  return new THREE.CanvasTexture(canvas);
}

function createSaturnRingsTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 64;
  const ctx = canvas.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 512, 0);
  grad.addColorStop(0.0, 'rgba(254, 240, 138, 0.1)');
  grad.addColorStop(0.2, 'rgba(202, 138, 4, 0.85)');
  grad.addColorStop(0.48, 'rgba(234, 179, 8, 0.9)');
  grad.addColorStop(0.55, 'rgba(0, 0, 0, 0.05)'); // Cassini division
  grad.addColorStop(0.65, 'rgba(161, 98, 7, 0.7)');
  grad.addColorStop(1.0, 'rgba(0, 0, 0, 0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 512, 64);
  return new THREE.CanvasTexture(canvas);
}

function createVenusTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 128);
  grad.addColorStop(0, '#eab308');
  grad.addColorStop(0.5, '#ca8a04');
  grad.addColorStop(1, '#eab308');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 256, 128);
  return new THREE.CanvasTexture(canvas);
}

function createBillboardLabel(text, color = '#38bdf8', scale = [3.2, 0.82, 1]) {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'rgba(8, 14, 28, 0.88)';
  if (ctx.roundRect) {
    ctx.roundRect(8, 8, 240, 48, 8);
  } else {
    ctx.rect(8, 8, 240, 48);
  }
  ctx.fill();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.stroke();

  ctx.font = 'bold 21px Inter, sans-serif';
  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 128, 32);

  const texture = new THREE.CanvasTexture(canvas);
  const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(scale[0], scale[1], scale[2]);
  return sprite;
}

// ============================================================================
// FLEET GEOMETRY (live satellites from the API → stylised scene orbits)
// ============================================================================

// Altitude (km) → scene radius. Exaggerated so LEO shells separate visibly around the 4.85-unit Earth.
function sceneOrbitRadius(sat, index) {
  const alt = Number.isFinite(sat.altitudeKm) ? sat.altitudeKm : 500;
  const t = Math.min(Math.max((alt - 350) / 1000, 0), 1);
  return 5.6 + t * 4.0 + (index % 3) * 0.06;
}

// Point on a circular orbit: inclination about the x axis, then RAAN about the (up) y axis.
function orbitPosition(radius, inc, raan, angle) {
  const x = radius * Math.cos(angle);
  const y = radius * Math.sin(angle) * Math.sin(inc);
  const z = radius * Math.sin(angle) * Math.cos(inc);
  return new THREE.Vector3(x * Math.cos(raan) + z * Math.sin(raan), y, -x * Math.sin(raan) + z * Math.cos(raan));
}

function disposeGroup(group) {
  while (group.children.length) {
    const child = group.children[group.children.length - 1];
    group.remove(child);
    child.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) => m.dispose());
    });
  }
}

// Helper to construct realistic satellite spacecraft
function createRealisticSatellite(sat, tier) {
  const satGroup = new THREE.Group();
  satGroup.userData = { satData: sat };
  const riskColor = new THREE.Color(tier.color);

  // Chassis
  const busGeo = new THREE.BoxGeometry(0.36, 0.28, 0.46);
  const busMat = new THREE.MeshStandardMaterial({
    color: 0xf1f5f9,
    metalness: 0.90,
    roughness: 0.20
  });
  const bus = new THREE.Mesh(busGeo, busMat);
  satGroup.add(bus);

  // MLI Gold Foil
  const mliGeo = new THREE.BoxGeometry(0.364, 0.05, 0.464);
  const mliMat = new THREE.MeshStandardMaterial({
    color: 0xd97706,
    metalness: 0.95,
    roughness: 0.28
  });
  const mliTop = new THREE.Mesh(mliGeo, mliMat);
  mliTop.position.set(0, 0.13, 0);
  satGroup.add(mliTop);

  // Risk status band
  const statusBandGeo = new THREE.BoxGeometry(0.37, 0.13, 0.47);
  const statusBandMat = new THREE.MeshStandardMaterial({
    color: riskColor,
    roughness: 0.35,
    metalness: 0.4
  });
  const statusBand = new THREE.Mesh(statusBandGeo, statusBandMat);
  satGroup.add(statusBand);

  // Solar Panels
  const panelLength = 0.95;
  const panelWidth = 0.38;
  const panelThickness = 0.025;

  const createSolarWing = (side) => {
    const wingGroup = new THREE.Group();
    const boomGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.25, 8);
    const boomMat = new THREE.MeshStandardMaterial({ color: 0x64748b, metalness: 0.8 });
    const boom = new THREE.Mesh(boomGeo, boomMat);
    boom.rotation.z = Math.PI / 2;
    boom.position.set(side * 0.125, 0, 0);
    wingGroup.add(boom);

    const wingGeo = new THREE.BoxGeometry(panelLength, panelWidth, panelThickness);
    const wingMat = new THREE.MeshStandardMaterial({
      color: 0x0284c7,
      metalness: 0.85,
      roughness: 0.25
    });
    const wing = new THREE.Mesh(wingGeo, wingMat);
    wing.position.set(side * (0.25 + panelLength / 2), 0, 0);
    wingGroup.add(wing);

    // Grid lines
    for (let i = 1; i <= 3; i++) {
      const seamGeo = new THREE.BoxGeometry(0.015, panelWidth * 0.95, panelThickness + 0.005);
      const seamMat = new THREE.MeshBasicMaterial({ color: 0x0f172a });
      const seam = new THREE.Mesh(seamGeo, seamMat);
      seam.position.set(side * (0.25 + (panelLength / 4) * i), 0, 0);
      wingGroup.add(seam);
    }
    return wingGroup;
  };

  satGroup.add(createSolarWing(1));
  satGroup.add(createSolarWing(-1));

  // Parabolic Dish
  const dishGeo = new THREE.SphereGeometry(0.22, 16, 8, 0, Math.PI * 2, 0, Math.PI / 3);
  const dishMat = new THREE.MeshStandardMaterial({
    color: 0xe2e8f0,
    metalness: 0.95,
    roughness: 0.2,
    side: THREE.DoubleSide
  });
  const dish = new THREE.Mesh(dishGeo, dishMat);
  dish.position.set(0, 0.22, 0.12);
  dish.rotation.x = -Math.PI / 3;
  satGroup.add(dish);

  // Thruster
  const thrusterGeo = new THREE.ConeGeometry(0.12, 0.22, 12, 1, true);
  const thrusterMat = new THREE.MeshStandardMaterial({
    color: 0x334155,
    side: THREE.DoubleSide,
    metalness: 0.95,
    roughness: 0.3
  });
  const thruster = new THREE.Mesh(thrusterGeo, thrusterMat);
  thruster.rotation.x = Math.PI / 2;
  thruster.position.set(0, 0, -0.27);
  satGroup.add(thruster);

  const thrusterGlowGeo = new THREE.SphereGeometry(0.035, 8, 8);
  const thrusterGlowMat = new THREE.MeshBasicMaterial({ color: riskColor });
  const thrusterGlow = new THREE.Mesh(thrusterGlowGeo, thrusterGlowMat);
  thrusterGlow.position.set(0, 0, -0.20);
  satGroup.add(thrusterGlow);

  return satGroup;
}

// ============================================================================
// MAIN GLOBE COMPONENT
// ============================================================================

export default function Globe3D({ 
  satellites = [],
  selectedSatellite, 
  onSelectSatellite, 
  filterRisk,
  showOrbits = true,
  autoRotate = true,
  cameraMode = 'SOLAR'
}) {
  const mountRef = useRef(null);
  const [hoveredSat, setHoveredSat] = useState(null);
  const [hoveredPlanet, setHoveredPlanet] = useState(null);

  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const earthGroupRef = useRef(null);
  const starsRef = useRef(null);
  const orbitsGroupRef = useRef(null);
  const satellitesGroupRef = useRef(null);
  const satMeshesRef = useRef([]);
  const planetMeshesRef = useRef([]);
  const moonPivotRef = useRef(null);
  const planetsGroupRef = useRef(null);
  const targetCamPosRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene & Centered Camera (Framing Earth & surrounding Solar Planets)
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 2000);
    camera.position.set(0, 24, 70);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // 2. WebGL Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.10;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 3. OrbitControls (Smooth zoom from Low Earth Orbit up to outer Solar System)
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enablePan = false; // Keeps Earth anchored dead-center
    controls.minDistance = 6.8;
    controls.maxDistance = 250.0; // Allows zooming out to view full Solar System
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 0.4;
    controlsRef.current = controls;

    // 4. Natural Lighting (Deep space realistic sun & ambient)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.70);
    scene.add(ambientLight);

    // Warm, realistic sunlight facing Earth from the Sun's position in deep space
    const sunLight = new THREE.DirectionalLight(0xfffaed, 2.4);
    sunLight.position.set(54, 26, -42);
    scene.add(sunLight);

    // Subtle neutral dark-side fill
    const spaceFillLight = new THREE.DirectionalLight(0x334155, 0.40);
    spaceFillLight.position.set(-25, -15, -20);
    scene.add(spaceFillLight);

    // Camera headlight for crisp spacecraft visibility
    const cameraLight = new THREE.DirectionalLight(0xffffff, 0.4);
    camera.add(cameraLight);
    scene.add(camera);

    // 5. Dynamic Deep Space Starfield
    const starsGeo = new THREE.BufferGeometry();
    const starCount = 2800;
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = 240 + Math.random() * 200; // Deep distant backdrop
      const sinPhi = Math.sin(phi);
      starPositions[i] = r * sinPhi * Math.cos(theta);
      starPositions[i + 1] = r * sinPhi * Math.sin(theta);
      starPositions[i + 2] = r * Math.cos(phi);
    }
    starsGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));

    const starCanvas = document.createElement('canvas');
    starCanvas.width = 32;
    starCanvas.height = 32;
    const starCtx = starCanvas.getContext('2d');
    const grad = starCtx.createRadialGradient(16, 16, 0, 16, 16, 16);
    grad.addColorStop(0, 'rgba(255, 255, 255, 1)');
    grad.addColorStop(0.3, 'rgba(224, 238, 255, 0.85)');
    grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
    starCtx.fillStyle = grad;
    starCtx.fillRect(0, 0, 32, 32);
    const starTexture = new THREE.CanvasTexture(starCanvas);

    const starsMat = new THREE.PointsMaterial({ 
      map: starTexture,
      size: 2.0, 
      transparent: true, 
      opacity: 0.85,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    const starField = new THREE.Points(starsGeo, starsMat);
    starsRef.current = starField;
    scene.add(starField);

    // ========================================================================
    // 5.5. SOLAR SYSTEM PLANETS & CELESTIAL BODIES IN OUTER SPACE
    // ========================================================================
    const planetsGroup = new THREE.Group();
    planetsGroupRef.current = planetsGroup;
    scene.add(planetsGroup);

    const planetMeshes = [];

    // Pre-create textures
    const texSun = createSunTexture();
    const texMoon = createMoonTexture();
    const texMars = createMarsTexture();
    const texJupiter = createJupiterTexture();
    const texSaturn = createSaturnTexture();
    const texSaturnRings = createSaturnRingsTexture();
    const texVenus = createVenusTexture();

    // 1. THE SUN (Sol) - The Supreme Luminary in Deep Space (Believably the largest body)
    const sunGeo = new THREE.SphereGeometry(8.5, 32, 32);
    const sunMat = new THREE.MeshBasicMaterial({ map: texSun });
    const sunMesh = new THREE.Mesh(sunGeo, sunMat);
    sunMesh.position.set(54, 26, -42);
    sunMesh.userData = {
      planetData: {
        id: 'sun',
        name: 'The Sun (Sol)',
        type: 'Yellow Dwarf Star (G2V)',
        distance: '1.0 AU (149.6M km)',
        color: '#f59e0b',
        diameter: '1,392,700 km'
      }
    };
    // Glowing corona aura
    const coronaGeo = new THREE.SphereGeometry(11.5, 32, 32);
    const coronaMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.28, side: THREE.BackSide });
    sunMesh.add(new THREE.Mesh(coronaGeo, coronaMat));
    const sunLabel = createBillboardLabel('THE SUN ☀️', '#f59e0b', [6.8, 1.7, 1]);
    sunLabel.position.set(0, 11.2, 0);
    sunMesh.add(sunLabel);
    planetsGroup.add(sunMesh);
    planetMeshes.push(sunMesh);

    // 2. THE MOON (Luna - Orbiting Earth outside satellite zone)
    const moonPivot = new THREE.Group();
    moonPivotRef.current = moonPivot;
    scene.add(moonPivot);

    const moonOrbitR = 12.0;
    const moonGeo = new THREE.SphereGeometry(0.85, 24, 24);
    const moonMat = new THREE.MeshStandardMaterial({ map: texMoon, roughness: 0.8 });
    const moonMesh = new THREE.Mesh(moonGeo, moonMat);
    moonMesh.position.set(moonOrbitR, 0, 0);
    moonMesh.userData = {
      planetData: {
        id: 'moon',
        name: 'The Moon (Luna)',
        type: 'Natural Satellite',
        distance: '384,400 km from Earth',
        color: '#cbd5e1',
        diameter: '3,474 km'
      }
    };
    const moonLabel = createBillboardLabel('MOON 🌕', '#cbd5e1', [4.2, 1.05, 1]);
    moonLabel.position.set(0, 1.45, 0);
    moonMesh.add(moonLabel);
    moonPivot.add(moonMesh);
    planetMeshes.push(moonMesh);

    // Moon Orbit Line circling Earth
    const moonOrbitPts = [];
    for (let i = 0; i <= 64; i++) {
      const th = (i / 64) * Math.PI * 2;
      moonOrbitPts.push(new THREE.Vector3(Math.cos(th) * moonOrbitR, 0, Math.sin(th) * moonOrbitR));
    }
    const moonOrbitLine = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(moonOrbitPts),
      new THREE.LineBasicMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.25 })
    );
    scene.add(moonOrbitLine);

    // 3. MERCURY (Smallest Terrestrial Planet)
    const mercGeo = new THREE.SphereGeometry(1.0, 24, 24);
    const mercMat = new THREE.MeshStandardMaterial({ color: 0xa1a1aa, roughness: 0.8 });
    const mercMesh = new THREE.Mesh(mercGeo, mercMat);
    mercMesh.position.set(28, 14, -22);
    mercMesh.userData = {
      planetData: {
        id: 'mercury',
        name: 'Mercury',
        type: 'Terrestrial Planet',
        distance: '0.39 AU from Sun',
        color: '#94a3b8',
        diameter: '4,879 km'
      }
    };
    const mercLabel = createBillboardLabel('MERCURY ☿', '#94a3b8', [4.4, 1.1, 1]);
    mercLabel.position.set(0, 1.7, 0);
    mercMesh.add(mercLabel);
    planetsGroup.add(mercMesh);
    planetMeshes.push(mercMesh);

    // 4. VENUS (Earth-Sized Shimmering Golden Atmosphere)
    const venusGeo = new THREE.SphereGeometry(1.85, 28, 28);
    const venusMat = new THREE.MeshStandardMaterial({ map: texVenus, roughness: 0.7 });
    const venusMesh = new THREE.Mesh(venusGeo, venusMat);
    venusMesh.position.set(-32, 16, -18);
    venusMesh.userData = {
      planetData: {
        id: 'venus',
        name: 'Venus',
        type: 'Terrestrial Planet (Twin)',
        distance: '0.72 AU from Sun',
        color: '#eab308',
        diameter: '12,104 km'
      }
    };
    const venusLabel = createBillboardLabel('VENUS ♀', '#eab308', [4.6, 1.15, 1]);
    venusLabel.position.set(0, 2.6, 0);
    venusMesh.add(venusLabel);
    planetsGroup.add(venusMesh);
    planetMeshes.push(venusMesh);

    // 5. MARS (The Red Planet with Polar Ice Caps)
    const marsGeo = new THREE.SphereGeometry(1.35, 28, 28);
    const marsMat = new THREE.MeshStandardMaterial({ map: texMars, roughness: 0.75 });
    const marsMesh = new THREE.Mesh(marsGeo, marsMat);
    marsMesh.position.set(34, -14, 22);
    marsMesh.userData = {
      planetData: {
        id: 'mars',
        name: 'Mars (The Red Planet)',
        type: 'Terrestrial Planet',
        distance: '1.52 AU from Sun',
        color: '#ef4444',
        diameter: '6,779 km'
      }
    };
    const marsLabel = createBillboardLabel('MARS ♂', '#ef4444', [4.4, 1.1, 1]);
    marsLabel.position.set(0, 2.1, 0);
    marsMesh.add(marsLabel);
    planetsGroup.add(marsMesh);
    planetMeshes.push(marsMesh);

    // 6. ASTEROID BELT (Floating orbital belt between Mars and Jupiter)
    const asteroidGeo = new THREE.BufferGeometry();
    const astCount = 700;
    const astPos = new Float32Array(astCount * 3);
    for (let i = 0; i < astCount * 3; i += 3) {
      const r = 46.0 + (Math.random() - 0.5) * 6.0;
      const th = Math.random() * Math.PI * 2;
      astPos[i] = Math.cos(th) * r;
      astPos[i + 1] = (Math.random() - 0.5) * 4.0;
      astPos[i + 2] = Math.sin(th) * r;
    }
    asteroidGeo.setAttribute('position', new THREE.BufferAttribute(astPos, 3));
    const asteroidBelt = new THREE.Points(
      asteroidGeo,
      new THREE.PointsMaterial({ 
        map: starTexture, 
        size: 0.45, 
        transparent: true, 
        opacity: 0.35, 
        depthWrite: false 
      })
    );
    planetsGroup.add(asteroidBelt);

    // 7. JUPITER (King of Planets - Largest Gas Giant with Great Red Spot & Moons)
    const jupGeo = new THREE.SphereGeometry(4.5, 32, 32);
    const jupMat = new THREE.MeshStandardMaterial({ map: texJupiter, roughness: 0.65 });
    const jupMesh = new THREE.Mesh(jupGeo, jupMat);
    jupMesh.position.set(-52, -22, 36);
    jupMesh.userData = {
      planetData: {
        id: 'jupiter',
        name: 'Jupiter (Gas Giant)',
        type: 'Gas Giant (King)',
        distance: '5.20 AU from Sun',
        color: '#d97706',
        diameter: '139,820 km'
      }
    };
    // Galilean moons around Jupiter
    const createMiniMoon = (dist, color) => {
      const m = new THREE.Mesh(
        new THREE.SphereGeometry(0.18, 12, 12),
        new THREE.MeshStandardMaterial({ color: color })
      );
      m.position.set(dist, 0, 0);
      return m;
    };
    jupMesh.add(createMiniMoon(6.0, 0xfacc15)); // Io
    jupMesh.add(createMiniMoon(7.5, 0xe2e8f0)); // Europa
    jupMesh.add(createMiniMoon(9.2, 0x94a3b8)); // Ganymede
    jupMesh.add(createMiniMoon(11.0, 0x64748b)); // Callisto

    const jupLabel = createBillboardLabel('JUPITER ♃', '#d97706', [6.0, 1.5, 1]);
    jupLabel.position.set(0, 5.8, 0);
    jupMesh.add(jupLabel);
    planetsGroup.add(jupMesh);
    planetMeshes.push(jupMesh);

    // 8. SATURN (Ringed Jewel - Second Largest Gas Giant)
    const saturnGeo = new THREE.SphereGeometry(3.6, 32, 32);
    const saturnMat = new THREE.MeshStandardMaterial({ map: texSaturn, roughness: 0.7 });
    const saturnMesh = new THREE.Mesh(saturnGeo, saturnMat);
    saturnMesh.position.set(-58, 28, -44);
    saturnMesh.userData = {
      planetData: {
        id: 'saturn',
        name: 'Saturn (Ringed Jewel)',
        type: 'Gas Giant',
        distance: '9.58 AU from Sun',
        color: '#facc15',
        diameter: '116,460 km'
      }
    };
    // 3D Planetary Ring
    const ringGeo = new THREE.RingGeometry(4.8, 8.6, 64);
    const ringPos = ringGeo.attributes.position;
    const ringUvs = ringGeo.attributes.uv;
    for (let i = 0; i < ringPos.count; i++) {
      const v = new THREE.Vector2(ringPos.getX(i), ringPos.getY(i));
      ringUvs.setXY(i, (v.length() - 4.8) / (8.6 - 4.8), 0.5);
    }
    const ringMat = new THREE.MeshBasicMaterial({
      map: texSaturnRings,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.90
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = Math.PI / 2;
    ringMesh.rotation.y = THREE.MathUtils.degToRad(26.7);
    saturnMesh.add(ringMesh);

    const saturnLabel = createBillboardLabel('SATURN ♄', '#facc15', [5.8, 1.45, 1]);
    saturnLabel.position.set(0, 5.0, 0);
    saturnMesh.add(saturnLabel);
    planetsGroup.add(saturnMesh);
    planetMeshes.push(saturnMesh);

    // 9. URANUS (Ice Giant with Faint Vertical Ring)
    const uranusGeo = new THREE.SphereGeometry(2.4, 28, 28);
    const uranusMat = new THREE.MeshStandardMaterial({ color: 0x67e8f9, roughness: 0.65 });
    const uranusMesh = new THREE.Mesh(uranusGeo, uranusMat);
    uranusMesh.position.set(64, -28, -38);
    uranusMesh.userData = {
      planetData: {
        id: 'uranus',
        name: 'Uranus (Ice Giant)',
        type: 'Ice Giant',
        distance: '19.2 AU from Sun',
        color: '#38bdf8',
        diameter: '50,724 km'
      }
    };
    const uRingGeo = new THREE.RingGeometry(3.0, 3.8, 48);
    const uRingMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide, transparent: true, opacity: 0.35 });
    const uRing = new THREE.Mesh(uRingGeo, uRingMat);
    uRing.rotation.y = Math.PI / 2;
    uranusMesh.add(uRing);

    const uranusLabel = createBillboardLabel('URANUS ♅', '#38bdf8', [5.0, 1.25, 1]);
    uranusLabel.position.set(0, 3.5, 0);
    uranusMesh.add(uranusLabel);
    planetsGroup.add(uranusMesh);
    planetMeshes.push(uranusMesh);

    // 10. NEPTUNE (Deep Azure Blue Ice Giant)
    const nepGeo = new THREE.SphereGeometry(2.3, 28, 28);
    const nepMat = new THREE.MeshStandardMaterial({ color: 0x2563eb, roughness: 0.65 });
    const nepMesh = new THREE.Mesh(nepGeo, nepMat);
    nepMesh.position.set(-68, 24, 52);
    nepMesh.userData = {
      planetData: {
        id: 'neptune',
        name: 'Neptune (Deep Blue)',
        type: 'Ice Giant',
        distance: '30.1 AU from Sun',
        color: '#3b82f6',
        diameter: '49,244 km'
      }
    };
    const nepLabel = createBillboardLabel('NEPTUNE ♆', '#3b82f6', [5.0, 1.25, 1]);
    nepLabel.position.set(0, 3.4, 0);
    nepMesh.add(nepLabel);
    planetsGroup.add(nepMesh);
    planetMeshes.push(nepMesh);

    // 11. PLUTO (Icy Dwarf Planet in Kuiper Belt)
    const plutoGeo = new THREE.SphereGeometry(0.65, 18, 18);
    const plutoMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.8 });
    const plutoMesh = new THREE.Mesh(plutoGeo, plutoMat);
    plutoMesh.position.set(76, 32, 58);
    plutoMesh.userData = {
      planetData: {
        id: 'pluto',
        name: 'Pluto (Dwarf Planet)',
        type: 'Kuiper Belt Object',
        distance: '39.5 AU from Sun',
        color: '#e2e8f0',
        diameter: '2,376 km'
      }
    };
    const plutoLabel = createBillboardLabel('PLUTO ♇', '#e2e8f0', [4.0, 1.0, 1]);
    plutoLabel.position.set(0, 1.2, 0);
    plutoMesh.add(plutoLabel);
    planetsGroup.add(plutoMesh);
    planetMeshes.push(plutoMesh);

    planetMeshesRef.current = planetMeshes;

    // ========================================================================
    // 6. CENTRAL EARTH GLOBE (Strictly Preserved Dead-Center!)
    // ========================================================================
    const EARTH_RADIUS = 4.85;
    const earthGroup = new THREE.Group();
    earthGroup.position.set(0, 0, 0);
    earthGroupRef.current = earthGroup;
    scene.add(earthGroup);

    // NASA Blue Marble Texture
    const textureLoader = new THREE.TextureLoader();
    const earthGeo = new THREE.SphereGeometry(EARTH_RADIUS, 64, 64);

    textureLoader.load(
      '/earth-blue-marble.jpg',
      (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        const earthMat = new THREE.MeshStandardMaterial({
          map: texture,
          metalness: 0.05,
          roughness: 0.60
        });
        const earthMesh = new THREE.Mesh(earthGeo, earthMat);
        earthGroup.add(earthMesh);
      },
      undefined,
      () => {
        const canvas = document.createElement('canvas');
        canvas.width = 1024;
        canvas.height = 512;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#06132b';
        ctx.fillRect(0, 0, 1024, 512);
        ctx.fillStyle = '#0284c7';
        for (let i = 0; i < 200; i++) {
          ctx.beginPath();
          ctx.arc(Math.random() * 1024, Math.random() * 512, Math.random() * 12 + 4, 0, Math.PI * 2);
          ctx.fill();
        }
        const canvasTex = new THREE.CanvasTexture(canvas);
        const fallbackMesh = new THREE.Mesh(earthGeo, new THREE.MeshStandardMaterial({ map: canvasTex }));
        earthGroup.add(fallbackMesh);
      }
    );

    // Thin realistic atmospheric haze hugging Earth's surface
    const atmosphereGeo = new THREE.SphereGeometry(EARTH_RADIUS + 0.06, 64, 64);
    const atmosphereMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.12,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending
    });
    const atmosphereMesh = new THREE.Mesh(atmosphereGeo, atmosphereMat);
    earthGroup.add(atmosphereMesh);

    // ========================================================================
    // 7. ORBITS & SATELLITES GROUPS (Earth-Centered Collision Screening Fleet)
    // ========================================================================
    const orbitsGroup = new THREE.Group();
    orbitsGroup.position.set(0, 0, 0);
    orbitsGroupRef.current = orbitsGroup;
    scene.add(orbitsGroup);

    const satellitesGroup = new THREE.Group();
    satellitesGroup.position.set(0, 0, 0);
    satellitesGroupRef.current = satellitesGroup;
    scene.add(satellitesGroup);


    // Satellites and their orbit lines are built from the `satellites` prop in a separate effect
    satMeshesRef.current = [];

    // 8. Pointer / Raycasting Events (Unified Satellites & Solar Planets)
    const raycaster = new THREE.Raycaster();
    raycaster.params.Line.threshold = 0.5;
    let pointerDownPos = { x: 0, y: 0 };

    const onPointerDown = (e) => {
      pointerDownPos = { x: e.clientX, y: e.clientY };
    };

    const getIntersectedObject = (e) => {
      const rect = container.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera);

      // 1. Check satellites first
      const satIntersects = raycaster.intersectObjects(satMeshesRef.current, true);
      if (satIntersects.length > 0) {
        let obj = satIntersects[0].object;
        while (obj && !obj.userData?.satData && obj.parent) {
          obj = obj.parent;
        }
        if (obj?.userData?.satData) {
          return { type: 'SATELLITE', data: obj.userData.satData };
        }
      }

      // 2. Check solar planets
      const planetIntersects = raycaster.intersectObjects(planetMeshesRef.current, true);
      if (planetIntersects.length > 0) {
        let pObj = planetIntersects[0].object;
        while (pObj && !pObj.userData?.planetData && pObj.parent) {
          pObj = pObj.parent;
        }
        if (pObj?.userData?.planetData) {
          return { type: 'PLANET', data: pObj.userData.planetData };
        }
      }

      return null;
    };

    const onMouseMove = (e) => {
      const hit = getIntersectedObject(e);
      if (hit) {
        container.style.cursor = 'pointer';
        if (hit.type === 'SATELLITE') {
          setHoveredSat(hit.data);
          setHoveredPlanet(null);
        } else if (hit.type === 'PLANET') {
          setHoveredPlanet(hit.data);
          setHoveredSat(null);
        }
      } else {
        container.style.cursor = 'grab';
        setHoveredSat(null);
        setHoveredPlanet(null);
      }
    };

    const onPointerUp = (e) => {
      if (e.target !== renderer.domElement) return;
      const distMoved = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);
      if (distMoved < 6) {
        const hit = getIntersectedObject(e);
        if (hit && hit.type === 'SATELLITE') {
          onSelectSatellite(hit.data);
        } else if (hit && hit.type === 'PLANET') {
          const targetObj = planetMeshesRef.current.find(p => p.userData?.planetData?.id === hit.data.id);
          if (targetObj) {
            const worldPos = new THREE.Vector3();
            targetObj.getWorldPosition(worldPos);
            const pRadius = targetObj.geometry?.parameters?.radius || 3.0;
            targetCamPosRef.current = new THREE.Vector3(worldPos.x, worldPos.y + pRadius * 0.4, worldPos.z + pRadius * 3.2);
            controls.target.copy(worldPos);
          }
        }
      }
    };

    container.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('mousemove', onMouseMove);
    container.addEventListener('pointerup', onPointerUp);

    // 9. Animation Render Loop
    let animationFrameId;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      // Smooth camera perspective transition (Earth <-> Solar Planets)
      if (targetCamPosRef.current) {
        camera.position.lerp(targetCamPosRef.current, 0.05);
        controls.target.lerp(new THREE.Vector3(0, 0, 0), 0.05);
        if (camera.position.distanceTo(targetCamPosRef.current) < 0.2) {
          targetCamPosRef.current = null;
        }
      }

      // Controls update
      controls.update();

      // Earth axial rotation
      if (earthGroup) {
        earthGroup.rotation.y += 0.0006;
      }

      // Deep space celestial drift
      if (starsRef.current) {
        starsRef.current.rotation.y += 0.0001;
      }

      // Moon revolution around Earth
      if (moonPivotRef.current) {
        moonPivotRef.current.rotation.y += 0.002;
      }

      // Solar planets gentle celestial drift in space
      if (planetsGroupRef.current) {
        planetsGroupRef.current.rotation.y += 0.00015;
      }

      // Orbit animation for satellites
      satMeshesRef.current.forEach((satGroup) => {
        const { radius, incRad, raanRad, speed } = satGroup.userData;
        satGroup.userData.angle += speed;
        const ang = satGroup.userData.angle;
        satGroup.position.copy(orbitPosition(radius, incRad, raanRad, ang));
        // Orient spacecraft prograde
        satGroup.lookAt(orbitPosition(radius, incRad, raanRad, ang + 0.02));
      });

      renderer.render(scene, camera);
    };

    animate();

    // 10. Resize Handling
    const handleResize = () => {
      if (!container) return;
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('mousemove', onMouseMove);
      container.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('resize', handleResize);
      controls.dispose();
      renderer.dispose();
      container.innerHTML = '';
    };
  }, []);

  // Update controls auto-rotation dynamically
  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.autoRotate = autoRotate;
    }
  }, [autoRotate]);

  // Update camera perspective dynamically when cameraMode switches
  useEffect(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    if (cameraMode === 'SOLAR') {
      targetCamPosRef.current = new THREE.Vector3(0, 24, 70);
      controlsRef.current.target.set(0, 0, 0);
    } else if (cameraMode === 'EARTH') {
      targetCamPosRef.current = new THREE.Vector3(0, 0, 14.5);
      controlsRef.current.target.set(0, 0, 0);
    }
  }, [cameraMode]);

  // Build satellites + orbit lines from the live fleet. Rebuilt only when membership or risk
  // changes; each satellite keeps its place on its orbit across rebuilds.
  const fleetSignature = satellites.map((s) => `${s.id}:${s.risk}:${s.status || ''}`).join('|');
  useEffect(() => {
    const orbitsGroup = orbitsGroupRef.current;
    const satellitesGroup = satellitesGroupRef.current;
    if (!orbitsGroup || !satellitesGroup) return;
    const previousAngles = new Map(satMeshesRef.current.map((m) => [m.userData.satData.id, m.userData.angle]));
    disposeGroup(orbitsGroup);
    disposeGroup(satellitesGroup);

    satMeshesRef.current = satellites.map((sat, index) => {
      const tier = RISK_TIERS[sat.risk] || RISK_TIERS.LOW;
      const radius = sceneOrbitRadius(sat, index);
      const incRad = THREE.MathUtils.degToRad(sat.inclinationDeg || 0);
      const raanRad = THREE.MathUtils.degToRad(Number.isFinite(sat.raanDeg) ? sat.raanDeg : (index * 360) / satellites.length);

      // Orbital Trajectory Line
      const segments = 128;
      const points = [];
      for (let i = 0; i <= segments; i++) {
        points.push(orbitPosition(radius, incRad, raanRad, (i / segments) * Math.PI * 2));
      }
      const orbitOpacity = sat.risk === 'CRITICAL' ? 0.40 : sat.risk === 'HIGH' ? 0.32 : 0.20;
      const orbitLine = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints(points),
        new THREE.LineBasicMaterial({ color: new THREE.Color(tier.color), transparent: true, opacity: orbitOpacity, linewidth: 1 })
      );
      orbitLine.userData = { risk: sat.risk };
      orbitsGroup.add(orbitLine);

      // Satellite model, starting at its real position along the orbit (argument of latitude)
      const satModel = createRealisticSatellite(sat, tier);
      satModel.userData.radius = radius;
      satModel.userData.incRad = incRad;
      satModel.userData.raanRad = raanRad;
      satModel.userData.speed = sat.orbitSpeed || 0.0015;
      satModel.userData.angle = previousAngles.get(sat.id)
        ?? (Number.isFinite(sat.argLatitudeDeg) ? THREE.MathUtils.degToRad(sat.argLatitudeDeg) : (index / satellites.length) * Math.PI * 2);
      satModel.position.copy(orbitPosition(radius, incRad, raanRad, satModel.userData.angle));
      satellitesGroup.add(satModel);
      return satModel;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fleetSignature]);

  // Keep hover / click data current between rebuilds (miss distance, Pc, TCA change every refresh)
  useEffect(() => {
    const byId = new Map(satellites.map((s) => [s.id, s]));
    satMeshesRef.current.forEach((m) => {
      const fresh = byId.get(m.userData.satData.id);
      if (fresh) m.userData.satData = fresh;
    });
  }, [satellites]);

  // Update visibility according to filters
  useEffect(() => {
    if (!satMeshesRef.current || !orbitsGroupRef.current) return;

    satMeshesRef.current.forEach((satGroup) => {
      const sat = satGroup.userData.satData;
      const visible = !filterRisk || filterRisk === 'ALL' || sat.risk === filterRisk;
      satGroup.visible = visible;
    });

    orbitsGroupRef.current.children.forEach((orbitLine) => {
      const risk = orbitLine.userData.risk;
      const visible = showOrbits && (!filterRisk || filterRisk === 'ALL' || risk === filterRisk);
      orbitLine.visible = visible;
    });
  }, [filterRisk, showOrbits, fleetSignature]);

  // Tactile selection focus: scale selected satellite slightly up
  useEffect(() => {
    if (!satMeshesRef.current) return;
    satMeshesRef.current.forEach((satGroup) => {
      const sat = satGroup.userData.satData;
      const isSelected = selectedSatellite && sat?.id === selectedSatellite.id;
      const targetScale = isSelected ? 1.4 : 1.0;
      satGroup.scale.set(targetScale, targetScale, targetScale);
    });
  }, [selectedSatellite, fleetSignature]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      <div 
        ref={mountRef} 
        style={{ 
          width: '100%', 
          height: '100%',
          display: 'block'
        }} 
      />

      {/* Satellite Hover Telemetry Badge */}
      {hoveredSat && (
        <div
          style={{
            position: 'absolute',
            top: 28,
            left: '50%',
            transform: 'translateX(-50%)',
            pointerEvents: 'none',
            zIndex: 40,
            padding: '8px 18px',
            borderRadius: '10px',
            background: 'rgba(8, 14, 28, 0.94)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255, 255, 255, 0.18)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.55)'
          }}
        >
          <span 
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: (RISK_TIERS[hoveredSat.risk] || RISK_TIERS.LOW).color
            }}
          />
          <span style={{ fontWeight: 700, fontSize: '14px', color: '#f8fafc' }}>
            {hoveredSat.name}
          </span>
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>
            Alt: {hoveredSat.altitudeKm} km
          </span>
          <span 
            style={{
              fontSize: '11px',
              fontWeight: 800,
              padding: '2px 8px',
              borderRadius: 4,
              color: '#ffffff',
              backgroundColor: (RISK_TIERS[hoveredSat.risk] || RISK_TIERS.LOW).color
            }}
          >
            {hoveredSat.risk} RISK
          </span>
        </div>
      )}

      {/* Solar Planet Hover Telemetry Badge */}
      {hoveredPlanet && !hoveredSat && (
        <div
          style={{
            position: 'absolute',
            top: 28,
            left: '50%',
            transform: 'translateX(-50%)',
            pointerEvents: 'none',
            zIndex: 40,
            padding: '8px 18px',
            borderRadius: '10px',
            background: 'rgba(8, 14, 28, 0.94)',
            backdropFilter: 'blur(12px)',
            border: `1px solid ${hoveredPlanet.color}`,
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)'
          }}
        >
          <span 
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: hoveredPlanet.color
            }}
          />
          <span style={{ fontWeight: 700, fontSize: '14px', color: '#f8fafc' }}>
            {hoveredPlanet.name}
          </span>
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>
            {hoveredPlanet.type}
          </span>
          <span 
            style={{
              fontSize: '11px',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 4,
              color: '#f8fafc',
              backgroundColor: 'rgba(255, 255, 255, 0.12)'
            }}
          >
            {hoveredPlanet.distance}
          </span>
        </div>
      )}
    </div>
  );
}
