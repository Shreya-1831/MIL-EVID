# MIL-EVID

## Static–Dynamic Evidence-Grounded Hybrid Retrieval-Augmented Generation Framework for Multi-Perspective Military Situation Analysis

MIL-EVID is an evidence-grounded research prototype for analyzing complex military and geopolitical situations from multiple analytical perspectives.

The system accepts a natural-language query, retrieves relevant evidence from static and dynamic sources, combines lexical and semantic retrieval, reranks evidence using a cross-encoder, and generates structured analysis across three perspectives:

- **Military**
- **Legal**
- **Historical**

The system also performs claim verification, contradiction detection, confidence scoring, and citation generation while maintaining persistent analysis history through PostgreSQL.

MIL-EVID is designed to provide an auditable evidence-analysis workflow rather than an opaque generative response.

---

## Scope

MIL-EVID is an **evidence-analysis and research system only**.

It does **not** perform or support:

- Military targeting
- Weapon selection
- Attack optimization
- Operational military planning
- Autonomous military decision-making
- Target identification
- Tactical engagement recommendations

The system focuses on evidence retrieval, source-grounded analysis, verification, contradiction identification, and explainability.

---

# Project Status

MIL-EVID has progressed from the initial ingestion and retrieval foundation into an integrated evidence-grounded analysis pipeline.

### Implementation Status

- [x] **Phase 1** — Project scaffolding, configuration, domain models, exception hierarchy, FastAPI application
- [x] **Phase 2** — Text preprocessing: cleaning, normalization, deduplication, chunking
- [x] **Phase 2.5** — PDF ingestion, country-scope filtering, local chunk storage, metadata persistence
- [x] **Phase 3** — BM25 lexical retrieval
- [x] **Phase 3** — Dense vector retrieval using Sentence Transformers and FAISS
- [x] **Phase 4** — Reciprocal Rank Fusion (RRF)
- [x] **Phase 4** — Cross-encoder reranking
- [x] **Phase 4** — Hybrid retrieval pipeline
- [x] **Phase 5** — Dynamic evidence retrieval
- [x] **Phase 5** — ACLED integration
- [x] **Phase 6** — Perspective-aware retrieval
- [x] **Phase 6** — Military perspective analysis
- [x] **Phase 6** — Legal perspective analysis
- [x] **Phase 6** — Historical perspective analysis
- [x] **Phase 7** — Claim verification
- [x] **Phase 7** — Contradiction detection
- [x] **Phase 8** — Confidence scoring
- [x] **Phase 9** — End-to-end pipeline orchestration
- [x] **Phase 9** — Real-time backend analysis status tracking
- [x] **Phase 10** — FastAPI analysis, evidence, retrieval, claims, perspective, ingestion, system, and authentication routes
- [x] **Phase 11** — PostgreSQL persistence for queries, analyses, perspectives, evidence, claims, and contradictions
- [x] **Phase 11** — Analysis history and persistent analysis records
- [x] **Phase 12** — React-based analyst dashboard and analysis interface
- [x] **Phase 12** — Frontend polling for real backend analysis progress
- [x] **Phase 12** — JWT authentication and token refresh workflow
- [x] **Phase 12** — Dashboard statistics and evidence-source visualization
- [x] **Phase 12** — Analysis history and persisted result visualization
- [ ] **Phase 13** — Extended evaluation, benchmarking, and research experiments

---

# Key Features

## 1. Hybrid Evidence Retrieval

MIL-EVID combines multiple retrieval strategies:

- BM25 lexical retrieval
- Dense semantic retrieval
- FAISS vector search
- Reciprocal Rank Fusion
- Cross-encoder reranking

This allows the system to capture both:

- Exact keyword and terminology matches
- Semantically related evidence

---

## 2. Perspective-Aware Analysis

The system analyzes retrieved evidence from three perspectives:

```text
                    Evidence
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     Military         Legal       Historical
        │              │              │
        └──────────────┼──────────────┘
                       ▼
              Multi-Perspective
                  Synthesis
```

### Military Perspective

Focuses on military developments, conflict dynamics, strategic context, and relevant evidence.

### Legal Perspective

Examines relevant international humanitarian law and legal frameworks supported by retrieved evidence.

### Historical Perspective

