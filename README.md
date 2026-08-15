# VERITAS

**Verified Evidence Reconciliation for Identity Trust & Audit System**

VERITAS is an advanced, pure-Python system that acts as a localized Security Operations Center (SOC) engine. It ingests identity claims from disparate sources, resolves conflicting signals using a mathematically deterministic three-tier cascade (confidence → source reliability → timestamp), and produces an immutable, cryptographically chained audit trail proving zero tampering. 

## Architecture (3-Phase Pipeline)
1. **Ingestion & Integrity Layer**: Validates structural schemas, detects malformed payloads, and rejects exact-hash duplicates. Approved signals are strictly appended to a JSONL log.
2. **Conflict Resolution Engine**: Deterministically resolves competing claims for the same identity. It groups by identity, applies the cascading priority rules, and ensures purely reproducible outputs.
3. **Immutable Audit & Replay Engine**: Packages every resolved decision into a cryptographically chained audit log (starting from a Genesis block). The Replay Engine can completely rebuild history from scratch in-memory and prove byte-for-byte consistency, verifying no live state divergence.

## 5 PRD Edge Cases Covered
- **Edge Case 1 & 2 (Duplicates)**: Rejects signals with the exact same `cryptographic_hash`. (Tested in `tests/test_ingestion.py::test_deduplication`)
- **Edge Case 3 (Conflicting Claims)**: Correctly applies the 3-tier cascade to resolve multiple different signals for one identity. (Tested in `tests/test_resolver.py::test_conflict_tiers`)
- **Edge Case 4 (Malformed)**: Rejects payloads missing required fields. (Tested in `tests/test_ingestion.py::test_malformed_payload`)
- **Edge Case 5 (Out-of-order)**: Timestamp resolution automatically re-slots late arrivals correctly due to grouping before resolution. (Tested in `tests/test_resolver.py::test_conflict_tiers`)

## Setup & Running

**1. Clone & Install**
```bash
git clone https://github.com/Bhandarihansraj/VERITAS.git
cd VERITAS
python -m venv .venv
# Activate venv: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Mac/Linux)
pip install -r requirements.txt
```

**2. Start the Server**
```bash
python cli.py serve --port 8585
```
*Open `ui/dashboard.html` in your browser to view the live SOC.*

**3. Run Simulations**
Open a second terminal and inject attack scenarios to populate the dashboard:
```bash
python cli.py simulate
```

**4. Run Deterministic Replay (Prove the chain)**
```bash
python cli.py replay
# Or click "Run Deterministic Replay" directly in the dashboard UI
```

**5. Run the Test Suite**
```bash
pytest tests/
```
