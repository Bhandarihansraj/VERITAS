# VERITAS

**Verified Evidence Reconciliation for Identity Trust & Audit System**

> *Real-time deepfake attack detection with cryptographically provable identity truth.*

VERITAS is a real-time, replayable, and cryptographically auditable identity conflict resolution engine. It processes multi-modal attack signals from synthetic media sources, reconciles conflicting identity claims across time, detects replayed or duplicated attack evidence, and generates immutable audit trails for forensic analysis — entirely local, pure Python, no external databases or cloud services.

---

## Architecture — 3-Phase Pipeline

```
Phase 1: Ingestion & Integrity   →  Phase 2: Conflict Resolution   →  Phase 3: Audit Trail & Replay
(signal intake, SHA-256 verify,      (deterministic 3-tier cascade,     (immutable hash-chained log,
 hash-based dedup, timeline          resolved identity state per         replay engine, chain verify,
 reconstruction)                     identity_claim)                     forensic dashboard, CLI)
```

### Phase 1 — Multi-Source Attack Signal Ingestion
- Accepts signals from three modalities: `video_stream`, `behavioral_log`, `device_fingerprint`
- Each signal validated against strict schema: `signal_type`, `identity_claim`, `source`, `confidence_score`, `timestamp`, `cryptographic_hash`
- SHA-256 hash-based deduplication rejects replayed or duplicated signals
- Out-of-order timestamps accepted and re-slotted into correct chronological position
- Append-only JSONL storage (`signals_log.jsonl`)
- HTTP endpoint: `POST /attack_signals` → `200 OK` | `409 Conflict` | `400 Bad Request`

### Phase 2 — Conflict Resolution Engine
- Groups all accepted signals by `identity_claim`
- Detects conflicts: same identity, different device fingerprints or sources
- Applies deterministic 3-tier resolution cascade (pure function, no wall-clock dependence):
  1. **Higher `confidence_score` wins**
  2. If tied → **higher source reliability wins** (configurable via `veritas/config/source_reliability.json`)
  3. If still tied → **latest `timestamp` wins**
- Outputs one resolved identity state per claim, recording exactly *which tier decided*

### Phase 3 — Immutable Audit Trail & Replay
- Every resolved identity packaged into a cryptographically chained audit record:
  - `original_signals`, `conflicting_signals`, `resolution_strategy`, `resolved_identity`, `timestamp`, `prev_hash`, `audit_hash`
- Chain starts from a fixed genesis value (`VERITAS_GENESIS`), each record links to the previous via `prev_hash`
- `verify_chain()` re-walks and recomputes every hash — detects single-character tampering at the exact record index
- **Deterministic Replay Engine** (`replay.py`): re-runs the full pipeline from `signals_log.jsonl` in memory, compares byte-for-byte against `audit_trail.json` — proves zero divergence, zero side effects

---

## 5 PRD Edge Cases Covered

| # | Edge Case | Phase | Where It's Tested |
|---|-----------|-------|-------------------|
| 1 | Duplicate signal with same hash and timestamp | Phase 1 | `tests/test_ingestion.py::test_deduplication` |
| 2 | Signal replay with same hash but later timestamp | Phase 1 | `tests/test_ingestion.py::test_replay_rejection` |
| 3 | Conflicting identity claim with different device fingerprint | Phase 2 | `tests/test_resolver.py::test_conflict_tiers` |
| 4 | Signal with missing cryptographic hash | Phase 1 | `tests/test_ingestion.py::test_malformed_payload` |
| 5 | Signal with out-of-order timestamp | Phase 1 | `tests/test_ingestion.py::test_out_of_order` |

---

## Repository Structure

