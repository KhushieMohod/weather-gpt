# SIH 2026 Master Submission

## Submission Identity

| Field | Detail |
| --- | --- |
| Problem Statement ID | 26068 |
| Team | Udgama |
| Theme | Disaster Management |
| Idea | WeatherGPT — Conversational AI for Forecasting, Alerts & Climate Information |

This document is the detailed narrative behind the six-slide presentation structure in the repository [README.md](../README.md).

## Phase 1: Forensic Problem Autopsy

### The visible symptoms

Weather information is abundant, but it is fragmented across forecasts, advisories, satellite products, model outputs, dashboards, and local observations. Users often receive a generic forecast without the location, time window, confidence, or action context needed to make a safe decision.

### Root causes

1. **Fragmented evidence:** Official and model-derived data live in separate systems with different formats, update cycles, spatial resolutions, and terminology.
2. **Weak trust signaling:** A user cannot easily tell which source is authoritative, how fresh it is, or whether multiple sources agree.
3. **Translation from data to action:** Forecast values do not automatically become understandable decisions for a farmer, district officer, mariner, or aviation operator.
4. **Unsafe conversational abstraction:** A generic LLM can produce fluent but unsupported answers when the retrieval context is incomplete or contradictory.
5. **Alert latency:** A dashboard that requires manual refresh is not sufficient for fast-moving hazards.

### Rural accessibility gaps

Rural users may have low bandwidth, intermittent connectivity, limited digital literacy, shared devices, and a preference for regional languages or voice interaction. A useful solution therefore needs concise local advisories, multilingual delivery, graceful degradation through cached data, and interfaces that work on modest hardware. It must communicate uncertainty without requiring the user to interpret a technical chart.

### Problem statement

WeatherGPT addresses the gap between trustworthy meteorological evidence and timely, understandable action. It fuses sources, scores their credibility, applies deterministic risk logic, and uses a guarded conversational layer to explain the result for a specific place and time.

## Phase 2: Existing Solution & Gap Analysis

| Existing option | Strengths | Gap WeatherGPT addresses |
| --- | --- | --- |
| IMD Meghdoot | Government-backed advisories and farmer-oriented weather information | Primarily a destination or advisory experience; it does not unify every operational source into one conversational, evidence-ranked workflow for multiple user groups. |
| Generic LLMs | Natural-language interaction and broad explanation ability | Not inherently grounded in current official weather feeds; vulnerable to hallucination, stale knowledge, unsupported certainty, and poor hazard accountability. |
| WeatherGPT prototype | Modular ingestion, RAG, source scoring, risk engine, and real-time delivery | MVP must continue hardening connectors, validation, multilingual UX, operational monitoring, and integration contracts before production deployment. |

The goal is not to replace official systems. WeatherGPT acts as an evidence-aware interpretation and delivery layer that preserves source attribution and escalates users toward official advisories when appropriate.

## Phases 3 & 4: Red-Team Critique and Blue-Team Reconstruction

### Red-team critique

The highest-risk failure modes are:

- An LLM invents a warning, observation, source, or numerical value.
- Conflicting feeds are merged as though they describe the same place and time.
- Duplicate satellite tiles, repeated bulletins, or mirrored API records distort confidence and retrieval ranking.
- A stale advisory is presented without its issue time, validity window, or expiry state.
- A high-risk deterministic signal is softened by a conversational answer.
- Poor connectivity prevents delivery even though a prior official advisory remains useful.

### Blue-team reconstruction

#### 1. Evidence-first ingestion

Every record carries source identity, authority class, observed time, issued time, valid time window, latitude and longitude or geometry, units, provenance URL, and ingestion timestamp. Schema validation rejects malformed or incomplete records before indexing.

#### 2. Dynamic credibility scoring

The pipeline computes a score from source authority, freshness, spatial match, completeness, cross-source agreement, and historical reliability. The score is visible as metadata and is used for ranking, conflict resolution, and response citations; it is not a license for the LLM to override an official emergency bulletin.

#### 3. Deterministic SQL overrides

