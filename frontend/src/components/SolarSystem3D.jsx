import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { SOLAR_SYSTEM_DATA } from '../data/solarSystemData';

// ============================================================================
// Procedural Canvas Texture Generators for Authentic Celestial Appearances
// ============================================================================

function createSunTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');

  const grad = ctx.createLinearGradient(0, 0, 0, 512);
  grad.addColorStop(0, '#f59e0b');
  grad.addColorStop(0.3, '#d97706');
  grad.addColorStop(0.5, '#b45309');
  grad.addColorStop(0.7, '#d97706');
  grad.addColorStop(1, '#f59e0b');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 1024, 512);

  // Solar granulation & turbulent flare noise
  for (let i = 0; i < 4000; i++) {
    const x = Math.random() * 1024;
    const y = Math.random() * 512;
    const r = Math.random() * 8 + 2;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = Math.random() > 0.5 ? 'rgba(254, 240, 138, 0.35)' : 'rgba(180, 83, 9, 0.4)';
    ctx.fill();
  }

  // Solar flares / sunspots
  for (let i = 0; i < 16; i++) {
    const x = Math.random() * 1024;
    const y = 150 + Math.random() * 212;
    ctx.beginPath();
    ctx.arc(x, y, Math.random() * 6 + 3, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(69, 10, 10, 0.7)';
    ctx.fill();
  }

  return new THREE.CanvasTexture(canvas);
}

function createMercuryTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#64748b';
  ctx.fillRect(0, 0, 512, 256);

  // Craters and regolith noise
  for (let i = 0; i < 1500; i++) {
    const x = Math.random() * 512;
    const y = Math.random() * 256;
    const r = Math.random() * 5 + 1;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = Math.random() > 0.5 ? 'rgba(30, 41, 59, 0.4)' : 'rgba(203, 213, 225, 0.25)';
    ctx.fill();
  }
  return new THREE.CanvasTexture(canvas);
}

function createVenusTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');

  const grad = ctx.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, '#eab308');
  grad.addColorStop(0.3, '#ca8a04');
  grad.addColorStop(0.5, '#d97706');
  grad.addColorStop(0.7, '#ca8a04');
  grad.addColorStop(1, '#eab308');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 512, 256);

  // Sulfuric acid cloud streaks
  for (let i = 0; i < 40; i++) {
    const y = Math.random() * 256;
    ctx.fillStyle = 'rgba(254, 240, 138, 0.15)';
    ctx.fillRect(0, y, 512, Math.random() * 8 + 2);
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

  // Lunar Maria (Dark volcanic basalt plains)
  const maria = [
    { x: 70, y: 50, r: 24 },
    { x: 120, y: 40, r: 30 },
    { x: 160, y: 70, r: 25 },
    { x: 90, y: 80, r: 20 }
  ];
  maria.forEach(m => {
    ctx.beginPath();
    ctx.arc(m.x, m.y, m.r, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(30, 41, 59, 0.55)';
    ctx.fill();
  });

  // Impact craters
  for (let i = 0; i < 400; i++) {
    const x = Math.random() * 256;
    const y = Math.random() * 128;
    ctx.beginPath();
    ctx.arc(x, y, Math.random() * 3 + 1, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(226, 232, 240, 0.4)';
    ctx.fill();
  }
  return new THREE.CanvasTexture(canvas);
}

function createMarsTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');

  // Red planet iron-oxide background
  ctx.fillStyle = '#c2410c';
  ctx.fillRect(0, 0, 512, 256);

  // Dark volcanic terrain & dust plains
  for (let i = 0; i < 800; i++) {
    const x = Math.random() * 512;
    const y = Math.random() * 256;
    ctx.beginPath();
    ctx.arc(x, y, Math.random() * 10 + 2, 0, Math.PI * 2);
    ctx.fillStyle = Math.random() > 0.6 ? 'rgba(124, 45, 18, 0.4)' : 'rgba(234, 88, 12, 0.3)';
    ctx.fill();
  }

  // Polar Ice Caps (North & South)
  ctx.fillStyle = '#f8fafc';
  ctx.fillRect(0, 0, 512, 16);
  ctx.fillRect(0, 240, 512, 16);

  return new THREE.CanvasTexture(canvas);
}

function createJupiterTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');

  // Multi-band gas giant bands
  const bands = [
    '#78350f', '#b45309', '#d97706', '#fef3c7', '#d97706', '#92400e',
    '#451a03', '#b45309', '#fef3c7', '#d97706', '#78350f', '#451a03'
  ];
  const bandHeight = 512 / bands.length;
  bands.forEach((color, i) => {
    ctx.fillStyle = color;
    ctx.fillRect(0, i * bandHeight, 1024, bandHeight);
  });

  // Atmospheric turbulence & eddies
  for (let i = 0; i < 1200; i++) {
    const x = Math.random() * 1024;
    const y = Math.random() * 512;
    ctx.fillStyle = Math.random() > 0.5 ? 'rgba(254, 243, 199, 0.25)' : 'rgba(69, 26, 3, 0.3)';
    ctx.fillRect(x, y, Math.random() * 30 + 10, Math.random() * 4 + 1);
  }

  // Great Red Spot
  ctx.beginPath();
  ctx.ellipse(320, 310, 45, 26, 0, 0, Math.PI * 2);
  ctx.fillStyle = '#b91c1c';
  ctx.fill();
  ctx.strokeStyle = '#7f1d1d';
  ctx.lineWidth = 4;
  ctx.stroke();

  return new THREE.CanvasTexture(canvas);
}

function createSaturnTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');

  // Tan/Golden subtle atmospheric bands
  const bands = ['#ca8a04', '#eab308', '#fef08a', '#eab308', '#ca8a04', '#a16207'];
  const bandHeight = 256 / bands.length;
  bands.forEach((color, i) => {
    ctx.fillStyle = color;
    ctx.fillRect(0, i * bandHeight, 512, bandHeight);
  });
  return new THREE.CanvasTexture(canvas);
}

function createSaturnRingsTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 64;
  const ctx = canvas.getContext('2d');

  // Radial ring brightness with Cassini Division gap
  const grad = ctx.createLinearGradient(0, 0, 512, 0);
  grad.addColorStop(0.0, 'rgba(254, 240, 138, 0.1)');
  grad.addColorStop(0.15, 'rgba(202, 138, 4, 0.85)');
  grad.addColorStop(0.45, 'rgba(234, 179, 8, 0.9)');
  grad.addColorStop(0.55, 'rgba(0, 0, 0, 0.05)'); // Cassini Division gap!
  grad.addColorStop(0.62, 'rgba(161, 98, 7, 0.7)');
  grad.addColorStop(0.90, 'rgba(202, 138, 4, 0.6)');
  grad.addColorStop(1.0, 'rgba(0, 0, 0, 0.0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 512, 64);

  return new THREE.CanvasTexture(canvas);
}

function createUranusTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');

  const grad = ctx.createLinearGradient(0, 0, 0, 128);
  grad.addColorStop(0, '#67e8f9');
  grad.addColorStop(0.5, '#38bdf8');
  grad.addColorStop(1, '#67e8f9');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 256, 128);
  return new THREE.CanvasTexture(canvas);
}

function createNeptuneTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');

  // Deep azure ice giant bands
  const grad = ctx.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, '#1d4ed8');
  grad.addColorStop(0.3, '#2563eb');
  grad.addColorStop(0.6, '#1e40af');
  grad.addColorStop(1, '#1d4ed8');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 512, 256);

  // Supersonic white storm bands
  for (let i = 0; i < 20; i++) {
    const y = Math.random() * 256;
    ctx.fillStyle = 'rgba(224, 242, 254, 0.3)';
    ctx.fillRect(0, y, 512, Math.random() * 3 + 1);
  }

  // Great Dark Spot
  ctx.beginPath();
  ctx.ellipse(220, 140, 25, 14, 0, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(15, 23, 42, 0.8)';
  ctx.fill();

  return new THREE.CanvasTexture(canvas);
}

