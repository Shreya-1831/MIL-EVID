# MIL-EVID

**Static–Dynamic Evidence-Grounded Hybrid Retrieval-Augmented Generation Framework for Multi-Perspective Military Situation Analysis**

MIL-EVID is a research prototype that takes a natural-language military situation query, retrieves relevant evidence from static and dynamic sources, and produces a structured, citation-supported, multi-perspective analysis.

The system combines **BM25 lexical retrieval, dense vector retrieval, Reciprocal Rank Fusion (RRF), and cross-encoder reranking**. Future stages add dynamic evidence, perspective analysis, contradiction detection, claim verification, and explainable confidence scoring.

### Scope

MIL-EVID is an **evidence-analysis system only**. It does not perform or support military targeting, weapon selection, attack optimization, operational planning, or autonomous military decision-making.

---

## Project Status

The project is being developed incrementally in phases.

* [x] **Phase 1** — Project scaffolding, configuration, domain models, exception hierarchy, FastAPI application
* [x] **Phase 2** — Preprocessing: cleaning, normalization, deduplication, chunking
* [x] **Phase 2.5** — PDF ingestion, country-scope filtering, local chunk storage, metadata-only PostgreSQL layer
* [ ] **Phase 3** — BM25 + Dense Retrieval
* [ ] **Phase 4** — RRF + Cross-Encoder + Hybrid Retrieval
* [ ] **Phase 5** — Dynamic Evidence Layer
* [ ] **Phase 6** — Perspective Analysis
* [ ] **Phase 7** — Contradiction Detection + Claim Verification
* [ ] **Phase 8** — Confidence Scoring
* [ ] **Phase 9** — Pipeline Orchestration
* [ ] **Phase 10** — API Routes
* [ ] **Phase 11** — Database: request history and remaining schema
* [ ] **Phase 12** — Tests

---

## Data Sources

MIL-EVID is designed around multiple evidence sources:

| Source            | Role                                               |
| ----------------- | -------------------------------------------------- |
| **UCDP**          | Conflict and event data                            |
| **ICRC IHL**      | International humanitarian law and legal evidence  |
| **UN Peacemaker** | Peace agreements and conflict-resolution documents |
| **SIPRI**         | Arms transfer data                                 |
| **ACLED**         | Dynamic conflict/event evidence                    |

Static sources are processed offline, while dynamic evidence is designed to be incorporated separately during retrieval.

---

## Architecture

The overall retrieval architecture is:

```text
                    User Query
                        │
                        ▼
                 Query Processing
                        │
                        ▼
              ┌───────────────────┐
              │  Hybrid Retrieval │
              └─────────┬─────────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
            BM25               FAISS
       Lexical Search      Dense Retrieval
              │                   │
              └─────────┬─────────┘
                        ▼
                Reciprocal Rank
                    Fusion
                        │
                        ▼
              Cross-Encoder Ranking
                        │
                        ▼
                 Evidence Set
                        │
                        ▼
            Multi-Perspective Analysis
               ┌────────┼────────┐
               ▼        ▼        ▼
            Military   Legal   Historical
               │        │        │
               └────────┼────────┘
                        ▼
           Verification & Confidence
                        │
                        ▼
              Evidence-Grounded
                    Response
```

---

## Storage Architecture

Chunk text and database metadata are deliberately separated.

| Data           | Storage           | Purpose                       |
| -------------- | ----------------- | ----------------------------- |
| Chunk text     | Local JSONL files | Source of truth for retrieval |
| Chunk metadata | PostgreSQL        | Lookup and citation metadata  |
| Embeddings     | FAISS index files | Dense vector retrieval        |
| BM25 index     | Local index files | Lexical retrieval             |

Chunk text is stored locally in:

```text
backend/data/processed/chunks/
```

FAISS and BM25 indexes are stored in:

```text
backend/indexes/faiss/
backend/indexes/bm25/
```

The database stores metadata rather than the full chunk text. This keeps the PostgreSQL database lightweight and prevents large document corpora from consuming database storage unnecessarily.

---

## Repository Structure

```text
mil-evid-backend/
│
├── README.md
├── .gitignore
│
├── backend/
│   ├── app/
│   │   ├── api/
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
└── ...
```

