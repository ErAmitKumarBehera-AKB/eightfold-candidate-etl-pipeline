# Candidate Data Transformer

A production-ready data pipeline that ingests candidate profiles from multiple unstructured sources (ATS, Recruiter CSVs, and GitHub), merges them using identity resolution and confidence-based conflict resolution, and projects them into a unified, configurable schema.

## 🌟 Key Features

- **Multi-Source Ingestion** — Supports `.csv`, ATS `.json`, and GitHub `.json` formats out of the box.
- **Live GitHub API Integration** — Fetches real candidate repositories and language stats via the GitHub REST API.
- **Identity Resolution** — Deduplicates candidates across sources using two-pass matching: exact email union first, fuzzy Name + Employer fallback second.
- **Confidence Scoring** — Assigns an `overall_confidence` score based on source provenance weights (GitHub `0.9` > Resume `0.8` > ATS `0.7` > Recruiter CSV `0.6`).
- **Schema Projection** — Fully configurable output schema with array wildcard support (`skills[].name`), runtime normalization, and `on_missing` policy (`null` / `omit` / `error`).
- **Interactive Web UI** — Glassmorphic 3-column dashboard: browse raw inputs, edit the live config, and view merged profiles as rich cards or raw JSON.
- **Comprehensive Test Suite** — 24 pytest tests covering normalizers, identity resolution, the projector engine, and end-to-end pipeline execution.

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Python 3.9+ required
python -m venv venv

.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac / Linux

pip install -r requirements.txt
```

### 2. Run the Web UI

```bash
uvicorn app:app --reload --port 8000
```

Open **http://127.0.0.1:8000** in your browser.

### 3. Run the Test Suite

```bash
python -m pytest tests/ -v
```

Expected output: **24 passed** in < 1s.

## 🏗️ Architecture

The pipeline follows a strict **Extract → Merge → Project** pattern, keeping each concern isolated and independently testable.

```
mock_data/              Raw input files (ATS JSON, GitHub JSON, Recruiter CSV)
    └── config.json     Projection schema config

src/
    ├── extractors.py   Reads raw sources → CanonicalProfile objects
    ├── merger.py       Identity resolution + confidence-based field fusion
    ├── projector.py    Schema mapping, wildcard extraction, on_missing policy
    ├── normalizers.py  Skill canonicalization, E164 phones, country codes
    ├── models.py       CanonicalProfile dataclass (single source of truth)
    └── pipeline.py     Orchestrator — ties all stages together

app.py                  FastAPI server — /api/run, /api/config, /api/inputs
web/                    Browser UI (HTML + CSS + JS, no framework)
tests/
    └── test_pipeline.py  24 pytest unit and integration tests
```

## 🛠️ Configuration

The output schema is controlled by a JSON config (editable live in the UI):

```json
{
  "fields": [
    { "path": "full_name",      "type": "string",   "required": true },
    { "path": "primary_email",  "from": "emails[0]","type": "string",   "required": true },
    { "path": "phone",          "from": "phones[0]","type": "string",   "normalize": "E164" },
    { "path": "skills",         "from": "skills",   "type": "string[]", "normalize": "canonical" },
    { "path": "current_employer","from": "experience[0].company", "type": "string" },
    { "path": "location",       "from": "location.city", "type": "string" }
  ],
  "include_confidence": true,
  "on_missing": "null"
}
```

| Key | Description |
|---|---|
| `path` | Key name in the output JSON |
| `from` | Source path in `CanonicalProfile`. Supports `[]` wildcards for arrays |
| `normalize` | `E164` (phone), `canonical` (skills), or omit for no normalization |
| `on_missing` | `null` → write `null`, `omit` → skip the field, `error` → abort pipeline |
| `include_confidence` | Attach `overall_confidence` and `provenance` map to every output record |

## 🔑 Design Decisions

| Decision | Rationale |
|---|---|
| Two-pass identity resolution | Email is the strongest signal; fuzzy Name+Employer catches records where email is absent without causing false merges |
| Source confidence weights | Mirrors real-world trust — code (GitHub) is harder to fake than a free-text resume |
| Config-driven projection | The pipeline is format-agnostic; changing the output schema requires zero code changes |
| `on_missing: error` mode | Enables strict mode for downstream APIs that require all fields to be non-null |
| Array wildcards (`skills[].name`) | Lets a single config field pluck a sub-property from every element without hardcoding loops |

## 👨‍💻 Author

**Amit Kumar Behera** — B.Tech CSE (Data Science), SOA University | CGPA 9.35

- 🔗 [LinkedIn](https://www.linkedin.com/in/amit-kumar-behera-b11370293)
- 🐙 [GitHub](https://github.com/ErAmitKumarBehera-AKB)
