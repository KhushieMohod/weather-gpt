# 🌦️ WeatherGPT — Smart India Hackathon 2026 (Team Udgama)

> Conversational, trust-grounded weather intelligence focused on Disaster Management.

**Team:** Udgama  |  **Event:** Smart India Hackathon 2026  |  **Theme:** Disaster Management
**Problem Statement ID:** 26068 — WeatherGPT: Conversational AI for Forecasting, Alerts & Climate Information

yo

---

## One-line Summary

WeatherGPT unifies multi-source meteorological data (IMD, ISRO-MOSDAC, GFS/WRF, ERA5 and ground observations) into a modular, RAG-backed conversational platform that delivers location-specific forecasts, risk detection, and actionable advisories for disaster preparedness and response.

---

## SIH 2026 Six-Slide Presentation Deck

### Slide 1 — Title & Idea Identity

- **Idea:** WeatherGPT — Conversational AI for Forecasting, Alerts & Climate Information
- **Problem Statement ID:** 26068
- **Team:** Udgama
- **Theme:** Disaster Management

### Slide 2 — Proposed Solution & Core Capabilities

WeatherGPT provides a trust-grounded weather intelligence layer for citizens, responders, and decision-makers. Its core capabilities are:

- Multi-source fusion across IMD, ISRO-MOSDAC, numerical weather models, reanalysis, and ground observations.
- Dynamic credibility scoring based on source authority, freshness, spatial relevance, agreement, and data quality.
- FAISS-backed retrieval-augmented generation (RAG) for grounded answers from advisories, forecasts, and historical context.
- Risk detection and alerts for hazards including cyclone, flood, heatwave, and severe weather events.
- Multilingual conversational delivery and WebSocket-based real-time updates for alert propagation.

### Slide 3 — Technical Approach & Architecture Flow

The system follows a modular flow: **source connectors -> validation and normalization -> spatial and temporal deduplication -> credibility scoring -> PostgreSQL and FAISS indexes -> deterministic risk engine -> guarded RAG response generation -> multilingual API, WebSockets, dashboards, and alerts**. Deterministic rules remain authoritative for safety-critical risk states, while the LLM explains verified context rather than inventing facts.

### Slide 4 — Feasibility, Viability & MVP Scope

- **Feasibility:** Python and FastAPI support rapid integration with government feeds, model outputs, databases, FAISS, and WebSockets.
- **Viability:** A modular pipeline allows low-cost incremental deployment, source substitution, and operation with cached advisories when feeds are delayed.
- **MVP:** Ingest priority IMD and MOSDAC data, normalize and score observations, index official advisories in FAISS, expose location-aware chat and risk endpoints, and deliver multilingual alerts through a web client.

### Slide 5 — Impact & Operational Benefits

- **Farmers:** Actionable local advisories for sowing, irrigation, crop protection, and extreme-weather preparation.
- **SDMAs and district administration:** Faster situational awareness, traceable evidence, localized risk alerts, and a shared operational view.
- **Marine and aviation operations:** Source-ranked forecasts, hazard summaries, and timely alerts for route, port, and airport decisions.

### Slide 6 — Research Foundation & Government System Integrations

The solution builds on meteorological data engineering, retrieval-augmented generation, uncertainty-aware source ranking, spatial deduplication, and deterministic hazard rules. Planned government integrations include **IMD Meghdoot** for farmer-oriented advisories and **MOSDAC** for satellite-derived rainfall and geospatial observations, alongside official IMD forecasts and bulletins.

The complete submission narrative is available in [docs/SIH_2026_Master_Submission.md](docs/SIH_2026_Master_Submission.md).

---

## Prototype Implementation Roadmap (5 Stages)

This repository follows a focused 5-stage prototype roadmap. Active status and implementation details are tracked in the project tracker: [Implementation.md](Implementation.md).

- **Stage 1 — Base Application Skeleton & FastAPI Structure**: Completed (see Stage 1 details and copy-pasteable boilerplate in the tracker).
- **Stage 2 — Data Ingestion & Processing Pipelines**: Implement connectors and ingestion pipelines for IMD, ISRO-MOSDAC, GFS/WRF, ERA5 plus ground station ingestion; include validation, deduplication, and credibility scoring.
- **Stage 3 — RAG + LLM Integration & Risk Engine**: Implement retrieval index, RAG pipeline, LLM safety/guardrails, and the Risk & Advisory engine (cyclone, flood, heatwave detectors).
- **Stage 4 — Frontend & Delivery Channels**: Build conversational UI, regional-language support, voice interfaces, push/alerting channels and dashboard visualizations.
- **Stage 5 — Deployment, Scaling & Real-Time Ops**: Containerized deployment, orchestration (K8s), monitoring, real-time alerting, and SLA-driven pipeline hardening.

---

## Modular Architecture & Core Data Sources

WeatherGPT is intentionally modular so teams can work independently on ingestion, intelligence, and delivery.

- **Data Layer**: Collects raw meteorological and observational data from:
  - IMD (official forecasts & bulletins)
  - ISRO-MOSDAC (satellite-derived rainfall & parameters)
  - GFS / WRF model outputs (numerical models)
  - ERA5 reanalysis (historical/context)
  - Third-party weather APIs & ground observations
- **Processing Layer**: Ingestion pipelines, quality checks, deduplication, normalization, and credibility scoring.
- **Intelligence Layer**: Retrieval (vector + metadata), RAG pipeline, LLM context handling, and domain logic for forecast interpretation.
- **Risk & Advisory Layer**: Event detectors, severity scoring, and action-oriented advisories.
- **Delivery Layer**: Conversational API, dashboards, alerts, and voice interfaces.

---

## Development Workflow

