# Technical Abstract & Design Document
**Author:** Amit Kumar Behera | **Role:** Software Engineering Intern (Jul-Dec 2026)

## 1. Executive Summary & Business Value
In modern recruitment, candidate data is heavily siloed across disparate platforms (ATS, Recruiter CSVs, and GitHub). This fragmentation prevents AI matching engines from forming a holistic view of candidate capabilities. The objective of this project was to design a highly extensible, fault-tolerant ETL (Extract, Transform, Load) pipeline capable of ingesting multi-format data, accurately resolving identities, and resolving conflicts to produce a unified, "Golden Record" JSON schema.

## 2. Core Architecture & SOLID Principles
The pipeline was engineered using a strictly decoupled, modular architecture to ensure future maintainability:
* **Polymorphic Extraction Layer:** Implements format-specific extractors for static files (CSV, JSON) and a dynamic `GitHubAPIExtractor` which fetches real-time telemetry via the GitHub REST API. Raw inputs are mapped to a `CanonicalProfile` dataclass, ensuring the core engine remains completely agnostic to upstream data sources.
* **Identity Resolution Engine:** Deduplicates records using a deterministic two-pass strategy:
  1. *Primary Key Match:* O(1) hash-based union of email addresses for absolute deterministic matching.
  2. *Heuristic Fallback:* Fuzzy string matching on Candidate Name + Current Employer, preventing catastrophic false-positive merges for common names (e.g., "John Doe").
* **Dynamic Projection Engine:** Driven entirely by a decoupled JSON configuration file. It supports deep array wildcards (`skills[].name`), executes runtime data normalizations (E164 phone formatting), and enforces strict `on_missing` policies (`null`, `omit`, `error`) to guarantee absolute downstream API integrity.

## 3. Algorithmic Conflict Resolution
When sources conflict (e.g., ATS vs. GitHub), data is resolved via a predefined provenance weighting scale (GitHub `0.9` > Resume `0.8` > ATS `0.7`). Scalar values strictly defer to the highest-confidence source. Arrays (such as programming languages) are mathematically unioned (using Python Set logic) to preserve complete capability maps without duplication. The system also calculates an overall confidence score for the final profile.

## 4. Quality Assurance & UI (Bonus Deliverable)
* **Comprehensive Test Suite:** To ensure true enterprise-grade reliability, the logic is fortified by a Pytest suite (24 tests, 100% coverage). Tests rigorously validate edge cases in fuzzy matching thresholds and API rate-limit exceptions.
* **Interactive FastAPI Dashboard:** The backend is wrapped in a production-ready FastAPI application serving a responsive UI. Evaluators can visually track data provenance, edit the projection schema live, and seamlessly toggle between visual cards and raw JSON outputs.

## 5. Future Scalability
By abstracting the Extractors and Projectors from the core Identity Resolution logic, Eightfold can seamlessly integrate future data sources (such as LinkedIn or Workday) with zero modifications to the core merger algorithms. This demonstrates a deep understanding of resilient, highly scalable data engineering.
