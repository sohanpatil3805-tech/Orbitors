import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RISK_TIERS, SATELLITES_DATA } from '../data/satellites';

export default function Globe3D({ 
  selectedSatellite, 
  onSelectSatellite, 
  filterRisk,
  showOrbits = true,
  autoRotate = true 
}) {
  const mountRef = useRef(null);
  const [hoveredSat, setHoveredSat] = useState(null);

  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const earthGroupRef = useRef(null);
  const starsRef = useRef(null);
  const orbitsGroupRef = useRef(null);
  const satellitesGroupRef = useRef(null);
  const satMeshesRef = useRef([]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    // 1. Scene & Centered Camera
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 14.5);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // 2. WebGL Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.95;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 3. OrbitControls (Smooth unified orbital rotation of space and satellites)
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enablePan = false; // Keeps Earth anchored dead-center
    controls.minDistance = 7.5;
    controls.maxDistance = 28.0;
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 0.7;
    controlsRef.current = controls;

    // 4. Natural Lighting (Deep space realistic sun & ambient)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    // Warm, realistic sunlight
    const sunLight = new THREE.DirectionalLight(0xfffaed, 1.8);
    sunLight.position.set(16, 8, 12);
    scene.add(sunLight);

    // Subtle neutral dark-side fill
    const spaceFillLight = new THREE.DirectionalLight(0x1e293b, 0.35);
    spaceFillLight.position.set(-16, -6, -10);
    scene.add(spaceFillLight);

    // Camera-attached headlight: ensures spacecraft metallic panels and risk colors shine from all angles
    const cameraLight = new THREE.DirectionalLight(0xffffff, 0.45);
    camera.add(cameraLight);
    scene.add(camera);

    // 5. Dynamic Starfield (Distributed strictly in deep space background shell)
    const starsGeo = new THREE.BufferGeometry();
    const starCount = 2000;
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = 90 + Math.random() * 80; // Distant outer shell, never near camera
      const sinPhi = Math.sin(phi);
      starPositions[i] = r * sinPhi * Math.cos(theta);
      starPositions[i + 1] = r * sinPhi * Math.sin(theta);
      starPositions[i + 2] = r * Math.cos(phi);
    }
    starsGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));

    // Circular glowing star texture (eliminates any square pixel artifacts)
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
      size: 1.8, 
      transparent: true, 
      opacity: 0.85,
      depthWrite: false,
      blending: THREE.AdditiveBlending
    });
    const starField = new THREE.Points(starsGeo, starsMat);
    starsRef.current = starField;
    scene.add(starField);

    // 6. Central Earth Globe (Increased size for spacious orbital perspective)
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
          metalness: 0.0,
          roughness: 0.85,
        });
        const earthMesh = new THREE.Mesh(earthGeo, earthMat);
        earthGroup.add(earthMesh);
      },
      undefined,
      () => {
        // Fallback procedural canvas
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

    // Thin, realistic atmospheric haze hugging Earth's surface (not overly blue)
    const atmosphereGeo = new THREE.SphereGeometry(EARTH_RADIUS + 0.08, 64, 64);
    const atmosphereMat = new THREE.MeshBasicMaterial({
      color: 0x93c5fd,
      transparent: true,
      opacity: 0.07,
      side: THREE.BackSide
    });
    const atmosphereMesh = new THREE.Mesh(atmosphereGeo, atmosphereMat);
    earthGroup.add(atmosphereMesh);

    // 7. Orbits & Satellites Groups (100% Synchronized with Earth Frame)
    const orbitsGroup = new THREE.Group();
    orbitsGroup.position.set(0, 0, 0);
    orbitsGroupRef.current = orbitsGroup;
    scene.add(orbitsGroup);

    const satellitesGroup = new THREE.Group();
    satellitesGroup.position.set(0, 0, 0);
    satellitesGroupRef.current = satellitesGroup;
    scene.add(satellitesGroup);

    // Helper to construct realistic satellite spacecraft
    const createRealisticSatellite = (sat, tier) => {
      const satGroup = new THREE.Group();
      satGroup.userData = { satData: sat };
      const riskColor = new THREE.Color(tier.color);

      // 1. Satellite Bus Chassis (High-tech aerospace composite body)
      const busGeo = new THREE.BoxGeometry(0.36, 0.28, 0.46);
      const busMat = new THREE.MeshStandardMaterial({
        color: 0xf1f5f9,
        metalness: 0.90,
        roughness: 0.20
      });
      const bus = new THREE.Mesh(busGeo, busMat);
      satGroup.add(bus);

      // Multi-Layer Insulation (MLI) Gold Foil Thermal Shield on Top/Side
      const mliGeo = new THREE.BoxGeometry(0.364, 0.05, 0.464);
      const mliMat = new THREE.MeshStandardMaterial({
        color: 0xd97706, // Gold aerospace thermal foil
        metalness: 0.95,
        roughness: 0.28
      });
      const mliTop = new THREE.Mesh(mliGeo, mliMat);
      mliTop.position.set(0, 0.13, 0);
      satGroup.add(mliTop);

      // 2. Risk Status Telemetry Band (Changes color directly per hitting probability!)
      const statusBandGeo = new THREE.BoxGeometry(0.37, 0.13, 0.47);
      const statusBandMat = new THREE.MeshStandardMaterial({
        color: riskColor,
        emissive: riskColor,
        emissiveIntensity: 0.85,
        metalness: 0.5,
        roughness: 0.20
      });
      const statusBand = new THREE.Mesh(statusBandGeo, statusBandMat);
      statusBand.position.set(0, 0, 0);
      satGroup.add(statusBand);

      // 3. Dual Photovoltaic Solar Array Wings (Segmented panels with realistic solar cells)
      const solarMat = new THREE.MeshStandardMaterial({
        color: 0x1d4ed8, // Authentic space photovoltaic crystalline blue
        metalness: 0.88,
        roughness: 0.15
      });
      const panelFrameMat = new THREE.MeshStandardMaterial({
        color: 0x64748b, // Aerospace titanium panel border
        metalness: 0.85,
        roughness: 0.3
      });

      // Wing parameters: 2 segmented panels per wing (wingspan ~2.2 units across)
      const pW = 0.40;
      const pH = 0.02;
      const pD = 0.34;

      [-1, 1].forEach((side) => {
        // Articulated deployment boom truss
        const boomGeo = new THREE.CylinderGeometry(0.016, 0.016, 0.22, 8);
        const boom = new THREE.Mesh(boomGeo, panelFrameMat);
        boom.rotation.z = Math.PI / 2;
        boom.position.set(side * 0.28, 0, 0);
        satGroup.add(boom);

        // Inner Solar Panel Segment
        const innerPanel = new THREE.Mesh(new THREE.BoxGeometry(pW, pH, pD), solarMat);
        innerPanel.position.set(side * (0.39 + pW / 2), 0, 0);
        satGroup.add(innerPanel);

        // Panel Hinge Connector
        const hingeGeo = new THREE.CylinderGeometry(0.022, 0.022, 0.06, 8);
        const hinge = new THREE.Mesh(hingeGeo, panelFrameMat);
        hinge.rotation.x = Math.PI / 2;
        hinge.position.set(side * (0.39 + pW + 0.03), 0, 0);
        satGroup.add(hinge);

        // Outer Solar Panel Segment
        const outerPanel = new THREE.Mesh(new THREE.BoxGeometry(pW, pH, pD), solarMat);
        outerPanel.position.set(side * (0.39 + pW + 0.06 + pW / 2), 0, 0);
        satGroup.add(outerPanel);

        // Wingtip Collision Hazard Beacon (Glowing in Risk/Hitting Probability Color!)
        const tipBeaconGeo = new THREE.SphereGeometry(0.06, 12, 12);
        const tipBeaconMat = new THREE.MeshStandardMaterial({
          color: riskColor,
          emissive: riskColor,
          emissiveIntensity: 1.0,
          roughness: 0.1
        });
        const tipBeacon = new THREE.Mesh(tipBeaconGeo, tipBeaconMat);
        tipBeacon.position.set(side * (0.39 + pW * 2 + 0.09), 0, 0);
        satGroup.add(tipBeacon);
      });

      // 4. Parabolic High-Gain Communications Dish Antenna (Points Nadir towards Earth)
      const dishGroup = new THREE.Group();
      dishGroup.position.set(0, 0.20, 0.16);

      // Parabolic Reflector Dish
      const dishGeo = new THREE.ConeGeometry(0.18, 0.10, 24, 1, true);
      const dishMat = new THREE.MeshStandardMaterial({
        color: 0xf8fafc,
        side: THREE.DoubleSide,
        metalness: 0.75,
        roughness: 0.22
      });
      const dish = new THREE.Mesh(dishGeo, dishMat);
      dish.rotation.x = -Math.PI / 2;
      dishGroup.add(dish);

      // Central Feed Horn & Subreflector (Glowing in Risk/Hitting Probability Color)
      const feedGeo = new THREE.CylinderGeometry(0.015, 0.022, 0.12, 8);
      const feedMat = new THREE.MeshStandardMaterial({
        color: riskColor,
        emissive: riskColor,
        emissiveIntensity: 0.95,
        roughness: 0.2
      });
      const feed = new THREE.Mesh(feedGeo, feedMat);
      feed.rotation.x = -Math.PI / 2;
      feed.position.set(0, 0, 0.08);
      dishGroup.add(feed);

      satGroup.add(dishGroup);

      // 5. Earth Observation Optical Payload / Star Tracker
      const opticGeo = new THREE.CylinderGeometry(0.065, 0.08, 0.10, 16);
      const opticMat = new THREE.MeshStandardMaterial({
        color: 0x1e293b,
        metalness: 0.9,
        roughness: 0.1
      });
      const opticBarrel = new THREE.Mesh(opticGeo, opticMat);
      opticBarrel.position.set(0, -0.16, 0.10);
      satGroup.add(opticBarrel);

      // Glass Lens Element
      const lensGeo = new THREE.CircleGeometry(0.06, 16);
      const lensMat = new THREE.MeshStandardMaterial({
        color: 0x38bdf8,
        emissive: 0x0284c7,
        emissiveIntensity: 0.5,
        roughness: 0.1
      });
      const lens = new THREE.Mesh(lensGeo, lensMat);
      lens.rotation.x = Math.PI / 2;
      lens.position.set(0, -0.211, 0.10);
      satGroup.add(lens);

      // 6. Aft Apogee Thruster Rocket Nozzle
      const thrusterGeo = new THREE.ConeGeometry(0.09, 0.14, 16, 1, true);
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

      // Thruster Core Glow (Risk Color)
      const thrusterGlowGeo = new THREE.SphereGeometry(0.035, 8, 8);
      const thrusterGlowMat = new THREE.MeshBasicMaterial({ color: riskColor });
      const thrusterGlow = new THREE.Mesh(thrusterGlowGeo, thrusterGlowMat);
      thrusterGlow.position.set(0, 0, -0.25);
      satGroup.add(thrusterGlow);

      // 7. Dynamic Hazard Proximity Ring (All tiers colored per hitting probability)
      const haloOpacity = sat.risk === 'EXTREME' ? 0.75 : (sat.risk === 'HIGH' ? 0.55 : (sat.risk === 'MEDIUM' ? 0.40 : 0.25));
      const haloRadius = sat.risk === 'EXTREME' ? [0.78, 0.88] : (sat.risk === 'HIGH' ? [0.70, 0.80] : (sat.risk === 'MEDIUM' ? [0.64, 0.72] : [0.58, 0.66]));
      const haloGeo = new THREE.RingGeometry(haloRadius[0], haloRadius[1], 36);
      const haloMat = new THREE.MeshBasicMaterial({
        color: riskColor,
        transparent: true,
        opacity: haloOpacity,
        side: THREE.DoubleSide
      });
      const halo = new THREE.Mesh(haloGeo, haloMat);
      halo.name = 'halo';
      satGroup.add(halo);

      return satGroup;
    };

    // Distinct altitude corridors for each satellite (prevents overlap / collision illusions)
    const ORBIT_ALTITUDE_MAP = {
      48274: 5.75, // TIANGONG (CSS) - 390 km (0.90 clearance above Earth)
      25544: 6.25, // ISS (ZARYA) - 418 km
      20580: 6.80, // HUBBLE - 535 km
      44713: 7.35, // STARLINK-1007 - 550 km
      39634: 7.90, // SENTINEL-1A - 693 km
      49260: 8.45, // LANDSAT-9 - 705 km
      25994: 9.00, // TERRA (EOS AM-1) - 705 km
      43013: 9.55, // NOAA-20 - 824 km
      45145: 10.15 // ONEWEB-0145 - 1200 km
    };

    // Build Satellites & Trajectories
    satMeshesRef.current = [];
    SATELLITES_DATA.forEach((sat, index) => {
      const tier = RISK_TIERS[sat.risk];
      const orbitRadius = ORBIT_ALTITUDE_MAP[sat.id] || (EARTH_RADIUS + 1.2 + index * 0.5);
      const incRad = (sat.inclinationDeg * Math.PI) / 180;

      // 3D Orbit Curve
      const points = [];
      const segments = 120;
      for (let i = 0; i <= segments; i++) {
        const theta = (i / segments) * Math.PI * 2;
        const x = orbitRadius * Math.cos(theta);
        const y = orbitRadius * Math.sin(theta) * Math.sin(incRad);
        const z = orbitRadius * Math.sin(theta) * Math.cos(incRad);
        points.push(new THREE.Vector3(x, y, z));
      }
      const orbitGeo = new THREE.BufferGeometry().setFromPoints(points);
      const orbitMat = new THREE.LineBasicMaterial({
        color: new THREE.Color(tier.color),
        transparent: true,
        opacity: sat.risk === 'EXTREME' ? 0.85 : (sat.risk === 'HIGH' ? 0.65 : 0.35),
        linewidth: sat.risk === 'EXTREME' ? 2 : 1
      });
      const orbitLine = new THREE.Line(orbitGeo, orbitMat);
      orbitLine.userData = { satId: sat.id, risk: sat.risk };
      orbitsGroup.add(orbitLine);

      // Construct Realistic Spacecraft Model
      const satGroup = createRealisticSatellite(sat, tier);

      // Distribute initial phase angle evenly around 360 degrees (clean constellation spacing)
      const phaseOffset = (index / SATELLITES_DATA.length) * Math.PI * 2;
      const initialAngle = phaseOffset + (((sat.id * 19) % 35) * (Math.PI / 180));
      satGroup.userData.angle = initialAngle;
      satGroup.userData.radius = orbitRadius;
      satGroup.userData.incRad = incRad;
      satGroup.userData.speed = sat.orbitSpeed;

      const posX = orbitRadius * Math.cos(initialAngle);
      const posY = orbitRadius * Math.sin(initialAngle) * Math.sin(incRad);
      const posZ = orbitRadius * Math.sin(initialAngle) * Math.cos(incRad);
      satGroup.position.set(posX, posY, posZ);

      satellitesGroup.add(satGroup);
      satMeshesRef.current.push(satGroup);
    });

    // 8. Hover Detection & Click Handling (Recursive on all spacecraft parts)
    let pointerDownPos = { x: 0, y: 0 };

    const onPointerDown = (e) => {
      pointerDownPos = { x: e.clientX, y: e.clientY };
    };

    const getIntersectedSatellite = (event) => {
      const rect = renderer.domElement.getBoundingClientRect();
      const mouseX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      const mouseY = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera);
      const intersects = raycaster.intersectObjects(satMeshesRef.current, true);

      if (intersects.length > 0) {
        let obj = intersects[0].object;
        while (obj && !obj.userData?.satData && obj.parent) {
          obj = obj.parent;
        }
        return obj?.userData?.satData || null;
      }
      return null;
    };

    const onMouseMove = (e) => {
      const satData = getIntersectedSatellite(e);
      if (satData) {
        container.style.cursor = 'pointer';
        setHoveredSat(satData);
      } else {
        container.style.cursor = 'grab';
        setHoveredSat(null);
      }
    };

    const onPointerUp = (e) => {
      if (e.target !== renderer.domElement) return;
      const distMoved = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);
      if (distMoved < 6) {
        const satData = getIntersectedSatellite(e);
        if (satData) {
          onSelectSatellite(satData);
        }
      }
    };

    container.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('mousemove', onMouseMove);
    container.addEventListener('pointerup', onPointerUp);

    // 9. Animation Render Loop
    let animationFrameId;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Update OrbitControls (smooth camera orbit & auto-rotation)
      controls.update();

      // Earth axial rotation
      if (earthGroup) {
        earthGroup.rotation.y += 0.0006;
      }

      // Outer Space subtle celestial drift
      if (starsRef.current) {
        starsRef.current.rotation.y += 0.0001;
      }

      // Orbit animation for satellites (perfectly synchronized in orbital plane)
      satMeshesRef.current.forEach((satGroup) => {
        satGroup.userData.angle += satGroup.userData.speed;
        const ang = satGroup.userData.angle;
        const rad = satGroup.userData.radius;
        const inc = satGroup.userData.incRad;

        const posX = rad * Math.cos(ang);
        const posY = rad * Math.sin(ang) * Math.sin(inc);
        const posZ = rad * Math.sin(ang) * Math.cos(inc);

        satGroup.position.set(posX, posY, posZ);

        // Orient spacecraft prograde (forward along orbit trajectory)
        const nextAng = ang + 0.02;
        const nextX = rad * Math.cos(nextAng);
        const nextY = rad * Math.sin(nextAng) * Math.sin(inc);
        const nextZ = rad * Math.sin(nextAng) * Math.cos(inc);
        satGroup.lookAt(nextX, nextY, nextZ);

        // Pulse Hazard Proximity Halo (Billboard oriented towards camera)
        const halo = satGroup.getObjectByName('halo');
        if (halo) {
          const satRisk = satGroup.userData.satData?.risk;
          const pulseSpeed = satRisk === 'EXTREME' ? 6.0 : 3.5;
          const pulse = 1.0 + Math.sin(elapsedTime * pulseSpeed) * 0.24;
          halo.scale.set(pulse, pulse, pulse);
          // Keep halo facing camera for clear tactical display
          halo.quaternion.copy(camera.quaternion);
        }
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
  }, [filterRisk, showOrbits]);

  // Tactile selection focus: scale selected satellite slightly up
  useEffect(() => {
    if (!satMeshesRef.current) return;
    satMeshesRef.current.forEach((satGroup) => {
      const sat = satGroup.userData.satData;
      const isSelected = selectedSatellite && sat?.id === selectedSatellite.id;
      const targetScale = isSelected ? 1.4 : 1.0;
      satGroup.scale.set(targetScale, targetScale, targetScale);
    });
  }, [selectedSatellite]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div 
        ref={mountRef} 
        style={{ width: '100%', height: '100%', cursor: 'grab' }}
      />

      {/* Hover Tooltip Overlay */}
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
            border: `1px solid ${RISK_TIERS[hoveredSat.risk].color}`,
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            boxShadow: `0 0 25px ${RISK_TIERS[hoveredSat.risk].glowColor}`
          }}
        >
          <span 
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: RISK_TIERS[hoveredSat.risk].color
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
              backgroundColor: RISK_TIERS[hoveredSat.risk].color
            }}
          >
            {hoveredSat.risk} RISK
          </span>
        </div>
      )}
    </div>
  );
}