- Active implementation tracker and all on-going tasks are maintained in: [Implementation.md](Implementation.md).
- To get started quickly, open the `Implementation.md` Stage 1 section — it contains ready-to-run FastAPI boilerplate (database config, SQLAlchemy models, router, CORS middleware, and a bootstrap script).

---

## Technologies (Recommended)

- Backend: `FastAPI` (prototype), Python
- Database: `PostgreSQL` with `SQLAlchemy`
- Data Processing: Python pipelines (Pandas, xarray, cfgrib, netCDF4)
- Models & Reanalysis: GFS/WRF outputs, ERA5 (ECMWF), MOSDAC/IMD feeds
- AI: Retrieval + LLM (RAG) with vector store
- Deployment: Docker, Kubernetes, CI/CD

---

## How to Contribute / Next Steps

- See the live tracker: [Implementation.md](Implementation.md) — it contains what to pick up next and the Stage 1 boilerplate to run locally.
- Prefer small, focused PRs per module (ingestion, processing, intelligence, UI).

---

## License & Credits

Team Udgama — Smart India Hackathon 2026

---

## Future Scope

The modular design allows WeatherGPT to evolve into a broader environmental intelligence platform.

Potential future extensions include:

* Integration with additional satellite datasets
* IoT-based weather stations
* More regional weather models
* Additional government services
* Hyperlocal weather intelligence
* Advanced disaster prediction
* Expanded multilingual support
* More sophisticated climate analytics
* Integration with additional public-service platforms

The project proposal specifically highlights expansion through **new satellites, IoT weather stations, regional models, and additional government services** without requiring the complete system to be rebuilt.

---

## 📁 Suggested Repository Structure

```text
WeatherGPT/
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── models/
│   ├── rag/
│   ├── risk_engine/
│   └── main.py
│
├── frontend/
│   ├── components/
│   ├── pages/
│   └── services/
│
├── data/
│   ├── ingestion/
│   ├── validation/
│   └── preprocessing/
│
├── models/
│   └── README.md
│
├── tests/
│
├── docs/
│   ├── architecture/
│   └── research/
│
├── deployment/
│   ├── docker/
│   └── kubernetes/
│
├── .env.example
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## ⚙️ Getting Started

### Prerequisites

Make sure the following are installed:

* Python 3.x
* Node.js and npm
* PostgreSQL
* Docker
* Git

### Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd WeatherGPT
```

### Backend Setup

```bash
cd backend

python -m venv venv
```

Activate the virtual environment:

**Windows:**

```bash
venv\Scripts\activate
```

**Linux/macOS:**

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file based on `.env.example`.

```env
DATABASE_URL=
WEATHER_API_KEY=
LLM_API_KEY=
RAG_CONFIG=
```

> Do not commit API keys, credentials, or other secrets to the repository.

### Run the Backend

```bash
uvicorn main:app --reload
```

---

## 🧪 Testing

Run the project's test suite using:

```bash
pytest
```

### SIH 2026 Compliance Checks

The automated SIH compliance suite covers extreme telemetry validation and credibility scoring, IMD cyclone advisory retrieval through the vector-store contract, critical rainfall threshold alerts, and the `/api/health` endpoint.

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
pip install pytest httpx
pytest tests\test_sih_compliance.py -q
```

The tests use a temporary SQLite database. The RAG check uses the checked-in `backend/rag/advisory_docs/imd_cyclone_advisory.txt` fixture and does not require an LLM API key.

### Live SIH Demonstration

Run the five-phase terminal demonstration from the repository root:

```powershell
python -m backend.scripts.demo_simulation
```

It uses an isolated in-memory SQLite session, persists and verifies severe-weather alerts, retrieves the local advisory documents, applies deterministic RAG safety guardrails, and prints Hindi/Telugu translation plus mock STT/TTS outputs. FAISS and external LLM services are optional for the demonstration.

For frontend testing:

```bash
npm test
```

### Run the integrated prototype

Install the backend dependencies from the repository root:

```powershell
pip install -r backend/requirements.txt
```

Choose one supported LLM provider. Gemini is the default:

```powershell
$env:LLM_PROVIDER="gemini"
$env:GEMINI_API_KEY="your-gemini-key"
python run_app.py
```

For OpenAI instead:

```powershell
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="your-openai-key"
python run_app.py
```

`run_app.py` seeds the local FAISS advisory index when it is missing, then starts FastAPI at `http://127.0.0.1:8000`. To force a rebuild after changing advisory files, run `python -m backend.scripts.ingest_docs`. Keep API keys in environment variables and never commit them.

> Update these commands according to the final implementation of the repository.

---

## 🐳 Docker Deployment

Build the application:

```bash
docker compose build
```

Start the services:

```bash
docker compose up
```

The proposed architecture supports containerized and cloud deployment using **Docker/Kubernetes**.

---

## 🔮 Project Vision

WeatherGPT aims to move weather applications beyond simply displaying forecasts.

### Traditional Approach

```text
Weather Data → Forecast → User
```

### WeatherGPT Approach

```text
Weather Data
     ↓
Verification & Fusion
     ↓
AI + RAG
     ↓
Risk Detection
     ↓
Context Understanding
     ↓
Actionable Recommendation
     ↓
User Decision
```

The ultimate objective is to make **verified weather and climate intelligence understandable, accessible, and actionable in the user's preferred language**.

---

## 📚 Research Foundation

The project draws on research related to:

* Quality control of crowdsourced rainfall data
* Crowdsourced personal weather stations
* Noise and credibility assessment in weather observations
* Social-media-based disaster intelligence
* Flood forecasting using crowdsourced information
* Multimodal deep learning for disaster assessment

## 👨‍💻 Team Udgama

**Udgama** — Building accessible, trustworthy, and actionable weather intelligence through conversational AI.

> **From fragmented weather data to informed decisions.**
