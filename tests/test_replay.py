import pytest
import json
import replay
from veritas.storage import Storage
from veritas.resolver import ConflictResolver
from veritas.audit import AuditTrail
from veritas.ingestion import _compute_content_hash

def _make_signal(**overrides):
    """Helper: build a valid signal with a correct cryptographic_hash."""
    base = {
        "signal_type": "device_fingerprint",
        "identity_claim": "user_conf",
        "source": "untrusted_source",
        "confidence_score": 0.5,
        "timestamp": "2024-01-01T10:00:00Z",
    }
    base.update(overrides)
    base["cryptographic_hash"] = _compute_content_hash(base)
    return base

def test_replay_deterministic(tmp_path, monkeypatch):
    sig_log = tmp_path / "test_signals.jsonl"
    audit_log = tmp_path / "audit_trail.json"
    
    import core.config
    monkeypatch.setattr(core.config.CFG, "signals_log_path", sig_log)
    monkeypatch.setattr(core.config.CFG, "base_dir", tmp_path)
    
    storage = Storage(sig_log, allowed_dir=tmp_path)
    storage.append_signal(_make_signal())
    
    resolver = ConflictResolver(storage)
    resolutions = resolver.resolve_conflicts()
    trail = AuditTrail(audit_log)
    trail.rebuild_from_resolutions(resolutions)
    
    # Verify deterministic success
    success = replay.run_replay()
    assert success is True
    
    # Tamper with the saved audit log
    with open(audit_log, "r") as f:
        data = f.read()
    data = data.replace('untrusted_source', 'trusted_source')
    with open(audit_log, "w") as f:
        f.write(data)
        
    # Verify replay fails when history is tampered
    success = replay.run_replay()
    assert success is False
