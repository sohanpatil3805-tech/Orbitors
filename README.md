OrbitGuard AI
Explainable Collision-Risk Assessment and Fuel-Efficient Avoidance for Low Earth Orbit Satellites
OrbitGuard AI is an AI-assisted decision-support project designed to
help assess potential satellite--debris conjunctions in Low Earth Orbit
(LEO). It combines orbital trajectory analysis, collision-risk
assessment, explainable machine learning, and simulated manoeuvre
comparison to help an operator decide whether an avoidance manoeuvre
should be considered.
Project status: Proposed / prototype-stage concept. Features and
performance claims should be updated to match the implementation and
evaluation results. This project is for research and simulation, not
for operational satellite control.

Problem Statement
LEO contains active satellites, defunct spacecraft, rocket bodies, and
debris fragments. Uncertainty in orbital measurements and predicted
trajectories makes it difficult to assess close approaches reliably.
Unnecessary avoidance manoeuvres can consume fuel and disrupt missions,
while insufficient response to a dangerous encounter can lead to a
collision and create more debris.
OrbitGuard AI aims to support better-informed decisions by identifying
potentially risky encounters, communicating uncertainty, explaining the
factors behind each assessment, and comparing the estimated risk and
cost of candidate avoidance options.
Proposed Solution
The proposed workflow is:
1. Acquire orbital and conjunction data from suitable public
   catalogues or conjunction data sources.
2. Screen for close approaches and calculate relevant encounter
   features, such as miss distance and relative velocity, where the
   input data supports them.
3. Assess collision risk using physics-based calculations and/or a
   machine-learning model.
4. Communicate uncertainty and avoid presenting unsupported
   precision when the available data is incomplete.
5. Explain model outputs using techniques such as SHAP, if a
   compatible trained model is used.
6. Compare candidate actions in simulation, including no action and
   feasible avoidance manoeuvres, against residual-risk and estimated
   fuel-cost objectives.
7. Present results through a dashboard with ranked alerts,
   explanations, uncertainty indicators, and decision-support
   recommendations.
Key Objectives
- Identify potentially dangerous satellite--debris close approaches.
- Combine orbital-analysis methods with AI-assisted risk assessment.
- Make model predictions more interpretable.
- Account for uncertainty and limitations in available orbital data.
- Compare no-action and simulated avoidance scenarios.
- Evaluate risk and estimated manoeuvre cost rather than treating
  every close approach as equally dangerous.
Planned Features
- Orbital/conjunction data ingestion
- Close-approach screening and feature extraction
- Risk scoring and alert ranking
- Machine-learning risk classification or prediction (if trained and
  validated)
- Explainability with SHAP (if supported by the selected model)
- Uncertainty and data-quality indicators
- Simulated manoeuvre comparison
- Dashboard for visualizing encounters and recommendations
- Evaluation against baseline strategies
Features marked as planned should not be described as implemented until
they are available in the repository.
System Workflow
Orbital / Conjunction Data
            |
            v
 Data Validation and Preparation
            |
            v
 Orbital Propagation and Close-Approach Screening
            |
            v
 Risk Assessment + Uncertainty Handling
            |
            v
 Explainability and Candidate Manoeuvre Simulation
            |
            v
 Compare Residual Risk, Fuel Cost and Constraints
            |
            v
 Operator-Facing Dashboard and Recommendation
Technology Stack
The final stack depends on the implementation. A possible stack is:
  Area                                Candidate technology
  Programming language                Python
  Data processing                     pandas, NumPy
  Machine learning                    scikit-learn / XGBoost
  Model explainability                SHAP
  Orbital analysis                    A suitable orbital-mechanics
                                      library and validated propagation
                                      methods
  Visualization/dashboard             Streamlit, Plotly, or the framework
                                      selected by the team
  Data source                         Public orbital catalogue and/or
                                      conjunction data, subject to access
                                      and licensing
  Version control                     Git and GitHub