Examines historical context, precedents, agreements, and conflict developments relevant to the query.

---

## 3. Static and Dynamic Evidence

MIL-EVID supports two evidence categories.

### Static Evidence

Static sources are processed offline and indexed for retrieval.

Current source categories include:

| Source | Role |
|---|---|
| **UCDP** | Conflict and event data |
| **ICRC Customary IHL** | International humanitarian law evidence |
| **UN Peacemaker** | Peace agreements and conflict-resolution documents |
| **SIPRI** | Arms transfer and security-related data |
| **ACLED** | Dynamic conflict and event evidence |

### Dynamic Evidence

Dynamic evidence can be retrieved at analysis time.

The current dynamic retrieval layer supports **ACLED-based evidence retrieval**, including configurable country and date parameters.

Dynamic evidence can be incorporated alongside static retrieval results during analysis.

---

# System Architecture

The current end-to-end architecture is:

```text
                         User
                          │
                          ▼
                  Natural Language Query
                          │
                          ▼
                  ┌─────────────────┐
                  │ Query Processing│
                  └────────┬────────┘
                           │
                           ▼
                Perspective-Aware Retrieval
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
         Military        Legal       Historical
             │             │             │
             └─────────────┼─────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Hybrid Retrieval│
                  └────────┬────────┘
                           │
                  ┌────────┴────────┐
                  ▼                 ▼
                BM25              FAISS
           Lexical Retrieval   Dense Retrieval
                  │                 │
                  └────────┬────────┘
                           ▼
                  Reciprocal Rank Fusion
                           │
                           ▼
                 Cross-Encoder Reranking
                           │
                           ▼
                    Evidence Selection
                           │
                           ▼
                Evidence Context Builder
                           │
                           ▼
               Multi-Perspective Analysis
                 ┌─────────┼─────────┐
                 ▼         ▼         ▼
              Military   Legal   Historical
                 │         │         │
                 └─────────┼─────────┘
                           ▼
                  Claim Extraction
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
          Claim Verification   Contradiction Detection
                 │                   │
                 └─────────┬─────────┘
                           ▼
                    Confidence Scoring
                           │
                           ▼
                  Citation Generation
                           │
                           ▼
                 Persisted Analysis
                           │
                           ▼
                Evidence-Grounded Response
```

---

# Real-Time Analysis Pipeline

The frontend does not simulate analysis progress.

Analysis stages are driven by the backend processing state stored in PostgreSQL.

The current processing states are:

```text
q   → Query Processing
r   → Perspective Retrieval
e   → Evidence Retrieval
rr  → Reranking
mp  → Multi-Perspective Analysis
cv  → Claim Verification
cd  → Contradiction Detection
cs  → Confidence Scoring
rg  → Response Generation
```

Final states:

```text
completed
failed
```

The frontend polls the backend analysis endpoint while processing is active.

```text
Frontend
    │
    │ POST /api/analysis
    ▼
Backend creates analysis record
    │
    │ returns analysis_id
    ▼
Frontend starts polling
    │
    │ GET /api/analysis/{id}
    │
    ├── q
    ├── r
    ├── e
    ├── rr
    ├── mp
    ├── cv
    ├── cd
    ├── cs
    ├── rg
    └── completed
```

This ensures that the processing interface reflects actual backend execution rather than a frontend timer or simulated progress sequence.

---

# Evidence Retrieval Architecture

MIL-EVID uses a hybrid retrieval architecture.

```text
                         Query
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
          BM25 Search             Dense Search
              │                         │
              │                    Sentence
              │                   Transformer
              │                         │
              │                       FAISS
              │                         │
              └────────────┬────────────┘
                           ▼
                    RRF Fusion
                           │
                           ▼
                 Cross-Encoder Reranker
                           │
                           ▼
                 Ranked Evidence Set
```

### BM25

BM25 provides lexical retrieval for exact terms, entities, names, and domain-specific terminology.

### Dense Retrieval

Sentence Transformer embeddings are used to represent evidence chunks semantically.

The current embedding model is:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Dense vectors are indexed using FAISS.

### Reciprocal Rank Fusion

RRF combines results from lexical and semantic retrieval into a unified ranking.

### Cross-Encoder Reranking

