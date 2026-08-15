import pytest
import json
import hashlib
from veritas.ingestion import IngestionEngine, _compute_content_hash
from veritas.storage import Storage
from core.exceptions import DuplicateSignalError, ValidationError, IntegrityError

def _make_signal(**overrides):
    """Helper: build a valid signal with a correct cryptographic_hash."""
    base = {
        "signal_type": "video_stream",
        "identity_claim": "test_user",
        "source": "test_src",
        "confidence_score": 0.9,
        "timestamp": "2024-01-01T12:00:00Z",
    }
    base.update(overrides)
    # Compute correct hash from content
    base["cryptographic_hash"] = _compute_content_hash(base)
    return base

@pytest.fixture
def test_storage(tmp_path):
    return Storage(tmp_path / "test_signals.jsonl", allowed_dir=tmp_path)

@pytest.fixture
def engine(test_storage):
    return IngestionEngine(test_storage)

def test_normal_ingestion(engine):
    payload = _make_signal()
    engine.validate_and_ingest(payload)
    timeline = engine.get_timeline()
    assert len(timeline) == 1
    assert timeline[0]["identity_claim"] == "test_user"

def test_duplicate_same_hash_same_time(engine):
    payload = _make_signal()
    engine.validate_and_ingest(payload)
    with pytest.raises(DuplicateSignalError):
        engine.validate_and_ingest(payload.copy())

def test_replay_same_hash_later_time(engine):
    """Edge case 2: attacker replays exact same signal — hash matches content but already seen."""
    payload = _make_signal()
    engine.validate_and_ingest(payload)
    
    # Exact same signal replayed (identical content = identical hash)
    with pytest.raises(DuplicateSignalError):
        engine.validate_and_ingest(payload.copy())

def test_replay_tampered_timestamp(engine):
    """Edge case 2b: attacker changes timestamp but reuses old hash — integrity check catches it."""
    payload = _make_signal()
    engine.validate_and_ingest(payload)
    
    replay_payload = payload.copy()
    replay_payload["timestamp"] = "2024-01-01T13:00:00Z"
    # Hash no longer matches content → IntegrityError
    with pytest.raises(IntegrityError):
        engine.validate_and_ingest(replay_payload)

def test_malformed_missing_hash(engine):
    payload = {
        "signal_type": "video_stream",
        "identity_claim": "test_user",
        "source": "test_src",
        "confidence_score": 0.9,
        "timestamp": "2024-01-01T12:00:00Z"
    }
    with pytest.raises(ValidationError):
        engine.validate_and_ingest(payload)

def test_integrity_failure(engine):
    """Signal with a hash that doesn't match its content."""
    payload = _make_signal()
    payload["cryptographic_hash"] = "a" * 64  # Wrong hash
    with pytest.raises(IntegrityError):
        engine.validate_and_ingest(payload)

def test_out_of_order_slotting(engine):
    p1 = _make_signal(identity_claim="user_2", timestamp="2024-01-02T12:00:00Z")
    p2_older = _make_signal(identity_claim="user_1", timestamp="2024-01-01T12:00:00Z")
    engine.validate_and_ingest(p1)
    engine.validate_and_ingest(p2_older)
    
    timeline = engine.get_timeline()
    assert len(timeline) == 2
    assert timeline[0]["identity_claim"] == "user_1"  # The older one comes first
    assert timeline[1]["identity_claim"] == "user_2"
