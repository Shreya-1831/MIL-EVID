# MIL-EVID

## An Evidence-Grounded Hybrid RAG Framework for Multi-Perspective Military Situation Analysis

MIL-EVID is a research-oriented evidence analysis framework designed to
support structured examination of complex military and geopolitical
situations. It combines heterogeneous static knowledge sources with
dynamically retrieved conflict-event information, hybrid lexical and
semantic retrieval, evidence reranking, multi-perspective language-model
analysis, and post-generation verification.

Rather than treating a language model's response as an isolated answer,
MIL-EVID preserves the relationship between retrieved evidence and
generated analysis. Its workflow is designed to improve evidence
relevance, traceability, transparency, and the identification of
potentially unsupported or contradictory claims.

> **Scope:** MIL-EVID is an academic research and evidence-analysis
> system. It is not intended for targeting, weapons guidance, tactical
> engagement, operational military planning, or autonomous military
> decision-making.

------------------------------------------------------------------------

## Table of Contents

-   [Objectives](#objectives)
-   [Key Capabilities](#key-capabilities)
-   [System Architecture](#system-architecture)
-   [End-to-End Workflow](#end-to-end-workflow)
-   [Hybrid Retrieval Pipeline](#hybrid-retrieval-pipeline)
-   [Evidence Sources](#evidence-sources)
-   [Multi-Perspective Analysis](#multi-perspective-analysis)
-   [Evidence Verification and
    Confidence](#evidence-verification-and-confidence)
-   [Data Processing and Storage](#data-processing-and-storage)
-   [Technology Stack](#technology-stack)
-   [Repository Structure](#repository-structure)
-   [Prerequisites](#prerequisites)
-   [Installation and Configuration](#installation-and-configuration)
-   [Running the Application](#running-the-application)
-   [Render Deployment](#render-deployment)
-   [Data Ingestion and Indexing](#data-ingestion-and-indexing)
-   [API Overview](#api-overview)
-   [Testing](#testing)
-   [Configuration Areas](#configuration-areas)
-   [Research Evaluation](#research-evaluation)
-   [Limitations](#limitations)
-   [Security Considerations](#security-considerations)
-   [Future Work](#future-work)
-   [License](#license)
-   [Disclaimer](#disclaimer)

------------------------------------------------------------------------

## Objectives

MIL-EVID investigates how a unified Retrieval-Augmented Generation (RAG)
pipeline can support complex military situation analysis by combining:

1.  **Hybrid retrieval** to capture both exact terminology and semantic
    similarity.
2.  **Evidence fusion and reranking** to improve the relevance of
    candidate passages.
3.  **Static and dynamic evidence integration** to combine curated
    reference material with time-sensitive conflict-event data.
4.  **Multi-perspective analysis** across military, legal, and
    historical dimensions.
5.  **Claim-level verification and contradiction detection** to identify
    analytical statements that may be unsupported or inconsistent with
    the available evidence.
6.  **Confidence-aware response generation** to communicate
    evidence-quality signals.
7.  **Evidence provenance and citations** to make the analysis easier to
    inspect and audit.
8.  **Persistent analysis records** to support history, review, and
    system evaluation.

## Key Capabilities

### 1. Hybrid Evidence Retrieval

The retrieval subsystem combines:

-   **BM25** for lexical retrieval and exact terminology matching.
-   **Sentence Transformers** for dense semantic embeddings.
-   **FAISS** for efficient vector similarity search.
-   **Reciprocal Rank Fusion (RRF)** to combine lexical and semantic
    result rankings.
-   **Cross-encoder reranking** to refine candidate ordering based on
    query--evidence relevance.

This design aims to reduce dependence on a single retrieval method.

### 2. Static and Dynamic Evidence

The framework supports offline processing and indexing of static
sources, while configured dynamic-source integration can retrieve
current event information at analysis time. Dynamic evidence can
supplement, rather than replace, the indexed evidence corpus.

### 3. Three Analytical Perspectives

Analysis is structured into three perspectives:

-   **Military:** relevant military developments, conflict dynamics, and
    broader situation context.
-   **Legal:** relevant legal frameworks and international humanitarian
    law, based on retrieved material.
-   **Historical:** historical context, precedents, agreements, and
    relevant developments over time.

The perspectives are intended to complement one another; they are not
independent guarantees of correctness.

### 4. Evidence Verification

The analysis pipeline includes claim verification and contradiction
detection. These stages compare generated claims and retrieved passages
using the available verification/NLI components and surface potential
support gaps or inconsistencies for review.

### 5. Confidence Scoring

MIL-EVID calculates an evidence-based confidence signal using factors
such as relevance, agreement, freshness, and source reliability. The
score is an analytical indicator, not a calibrated probability that a
statement is true.

### 6. Analyst Interface and Persistence

The React interface supports query submission, multi-perspective result
presentation, evidence inspection, confidence information, and analysis
history. FastAPI exposes the backend pipeline through API routes, while
PostgreSQL stores application and analysis metadata.

------------------------------------------------------------------------

## System Architecture

``` text
                         Analyst
                            |
                            v
                  Natural-Language Query
                            |
                            v
                    Query Processing
                            |
                            v
                 Perspective-Aware Pipeline
                            |
             +--------------+--------------+
             |                             |
             v                             v
      Static Evidence                Dynamic Evidence
   (processed and indexed)          (configured source API)
             |                             |
             +--------------+--------------+
                            |
                            v
                    Hybrid Retrieval
                    /              \
                   v                v
             BM25 Retrieval    Dense Retrieval
                                  |
                         Sentence Transformer
                                  |
                                 FAISS
                   \                /
                    +--------------+
                            |
                            v
                  Reciprocal Rank Fusion
                            |
                            v
                  Cross-Encoder Reranking
                            |
                            v
                    Evidence Selection
                            |
                            v
                 Evidence Context Construction
                            |
                            v
                 Multi-Perspective Analysis
                  /          |           \
                 v           v            v
             Military       Legal      Historical
                  \          |           /
                   +---------+----------+
                            |
                            v
                    Claim Verification
                            |
                            v
                   Contradiction Detection
                            |
                            v
                     Confidence Scoring
                            |
                            v
                 Evidence-Linked Response
                            |
                            v
                 PostgreSQL Persistence
                            |
                            v
                     React Dashboard
```

### Main Components

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Data ingestion                      Loads source datasets and documents
                                      for processing.

  Preprocessing                       Normalizes text and metadata,
                                      removes unwanted characters, and
                                      handles duplicates.

  Chunking                            Splits documents into
                                      retrieval-sized passages while
                                      preserving useful context.

  BM25 index                          Supports lexical retrieval over
                                      indexed evidence.

  Embedding model                     Encodes evidence passages and
                                      queries into dense vectors.

  FAISS index                         Supports dense vector similarity
                                      search.

  RRF fusion                          Combines candidate rankings from
                                      lexical and dense retrieval.

  Cross-encoder reranker              Reorders retrieved candidates using
                                      query--passage relevance.

  Perspective analysis                Produces military, legal, and
                                      historical analyses from the
                                      selected evidence.

  Claim verifier                      Assesses whether generated claims
                                      are supported by available
                                      evidence.

  Contradiction detector              Identifies potentially conflicting
                                      evidence or claims.

  Confidence scorer                   Aggregates evidence-quality signals
                                      into a confidence indicator.

  FastAPI backend                     Exposes analysis and supporting
                                      capabilities through API endpoints.

  PostgreSQL                          Stores application state, metadata,
                                      and persistent analysis records.

  React frontend                      Provides the analyst-facing
                                      interface and analysis history.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## End-to-End Workflow

A typical analysis follows these stages:

1.  **Query submission:** The analyst enters a natural-language question
    about a military or geopolitical situation.
2.  **Query processing:** The backend prepares the query and checks
    whether it is sufficiently specific for analysis.
3.  **Evidence retrieval:** BM25 and dense retrieval independently
    identify candidate evidence.
4.  **Rank fusion:** RRF merges the candidate lists into a combined
    ranking.
5.  **Reranking:** A cross-encoder refines the ranking of retrieved
    evidence.
6.  **Evidence selection:** The system selects a bounded set of relevant
    passages and retains their source metadata.
7.  **Context construction:** The selected passages are assembled into
    an evidence context for generation.
8.  **Multi-perspective analysis:** The language model produces
    military, legal, and historical perspectives.
9.  **Claim verification:** Generated claims are compared with the
    available evidence.
10. **Contradiction detection:** Potentially conflicting evidence or
    claims are identified.
11. **Confidence scoring:** Evidence relevance, agreement, freshness,
    and reliability signals contribute to the confidence indicator.
12. **Response assembly:** The system returns structured analysis with
    available evidence references and verification information.
13. **Persistence:** Analysis state and supported results are stored for
    later access through the application.

The actual evidence available to a query depends on the indexed corpus,
source coverage, retrieval settings, and any configured dynamic-source
access.

------------------------------------------------------------------------

## Hybrid Retrieval Pipeline

### BM25 Lexical Retrieval

BM25 ranks passages using lexical overlap and term-frequency-based
relevance. It is useful for exact names, dates, terminology, and
domain-specific phrases that may be important in military and legal
documents.

### Dense Semantic Retrieval

The embedding model represents queries and evidence chunks in a shared
vector space. This enables retrieval of semantically related passages
even when the query and evidence use different wording.

**Embedding model:**

``` text
sentence-transformers/all-MiniLM-L6-v2
```

The model is intentionally specified as part of the project
configuration and should not be silently replaced when reproducing the
reported pipeline.

### FAISS Vector Search

FAISS indexes dense vectors and retrieves nearest-neighbour candidates.
The implementation uses an inner-product index (`IndexFlatIP`); vector
normalization and similarity interpretation should remain consistent
between indexing and querying.

### Reciprocal Rank Fusion

RRF combines rankings from the BM25 and dense retrieval channels. It
uses rank positions rather than directly comparing scores from different
retrieval systems, helping integrate the two result lists.

Conceptually:

``` text
BM25 candidate ranking ---------+
                                 +--> Reciprocal Rank Fusion --> Combined ranking
FAISS candidate ranking --------+
```

### Cross-Encoder Reranking

The cross-encoder evaluates query--passage pairs and reranks the fused
candidate set. This additional relevance-estimation step is applied
before evidence is supplied to the generation stage.

### Retrieval Traceability

Evidence metadata is retained through retrieval and analysis so that the
system can associate relevant output with its source and evidence
record. Retrieval relevance does not, by itself, establish that a source
is authoritative or that a claim is true.

------------------------------------------------------------------------

## Evidence Sources

The framework integrates heterogeneous source categories to cover
conflict events, military-related data, legal material, and peace
processes.

  -----------------------------------------------------------------------
  Source                  Evidence category       Intended contribution
  ----------------------- ----------------------- -----------------------
  **UCDP Georeferenced    Conflict-event records  Structured information
  Event Dataset (GED)**                           about organized
                                                  violence and conflict
                                                  events.

  **UCDP Dyadic Dataset** Conflict-party records  Information about
                                                  conflict dyads and
                                                  parties to conflict.

  **SIPRI**               Security and            Security-related data
                          arms-transfer           and relevant
                          information             arms-transfer context.

  **ICRC International    Legal documents and     Legal evidence relevant
  Humanitarian Law        reference material      to international
  (IHL)**                                         humanitarian law.

  **UN Peacemaker**       Peace agreements and    Agreements,
                          documents               negotiations, and
                                                  conflict-resolution
                                                  context.

  **ACLED API**           Dynamic conflict-event  Configurable event
                          data                    information retrieved
                                                  from an external source
                                                  when access is
                                                  available.
  -----------------------------------------------------------------------

### Static Evidence

Static datasets and documents are processed into normalized evidence
chunks and indexed for retrieval. This permits repeatable retrieval over
a locally prepared corpus.

### Dynamic Evidence

The ACLED integration provides a dynamic evidence path. Availability
depends on valid configuration, access permissions, network
connectivity, and the external source's coverage. Dynamic results should
be interpreted with their time and source context.

### Geographic Scope

The prepared UCDP datasets and country-focused processing use a defined
set of countries relevant to the project. The supported scope is
determined by the configured data filters and the evidence actually
present in the corpus; it should not be assumed that every source has
equal coverage for every country.

------------------------------------------------------------------------

## Multi-Perspective Analysis

### Military Perspective

Examines relevant military developments and conflict dynamics using
retrieved evidence. The output is analytical and descriptive, not a
recommendation for operational action.

### Legal Perspective

Examines applicable legal concepts and international humanitarian law
references present in the evidence. Legal output is a research aid and
does not replace qualified legal advice or authoritative legal
interpretation.

### Historical Perspective

Examines relevant prior events, historical context, agreements, and
developments that may help explain the situation under analysis.

### Perspective-Aware Evidence Selection

Evidence may be relevant to more than one perspective. Perspective
labels guide organization and analysis but should not be treated as
rigid source restrictions. Source provenance is retained so that an
analyst can inspect why a passage was included.

------------------------------------------------------------------------

## Evidence Verification and Confidence

### Claim Verification

Claim verification evaluates generated analytical statements against
retrieved evidence. Its purpose is to flag claims that appear supported,
insufficiently supported, or inconsistent with the available passages.
Results remain dependent on retrieval coverage and the behavior of the
underlying language/NLI models.

### Contradiction Detection

The contradiction-detection process identifies potentially conflicting
evidence. A conceptual pipeline is:

``` text
Retrieved Evidence
       |
       v
Event / Topic Pre-Clustering
       |
       v
Candidate Evidence Pairs
       |
       v
Natural-Language Inference
       |
       v
Potential Contradictions for Review
```

Pre-clustering can reduce unnecessary pairwise comparisons by focusing
evaluation on potentially related passages. A detected contradiction may
reflect differences in time, definitions, reporting scope, or source
quality; it requires contextual interpretation.

### Confidence Scoring

The confidence component uses evidence-related signals, including:

-   Query--evidence relevance
-   Agreement across retrieved evidence
-   Evidence freshness where available
-   Source reliability indicators
-   Verification-related signals supported by the implementation

The displayed score is an indicator for prioritizing review. Unless
separately calibrated and validated, it must **not** be interpreted as a
statistical probability of correctness.

### Citation and Provenance

The system retains evidence references and source metadata to make the
analysis inspectable. Depending on the source record, metadata may
include source name, source type, publication or event date, evidence
identifier, perspective, and a local evidence reference.

------------------------------------------------------------------------

## Data Processing and Storage

### Preprocessing

The ingestion pipeline includes:

-   Unicode normalization
-   Control-character removal
-   Whitespace normalization
-   Date and URL normalization where applicable
-   Metadata cleaning
-   Exact duplicate detection
-   Sentence-aware chunking with configurable chunk size and overlap
-   Country-scope filtering for applicable structured datasets

Near-duplicate processing may be disabled for structured sources where
record-level semantics make it inappropriate.

### Storage Separation

MIL-EVID separates large retrieval artefacts from relational application
metadata.

  -----------------------------------------------------------------------
  Data                    Storage                 Purpose
  ----------------------- ----------------------- -----------------------
  Full evidence chunk     Local JSONL files       Stores the text used
  text                                            during retrieval and
                                                  analysis.

  Evidence and chunk      PostgreSQL              Supports lookup,
  metadata                                        provenance, and
                                                  application-level
                                                  references.

  Dense vectors           Local FAISS index files Supports semantic
                                                  retrieval.

  Lexical index           Local BM25 index files  Supports lexical
                                                  retrieval.

  Users and application   PostgreSQL              Supports authenticated
  records                                         application use.

  Queries and analyses    PostgreSQL              Supports persistent
                                                  analysis history and
                                                  lifecycle state.

  Perspective results,    PostgreSQL              Stores structured
  claims, and                                     analysis outputs where
  contradictions                                  implemented.
  -----------------------------------------------------------------------

Common artefact locations in the repository include:

``` text
backend/data/processed/chunks/
backend/indexes/faiss/
backend/indexes/bm25/
```

Use the actual repository configuration as the source of truth if these
paths differ in a particular checkout. Large local chunk files and
generated indexes may need to be created by the ingestion/indexing
workflow rather than downloaded from version control.

### Database

PostgreSQL stores application and evidence metadata, as well as
persistent analysis state. SQLAlchemy is used for database access. Full
evidence text and retrieval indexes remain outside PostgreSQL to avoid
storing the entire retrieval corpus as relational rows.

------------------------------------------------------------------------

## Technology Stack

  -----------------------------------------------------------------------
  Layer                               Technologies
  ----------------------------------- -----------------------------------
  Programming languages               Python, JavaScript

  Frontend                            React.js, React Router, Recharts,
                                      Lucide React, utility-based styling

  Backend API                         FastAPI, Uvicorn, Pydantic

  Database                            PostgreSQL, SQLAlchemy

  Data processing                     Pandas, NumPy

  Lexical retrieval                   `rank-bm25` / BM25Okapi

  Embeddings                          Sentence Transformers

  Dense vector search                 FAISS

  Ranking                             Reciprocal Rank Fusion,
                                      cross-encoder reranking

  Language-model inference            Ollama with the configured local
                                      model (for example, the model
                                      selected in the backend
                                      configuration)

  Verification                        Natural-language inference
                                      components for claim verification
                                      and contradiction detection

  Dynamic evidence                    ACLED API integration

  Version control                     Git, GitHub

  Testing                             pytest
  -----------------------------------------------------------------------

Exact package versions and required configuration values should be taken
from the repository's dependency and environment-example files.

------------------------------------------------------------------------

## Repository Structure

The following is a logical overview. Some filenames and subdirectories
may vary between revisions.

``` text
mil-evid/
├── README.md
├── backend/
│   ├── app/
│   │   ├── api/              # API routers and schemas
│   │   ├── core/             # Configuration and core application logic
│   │   ├── database/         # Database setup and persistence
│   │   ├── domain/           # Domain models and contracts
│   │   ├── modules/
│   │   │   ├── query/        # Query processing and specificity checks
│   │   │   ├── ingestion/    # Evidence ingestion and preprocessing
│   │   │   ├── retrieval/    # BM25, dense retrieval, fusion, reranking
│   │   │   └── analysis/     # Perspectives, verification, confidence
│   │   ├── repositories/     # Persistence access
│   │   ├── services/         # Pipeline orchestration and application services
│   │   └── ...
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │   │   └── chunks/
│   │   └── dynamic/
│   ├── indexes/
│   │   ├── bm25/
│   │   └── faiss/
│   ├── scripts/              # Dataset processing and ingestion scripts
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   ├── public/
│   └── package.json
└── ...
```

For exact entry points and module names, inspect the current checked-out
source tree.

------------------------------------------------------------------------

## Prerequisites

The following are recommended starting requirements for local
development and evidence processing:

-   64-bit Windows or Linux
-   Python environment compatible with the project's pinned dependencies
-   Node.js and the package manager specified by the frontend repository
-   PostgreSQL database and a valid connection string
-   Ollama installed locally, with the model required by the project
    downloaded
-   Internet access for initial dependency/model installation and
    configured external data access
-   At least **16 GB RAM** recommended
-   At least **256 GB SSD** recommended for datasets, indexes, models,
    and generated artefacts
-   A GPU with approximately **6 GB VRAM or more** can help with
    embedding, reranking, and local model inference; actual needs depend
    on model and workload

The full pipeline may run on CPU, but preprocessing, embedding
generation, reranking, and local language-model inference can be
significantly slower without suitable hardware.

------------------------------------------------------------------------

## Installation and Configuration

> The commands below describe the standard local-development workflow.
> Confirm paths, environment variable names, scripts, and
> package-manager requirements against the current repository before
> running them.

### 1. Clone the Repository

``` bash
git clone <YOUR_REPOSITORY_URL>
cd mil-evid
```

Replace `<YOUR_REPOSITORY_URL>` with the repository's actual Git URL.

### 2. Set Up the Backend

``` bash
cd backend
python -m venv .venv
```

Activate the environment on Windows PowerShell:

``` powershell
.\.venv\Scripts\Activate.ps1
```

On Windows Command Prompt:

``` bat
.venv\Scripts\activate.bat
```

On Linux/macOS:

``` bash
source .venv/bin/activate
```

Install dependencies:

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the provided example configuration and edit the local file:

**Windows PowerShell**

``` powershell
Copy-Item .env.example .env
```

**Linux/macOS**

``` bash
cp .env.example .env
```

Set the required values in `backend/.env`, based on the variables
defined in `backend/.env.example`. Typical configuration categories
include:

-   PostgreSQL connection settings
-   Application/authentication secrets
-   Model and inference settings
-   Retrieval and reranking parameters
-   Optional dynamic-source credentials, including ACLED where required
-   Logging and application configuration

The exact variable names are repository-specific. Do not add real
secrets to the README or commit the `.env` file.

### 4. Configure PostgreSQL

Create or select a PostgreSQL database and configure the connection
string using the repository's environment settings. Run the database
initialization or migration procedure documented by the current backend
implementation.

Do not assume that an empty database is ready until the project's schema
initialization has completed successfully.

### 5. Configure Local Language-Model Inference

Install and start Ollama according to its official installation
instructions. Pull the language model configured by the project and
ensure the backend can reach the local Ollama service.

The configured model name must match the backend settings. Model
availability and hardware requirements vary.

### 6. Set Up the Frontend

Open a separate terminal and navigate to the frontend:

``` bash
cd frontend/artifacts/mil-evid
```

Install dependencies using the package manager and lockfile present in
the repository. For an npm-managed frontend:

``` bash
npm install
```

If the repository uses pnpm, use its lockfile and workspace
configuration instead:

``` bash
pnpm install
```

Do not mix package managers in the same working tree unless the
repository explicitly supports it.

------------------------------------------------------------------------

## Running the Application

### Start the Backend

From the backend directory, use the repository's configured FastAPI
entry point. The standard command, if `app.main:app` is the entry point,
is:

``` bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The local API is then typically available at:

``` text
http://127.0.0.1:8000
```

FastAPI's interactive API documentation is typically available at:

``` text
http://127.0.0.1:8000/docs
```

Use the actual health-check route defined by the application rather than
assuming one exists at a particular path.

### Start the Frontend

In a separate terminal:

``` bash
cd frontend/artifacts/mil-evid
```

Run the development script defined in `frontend/package.json`, commonly:

``` bash
npm run dev
```

or, for a pnpm-managed workspace:

``` bash
pnpm dev
```

Use the local URL printed by the frontend development server. Configure
the frontend's backend/API base URL according to the project's
environment configuration.

### Verify the End-to-End Setup

Before submitting a full analysis, verify that:

1.  The backend starts without configuration or import errors.
2.  PostgreSQL is reachable and the required schema is initialized.
3.  The configured local language model is available.
4.  Required static datasets and indexes exist, or the documented
    ingestion/indexing steps have been completed.
5.  Optional dynamic-source credentials are configured if dynamic
    evidence is needed.
6.  The frontend can reach the backend.
7.  Authentication and a small test query work as expected.

------------------------------------------------------------------------

## Data Ingestion and Indexing

Ingestion and index-generation commands are implementation-specific.
Review the scripts under `backend/scripts/` and use the documented entry
points in the current repository.

The conceptual ingestion flow is:

``` text
Raw CSV / PDF / Structured Sources
                 |
                 v
         Source-Specific Parsing
                 |
                 v
       Filtering and Normalization
                 |
                 v
         Duplicate Identification
                 |
                 v
           Sentence-Aware Chunking
                 |
                 v
       Local JSONL Chunk Persistence
                 |
                 +-----------------------+
                 |                       |
                 v                       v
       PostgreSQL Metadata       Retrieval Index Generation
                                         |
                                  +------+------+
                                  |             |
                                  v             v
                               BM25 Index    FAISS Index
```

### Processing Notes

-   Preserve source identifiers and metadata during preprocessing.
-   Apply country filters only to sources for which the project defines
    such a scope.
-   Treat legal documents such as IHL references according to their
    source-specific coverage.
-   Use consistent chunking and normalization settings when rebuilding
    indexes.
-   Keep the embedding model consistent between index generation and
    query-time retrieval.
-   Rebuild or update indexes after changing the processed corpus.
-   Avoid placing credentials or large sensitive artefacts in version
    control.

### Dynamic Retrieval

Dynamic ACLED retrieval is configured separately from the static
ingestion pipeline. Its operation depends on credentials, source
permissions, supported query parameters, and external availability. When
the dynamic source is unavailable, analysis coverage may be limited to
the indexed evidence, depending on application behavior.

------------------------------------------------------------------------

## Render Deployment

MIL-EVID can be deployed as a Render Web Service for the FastAPI backend
while Ollama runs on a separate computer. This is a split deployment:
Render hosts the API, while the computer running Ollama provides
language-model inference.

### Deployment Layout

``` text
Analyst's browser
       |
       v
Render Web Service (FastAPI)
       |
       +----> PostgreSQL database
       |
       +----> Processed evidence chunks and BM25/FAISS indexes
       |
       +----> Secure connection to Ollama on a separate computer
```

### 1. Prepare the Repository

The backend entry point is `backend/app/main.py`. When `backend` is
configured as the Render Root Directory, the expected commands are:

**Build Command**

``` bash
pip install -r requirements.txt
```

**Start Command**

``` bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

These commands assume `backend/requirements.txt` exists and
`backend/app/main.py` exposes the FastAPI instance as `app`. Confirm
those details in the current checkout before deploying.

### 2. Supply Evidence and Retrieval Indexes

The application uses processed evidence chunks and persisted retrieval
indexes. Relevant local paths include:

``` text
backend/data/processed/chunks/
backend/indexes/bm25/bm25_index.pkl
backend/indexes/faiss/faiss_index.bin
backend/indexes/faiss/metadata.json
```

The repository's `.gitignore` may exclude raw or intermediate datasets,
and previously ignored files are not automatically uploaded to Git.
Before deploying, verify that every runtime asset required by the
loaders is available to the Render service.

Do not commit the entire raw dataset merely to make deployment work.
Choose an explicit asset-delivery method appropriate for the files'
sizes, such as tracking only the required runtime assets or downloading
them from controlled external storage during deployment. If assets are
downloaded at startup, account for startup time and verify their
integrity. Render's filesystem should not be treated as permanent
storage unless the service is configured with an appropriate persistent
disk.

### 3. Configure PostgreSQL

Configure the database connection using the environment-variable names
expected by `backend/app/core/config.py`. Use a database reachable from
Render, and ensure the schema/migrations have been applied. Do not put
database credentials in the README or commit them to Git.

### 4. Connect Render to Ollama Running Elsewhere

Ollama running on a developer computer is not reachable from Render
through `localhost` or `127.0.0.1`. Those addresses refer to the machine
on which the backend process is running.

To use a local Ollama instance:

1.  Keep the computer running, connected to the internet, and running
    Ollama whenever hosted analysis requests need the model.
2.  Establish a secure, authenticated network path between Render and
    that computer using a suitable private-network or access-controlled
    tunnel solution.
3.  Configure the backend's Ollama endpoint using the actual
    environment-variable name supported by the current configuration
    module.
4.  Test connectivity from the deployed service and confirm that the
    configured model is available.

**Do not expose Ollama's port `11434` directly to the public internet
without appropriate access controls.** Do not assume that setting the
endpoint to `http://localhost:11434` will work from Render. If the
computer is offline or the secure connection is unavailable,
model-backed analyses will fail or time out.

### 5. Memory, Latency, and Availability

Hosting FastAPI separately from Ollama avoids placing the language
model's inference workload on the Render API instance, but the backend
still needs memory for its Python process, embedding model,
cross-encoder, BM25 index, FAISS index, and retrieved evidence. The
exact RAM requirement depends on the models, corpus, worker count, and
concurrency.

For the first deployment:

-   Start with one web-service worker and low request concurrency.
-   Load indexes and models once per process where supported; avoid
    rebuilding indexes on each request.
-   Confirm the Render instance has enough memory and disk space for the
    assets it must load.
-   Test health checks, retrieval, database connectivity, and one
    complete analysis.
-   Expect longer response times when inference runs on a separate
    computer or the model is cold.
-   Monitor logs and memory usage before increasing concurrency.

### 6. Deployment Verification Checklist

-   [ ] The service builds successfully from the `backend` directory.
-   [ ] The configured FastAPI entry point starts and binds to `$PORT`.
-   [ ] Required processed chunks and retrieval indexes are present and
    load successfully.
-   [ ] PostgreSQL is reachable and the required schema exists.
-   [ ] The embedding model and cross-encoder can load within the
    service's memory limit.
-   [ ] Render can securely reach the configured Ollama endpoint.
-   [ ] The required Ollama model is available on the inference
    computer.
-   [ ] A query with no relevant evidence returns an appropriately
    limited response rather than unsupported claims.
-   [ ] A complete analysis finishes within the hosting platform's
    request and proxy time limits.
-   [ ] Secrets are configured in Render's environment settings, not
    committed to Git.

A successful deployment does not by itself establish factual
reliability. Evaluate retrieval relevance, claim support, citation
quality, contradiction detection, and end-to-end latency after
deployment.

------------------------------------------------------------------------

## API Overview

The backend exposes API areas for analysis and supporting application
capabilities. The current implementation includes route groups for areas
such as:

``` text
/api/auth
/api/analysis
/api/evidence
/api/retrieval
/api/claims
/api/perspectives
/api/ingestion
/api/system
```

The precise route paths, HTTP methods, request models, and response
schemas are defined by the current FastAPI routers. Use the generated
OpenAPI documentation at `/docs` to inspect the authoritative API
contract.

### Typical Analysis Interaction

Conceptually, an analysis workflow involves:

``` text
Submit query
    |
    v
Receive analysis identifier
    |
    v
Poll analysis status / retrieve result
    |
    v
Inspect perspectives, evidence, claims,
contradictions, confidence, and citations
```

A query may include retrieval configuration where supported by the
backend. Do not assume optional fields or parameter names without
checking the actual request schema.

### Analysis Lifecycle

The processing pipeline can report intermediate stages such as query
processing, retrieval, reranking, perspective analysis, claim
verification, contradiction detection, confidence scoring, and response
generation. The frontend is designed to reflect backend processing state
rather than relying solely on a simulated progress timer.

------------------------------------------------------------------------

## Testing

Run tests from the backend environment:

``` bash
cd backend
pytest
```

For more detailed output:

``` bash
pytest -v
```

The existing test suite covers implemented components such as
preprocessing, ingestion, retrieval-related behavior, data-source
mapping, repositories, and application logic. Test coverage depends on
the current repository revision.

For reproducible experiments, record:

-   Dataset versions and filtering criteria
-   Chunk size and overlap
-   Embedding model and version
-   BM25 parameters
-   Dense retrieval settings
-   RRF configuration
-   Cross-encoder model and reranking depth
-   Language-model name and inference parameters
-   Hardware and software environment
-   Evaluation queries and relevance judgments
-   Latency and quality metrics

A passing unit-test suite does not, by itself, establish retrieval
quality or factual reliability.

------------------------------------------------------------------------

## Configuration Areas

Application configuration is defined in the backend configuration module
and the environment-example file. Review the current repository before
changing values.

  -----------------------------------------------------------------------
  Configuration area                  Purpose
  ----------------------------------- -----------------------------------
  Database                            PostgreSQL connection and pool
                                      behavior

  Authentication                      Secret values and token/session
                                      behavior

  Data sources                        Source paths, filtering, and
                                      optional API credentials

  Chunking                            Chunk length, overlap, and text
                                      processing

  Embeddings                          Model identifier and embedding
                                      configuration

  BM25                                Lexical retrieval parameters

  FAISS                               Vector index and similarity-search
                                      configuration

  RRF                                 Rank-fusion parameters

  Reranking                           Cross-encoder model and candidate
                                      limits

  Analysis                            Perspective-specific prompts and
                                      generation parameters

  Verification                        Claim-verification and
                                      contradiction-detection settings

  Confidence                          Evidence-signal weights and score
                                      aggregation

  Application                         Logging, runtime, and API settings
  -----------------------------------------------------------------------

Avoid changing model identifiers or retrieval settings during a
benchmark unless the experiment explicitly evaluates that change.

------------------------------------------------------------------------

## Research Evaluation

MIL-EVID is designed to be evaluated as a pipeline, not only by the
fluency of its generated responses. Useful evaluation dimensions
include:

  -----------------------------------------------------------------------
  Evaluation area                     Example measures
  ----------------------------------- -----------------------------------
  Retrieval relevance                 Precision@k, Recall@k, MRR, nDCG@k

  Ranking quality                     Relevant-evidence position before
                                      and after reranking

  Evidence coverage                   Coverage of required entities,
                                      events, dates, and perspectives

  Citation support                    Fraction of claims linked to
                                      relevant supporting evidence

  Claim verification                  Precision, recall, and F1 against
                                      manually labelled claims

  Contradiction detection             Precision, recall, and F1 against
                                      annotated evidence pairs

  Confidence quality                  Calibration and relationship
                                      between scores and verified
                                      outcomes

  Runtime                             End-to-end latency and stage-level
                                      latency

  Robustness                          Behavior with ambiguous queries,
                                      conflicting reports, and missing
                                      evidence
  -----------------------------------------------------------------------

Metrics should be calculated on a documented evaluation set with
explicit annotation rules. Comparative claims against a baseline should
only be reported when the same queries, corpus conditions, and
evaluation criteria are used. No performance percentage is asserted here
unless it is supported by a reproducible experiment.

------------------------------------------------------------------------

## Limitations

### Evidence Coverage and Freshness

The analysis is constrained by the available source corpus, source
coverage, update frequency, and configured dynamic-source access.

### Retrieval Errors

The retrieval system may miss relevant evidence or rank partially
relevant passages highly. Hybrid retrieval and reranking reduce some
retrieval limitations but do not eliminate them.

### Source Conflicts

Sources may differ because of reporting time, definitions, scope, or
reliability. A detected conflict requires contextual review and should
not automatically be treated as proof that one source is false.

### Language-Model Errors

Generated analysis may still contain incorrect, incomplete, or
unsupported statements even when evidence is provided. Users should
inspect the underlying evidence and citations.

### Confidence Interpretation

Confidence scores are analytical indicators. They should not be
interpreted as guarantees of correctness or as calibrated probabilities
unless calibration has been separately evaluated.

### Dynamic Data Dependencies

Dynamic evidence depends on external API availability, access
permissions, credentials, rate limits, and the source's own data
coverage.

### Research Prototype

MIL-EVID is a research prototype. It should be used for research,
evidence exploration, and structured analysis, not as an autonomous
decision-making system.

------------------------------------------------------------------------

## Security Considerations

-   Keep database passwords, API keys, authentication secrets, and
    access tokens in environment variables or an approved secret store.
-   Never commit `.env` files, private keys, credentials, or production
    data.
-   Use least-privilege database credentials.
-   Validate and constrain user input at API boundaries.
-   Protect authenticated routes and review token lifecycle and refresh
    behavior.
-   Restrict CORS and network exposure appropriately for the deployment
    environment.
-   Treat externally retrieved documents and event data as untrusted
    input.
-   Avoid logging access tokens, secrets, or unnecessary personal data.
-   Review licensing and terms of use for each external dataset and API
    before redistribution or deployment.

------------------------------------------------------------------------

## Future Work

Potential research extensions include:

-   Larger and more systematic retrieval benchmarks
-   Ablation studies comparing BM25, dense retrieval, RRF, and reranking
-   Evaluation of perspective coverage and analytical consistency
-   Improved claim-level evidence attribution
-   Contradiction-detection evaluation on annotated evidence pairs
-   Confidence calibration and uncertainty communication
-   Robust handling of temporal changes and conflicting reports
-   Dynamic-source freshness and failure-mode evaluation
-   Latency and memory optimization for larger corpora
-   Reproducible experiment tracking and dataset versioning

These items are research directions and should not be interpreted as
completed features unless implemented and validated in the current
codebase.

------------------------------------------------------------------------

## License

The applicable project license should be specified by the repository
owner. Until a license is added, reuse and redistribution permissions
should not be assumed.

``` text
License: To be determined
```

------------------------------------------------------------------------

## Disclaimer

MIL-EVID is an academic and research-oriented evidence-analysis
framework. It supports retrieval, organization, verification, and
interpretation of publicly available or otherwise authorized evidence.
It does not provide targeting recommendations, weapons guidance,
tactical engagement instructions, operational military planning, or
autonomous military decisions.

Generated outputs may be incomplete or inaccurate. Analysts should
independently review the underlying sources, dates, context, and
citations before relying on any result.