The retrieved candidates are reranked using a cross-encoder to improve query-evidence relevance before the evidence is passed to the analysis stage.

---

# Perspective-Aware Retrieval

Retrieval is performed with awareness of the requested analytical perspectives.

The system currently uses exactly three perspectives:

```text
Military
Legal
Historical
```

The retrieved evidence retains source and perspective metadata so that downstream analysis can distinguish evidence provenance and relevance.

Example evidence metadata:

```text
Source:
UCDP Dyadic

Perspective:
Historical

Chunk:
ucdp-dyadic-14117-2022::chunk-0000

Reranker Score:
0.1157
```

Perspective-aware retrieval allows evidence from one source category to remain useful to another analytical perspective when the evidence is relevant to the query.

---

# Evidence Context Construction

After retrieval and reranking, the system constructs an evidence context for the language model.

The context builder is responsible for:

- Selecting relevant evidence
- Preserving source metadata
- Maintaining perspective information
- Preparing evidence for multi-perspective analysis
- Supporting citation generation
- Incorporating dynamic evidence when available

The final response is therefore generated from a structured evidence context rather than an unrestricted language-model prompt.

---

# Claim Verification

MIL-EVID performs claim-level verification after multi-perspective analysis.

The verification stage evaluates generated claims against available evidence using the system's natural-language inference infrastructure.

The verification process is intended to identify whether generated claims are adequately supported by retrieved evidence.

---

# Contradiction Detection

MIL-EVID also detects potentially contradictory evidence.

The contradiction detection pipeline uses:

```text
Evidence
   ↓
Event / Topic Pre-Clustering
   ↓
Candidate Evidence Pairs
   ↓
NLI Analysis
   ↓
Contradiction Identification
```

Pre-clustering reduces unnecessary pairwise comparisons by restricting NLI evaluation to potentially related evidence.

A shared NLI adapter is used for both:

- Claim verification
- Contradiction detection

---

# Confidence Scoring

The system calculates an overall confidence score using evidence and verification signals.

Confidence is represented internally on a:

```text
0–100 scale
```

For example:

```text
47.1
```

is displayed as:

```text
47.1%
```

Confidence is intended to provide an explainable indication of evidence-supported analysis quality rather than a guarantee of factual correctness.

---

# Citation Support

MIL-EVID preserves evidence metadata throughout the retrieval and analysis pipeline.

The system can associate generated analytical content with the evidence used to support it.

Citation-related metadata can include:

- Source name
- Source type
- Publication information
- Evidence chunk identifier
- Perspective
- Evidence text or local chunk reference

This enables the resulting analysis to remain traceable to its evidence base.

---

# Storage Architecture

MIL-EVID deliberately separates retrieval data from relational metadata.

| Data | Storage | Purpose |
|---|---|---|
| Chunk text | Local JSONL files | Source of truth for retrieval |
| Chunk metadata | PostgreSQL | Lookup and citation metadata |
| Embeddings | FAISS index files | Dense retrieval |
| BM25 index | Local index files | Lexical retrieval |
| Query history | PostgreSQL | Persistent user analysis history |
| Analysis records | PostgreSQL | Analysis lifecycle and results |
| Perspective results | PostgreSQL | Persisted multi-perspective analysis |
| Claims | PostgreSQL | Claim-level persistence |
| Contradictions | PostgreSQL | Contradiction persistence |
| Dynamic evidence metadata | PostgreSQL | Freshness and persistence |

Chunk text is stored locally in:

```text
backend/data/processed/chunks/
```

FAISS indexes are stored in:

```text
backend/indexes/faiss/
```

BM25 indexes are stored in:

```text
backend/indexes/bm25/
```

The PostgreSQL database primarily stores metadata, application state, and persisted analysis results.

---

# Database Architecture

MIL-EVID uses PostgreSQL with SQLAlchemy.

The database stores persistent application state including:

```text
Users
  │
  ▼
Queries
  │
  ▼
Analyses
  │
  ├── Perspectives
  ├── Evidence
  ├── Claims
  └── Contradictions
```

Analysis lifecycle information includes:

- Analysis ID
- Query ID
- Status
- Final answer
- Overall confidence
- Start time
- Completion time

The analysis status is stored using compact processing-stage identifiers such as:

