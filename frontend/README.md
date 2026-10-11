# OrbitGuard AI — web front end

React 19 + Three.js mission-control site, built with Vite. All data comes from the FastAPI backend
(`../backend`); the dev server proxies `/api` to `http://127.0.0.1:8000` (override with `ORBITGUARD_API`,
or set `VITE_API_BASE` to call another host directly).

```bash
npm install
npm run dev      # http://localhost:5173  (start the backend first: python ../backend/run.py)
npm run build    # production bundle in dist/
npm run lint     # oxlint
```

| View | Backend endpoints |
|---|---|
| 3D Fleet Globe | `/api/status`, `/api/conjunctions/satellites` — watchlist on its real orbit planes, coloured by risk |
| 72h Screening | `/api/conjunctions/screen`, `/api/scenario` (inject a simulated threat), `/api/refresh` |
| ML & SHAP (XAI) | `/api/conjunctions/detail/{key}`, `/api/predict/esa-replay/{id}`, `/api/predict/what-if` |
| Δv Maneuver | `/api/maneuver/plan/{key}`, `/api/maneuver/decision`, `/api/maneuver/optimize` |
| ESA Replay & KPIs | `/api/benchmark/metrics`, `/api/predict/esa-events` |
| Solar System | static orrery (`src/data/solarSystemData.js`) |

Shared code: `src/api.js` (fetch + polling hook), `src/lib/format.js` (risk tiers, Pc formatting, API → globe
mapping), `src/components/ui.jsx` (panels, charts). When the backend is unreachable the globe shows the bundled
sample fleet (`src/data/satellites.js`) and the header says `OFFLINE · SAMPLE DATA`.
