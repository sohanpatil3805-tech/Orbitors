# OrbitGuard AI 🛰️🚀

**AI-Assisted Collision Risk Assessment for Low Earth Orbit Satellites**

OrbitGuard AI screens important satellites against the whole tracked catalogue every time new orbit data arrives, estimates the probability of collision with a validated physics engine and an ML uncertainty model (using live space weather), shows the result on a risk-coloured 3D globe, and suggests avoidance manoeuvres that an operator can accept or decline.

---

## 🌟 Features

| Module | Description |
|---|---|
| **Live screening (SGP4)** | 25 important satellites (ISS, Tiangong, Hubble, Sentinels, Landsat, ISRO EOS…) screened against ~19–30k objects for the next 72 h |
| **Space-Track + CelesTrak** | Full public catalogue and official public CDMs from Space-Track when credentials are set; CelesTrak active + debris groups otherwise |
| **Space weather** | Daily F10.7, 81-day mean, sunspot number, Ap/Kp from CelesTrak — inputs to the uncertainty model |
| **Physics risk engine** | Standard 2D probability of collision; reproduces ESA's own risk values to 0.03 log₁₀ |
| **ML uncertainty model** | GPU XGBoost trained on 320K object-states from ESA CDMs — predicts the position uncertainty public orbit data lacks |
| **Manoeuvre planner** | Smallest burn that clears a HIGH/CRITICAL conjunction, checked against the whole catalogue for new conflicts; suggests the *other* satellite move when that's better |
| **Operator decisions** | Accept / decline each suggestion; logged as an audit trail and drawn on the 3D view |
| **Risk-coloured 3D view** | 🔴 red glowing path = danger · 🟠 orange = review · ⚪ white = safe · 🟢 dashed = accepted burn |
| **Auto-refresh** | Re-checks every 5 min; new orbit data (every 2 h) triggers re-screening — no clicking needed |
| **Validation suite** | 13 checks against independent references + 12 offline unit tests |
| **SHAP explainability** | Why the full-CDM model predicts a given risk |

---

## 🏗️ Architecture