```text
q
r
e
rr
mp
cv
cd
cs
rg
completed
failed
```

No separate migration-only progress columns are required for the current implementation.

---

# Authentication

MIL-EVID provides API authentication and user-specific analysis history.

Authentication endpoints include:

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/auth/me
```

The frontend maintains authenticated sessions and supports access-token refresh when a token expires during long-running analysis polling.

---

# API

The FastAPI backend exposes multiple API modules.

Current API areas include:

```text
/api/auth
/api/analysis
/api/evidence
/api/retrieval
/api/claims
/api/perspectives
/api/ingestion
/api/system
```

### Analysis

```text
POST /api/analysis
GET  /api/analysis
GET  /api/analysis/{analysis_id}
DELETE /api/analysis/{analysis_id}
```

### Authentication

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
GET  /api/auth/me
```

### Evidence

```text
GET /api/evidence
GET /api/evidence/{id}
GET /api/evidence/sources
```

Exact request and response schemas are available through the FastAPI OpenAPI documentation.

---

# Frontend

MIL-EVID includes a React-based analyst interface.

The frontend provides:

- Analyst dashboard
- New analysis interface
- Real-time analysis status
- Analysis history
- Evidence exploration
- Perspective visualization
- Evidence-source statistics
- Confidence statistics
- Analysis trend visualization
- Authentication
- User profile/session information

The dashboard uses persisted backend data rather than mock analysis values.

---

# Dashboard

The dashboard provides an overview of the user's analysis history.

Current dashboard metrics include:

```text
Total Analyses
Completed Analyses
Average Confidence
Evidence Records
```

Additional visualizations include:

- Analysis trends
- Perspective distribution
- Evidence source distribution
- Recent analyses
- Perspective coverage

Confidence values are displayed consistently using the backend's 0–100 representation.

---

# Repository Structure

The repository is organized into backend and frontend components.

```text
mil-evid/
│
├── README.md
├── .gitignore
│
├── backend/
│   │
│   ├── app/
│   │   ├── api/
│   │   │   ├── routers/
│   │   │   └── schemas/
│   │   │
│   │   ├── core/
│   │   ├── database/
│   │   ├── domain/
│   │   ├── modules/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── utils/
│   │
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │   ├── dynamic/
│   │   └── pilot/
│   │
│   ├── indexes/
│   │   ├── faiss/
│   │   └── bm25/
│   │
│   ├── scripts/
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── ...
│   │
│   ├── public/
│   ├── package.json
│   └── ...
│
└── ...
```

---

# Technology Stack

## Backend

- Python
- FastAPI
- Pydantic
- Pydantic Settings
- SQLAlchemy
- PostgreSQL
- Uvicorn

## Retrieval & NLP

- BM25
- Sentence Transformers
- FAISS
- Cross-Encoder Reranking
- Natural Language Inference
- Ollama / local LLM inference

## Data Processing

- PDF extraction
- Text cleaning
- Normalization
- Deduplication
- Chunking
- Country-scope filtering
- Metadata extraction

## Dynamic Evidence

- ACLED

## Frontend

- React
- React Router
- Recharts
- Lucide React
- Tailwind CSS / utility-based styling

---

# Setup

## 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd mil-evid
```

---

# Backend Setup

## 2. Create a Virtual Environment

From the backend directory:

```bash
cd backend
python -m venv .venv
```

Activate on Windows:

```bash
.venv\Scripts\activate
```

Activate on Linux/macOS:

```bash
source .venv/bin/activate
```

---

## 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Create the environment file:

```text
backend/.env.example
        ↓
backend/.env
```

Configure the required values, including database settings and optional dynamic-source credentials.

Never commit:

```text
.env
```

or other credentials and secrets to GitHub.

---

# Running the Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

Health endpoint:

```text
http://localhost:8000/health
```

---

# Frontend Setup

Open another terminal.

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Run the development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

The frontend communicates with the FastAPI backend running on:

```text
http://localhost:8000
```

---

# Data Ingestion

## PDF Sources

ICRC and UN Peacemaker documents can be processed using:

```bash
python -m scripts.ingest_pdf_sources
```

To process local chunks without requiring PostgreSQL:

```bash
python -m scripts.ingest_pdf_sources --skip-db
```

Individual source categories can be selected:

```bash
python -m scripts.ingest_pdf_sources --sources icrc
```

```bash
python -m scripts.ingest_pdf_sources --sources un_peacemaker
```

The ingestion pipeline follows:

```text
Raw Documents
      ↓
