# Implementation Tracker — WeatherGPT (Active)

This file is the active project tracker for WeatherGPT. Follow this file for current status, what to pick up next, and copy-pasteable Stage 1 boilerplate to run the prototype backend locally.

## Project Status (Roadmap)

- **Stage 1 — Base Application Skeleton & FastAPI Structure**: ✅ Completed
- **Stage 2 — Data Ingestion & Processing Pipelines**: In progress / TODO
- **Stage 3 — RAG + LLM Integration & Risk Engine**: TODO
- **Stage 4 — Frontend & Delivery Channels**: TODO
- **Stage 5 — Deployment, Scaling & Real-Time Ops**: TODO
- **Stage 7 — SIH 2026 Master Alignment**: ✅ Completed

## Stage 7 — Completed: SIH 2026 Master Alignment

- [x] Registered the official six-slide SIH 2026 presentation structure in `README.md`.
- [x] Documented the problem autopsy, existing-solution gap analysis, red-team critique, and blue-team reconstruction.
- [x] Recorded the 100-point self-assessment and the government-system integration strategy.
- [x] Linked the detailed submission master at `docs/SIH_2026_Master_Submission.md`.

---

## Stage 1 — Completed: FastAPI Skeleton & Bootstrapping

What this includes (copy-pasteable files below):

- `requirements.txt` (minimal)
- `src/app/database.py` (SQLAlchemy configuration)
- `src/app/models.py` (SQLAlchemy models)
- `src/app/schemas.py` (Pydantic schemas)
- `src/app/routers/weather.py` (FastAPI router)
- `src/app/main.py` (FastAPI app with CORS middleware)
- `scripts/bootstrap.py` (bootstrapping script to create DB tables)

Instructions: create the files below in your workspace, install the dependencies, set `DATABASE_URL`, and run `uvicorn src.app.main:app --reload`.

---

## Minimal `requirements.txt`

```text
fastapi>=0.95.0
uvicorn[standard]>=0.22.0
SQLAlchemy>=1.4
psycopg2-binary>=2.9
pydantic>=1.10
python-dotenv>=1.0
```

---

## File: `src/app/database.py`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/weatherdb")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## File: `src/app/models.py`

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, func
from .database import Base


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    parameter = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    units = Column(String, nullable=True)
    observed_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
```

---

## File: `src/app/schemas.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ObservationCreate(BaseModel):
    source: str
    lat: float
    lon: float
    parameter: str
    value: Optional[float]
    units: Optional[str]


class ObservationOut(ObservationCreate):
    id: int
    observed_at: datetime

    class Config:
        orm_mode = True
```

---

## File: `src/app/routers/weather.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.post("/observations", response_model=schemas.ObservationOut)
def create_observation(payload: schemas.ObservationCreate, db: Session = Depends(get_db)):
    obs = models.Observation(**payload.dict())
    db.add(obs)
    db.commit()
    db.refresh(obs)
    return obs


@router.get("/observations", response_model=List[schemas.ObservationOut])
def list_observations(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Observation).order_by(models.Observation.observed_at.desc()).limit(limit).all()


@router.get("/observations/{obs_id}", response_model=schemas.ObservationOut)
def get_observation(obs_id: int, db: Session = Depends(get_db)):
    obs = db.query(models.Observation).filter(models.Observation.id == obs_id).first()
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs
```

---

## File: `src/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from .database import engine, Base
from .routers import weather

app = FastAPI(title="WeatherGPT API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(weather.router)


@app.on_event("startup")
def on_startup():
    # Create tables (development bootstrap)
    Base.metadata.create_all(bind=engine)


@app.get("/healthz")
def health():
    return {"status": "ok"}
```

---

## File: `scripts/bootstrap.py`

```python
"""
Bootstrap script for local development. Creates DB tables and an example record.
Usage: `python scripts/bootstrap.py`
Ensure `DATABASE_URL` is set in environment or a `.env` file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from src.app.database import engine, Base, SessionLocal
from src.app.models import Observation


def bootstrap():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        sample = Observation(source="bootstrap", lat=12.97, lon=77.59, parameter="temp", value=30.5, units="C")
        db.add(sample)
        db.commit()
        print("Inserted sample observation id:", sample.id)
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap()
```

---

## Quickstart (Development)

1. Create a Python virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Set `DATABASE_URL` in your environment or `.env` (Postgres example):

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/weatherdb
```

3. Bootstrap and run locally:

```bash
python scripts/bootstrap.py
uvicorn src.app.main:app --reload --port 8000
```

4. API endpoints:

- `GET /healthz`
- `POST /api/weather/observations` (create)
- `GET /api/weather/observations` (list)
- `GET /api/weather/observations/{id}` (retrieve)

---

## Notes & Next Actions

- Stage 1 is complete. Next pick: implement Stage 2 ingestion connectors (IMD pull, MOSDAC S3 or API, GFS/WRF fetcher, ERA5 ingestion), build validation/dedup pipeline, and add an ingestion queue / scheduler.
- Add tests for the API and CI for formatting and linting.

---

If you'd like, I can: create these files in the repo directly, or scaffold a small Docker Compose for local Postgres + the FastAPI service. Tell me which next step you prefer.