```
veritas/
├── core/                         # Shared infrastructure (config, logger, exceptions)
│   ├── __init__.py
│   ├── config.py
│   ├── exceptions.py
│   └── logger.py
├── veritas/                      # Core engine modules
│   ├── __init__.py
│   ├── ingestion.py              # Phase 1: validate, hash-verify, dedup, timeline buffer
│   ├── storage.py                # Phase 1: append-only JSONL read/write with path-traversal guard
│   ├── server.py                 # Phase 1-3: stdlib http.server endpoints
│   ├── resolver.py               # Phase 2: deterministic 3-tier conflict resolution cascade
│   ├── audit.py                  # Phase 3: hash-chained audit trail + verify_chain()
│   └── config/
│       └── source_reliability.json  # Phase 2: reliability tier config
├── ui/
│   └── dashboard.html            # Live SOC-style dashboard (ingestion + conflicts + audit + replay)
├── samples/                      # Sample JSON payloads covering all 5 edge cases
│   ├── normal.json
│   ├── duplicate.json
│   ├── replay.json
│   ├── malformed.json
│   ├── out_of_order.json
│   └── conflict_tier[1-3]_[a|b].json
├── tests/
│   ├── test_ingestion.py         # Phase 1 tests (edge cases 1, 2, 4, 5)
│   ├── test_resolver.py          # Phase 2 tests (edge case 3 — all 3 cascade tiers)
│   ├── test_audit.py             # Phase 3 tests (chain integrity + tamper detection)
│   └── test_replay.py            # Phase 3 tests (deterministic replay + tamper failure)
├── cli.py                        # CLI: serve, ingest, simulate, resolve, replay, verify
├── replay.py                     # Deterministic replay engine (top-level script)
├── start_demo.bat                # One-click demo launcher (Windows)
├── requirements.txt              # pytest only — engine is pure stdlib
├── pytest.ini
├── signals_log.jsonl             # Generated at runtime (gitignored)
├── audit_trail.json              # Generated at runtime (gitignored)
└── chain_proof.json              # Generated by `veritas verify` (gitignored)
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Bhandarihansraj/VERITAS.git
cd VERITAS
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python cli.py serve --port 8585
```

### 3. Open the Dashboard

Open `ui/dashboard.html` in your browser. The dashboard polls `http://127.0.0.1:8585` automatically.

### 4. Run Attack Simulations

In a second terminal:

```bash
python cli.py simulate
```

This fires all sample signals (normal, duplicate, replayed, malformed, out-of-order, conflicting) through the live server. Watch the dashboard update in real time.

To run a specific scenario:

```bash
python cli.py simulate --scenario duplicate
python cli.py simulate --scenario conflict
```

### 5. Verify the Audit Chain

```bash
python cli.py verify
```

Outputs `chain_proof.json` with `first_hash`, `last_hash`, `record_count`, and `verified: true/false`.

### 6. Run Deterministic Replay

```bash
python cli.py replay
```

Re-runs the entire pipeline from stored signals, compares byte-for-byte against `audit_trail.json`, and prints `PASS` or `FAIL` with the exact diverging record.

You can also click **"Run Deterministic Replay"** directly in the dashboard UI for a live demo.

### 7. Run the Full Test Suite

```bash
pytest tests/
```

All 12 tests across all 3 phases must pass. Covers every PRD edge case, tamper detection, and replay determinism.

---

## Constraints (as per PRD)

- ✅ Pure Python + standard library only (no external deps beyond `pytest`)
- ✅ No external databases, cloud services, or distributed systems
- ✅ No ML/LLM libraries
- ✅ No FastAPI — uses Python stdlib `http.server`
- ✅ No network access or external APIs required
- ✅ All decisions deterministic: same input → same output, every run
- ✅ Audit trails cryptographically immutable and replayable
- ✅ Replay has zero side effects — reads only, never writes
- ✅ 100 signals processed in under 10 seconds

---

## Deliverables Checklist (PRD §Deliverables)

- [x] **Public GitHub repository** — [github.com/Bhandarihansraj/VERITAS](https://github.com/Bhandarihansraj/VERITAS)
- [x] **Backend CLI + local API** — `cli.py` with `serve`, `ingest`, `simulate`, `resolve`, `replay`, `verify` commands
- [x] **Sample attack signal JSONs** — `samples/` directory covering all ≥5 edge cases
- [x] **Generated audit trail** — `audit_trail.json` (runtime-generated, gitignored)
- [x] **Replay script** — `replay.py` regenerates decisions from audit logs
- [x] **Automated test suite** — `pytest tests/` covers all edge cases including replay and timestamp transitions
- [x] **Documentation** — This README with clone → setup → run → test → replay instructions