PDF Extraction
      ↓
Evidence Mapping
      ↓
Cleaning
      ↓
Normalization
      ↓
Deduplication
      ↓
Chunking
      ↓
Local Chunk Store
      ↓
Metadata Store
```

Country-scope filtering is applied to relevant UN Peacemaker sources before PDF extraction.

ICRC legal material is treated as global legal evidence.

---

# Indexing

Evidence chunks are represented through two complementary retrieval mechanisms:

```text
                    Evidence Chunks
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
           BM25              Sentence Transformer
      Lexical Representation       Embeddings
             │                         │
             │                       FAISS
             │                         │
             └────────────┬────────────┘
                          ▼
                     RRF Fusion
                          │
                          ▼
                 Cross-Encoder
                    Reranking
```

BM25 handles lexical and exact-match retrieval.

Sentence Transformers and FAISS provide semantic retrieval.

RRF combines the retrieval results.

The cross-encoder then reranks candidate evidence before context construction.

---

# Dynamic Evidence

Dynamic evidence is retrieved separately from static indexed evidence.

Current dynamic integration includes ACLED.

Dynamic retrieval supports configurable parameters such as:

```text
Country
Start Date
End Date
Updated Since
```

Dynamic evidence can then be incorporated into the analysis evidence set.

The architecture keeps dynamic retrieval separate from the static indexing layer so that freshness-sensitive information can be obtained at analysis time.

---

# Analysis Request

An analysis request accepts a natural-language query and retrieval configuration.

Example:

```json
{
  "query": "How did a major military conflict alter the regional military balance?",
  "retrieval_top_k": 50,
  "rerank_top_k": 8
}
```

Optional ACLED parameters can be supplied when dynamic evidence is required.

The backend currently uses three analytical perspectives:

```text
Military
Legal
Historical
```

---

# Analysis Lifecycle

A typical analysis proceeds through:

```text
1. Query Processing
        ↓
2. Perspective Retrieval
        ↓
3. Evidence Retrieval
        ↓
4. Reranking
        ↓
5. Multi-Perspective Analysis
        ↓
6. Claim Verification
        ↓
7. Contradiction Detection
        ↓
8. Confidence Scoring
        ↓
9. Response Generation
        ↓
10. Persistence
```

The resulting analysis is stored in PostgreSQL for later access through the analysis history.

---

# Architecture Decisions

Several architectural decisions guide the implementation.

### 1. Shared NLI Adapter

A shared NLI adapter is used for both contradiction detection and claim verification because both tasks require entailment and contradiction judgments.

### 2. Shared Text Generation Interface

A shared `TextGenerationPort` provides a common interface for:

- Query analysis
- Perspective analysis
- Claim extraction

This allows the underlying LLM implementation to be changed without redesigning the core application architecture.

### 3. Event / Topic Pre-Clustering

Evidence is pre-clustered by potentially related events or topics before contradiction analysis.

This reduces unnecessary pairwise NLI comparisons.

### 4. Separate Dynamic Evidence Layer

Dynamic evidence is retrieved independently from the static evidence indexes.

This allows time-sensitive information to be incorporated without rebuilding the static corpus.

### 5. PostgreSQL Persistence

PostgreSQL is used for persistent application metadata and analysis history.

Large retrieval corpora remain outside the relational database.

### 6. Local Retrieval Indexes

FAISS and BM25 indexes are stored locally for efficient retrieval.

### 7. Synchronous SQLAlchemy

The current implementation uses synchronous SQLAlchemy database operations while FastAPI manages API request execution and background analysis processing.

### 8. Backend-Driven Processing Status

Analysis progress is represented by backend state rather than frontend timers.

This keeps the UI synchronized with actual pipeline execution.

---

# Testing

Run the test suite from the backend directory:

```bash
pytest
```

Tests cover the implemented backend components including areas such as:

- Preprocessing
- Ingestion
- Chunking
- Data-source mappings
- Repository behavior
- Application components

Additional evaluation and benchmarking are part of ongoing research development.

---

# Configuration

Application configuration is managed through:

```text
backend/app/core/config.py
```

Configuration includes values related to:

- PostgreSQL connection
- Database pool configuration
- Dynamic-source credentials
- Model configuration
- Retrieval parameters
- Reranking parameters
- Confidence-scoring parameters
- Application settings

See:

```text
backend/.env.example
```

for available environment variables.

---

# Example End-to-End Workflow

A typical MIL-EVID workflow is:

```text
User enters a military situation query
              │
              ▼
        Query Processing
              │
              ▼
    Perspective-Aware Retrieval
              │
              ▼
       BM25 + Dense Search
              │
              ▼
          RRF Fusion
              │
              ▼
    Cross-Encoder Reranking
              │
              ▼
      Evidence Context
              │
              ▼
   ┌──────────┼──────────┐
   ▼          ▼          ▼
