# OrbitGuard AI 🛰️🚀

**AI-Assisted Collision Risk Assessment for Low Earth Orbit Satellites**

OrbitGuard AI identifies risky satellite–debris close approaches, predicts collision probability using GPU-accelerated machine learning, explains predictions with SHAP, simulates avoidance manoeuvres, and displays everything on a premium real-time dashboard.

---

## 🌟 Features

| Module | Description |
|---|---|
| **CelesTrak Live Integration** | Real-time orbital data from CelesTrak (10,000+ active satellites, debris fields) |
| **GPU-Accelerated ML** | XGBoost with CUDA on RTX 4060 — trains on 162K+ CDM conjunction events |
| **SHAP Explainability** | Understand *why* a conjunction is risky via waterfall charts, dependence plots |
| **Manoeuvre Simulation** | Evaluate ΔV burns with Tsiolkovsky equation, compare risk/fuel trade-offs |
| **3D Orbit Visualization** | Interactive Plotly 3D Earth + orbit traces + satellite markers |
| **Premium Dashboard** | Streamlit with glassmorphism, dark mode, live data, 6 specialized pages |

---

## 🏗️ Architecture

```
OrbitGuard AI
├── app.py                    # Streamlit Dashboard (6 pages)
├── config.py                 # Centralised configuration
├── celestrak_fetcher.py      # CelesTrak live TLE/GP data fetcher
├── data_preprocessing.py     # Feature engineering pipeline (100+ features)
├── collision_model.py        # GPU-accelerated XGBoost model
├── explainability.py         # SHAP-based risk explanations
├── manoeuvre_simulator.py    # Collision avoidance simulation
├── orbit_visualizations.py   # 3D orbit + gauge + chart utilities
├── export_dataset.py         # Exports the trained dataset + predictions to JSON
├── Dataset/
│   ├── train_data.csv        # 162K CDM rows (13,154 conjunction events)
│   └── test_data.csv         # 24K CDM rows (2,167 events)
├── models/                   # Saved model artifacts
├── exports/                  # JSON exports (see below)
└── requirements.txt          # Python dependencies
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Train the Model (GPU-Accelerated)
```bash
python collision_model.py
```
This uses your **RTX 4060** (8GB VRAM, CUDA 13.2) for accelerated training.

Training uses an event-grouped validation split (no conjunction event appears in both train and validation) with early stopping, and saves `models/orbitguard_model.json`, `_meta.json` (metrics) and `_preprocessor.pkl`.

### 3. Export the Trained Dataset to JSON
```bash
python export_dataset.py              # full export (~570 MB)
python export_dataset.py --sample 5000  # first 5,000 rows of each set
```

| File | Contents |
|---|---|
| `exports/trained_dataset.json` | Every training row: original CDM fields, engineered features, `split` (train/val), `predicted_risk`, `risk_level`, `predicted_risk_level`, `prediction_error` |
| `exports/test_predictions.json` | Every test row with the same prediction fields |
| `exports/model_summary.json` | Training/test metrics, feature importance, risk-level breakdowns |

### 4. Launch the Dashboard
```bash
streamlit run app.py
```

### Current Results

| Metric | Value |
|---|---|
| Test RMSE (log₁₀ Pc) | 0.151 |
| Test R² | 0.9998 |
| Alert precision / recall (risk ≥ −4.5) | 0.971 / 0.953 |

Note: each row's `risk` is the collision probability computed from that same CDM, and features such as `max_risk_estimate` / `max_risk_scaling` come from the same calculation. The model is therefore a fast, explainable emulator of the CDM risk computation, not a forecast of how risk will evolve in later CDMs.

---

## 📊 Dataset

The CDM (Conjunction Data Message) dataset contains **162,635 training** and **24,485 test** conjunction events with **100+ features** including:

- **Orbital elements**: Semi-major axis, eccentricity, inclination
- **Relative dynamics**: Miss distance, relative speed, position/velocity in RTN frame
- **Covariance data**: Position/velocity uncertainties (σ_r, σ_t, σ_n)
- **Observation quality**: Weighted RMS, observation counts, OD span
- **Space weather**: F10.7, F3M, SSN, AP indices
- **Target**: `risk` — log₁₀ collision probability

---

## 🧠 How It Works

```
CelesTrak Live TLE Data
        ↓
Orbital Element Extraction
        ↓
Close-Approach Screening
        ↓
Feature Engineering (100+ derived features)
        ↓
XGBoost GPU Prediction (RTX 4060)
        ↓
SHAP Explainability Analysis
        ↓
Manoeuvre Simulation & Comparison
        ↓
Dashboard Alerts & Visualization
```

### Risk Levels

| Level | log₁₀ Pc | Action |
|---|---|---|
| 🔴 CRITICAL | ≥ -3.0 | Immediate manoeuvre required |
| 🟠 HIGH | ≥ -4.5 | Plan manoeuvre |
| 🟡 MEDIUM | ≥ -6.0 | Monitor closely |
| 🟢 LOW | ≥ -7.5 | Standard monitoring |
| 🔵 NEGLIGIBLE | < -7.5 | No action needed |

---

## 🖥️ GPU Acceleration

OrbitGuard AI leverages the **NVIDIA RTX 4060** (Ada Lovelace):
- **8 GB GDDR6 VRAM** — fits the full dataset
- **CUDA 13.2** — XGBoost `device=cuda` with histogram tree method
- **Training speedup**: ~5-10× faster than CPU
- **Inference**: Real-time predictions on conjunction events

---

## 🌍 CelesTrak Integration

Live orbital data is fetched from [CelesTrak](https://celestrak.org/) including:
- **Active satellites** (10,000+)
- **Space stations** (ISS, Tiangong)
- **Debris fields** (Cosmos 1408, Fengyun 1C, Iridium 33, Cosmos 2251)
- **Constellation tracking** (Starlink, OneWeb, Planet, Spire)

Data is cached with a 5-minute TTL for responsive browsing.

---

## 📋 Tech Stack

| Component | Technology |
|---|---|
| ML Framework | XGBoost (CUDA GPU) |
| Explainability | SHAP (TreeExplainer) |
| Dashboard | Streamlit |
| Visualization | Plotly (3D + 2D) |
| Orbital Mechanics | SGP4, Astropy |
| Live Data | CelesTrak GP API |
| Language | Python 3.14 |
| GPU | NVIDIA RTX 4060 (CUDA 13.2) |

---

## ⚠️ Disclaimer

**For research and simulation only.** This is not a certified collision-warning or satellite-control system. Real-world conjunction assessment requires validated orbital determination, official CDM sources (e.g., 18th SDS), and domain-expert review.

---

*Built for the OrbitGuard AI Hackathon 🏆*