function createPlutoTexture() {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#78716c';
  ctx.fillRect(0, 0, 256, 128);

  // Heart-shaped Tombaugh Regio ice plain
  ctx.beginPath();
  ctx.arc(100, 60, 20, 0, Math.PI * 2);
  ctx.arc(130, 60, 20, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(245, 245, 244, 0.7)';
  ctx.fill();
  return new THREE.CanvasTexture(canvas);
}

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function SolarSystem3D({
  selectedBody,
  onSelectBody,
  simSpeed = 1,
  showOrbits = true,
  showAsteroidBelt = true
}) {
  const mountRef = useRef(null);
  // The render loop is created once, so it reads the current speed through a ref
  const simSpeedRef = useRef(simSpeed);
  useEffect(() => { simSpeedRef.current = simSpeed; }, [simSpeed]);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const rendererRef = useRef(null);

  // References for live animation
  const planetMeshesRef = useRef([]);
  const orbitLinesRef = useRef([]);
  const asteroidBeltRef = useRef(null);
  const earthMoonRef = useRef(null);
  const animationFrameRef = useRef(null);
  const targetCameraPosRef = useRef(null);
  const targetLookAtRef = useRef(null);

  const [hoveredBody, setHoveredBody] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const currentMount = mountRef.current;
    if (!currentMount) return;

    const width = currentMount.clientWidth || window.innerWidth;
    const height = currentMount.clientHeight || window.innerHeight;

    // 1. Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 2000);
    camera.position.set(0, 58, 100);
    cameraRef.current = camera;

    // 3. WebGL Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    currentMount.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. OrbitControls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 6;
    controls.maxDistance = 350;
    controls.maxPolarAngle = Math.PI / 2 + 0.15; // Allow slight under-plane tilt
    controlsRef.current = controls;

    // 5. Lighting
    // Central Sun light
    const sunLight = new THREE.PointLight(0xffffff, 3.2, 500, 0.4);
    sunLight.position.set(0, 0, 0);
    scene.add(sunLight);

    // Subtle ambient space illumination
    const ambientLight = new THREE.AmbientLight(0x334155, 0.45);
    scene.add(ambientLight);

    // Deep starry cosmic background
    const starGeo = new THREE.BufferGeometry();
    const starCount = 3000;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      const radius = 300 + Math.random() * 600;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      starPos[i] = radius * Math.sin(phi) * Math.cos(theta);
      starPos[i + 1] = radius * Math.sin(phi) * Math.sin(theta);
      starPos[i + 2] = radius * Math.cos(phi);
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.8, transparent: true, opacity: 0.75 });
    const starField = new THREE.Points(starGeo, starMat);
    scene.add(starField);

    // 6. Pre-generate Textures
    const textureLoader = new THREE.TextureLoader();
    let earthTexture;
    try {
      earthTexture = textureLoader.load('/earth-blue-marble.jpg');
    } catch {
      earthTexture = null;
    }

    const textures = {
      sun: createSunTexture(),
      mercury: createMercuryTexture(),
      venus: createVenusTexture(),
      moon: createMoonTexture(),
      mars: createMarsTexture(),
      jupiter: createJupiterTexture(),
      saturn: createSaturnTexture(),
      saturnRings: createSaturnRingsTexture(),
      uranus: createUranusTexture(),
      neptune: createNeptuneTexture(),
      pluto: createPlutoTexture()
    };

    // 7. Build Sun & Celestial Bodies
    const planetEntries = [];
    const orbitLines = [];

    SOLAR_SYSTEM_DATA.forEach((body) => {
      if (body.id === 'moon') return; // Handled as child of Earth

      // Orbits (if not Sun)
      if (body.orbitDistanceVisual > 0) {
        const orbitPoints = [];
        const segments = 128;
        for (let i = 0; i <= segments; i++) {
          const theta = (i / segments) * Math.PI * 2;
          orbitPoints.push(new THREE.Vector3(
            Math.cos(theta) * body.orbitDistanceVisual,
            0,
            Math.sin(theta) * body.orbitDistanceVisual
          ));
        }
        const orbitGeo = new THREE.BufferGeometry().setFromPoints(orbitPoints);
        const orbitMat = new THREE.LineBasicMaterial({
          color: 0x64748b,
          transparent: true,
          opacity: 0.25,
          linewidth: 1
        });
        const orbitLine = new THREE.Line(orbitGeo, orbitMat);
        scene.add(orbitLine);
        orbitLines.push(orbitLine);
      }

      // Celestial Mesh
      let material;
      if (body.id === 'sun') {
        material = new THREE.MeshBasicMaterial({ map: textures.sun });
      } else if (body.id === 'earth' && earthTexture) {
        material = new THREE.MeshStandardMaterial({
          map: earthTexture,
          roughness: 0.65,
          metalness: 0.1
        });
      } else {
        material = new THREE.MeshStandardMaterial({
          map: textures[body.id] || null,
          color: textures[body.id] ? 0xffffff : body.visualColor,
          roughness: 0.7,
          metalness: 0.15
        });
      }

      const sphereGeo = new THREE.SphereGeometry(body.visualRadius, 32, 32);
      const sphereMesh = new THREE.Mesh(sphereGeo, material);
      sphereMesh.userData = { bodyData: body };

      // Sun Corona Glow Atmosphere
      if (body.id === 'sun') {
        const coronaGeo = new THREE.SphereGeometry(body.visualRadius * 1.15, 32, 32);
        const coronaMat = new THREE.MeshBasicMaterial({
          color: 0xf59e0b,
          transparent: true,
          opacity: 0.28,
          side: THREE.BackSide
        });
        const coronaMesh = new THREE.Mesh(coronaGeo, coronaMat);
        sphereMesh.add(coronaMesh);
      }

      // Group holding planet and rotating around its orbit
      const pivotGroup = new THREE.Group();
      sphereMesh.position.set(body.orbitDistanceVisual, 0, 0);

      // Axial Tilt
      if (body.axialTilt) {
        sphereMesh.rotation.z = THREE.MathUtils.degToRad(body.axialTilt);
      }

      // Saturn Rings
      if (body.id === 'saturn') {
        const ringGeo = new THREE.RingGeometry(3.6, 6.6, 64);
        // Correct UVs for radial ring map
        const pos = ringGeo.attributes.position;
        const uvs = ringGeo.attributes.uv;
        for (let i = 0; i < pos.count; i++) {
          const v = new THREE.Vector2(pos.getX(i), pos.getY(i));
          uvs.setXY(i, (v.length() - 3.6) / (6.6 - 3.6), 0.5);
        }
        const ringMat = new THREE.MeshBasicMaterial({
          map: textures.saturnRings,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.88
        });
        const ringMesh = new THREE.Mesh(ringGeo, ringMat);
        ringMesh.rotation.x = Math.PI / 2;
        sphereMesh.add(ringMesh);
      }

      // Uranus Ring
      if (body.id === 'uranus') {
        const ringGeo = new THREE.RingGeometry(2.6, 3.4, 48);
        const ringMat = new THREE.MeshBasicMaterial({
          color: 0x67e8f9,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.35
        });
        const ringMesh = new THREE.Mesh(ringGeo, ringMat);
        ringMesh.rotation.x = Math.PI / 2;
        sphereMesh.add(ringMesh);
      }

      // Earth's Moon
      if (body.id === 'earth') {
        const moonData = SOLAR_SYSTEM_DATA.find(b => b.id === 'moon');
        const moonGeo = new THREE.SphereGeometry(moonData.visualRadius, 16, 16);
        const moonMat = new THREE.MeshStandardMaterial({
          map: textures.moon,
          roughness: 0.8
        });
        const moonMesh = new THREE.Mesh(moonGeo, moonMat);
        moonMesh.userData = { bodyData: moonData };
        moonMesh.position.set(2.8, 0, 0);

        // Moon Orbit line
        const moonOrbitPoints = [];
        for (let i = 0; i <= 64; i++) {
          const theta = (i / 64) * Math.PI * 2;
          moonOrbitPoints.push(new THREE.Vector3(Math.cos(theta) * 2.8, 0, Math.sin(theta) * 2.8));
        }
        const moonOrbitLine = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints(moonOrbitPoints),
          new THREE.LineBasicMaterial({ color: 0x94a3b8, transparent: true, opacity: 0.3 })
        );
        sphereMesh.add(moonOrbitLine);

        const moonPivot = new THREE.Group();
        moonPivot.add(moonMesh);
        sphereMesh.add(moonPivot);
        earthMoonRef.current = { pivot: moonPivot, mesh: moonMesh };
      }

      // Add clickable sphere
      pivotGroup.add(sphereMesh);
      scene.add(pivotGroup);

      planetEntries.push({
        data: body,
        mesh: sphereMesh,
        pivot: pivotGroup,
        orbitRadius: body.orbitDistanceVisual,
        speed: body.orbitSpeed,
        angle: Math.random() * Math.PI * 2
      });
    });

    planetMeshesRef.current = planetEntries;
    orbitLinesRef.current = orbitLines;

    // 8. Asteroid Belt (Between Mars at 27.5 and Jupiter at 38.0)
    const asteroidGeo = new THREE.BufferGeometry();
    const asteroidCount = 1800;
    const asteroidPositions = new Float32Array(asteroidCount * 3);
    for (let i = 0; i < asteroidCount * 3; i += 3) {
      const r = 31.5 + (Math.random() - 0.5) * 5.0; // radius band 29 - 34
      const theta = Math.random() * Math.PI * 2;
      const ySpread = (Math.random() - 0.5) * 1.8;
      asteroidPositions[i] = Math.cos(theta) * r;
      asteroidPositions[i + 1] = ySpread;
      asteroidPositions[i + 2] = Math.sin(theta) * r;
    }
    asteroidGeo.setAttribute('position', new THREE.BufferAttribute(asteroidPositions, 3));
    const asteroidMat = new THREE.PointsMaterial({
      color: 0x94a3b8,
      size: 0.45,
      transparent: true,
      opacity: 0.55
    });
    const asteroidBelt = new THREE.Points(asteroidGeo, asteroidMat);
    scene.add(asteroidBelt);
    asteroidBeltRef.current = asteroidBelt;

    // 9. Resize Handling
    const handleResize = () => {
      if (!currentMount) return;
      const w = currentMount.clientWidth;
      const h = currentMount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // 10. Animation Render Loop
    let lastTime = performance.now();
    const animate = (time) => {
      animationFrameRef.current = requestAnimationFrame(animate);
      const delta = (time - lastTime) / 1000;
      lastTime = time;

      // Orbit revolution & rotation
      planetEntries.forEach(entry => {
        // Orbit revolution around Sun
        if (entry.data.id !== 'sun' && entry.speed > 0) {
          entry.angle += entry.speed * simSpeedRef.current * delta * 2.5;
          entry.mesh.position.x = Math.cos(entry.angle) * entry.orbitRadius;
          entry.mesh.position.z = Math.sin(entry.angle) * entry.orbitRadius;
        }

        // Axial self-rotation
        entry.mesh.rotation.y += 0.008 * (entry.data.id === 'sun' ? 0.3 : 1);
      });

      // Moon revolution around Earth
      if (earthMoonRef.current) {
        earthMoonRef.current.pivot.rotation.y += 0.04 * simSpeedRef.current;
      }

      // Asteroid belt slow drift
      if (asteroidBeltRef.current) {
        asteroidBeltRef.current.rotation.y += 0.0006 * simSpeedRef.current;
      }

      // Smooth camera transition when focusing a body
      if (targetCameraPosRef.current && targetLookAtRef.current) {
        camera.position.lerp(targetCameraPosRef.current, 0.06);
        controls.target.lerp(targetLookAtRef.current, 0.06);

        if (camera.position.distanceTo(targetCameraPosRef.current) < 0.2) {
          targetCameraPosRef.current = null;
          targetLookAtRef.current = null;
        }
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animate(performance.now());

    // Clean up
    return () => {
      window.removeEventListener('resize', handleResize);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      if (currentMount && renderer.domElement) {
        currentMount.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update visibility toggles
  useEffect(() => {
    orbitLinesRef.current.forEach(line => {
      line.visible = showOrbits;
    });
  }, [showOrbits]);

  useEffect(() => {
    if (asteroidBeltRef.current) {
      asteroidBeltRef.current.visible = showAsteroidBelt;
    }
  }, [showAsteroidBelt]);

  // Handle camera transition when selectedBody changes
  useEffect(() => {
    if (!selectedBody || !cameraRef.current || !controlsRef.current) return;

    if (selectedBody.id === 'sun') {
      targetLookAtRef.current = new THREE.Vector3(0, 0, 0);
      targetCameraPosRef.current = new THREE.Vector3(0, 12, 24);
      return;
    }

    const entry = planetMeshesRef.current.find(p => p.data.id === selectedBody.id);
    if (entry) {
      const worldPos = new THREE.Vector3();
      entry.mesh.getWorldPosition(worldPos);

      targetLookAtRef.current = worldPos.clone();
      const offsetDist = Math.max(entry.data.visualRadius * 3.5, 4.0);
      targetCameraPosRef.current = new THREE.Vector3(
        worldPos.x + offsetDist * 0.7,
        worldPos.y + offsetDist * 0.5,
        worldPos.z + offsetDist
      );
    }
  }, [selectedBody]);

  // Raycasting for planet clicks and hover
  const handlePointerDown = (event) => {
    if (!mountRef.current || !cameraRef.current || !sceneRef.current) return;

    const rect = mountRef.current.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    );

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, cameraRef.current);

    const clickableMeshes = [];
    planetMeshesRef.current.forEach(entry => clickableMeshes.push(entry.mesh));
    if (earthMoonRef.current) clickableMeshes.push(earthMoonRef.current.mesh);

    const intersects = raycaster.intersectObjects(clickableMeshes, false);
    if (intersects.length > 0) {
      const clicked = intersects[0].object.userData.bodyData;
      if (clicked && onSelectBody) {
        onSelectBody(clicked);
      }
    }
  };

  const handlePointerMove = (event) => {
    if (!mountRef.current || !cameraRef.current) return;
    const rect = mountRef.current.getBoundingClientRect();
    setMousePos({ x: event.clientX, y: event.clientY });

    const mouse = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    );

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, cameraRef.current);

    const clickableMeshes = [];
    planetMeshesRef.current.forEach(entry => clickableMeshes.push(entry.mesh));
    if (earthMoonRef.current) clickableMeshes.push(earthMoonRef.current.mesh);

    const intersects = raycaster.intersectObjects(clickableMeshes, false);
    if (intersects.length > 0) {
      setHoveredBody(intersects[0].object.userData.bodyData);
    } else {
      setHoveredBody(null);
    }
  };

  return (
    <div 
      style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
    >
      <div ref={mountRef} style={{ width: '100%', height: '100%', cursor: hoveredBody ? 'pointer' : 'grab' }} />

      {/* Floating Hover Tooltip */}
      {hoveredBody && (
        <div 
          style={{
            position: 'fixed',
            left: mousePos.x + 14,
            top: mousePos.y - 28,
            pointerEvents: 'none',
            zIndex: 60,
            background: 'rgba(8, 14, 28, 0.94)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255, 255, 255, 0.18)',
            padding: '6px 12px',
            borderRadius: 8,
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}
        >
          <span 
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              backgroundColor: hoveredBody.visualColor || '#38bdf8'
            }}
          />
          <span style={{ fontSize: 12, fontWeight: 700, color: '#f8fafc' }}>
            {hoveredBody.name}
          </span>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>
            {hoveredBody.orbitDistanceAU > 0 ? `${hoveredBody.orbitDistanceAU} AU` : '0 AU (Center)'}
          </span>
        </div>
      )}
    </div>
  );
}
