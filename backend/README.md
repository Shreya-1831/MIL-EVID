# MIL-EVID

**Static–Dynamic Evidence-Grounded Hybrid Retrieval-Augmented Generation
Framework for Multi-Perspective Military Situation Analysis.**

MIL-EVID is a research prototype that takes a natural-language military
situation query, retrieves evidence from static (UCDP, ICRC IHL, UN
Peacemaker) and dynamic (ACLED) sources, fuses BM25 + dense retrieval
via Reciprocal Rank Fusion and cross-encoder reranking, and produces a
structured, citation-supported, multi-perspective (military / legal /
historical) analysis with contradiction detection, claim verification,
and an explainable confidence score.

**Scope note:** this is an evidence-analysis system only. It does not
perform, and is not designed to perform, military targeting, weapon
selection, attack optimization, operational planning, or autonomous
military decision-making.

## Status

This repository is being built in phases. Completed so far:

- [x] Phase 1 — project scaffolding, configuration, domain models,
      exception hierarchy, FastAPI application setup
- [x] Phase 2 — Preprocessing (cleaning, normalization, deduplication, chunking)
- [x] Phase 2.5 — PDF ingestion (ICRC, UN Peacemaker), country-scope
      filtering, local chunk-text storage, metadata-only Postgres layer
- [ ] Phase 3 — BM25 + Dense Retrieval
- [ ] Phase 4 — RRF + Cross-Encoder + Hybrid Retrieval
- [ ] Phase 5 — Dynamic Evidence Layer
- [ ] Phase 6 — Perspective Analysis
- [ ] Phase 7 — Contradiction Detection + Claim Verification
- [ ] Phase 8 — Confidence Scoring
- [ ] Phase 9 — Pipeline Orchestration
- [ ] Phase 10 — API Routes
- [ ] Phase 11 — Database (request history, remaining schema)
- [ ] Phase 12 — Tests

## Storage architecture (important — read before ingesting data)

**Chunk text and database metadata are deliberately split across two
stores:**

| What | Where | Why |
|---|---|---|
| Chunk **text** | Local JSONL files, `data/processed/chunks/<source>.jsonl` | Source of truth. No size ceiling; BM25/FAISS index builders read directly from here. |
| Chunk **metadata** (id, source, title, date, url, perspective) | Postgres (`evidence_metadata` table) | Small footprint (~hundreds of bytes/row) for lookup and citation, independent of corpus size. |
| Embeddings | FAISS index files, `indexes/faiss/` | Never stored in Postgres. |

This split exists because storing full chunk text in Postgres
previously exhausted a 512MB free-tier database at ~285k UCDP records
alone (`DiskFull`). Ingesting ICRC and UN Peacemaker PDFs on top of
that would make it worse, not better — so full text now never reaches
the database at all.

`scripts/ingest_pdf_sources.py` demonstrates the pattern: walk raw
PDFs → map to `EvidenceDocument` → clean → normalize → dedupe → chunk
→ write chunk text locally → upsert metadata only to Postgres. Run
with `--skip-db` to populate/validate the local chunk store without a
reachable database at all.

## Ingesting ICRC and UN Peacemaker sources

```bash
# Both sources, writing to both the local chunk store and Postgres:
python -m scripts.ingest_pdf_sources

# Local chunk store only (no database required):
python -m scripts.ingest_pdf_sources --skip-db

# One source at a time:
python -m scripts.ingest_pdf_sources --sources icrc
python -m scripts.ingest_pdf_sources --sources un_peacemaker
```

Country-scope filtering (`PRIMARY_COUNTRIES` in `.env`) is applied to
UN Peacemaker at the folder level, before PDF text extraction runs —
out-of-scope countries never pay extraction cost. ICRC customary IHL
and treaty text is global legal material with no country dimension
and is never filtered.

Country names across sources (UCDP codes, SIPRI/UN Peacemaker folder
names, filename abbreviations like "US"/"UK") are normalized through
`app/modules/preprocessing/country_filter.py` — extend its alias map
there if a new source spells a country differently.

## Architecture adjustments from the original spec

A short architecture review preceded implementation. Net changes:

1. **One shared NLI adapter**, not two — contradiction detection and
   claim verification both reduce to entailment/contradiction judgments
   over a (premise, hypothesis) pair, so they share one model behind
   one `NLIAdapter` protocol.
2. **One shared `TextGenerationPort`** protocol for query analysis,
   perspective analysis, and claim extraction, each with a deterministic
   rule-based default and a single pluggable seam for a future LLM.
3. **Event/topic pre-clustering** (metadata-only: date window, region,
   shared actors) gates contradiction comparisons to avoid O(n²) NLI
   calls across the full corpus.
4. **Dynamic evidence uses a separate, small FAISS index** merged with
   the static index at query time, rather than being injected into the
   offline-built static index.
5. **Sync SQLAlchemy**, async only at the FastAPI route layer (which
   offloads CPU-bound retrieval/inference via a threadpool) — mixing an
   async DB driver with blocking ML inference added complexity with no
   benefit at this scale.
6. **Dynamic evidence cache is a real Postgres table**, not implicit
   in-memory state, so "freshness" is queryable and survives restarts.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env with real DATABASE_URL and (optionally) ACLED credentials
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Check it's alive:

```bash
curl http://localhost:8000/health
```

## Project layout

See `backend/app` for the module breakdown: `api/` (FastAPI routes and
schemas), `core/` (config, logging, exceptions), `domain/` (Pydantic
domain models and enums), `modules/` (retrieval, preprocessing,
verification, etc. — the business logic), `services/pipeline.py` (thin
orchestration only), `repositories/` and `database/` (persistence).

## Configuration

All configuration is environment-based (`app/core/config.py`, backed by
`pydantic-settings`). Nothing is hardcoded: database URL, ACLED
credentials, model names, retrieval parameters, and confidence-scoring
weights are all read from the environment. See `.env.example` for the
full list and defaults.

## Testing

```bash
pytest
```

Tests use mocked external services (no real ACLED calls) and small,
deterministic evidence fixtures.