Safety-critical facts are resolved in a deterministic query layer before response generation. SQL overrides take precedence when a current official bulletin, active hazard threshold, or explicitly sourced observation conflicts with generated text. The response stores the selected evidence IDs and validity timestamps so that an answer can be audited and reproduced.

#### 4. Spatial and temporal deduplication

Records are grouped by normalized source, parameter, time window, and spatial cell or geometry. Near-identical observations are collapsed using configurable spatial and temporal tolerances, while genuinely different resolutions remain separately attributable. This prevents repeated tiles and mirrored bulletins from inflating confidence or crowding the FAISS index.

#### 5. Guarded RAG and response policy

FAISS retrieves relevant, credibility-ranked chunks with metadata filters for location, hazard, source, and validity. The generator must answer from retrieved evidence, state when evidence is missing or conflicting, include source and time context, and avoid fabricating precise values. If confidence is below policy thresholds, the system returns a transparent limitation and points to the relevant official channel.

#### 6. Real-time and low-connectivity delivery

WebSockets distribute new risk states and advisory updates to connected clients. Clients retain the last verified advisory, show its timestamp and expiry, and reconcile updates when connectivity returns. Multilingual templates keep emergency instructions short and consistent across languages.

### Reconstructed architecture flow

```text
Government feeds and models
        |
        v
Validated ingestion -> spatial/temporal deduplication -> credibility scoring
        |                                                   |
        v                                                   v
PostgreSQL evidence store ----------------------------> FAISS retrieval index
        |                                                   |
        +--> deterministic risk engine --> alert policy ----+
                                                            |
                                     guarded RAG + citations
                                                            |
                         multilingual API / WebSockets / dashboards
```

## Phase 15: 100-Point Self-Assessment

| Assessment area | Points | Self-assessment |
| --- | ---: | --- |
| Problem clarity and root-cause fit | 15 | Defines the evidence fragmentation, trust, accessibility, and actionability problem rather than treating a generic forecast as the solution. |
| Novelty and differentiation | 15 | Combines credibility scoring, deterministic safety overrides, spatial deduplication, FAISS RAG, risk rules, and multilingual real-time delivery. |
| Technical feasibility | 15 | Uses established components: FastAPI, PostgreSQL, FAISS, Python data tooling, WebSockets, and modular source adapters. |
| Data and research foundation | 10 | Grounds the system in IMD, IMD Meghdoot, MOSDAC, model outputs, reanalysis, and documented provenance. |
| Safety, trust, and reliability | 15 | Makes official evidence authoritative, constrains generation, records citations, handles conflicts, and exposes freshness and uncertainty. |
| MVP completeness and delivery plan | 10 | Defines a shippable first increment around priority feeds, advisories, risk endpoints, conversational access, and alerts. |
| User and operational impact | 10 | Covers farmers, SDMAs, district response teams, marine operations, and aviation stakeholders with role-specific benefits. |
| Scalability and maintainability | 5 | Keeps ingestion, intelligence, risk, storage, and delivery modular so connectors and channels can evolve independently. |
| Presentation readiness and traceability | 5 | Maps directly to the official six-slide structure and links claims to evidence, integrations, and implementation stages. |
| **Total** | **100** | **Submission-ready baseline; production readiness remains subject to connector, load, field, and safety validation.** |

## Government Integration Roadmap

1. Start with documented, permissioned IMD forecast and bulletin interfaces and preserve the original advisory metadata.
2. Integrate IMD Meghdoot content for farmer-oriented advisories, language coverage, and crop-relevant action context.
3. Integrate MOSDAC satellite-derived rainfall and geospatial products with explicit resolution, timestamp, and processing-level metadata.
4. Add source health monitoring, contract tests, rate-limit handling, and fallback behavior before operational rollout.
5. Keep every generated answer traceable to the underlying government or validated observational evidence.

## Submission Position

WeatherGPT is positioned as a responsible interpretation and alerting layer for disaster management: conversational where explanation helps, deterministic where safety demands it, and transparent about the evidence behind every recommendation.