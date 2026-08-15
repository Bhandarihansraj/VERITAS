# VERITAS Phase 1

**Verified Evidence Reconciliation for Identity Trust & Audit System**

This is Phase 1 of 3: Ingestion & Integrity Layer.

## Setup

```bash
# Optional but recommended: use a virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Running Tests

```bash
pytest tests/
```

## Running the Server and UI

1. Open `ui/dashboard.html` in your browser.
2. In a terminal, run the server:
```bash
python cli.py serve
```

3. In another terminal, simulate the attack signals (which cover all edge cases):
```bash
python cli.py simulate
```

Watch the dashboard populate in real-time and properly slot out-of-order items, while discarding duplicated/malformed events!