```
OrbitGuard AI
├── dashboard.py              # Streamlit dashboard (8 pages) — named so it never shadows backend/app
├── config.py                 # All settings: watchlist, thresholds, data sources
│
├── ── live data ──
├── catalog.py                # Space-Track or CelesTrak catalogue + SATCAT metadata → SGP4 objects
├── spacetrack_client.py      # Space-Track login, GP catalogue, public CDMs (optional)
├── celestrak_fetcher.py      # CelesTrak GP groups
├── space_weather.py          # F10.7 / Ap / Kp / sunspots from CelesTrak
├── http_cache.py             # Polite disk-cached downloads
│
├── ── physics + ML ──
├── screening.py              # SGP4 conjunction screening (72 h)
├── risk_engine.py            # Probability of collision (2D Pc), risk levels, live assessment
├── uncertainty_model.py      # ML uncertainty model (6 GPU XGBoost regressors)
├── orbit_propagation.py      # SGP4 helpers + J2 propagator for burns
├── manoeuvre_planner.py      # Avoidance burn search, verification, conflict check
├── live_pipeline.py          # catalogue → screening → risk → summary (disk-cached)
├── decisions.py              # Operator accept/decline log
├── scenario.py               # Simulated threats for testing
│
├── ── CDM model (dataset) ──
├── data_preprocessing.py     # Feature engineering (118 features)
├── collision_model.py        # GPU XGBoost CDM risk model
├── explainability.py         # SHAP explanations
├── export_dataset.py         # Dataset + predictions → JSON
├── orbit_visualizations.py   # 3D Earth, risk-coloured orbits, charts
│
├── validate.py               # Full validation report → exports/validation_report.json
├── tests/                    # Fast offline unit tests
├── assets/earth_texture.jpg  # Blue Marble texture for the 3D globe (from frontend/public)
├── .streamlit/config.toml    # Dashboard theme
├── backend/                  # FastAPI service (separate app; run from backend/: python run.py)
├── frontend/                 # React frontend
├── Dataset/                  # ESA CDM train/test CSVs (git-ignored)
├── models/                   # Trained models (CDM model + models/uncertainty/)
└── exports/                  # JSON exports + validation report
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Connect Space-Track
Create a free account at [space-track.org](https://www.space-track.org/auth/createAccount), copy `.env.example` to `.env` and fill in your login. `.env` is git-ignored. Without it the app uses CelesTrak.

### 3. Train the models (already trained in `models/`)
```bash
python collision_model.py      # full-CDM risk model (GPU, ~4 s)
python uncertainty_model.py    # live uncertainty model (GPU, ~15 s)
python -c "from collision_model import evaluate_splits; evaluate_splits()"   # train/val/test accuracy → Settings page
```

### 4. Launch the dashboard
```bash
streamlit run dashboard.py     # or: python -m streamlit run dashboard.py
```
The first load screens the watchlist (about a minute); later loads use the cache until new orbit data arrives.

### 5. Check it is correct
```bash
python -m unittest discover tests   # 12 fast offline checks (~3 s)
python validate.py                  # full report (~5 min) → 🧪 Validation page
```

---

## 🧠 How It Works

```
Space-Track GP / CelesTrak GP  +  SATCAT (type, owner, size, status)  +  space weather
                                   ↓
          SGP4 screening: watchlist vs catalogue, 60 s steps, 72 h
          (straight-line closest approach within each step, then exact refinement)
                                   ↓
     close approaches < 10 km: time of closest approach (TCA), miss vector, speed
                                   ↓
   ML uncertainty model (altitude, type, size, time to TCA, data age, F10.7, Ap…)
          + assumed TLE error growth  →  each object's covariance
                                   ↓
     2D probability of collision (encounter plane, combined hard-body radius)
     — or Space-Track's official Pc when a public CDM exists
                                   ↓
        risk level → status (DANGER / REVIEW / SAFE) → 3D colours + alerts
                                   ↓
 HIGH/CRITICAL → manoeuvre search (J2 model) → verify → screen new path → suggest
                                   ↓
                     operator accepts / declines → log + 3D
