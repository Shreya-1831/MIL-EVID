# MIL-EVID

### Hybrid RAG Backend for Multi-Perspective Military Situation Analysis

MIL-EVID is a full-stack AI-powered Retrieval-Augmented Generation (RAG) system designed for analyzing military situations from multiple perspectives, including **military, legal, and historical viewpoints**.

The system retrieves relevant evidence from a document collection using a **hybrid search architecture** that combines lexical and semantic retrieval before passing the retrieved context to a Large Language Model (LLM) for analysis.

---

## 🎯 Project Objective

The objective of MIL-EVID is to build an evidence-grounded military situation analysis system that can:

* Retrieve relevant information from a large document collection
* Perform both keyword-based and semantic search
* Combine multiple retrieval strategies
* Provide context-grounded responses
* Support military, legal, and historical perspectives
* Reduce unsupported or hallucinated responses
* Preserve evidence and source information for retrieved content

---

## 🏗️ System Overview

MIL-EVID follows a phased Hybrid RAG architecture:

```text
Documents
    ↓
Document Processing
    ↓
Text Extraction & Cleaning
    ↓
Chunking
    ↓
Indexing
    ├── BM25 Index
    │     └── Lexical Search
    │
    └── Sentence Transformer
          ↓
       Embeddings
          ↓
       FAISS Index
          └── Semantic Search
```

The retrieved results are later combined and used as context for the generation stage.

---

## 🔍 Hybrid Retrieval

MIL-EVID uses two complementary retrieval methods.

### 1. BM25

BM25 performs lexical/keyword-based retrieval.

It is useful when the query contains:

* Specific names
* Locations
* Military terminology
* Legal terminology
* Dates
* Operations
* Organizations
* Exact phrases

### 2. FAISS + Sentence Transformers

Sentence Transformer models convert document chunks into dense vector embeddings.

FAISS is then used for efficient similarity search.

This allows the system to retrieve semantically related information even when the exact query words do not appear in the document.

### 3. Hybrid Retrieval

The two retrieval methods are combined to improve recall and relevance:

```text
User Query
    │
    ├───────────────┐
    ↓               ↓
  BM25            FAISS
 Lexical         Semantic
 Search           Search
    │               │
    └───────┬───────┘
            ↓
      Result Fusion
            ↓
     Relevant Evidence
```

---

## 🧩 Project Architecture

The project is being developed incrementally in multiple phases.

### Phase 1 — Backend Scaffolding

* FastAPI application setup
* Project structure
* Configuration management
* Environment variable handling
* API foundation

### Phase 2 — Dataset & Document Processing

* Dataset preparation
* Document ingestion
* Text extraction
* Cleaning
* Document normalization

### Phase 3 — Chunking

Documents are divided into smaller chunks suitable for retrieval.

```text
Document
   ↓
Text
   ↓
Chunks
   ↓
Metadata
```

Each chunk retains relevant metadata so that retrieved evidence can later be traced back to its source.

### Phase 4 — Indexing

Each chunk is represented in two ways:

```text
Chunks
   ├── BM25 Index
   │
   └── Sentence Transformer
           ↓
       Embeddings
           ↓
         FAISS
```

BM25 enables lexical retrieval, while FAISS enables semantic retrieval.

### Upcoming Phases

* Hybrid retrieval
* Result fusion / ranking
* Query processing
* Multi-perspective analysis
* LLM-based generation
* Evidence/citation handling
* API integration
* Frontend integration
* Evaluation

---

## 🛠️ Technology Stack

### Backend

* Python
* FastAPI
* Pydantic / Pydantic Settings
* Uvicorn

### Retrieval

* BM25
* Sentence Transformers
* FAISS

### Database

* PostgreSQL

### AI / NLP

* Sentence Transformer embeddings
* Large Language Model for generation

### Development

* Git
* GitHub
* Python virtual environment

---

## 📁 Project Structure

The structure may evolve as additional phases are implemented.

```text
mil-evid-backend/
│
├── backend/
│   ├── app/
│   │   ├── ...
│   │
│   ├── ...
│
├── data/
│   └── ...
│
├── tests/
│   └── ...
│
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── ...
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd mil-evid-backend
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file based on `.env.example`.

```bash
copy .env.example .env
```

Do **not** commit `.env` to GitHub.

---

## ▶️ Running the Backend

From the backend project directory:

```bash
uvicorn app.main:app --reload
```

The API will be available locally at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 📊 Current Project Status

| Component                       | Status      |
| ------------------------------- | ----------- |
| FastAPI backend                 | ✅ Completed |
| Project scaffolding             | ✅ Completed |
| Configuration management        | ✅ Completed |
| Dataset preparation             | ✅ Completed |
| Document processing             | ✅ Completed |
| Chunking                        | ✅ Completed |
| BM25 indexing                   | ✅ Completed |
| Sentence Transformer embeddings | ✅ Completed |
| FAISS indexing                  | ✅ Completed |
| Hybrid retrieval                | 🔄 Next     |
| Result fusion / ranking         | 🔄 Pending  |
| Query processing                | 🔄 Pending  |
| Multi-perspective analysis      | 🔄 Pending  |
| LLM generation                  | 🔄 Pending  |
| Evidence / citations            | 🔄 Pending  |
| Frontend                        | 🔄 Pending  |
| Evaluation                      | 🔄 Pending  |

---

## 🔐 Security

Sensitive configuration values should be stored in environment variables.

The following files should **never** be committed:

```text
.env
API keys
database passwords
access tokens
private credentials
local generated indexes
large generated datasets
```

Use `.env.example` to document required environment variables without exposing their values.

---

## 🚧 Development Status

MIL-EVID is currently under active development.

The system is being implemented incrementally, with each phase tested before moving to the next phase.

The current milestone establishes the **document processing, chunking, and indexing foundation required for hybrid retrieval**.

---

## 📌 Future Goal

The final system will allow a user to provide a military-related query and receive an evidence-grounded analysis generated from retrieved documents.

Conceptually:

```text
User Query
     ↓
Query Processing
     ↓
┌─────────────────────┐
│   Hybrid Retrieval  │
│                     │
│  BM25 + FAISS       │
└─────────┬───────────┘
          ↓
   Evidence Ranking
          ↓
 ┌────────────────────┐
 │ Multi-Perspective  │
 │ Analysis           │
 │                    │
 │ Military           │
 │ Legal              │
 │ Historical         │
 └─────────┬──────────┘
           ↓
        LLM
           ↓
 Evidence-Grounded
      Response
```

---

## 👩‍💻 Project

**MIL-EVID — Hybrid RAG Backend for Multi-Perspective Military Situation Analysis**

Developed as an internship project.