Only list tools that are actually used in the project as implemented.
Record exact versions in a requirements file when the environment is
established.
Data
Potential inputs include:
- Orbital element data for satellites and tracked debris
- Conjunction or close-approach records, where available
- Object metadata relevant to screening
- Space-weather information when relevant to the propagation approach
Document each data source, retrieval date, licence/usage terms, missing
fields, and preprocessing decisions. Two-Line Element (TLE) data is
useful for broad screening, but it should not automatically be treated
as sufficient for operationally reliable collision probabilities or
high-precision manoeuvre planning.
Evaluation Plan
Evaluate the system using reproducible experiments and compare it with
appropriate baselines, such as a physics-only screening method and a
simple risk-threshold strategy.
Possible metrics include:
- Precision, recall, and false-negative rate for risk classification
- Calibration and reliability of predicted probabilities, when
  ground-truth labels and sufficient data are available
- Performance under noisy or incomplete input data
- Residual risk in simulated avoidance scenarios
- Estimated manoeuvre delta-v or fuel cost, where the model supports
  these calculations
- Number of unnecessary manoeuvres recommended
- Runtime and explanation quality
Report actual results, dataset details, assumptions, and limitations. Do
not claim improved safety or fuel savings unless experiments support the
claim.
Getting Started
The repository setup will depend on the code and framework selected by
the team. For a Python-based implementation, a typical starting point
is:
1. Clone the repository
git clone <REPOSITORY_URL>
cd <REPOSITORY_DIRECTORY>
2. Create and activate a virtual environment
Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
3. Install dependencies
Once the project has a requirements.txt file:
pip install -r requirements.txt
4. Configure data and run
Add the actual data configuration and run commands here once the
entry-point script or dashboard has been implemented. Do not commit API
keys, credentials, private conjunction data, or large raw datasets to
the repository.
Suggested Repository Structure
orbitguard-ai/
├── data/
│   ├── raw/              # Local-only raw data; usually excluded from Git
│   └── processed/
├── notebooks/            # Exploration and experiments
├── src/
│   ├── data/             # Data ingestion and validation
│   ├── orbit/            # Propagation and close-approach screening
│   ├── risk/             # Risk assessment and calibration
│   ├── explainability/   # Model explanations
│   ├── optimization/     # Candidate manoeuvre simulation
│   └── dashboard/        # User interface
├── tests/
├── requirements.txt
├── .gitignore
└── README.md
This is a suggested structure; adapt it to the repository's actual code.
Safety and Limitations
- OrbitGuard AI is a research and decision-support prototype, not a
  certified collision-avoidance system.
- Recommendations must be reviewed by qualified satellite operators
  before any real-world action.
- Orbital data can be stale, uncertain, incomplete, or inconsistent
  across sources.
- Machine-learning predictions depend on the quality and
  representativeness of training and evaluation data.
- Collision probability calculations require appropriate uncertainty
  information and validated assumptions.
- Manoeuvre feasibility, spacecraft dynamics, fuel limits, mission
  constraints, and coordination with other operators must be modelled
  before recommendations can be considered actionable.
- A dashboard risk score is not a substitute for authoritative
  conjunction assessment.
Research Direction
A proposed research question is:
Does uncertainty-aware, explainable AI-assisted manoeuvre selection
reduce simulated collision risk and estimated fuel expenditure
compared with threshold-based collision avoidance under noisy orbital
data?

To investigate this, establish baselines, define assumptions and
constraints, use reproducible simulations, and report results with
limitations. Novelty should be established through a review of relevant
prior work rather than assumed.
Roadmap
- [ ] Select and document data sources
- [ ] Build data validation and preprocessing
- [ ] Implement orbital screening and close-approach features
- [ ] Establish a physics-based or threshold-based baseline
- [ ] Train and validate an AI risk model, if appropriate data is
  available
- [ ] Add probability calibration and uncertainty reporting
- [ ] Add model explanations
- [ ] Implement simulated manoeuvre comparison
- [ ] Build the dashboard
- [ ] Run comparative experiments and document results
Team Contributions
Add team member names and responsibilities here.
Contributing
1. Create a branch for your change.
2. Keep experiments reproducible and document data assumptions.
3. Add tests for new calculations and data-processing steps.
4. Avoid committing secrets or restricted datasets.
5. Submit a pull request describing the change and its validation.
License
No licence has been specified yet. Add a LICENSE file before
distributing or reusing the project publicly.
Disclaimer
OrbitGuard AI is intended for educational, research, and simulation
purposes. It does not provide certified operational collision warnings
or autonomous satellite-control commands.
