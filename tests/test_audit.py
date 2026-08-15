import pytest
import json
from pathlib import Path
from veritas.audit import AuditTrail, verify_chain, generate_audit_record, GENESIS_HASH

@pytest.fixture
def temp_audit_file(tmp_path):
    return tmp_path / "audit_trail.json"

def test_audit_generation(temp_audit_file):
    resolved = {
        "identity_claim": "test_id",
        "resolved_signal": {"timestamp": "2024-01-01T10:00:00Z", "val": 1},
        "conflicting_signals": [{"timestamp": "2024-01-01T09:00:00Z", "val": 2}],
        "resolution_strategy": "timestamp",
        "resolved_at": "2024-01-01T10:00:00Z"
    }
    
    trail = AuditTrail(temp_audit_file)
    rec = generate_audit_record(resolved, GENESIS_HASH)
    trail.append_record(rec)
    
    records = trail.load_records()
    assert len(records) == 1
    assert records[0]["prev_hash"] == GENESIS_HASH
    
    success, proof = verify_chain(temp_audit_file)
    assert success is True

def test_audit_tampering(temp_audit_file):
    resolved = {
        "identity_claim": "test_id",
        "resolved_signal": {"timestamp": "2024-01-01T10:00:00Z", "val": 1},
        "conflicting_signals": [],
        "resolution_strategy": "single_claim",
        "resolved_at": "2024-01-01T10:00:00Z"
    }
    trail = AuditTrail(temp_audit_file)
    rec = generate_audit_record(resolved, GENESIS_HASH)
    trail.append_record(rec)
    
    with open(temp_audit_file, "r") as f:
        data = f.read()
        
    data = data.replace('"val": 1', '"val": 999')
    with open(temp_audit_file, "w") as f:
        f.write(data)
        
    success, proof = verify_chain(temp_audit_file)
    assert success is False
    assert "Tampered record" in proof["error"]