```

### Risk levels and colours

| Level | log₁₀ Pc | Status / 3D colour | Action |
|---|---|---|---|
| 🔴 CRITICAL | ≥ −3.0 | DANGER — red, glowing | Manoeuvre |
| 🟠 HIGH | ≥ −4.5 | DANGER — red, glowing | Plan manoeuvre (suggestion generated) |
| 🟡 MEDIUM | ≥ −6.0 | REVIEW — orange | Check closely |
| 🟢 LOW | ≥ −7.5 | SAFE — white (orange if the pass is < 1 km) | Standard monitoring |
| 🔵 NEGLIGIBLE | < −7.5 | SAFE — white | None |

### Manoeuvre suggestions
For every HIGH/CRITICAL conjunction the planner tries burns 0.5–7.5 orbits before closest approach in six directions (prograde, retrograde, radial ±, normal ±) and finds the **smallest ΔV** that brings risk below 10⁻⁷ and the miss distance above 2 km. Each suggestion lists burn time, direction, ΔV, burn duration, fuel, altitude change, new miss distance and new risk. It is then:

1. **verified** with full nonlinear propagation, and
2. **screened against the whole catalogue**, so a burn that creates a new HIGH/CRITICAL approach is rejected.

If the other object is a working satellite, its options are computed too. When it is the better mover, the suggestion becomes "ask <owner> to manoeuvre <satellite>". If no conflict-free burn exists, the satellites that would also need to move are listed.

---

## 🧪 Validation results

Run `python validate.py`. Latest results (also on the 🧪 Validation page):

| Check | Reference | Result |
|---|---|---|
| A1 Pc engine vs ESA risk values | 24,478 ESA test CDMs | error 0.033 log₁₀, Spearman 0.994, alert P/R 0.991 / 0.960 ✅ |
| A2 Closed-form case | 1 − exp(−R²/2σ²) | relative error 2×10⁻⁶ ✅ |
| A3 Monte Carlo | 4M samples × 6 geometries | 6/6 agree ✅ |
| B1 Uncertainty prediction | per-type median baseline | ML better in 6/6 (along-track 1.5× vs 2.9×) ✅ |
| B2 Risk without covariance | same baseline | Spearman 0.71 vs 0.44, error 2.98 vs 8.16 ✅ |
| B3 Full-CDM XGBoost model | ESA test set | R² 0.9998, alert P/R 0.971 / 0.953 ✅ |
| C1 Simulated threats found | injected 0 m – 3 km | 4/4, TCA < 1 s, miss < 5 m ✅ |
| C2 vs CelesTrak SOCRATES | 356 pairs on the same orbit data | median 0.3 m, 0.004 s ✅ |
| C3 vs Space-Track CDMs | official public CDMs | needs credentials ⏭️ |
| D1 Linear burn model | nonlinear J2 propagation | worst 1.9% ✅ |
| D2 Burn drift | Clohessy–Wiltshire theory | within 5% ✅ |
| D3 Fuel | rocket equation | exact ✅ |
| D4 End to end | 3 simulated collision courses | 3/3 cleared by an independently re-checked burn ✅ |

**Testing it yourself in the dashboard:** ⚙️ Settings → *Test scenario* injects a simulated debris piece or satellite on a collision course with any watchlist satellite (you choose the time and miss distance). The satellite turns red in 3D and a manoeuvre suggestion appears on the 🚀 page. You know the ground truth, so you can check the alert time, the distance and whether the burn clears it.

### Honest limitations
- Public GP/TLE orbits are accurate to about a kilometre, so live Pc uses assumed TLE error growth (`config.TLE_SIGMA_KM`) plus the ML uncertainty. Live risk is therefore approximate, and it is **conservative** in dense shells such as Starlink's. Space-Track's official CDM Pc replaces it when available.
- With real covariance the engine matches ESA (A1). With predicted covariance it catches about two-thirds of ESA's high-risk alerts (B2). That is the honest accuracy of risk from public data.
- The burn model is impulsive and uses two-body + J2 relative to the SGP4 path. It does not model finite burns, attitude constraints or other operators' plans.
- The full-CDM XGBoost model mostly reproduces the Pc already contained in each CDM (`max_risk_*` features), so it is an explainable emulator, not a forecast.

---

## 📊 Dataset

ESA collision-avoidance CDMs: **162,634 training** and **24,484 test** rows (13,154 / 2,167 events), 103 columns. The columns cover:
- relative position and velocity in the RTN frame
- each object's covariance
- orbits
- tracking quality
- object size and type
- space weather (F10, F3M, SSN, AP)
- the target, `risk` (log₁₀ Pc)

---

## 📋 Tech Stack

| Component | Technology |
|---|---|
| Orbit propagation | SGP4 (vectorised), SciPy DOP853 two-body + J2 |
| Collision probability | 2D Pc (Foster / Akella–Alfriend), Gauss–Legendre integration |
| ML | XGBoost (CUDA GPU) — uncertainty model + CDM risk model |
| Explainability | SHAP (TreeExplainer) |
| Data | Space-Track GP + public CDM, CelesTrak GP / SATCAT / SOCRATES / space weather |
| Dashboard | Streamlit + Plotly 3D |
| Language / GPU | Python 3.14 / NVIDIA RTX 4060 |

---

## ⚠️ Disclaimer

**For research and simulation only.** This is not a certified collision-warning or satellite-control system. Real-world conjunction assessment requires validated orbit determination, official CDM sources (e.g. 18th SDS), and review by the satellite's operator.

---

*Built for the OrbitGuard AI Hackathon 🏆*
