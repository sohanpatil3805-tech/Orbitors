import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
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
  const satellitesGroupRef = useRef(null);
  const orbitsGroupRef = useRef(null);
  const earthGroupRef = useRef(null);
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
    // Position camera dead-center along Z-axis looking straight at (0, 0, 0)
    camera.position.set(0, 0, 11.5);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // 2. WebGL Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 3. Realistic Sunlight & Ambient Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xffffff, 2.2);
    sunLight.position.set(15, 6, 12);
    scene.add(sunLight);

    // Subtle atmospheric rim light from deep space
    const rimLight = new THREE.DirectionalLight(0x38bdf8, 0.9);
    rimLight.position.set(-15, -4, -10);
    scene.add(rimLight);

    // 4. Starfield Background
    const starsGeo = new THREE.BufferGeometry();
    const starCount = 1500;
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i += 3) {
      starPositions[i] = (Math.random() - 0.5) * 180;
      starPositions[i + 1] = (Math.random() - 0.5) * 180;
      starPositions[i + 2] = (Math.random() - 0.5) * 180;
    }
    starsGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    const starsMat = new THREE.PointsMaterial({ 
      color: 0xffffff, 
      size: 0.65, 
      transparent: true, 
      opacity: 0.8 
    });
    const starField = new THREE.Points(starsGeo, starsMat);
    scene.add(starField);

    // 5. Centered Earth Globe
    const earthGroup = new THREE.Group();
    earthGroup.position.set(0, 0, 0); // Explicit dead-center
    earthGroupRef.current = earthGroup;
    scene.add(earthGroup);

    // Load Photorealistic NASA Blue Marble Texture from /earth-blue-marble.jpg
    const textureLoader = new THREE.TextureLoader();
    const earthGeo = new THREE.SphereGeometry(3.6, 64, 64);

    textureLoader.load(
      '/earth-blue-marble.jpg',
      (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        const earthMat = new THREE.MeshStandardMaterial({
          map: texture,
          metalness: 0.1,
          roughness: 0.7,
        });
        const earthMesh = new THREE.Mesh(earthGeo, earthMat);
        earthGroup.add(earthMesh);
      },
      undefined,
      () => {
        // Fallback procedural canvas if texture load fails
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

    // Atmospheric Glow Halo Mesh
    const atmosphereGeo = new THREE.SphereGeometry(3.85, 48, 48);
    const atmosphereMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.16,
      side: THREE.BackSide
    });
    const atmosphereMesh = new THREE.Mesh(atmosphereGeo, atmosphereMat);
    earthGroup.add(atmosphereMesh);

    // Outer soft blue aura ring
    const auraGeo = new THREE.RingGeometry(3.9, 4.3, 64);
    const auraMat = new THREE.MeshBasicMaterial({
      color: 0x06b6d4,
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide
    });
    const auraMesh = new THREE.Mesh(auraGeo, auraMat);
    earthGroup.add(auraMesh);

    // 6. Orbits & Satellites Groups (Dead Center)
    const orbitsGroup = new THREE.Group();
    orbitsGroup.position.set(0, 0, 0);
    orbitsGroupRef.current = orbitsGroup;
    scene.add(orbitsGroup);

    const satellitesGroup = new THREE.Group();
    satellitesGroup.position.set(0, 0, 0);
    satellitesGroupRef.current = satellitesGroup;
    scene.add(satellitesGroup);

    // Build Satellites & Trajectories
    satMeshesRef.current = [];
    SATELLITES_DATA.forEach((sat) => {
      const tier = RISK_TIERS[sat.risk];
      const orbitRadius = 3.6 * sat.orbitRadiusScale;
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

      // Satellite Group
      const satGroup = new THREE.Group();
      satGroup.userData = { satData: sat };

      // Satellite Metallic Core
      const bodyGeo = new THREE.BoxGeometry(0.16, 0.12, 0.12);
      const bodyMat = new THREE.MeshStandardMaterial({
        color: 0xf1f5f9,
        metalness: 0.9,
        roughness: 0.1
      });
      const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
      satGroup.add(bodyMesh);

      // Solar Arrays
      const panelGeo = new THREE.BoxGeometry(0.52, 0.02, 0.16);
      const panelMat = new THREE.MeshStandardMaterial({
        color: 0x0284c7,
        metalness: 0.6,
        roughness: 0.3
      });
      const panelMesh = new THREE.Mesh(panelGeo, panelMat);
      satGroup.add(panelMesh);

      // Glowing Beacon Sphere (Risk Tier Color)
      const beaconGeo = new THREE.SphereGeometry(0.24, 16, 16);
      const beaconMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(tier.color),
        transparent: true,
        opacity: 0.9
      });
      const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
      satGroup.add(beaconMesh);

      // Pulsing Halo for Extreme & High Risk
      if (sat.risk === 'EXTREME' || sat.risk === 'HIGH') {
        const haloGeo = new THREE.SphereGeometry(0.48, 16, 16);
        const haloMat = new THREE.MeshBasicMaterial({
          color: new THREE.Color(tier.color),
          transparent: true,
          opacity: 0.35,
          wireframe: true
        });
        const haloMesh = new THREE.Mesh(haloGeo, haloMat);
        haloMesh.name = 'halo';
        satGroup.add(haloMesh);
      }

      // Initial orbital position
      const initialAngle = ((sat.id * 57) % 360) * (Math.PI / 180);
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

    // 7. Mouse Orbit Controls & Interaction
    let isDragging = false;
    let prevMousePos = { x: 0, y: 0 };

    const onMouseDown = (e) => {
      // Don't drag if clicking UI buttons
      if (e.target !== renderer.domElement) return;
      isDragging = true;
      prevMousePos = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      // Raycaster for hover selection
      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera);
      const intersects = raycaster.intersectObjects(
        satMeshesRef.current.map((g) => g.children[2]),
        false
      );

      if (intersects.length > 0) {
        container.style.cursor = 'pointer';
        const hoveredGroup = intersects[0].object.parent;
        setHoveredSat(hoveredGroup.userData.satData);
      } else {
        container.style.cursor = isDragging ? 'grabbing' : 'grab';
        setHoveredSat(null);
      }

      if (isDragging) {
        const deltaX = e.clientX - prevMousePos.x;
        const deltaY = e.clientY - prevMousePos.y;

        earthGroup.rotation.y += deltaX * 0.005;
        earthGroup.rotation.x += deltaY * 0.005;

        prevMousePos = { x: e.clientX, y: e.clientY };
      }
    };

    const onMouseUp = () => {
      isDragging = false;
      container.style.cursor = 'grab';
    };

    const onClick = (e) => {
      if (e.target !== renderer.domElement) return;
      const rect = renderer.domElement.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera);
      const intersects = raycaster.intersectObjects(
        satMeshesRef.current.map((g) => g.children[2]),
        false
      );

      if (intersects.length > 0) {
        const clickedGroup = intersects[0].object.parent;
        onSelectSatellite(clickedGroup.userData.satData);
      }
    };

    const onWheel = (e) => {
      e.preventDefault();
      // Keep camera centered, adjust zoom distance between 8.0 and 20.0
      camera.position.z = Math.min(20, Math.max(8.0, camera.position.z + e.deltaY * 0.015));
    };

    container.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    container.addEventListener('click', onClick);
    container.addEventListener('wheel', onWheel, { passive: false });

    // 8. Animation Loop
    let animationFrameId;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Earth auto rotation (centered)
      if (autoRotate && !isDragging) {
        earthGroup.rotation.y += 0.0008;
      }

      // Orbit animation for satellites
      satMeshesRef.current.forEach((satGroup) => {
        satGroup.userData.angle += satGroup.userData.speed;
        const ang = satGroup.userData.angle;
        const rad = satGroup.userData.radius;
        const inc = satGroup.userData.incRad;

        satGroup.position.x = rad * Math.cos(ang);
        satGroup.position.y = rad * Math.sin(ang) * Math.sin(inc);
        satGroup.position.z = rad * Math.sin(ang) * Math.cos(inc);

        // Pulse Beacon Halo
        const halo = satGroup.getObjectByName('halo');
        if (halo) {
          const pulse = 1.0 + Math.sin(elapsedTime * 4.5) * 0.28;
          halo.scale.set(pulse, pulse, pulse);
        }
      });

      renderer.render(scene, camera);
    };

    animate();

    // 9. Resize Handling
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
      container.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      container.removeEventListener('click', onClick);
      container.removeEventListener('wheel', onWheel);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      container.innerHTML = '';
    };
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
              borderRadius: '4px',
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