Military     Legal    Historical
Analysis    Analysis   Analysis
   │          │          │
   └──────────┼──────────┘
              ▼
       Claim Verification
              │
              ▼
     Contradiction Detection
              │
              ▼
       Confidence Scoring
              │
              ▼
      Citation Generation
              │
              ▼
      Persisted Analysis
              │
              ▼
      Analyst Dashboard
```

---

# Research Objectives

MIL-EVID is intended to investigate how retrieval-augmented generation can be combined with:

- Multi-perspective evidence analysis
- Hybrid lexical and semantic retrieval
- Dynamic evidence retrieval
- Evidence provenance
- Claim verification
- Contradiction detection
- Confidence estimation
- Explainable citation support

The broader objective is to improve the traceability and interpretability of generated analysis by explicitly grounding the system in retrieved evidence.

---

# Current Development Focus

The current implementation has established the core end-to-end application.

Current development areas include:

- Retrieval quality evaluation
- Evidence ranking evaluation
- Multi-perspective analysis evaluation
- Claim verification evaluation
- Contradiction detection evaluation
- Confidence calibration
- Dynamic evidence evaluation
- Larger-scale benchmarking
- Research experimentation
- System performance optimization

---

# Limitations

MIL-EVID remains a research prototype and has several limitations.

### Evidence Coverage

The quality of the generated analysis depends on the coverage, freshness, and quality of the available evidence sources.

### Retrieval Errors

Relevant evidence may not always be retrieved, while retrieved evidence may sometimes be only partially relevant.

### Model Limitations

Language-model outputs may contain errors even when evidence is provided.

### Confidence Interpretation

The confidence score is an analytical signal and should not be interpreted as a guarantee of factual correctness.

### Dynamic Data

Dynamic evidence availability depends on the corresponding external data source and configured access credentials.

### Research Prototype

The system is intended for research and evaluation rather than deployment as an autonomous operational decision-making system.

---

# Security and Privacy Considerations

The application uses authenticated API access and user-specific analysis history.

Sensitive configuration values must be stored in environment variables rather than source code.

Do not commit:

```text
.env
API credentials
Database passwords
Authentication secrets
Access tokens
Private keys
```

to the repository.

---

# Research / Development Status

MIL-EVID is currently an **integrated research prototype under active development**.

The current implementation includes:

- Evidence ingestion
- Text preprocessing
- Local chunk storage
- BM25 retrieval
- Dense retrieval
- FAISS indexing
- Hybrid retrieval
- Reciprocal Rank Fusion
- Cross-encoder reranking
- Dynamic ACLED evidence retrieval
- Perspective-aware retrieval
- Military analysis
- Legal analysis
- Historical analysis
- Claim verification
- Contradiction detection
- Confidence scoring
- Citation support
- PostgreSQL persistence
- Authentication
- Real-time analysis status tracking
- React analyst dashboard
- Analysis history
- Evidence exploration

The next stage of development focuses on systematic evaluation, benchmarking, confidence calibration, retrieval quality, and research experimentation.

---

# License

Add the project's applicable license here.

```text
License: To be determined
```

---

# Disclaimer

MIL-EVID is an academic/research-oriented evidence analysis system.

It is designed to support research, evidence exploration, and structured analysis. It does not provide military operational advice, targeting recommendations, weapons guidance, or autonomous military decision-making.