---

## Technology Stack

### Backend

* Python
* FastAPI
* Pydantic
* Pydantic Settings
* SQLAlchemy
* PostgreSQL

### Retrieval & NLP

* BM25
* Sentence Transformers
* FAISS
* Cross-Encoder Reranking
* Natural Language Inference

### Data Processing

* PDF extraction
* Text cleaning
* Normalization
* Deduplication
* Chunking
* Country-scope filtering

---

## Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd mil-evid-backend
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure environment variables

Create `.env` from `.env.example`:

```text
backend/.env.example
        ↓
backend/.env
```

Add the required database configuration and optional dynamic-source credentials.

**Never commit `.env` or other credentials to GitHub.**

---

## Running the API

From the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The API will run locally at:

```text
http://localhost:8000
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

---

## Data Ingestion

### PDF Sources

ICRC and UN Peacemaker documents can be ingested using:

```bash
python -m scripts.ingest_pdf_sources
```

To process the local chunk store without requiring PostgreSQL:

```bash
python -m scripts.ingest_pdf_sources --skip-db
```

Individual sources can also be selected:

```bash
python -m scripts.ingest_pdf_sources --sources icrc
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

Country-scope filtering is applied to UN Peacemaker sources before PDF extraction. ICRC legal material is treated as global legal evidence.

---

## Indexing

The indexing phase represents each chunk in two complementary ways:

```text
                Chunks
                   │
          ┌────────┴────────┐
          ▼                 ▼
        BM25          Sentence Transformer
     Lexical Index       Embeddings
                              │
                              ▼
                            FAISS
```

**BM25** handles exact and keyword-oriented retrieval.

**Sentence Transformer + FAISS** handles semantic similarity.

The next retrieval stage combines these results through **Reciprocal Rank Fusion** and then applies **cross-encoder reranking**.

---

## Architecture Decisions

Several architectural decisions were made during implementation:

1. **One shared NLI adapter** is used for both contradiction detection and claim verification because both tasks rely on entailment/contradiction judgments.

2. **One shared `TextGenerationPort`** provides a common interface for query analysis, perspective analysis, and claim extraction, allowing a future LLM to be integrated without changing the core architecture.

3. **Event/topic pre-clustering** reduces unnecessary pairwise NLI comparisons by restricting contradiction analysis to potentially related evidence.

4. **Dynamic evidence uses a separate FAISS index**, which can be merged with the static retrieval results at query time.

5. **Synchronous SQLAlchemy** is used for database operations, while FastAPI handles asynchronous request execution at the API layer.

6. **Dynamic evidence caching uses PostgreSQL**, allowing freshness information to persist across application restarts.

---

## Testing

Run the test suite from the `backend` directory:

```bash
pytest
```

Tests include unit and integration coverage for preprocessing, ingestion, chunking, repositories, and data-source mappings.

---

## Configuration

Configuration is environment-based and managed through:

```text
backend/app/core/config.py
```

Configuration includes items such as:

* Database connection
* Dynamic-source credentials
* Model names
* Retrieval parameters
* Confidence-scoring parameters

See:

```text
backend/.env.example
```

for the available configuration variables.

---

## Future Pipeline

The completed system is intended to follow this flow:

```text
Military Situation Query
          ↓
    Query Analysis
          ↓
    Hybrid Retrieval
    ┌─────┴─────┐
    ↓           ↓
  BM25        FAISS
    └─────┬─────┘
          ↓
      RRF Fusion
          ↓
 Cross-Encoder Reranking
          ↓
   Evidence Selection
          ↓
 Multi-Perspective Analysis
 ┌────────┼─────────┐
 ↓        ↓         ↓
Military  Legal  Historical
 └────────┼─────────┘
          ↓
 Contradiction Detection
          ↓
   Claim Verification
          ↓
 Confidence Scoring
          ↓
 Citation-Supported Response
```

---

## Research / Development Status

MIL-EVID is currently a **research prototype under active development**.

The current implementation establishes the foundation for evidence ingestion, preprocessing, chunking, local chunk storage, and metadata persistence. Hybrid retrieval and the subsequent analysis pipeline are being implemented incrementally.
