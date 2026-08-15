import pytest
from veritas.ingestion import IngestionEngine
from veritas.storage import Storage
from core.exceptions import DuplicateSignalError, ValidationError

@pytest.fixture
def test_storage(tmp_path):
    return Storage(tmp_path / "test_signals.jsonl", allowed_dir=tmp_path)

@pytest.fixture
def engine(test_storage):
    return IngestionEngine(test_storage)

def test_normal_ingestion(engine):
    payload = {
        "signal_type": "video_stream",
        "identity_claim": "test_user",
        "source": "test_src",
        "confidence_score": 0.9,
        "timestamp": "2024-01-01T12:00:00Z",
        "cryptographic_hash": "a" * 64
    }
    engine.validate_and_ingest(payload)
    timeline = engine.get_timeline()
    assert len(timeline) == 1
    assert timeline[0]["identity_claim"] == "test_user"

def test_duplicate_same_hash_same_time(engine):
    payload = {
        "signal_type": "video_stream",
        "identity_claim": "test_user",
        "source": "test_src",
        "confidence_score": 0.9,
        "timestamp": "2024-01-01T12:00:00Z",
        "cryptographic_hash": "a" * 64
    }
    engine.validate_and_ingest(payload)
    with pytest.raises(DuplicateSignalError):
        engine.validate_and_ingest(payload.copy())

def test_replay_same_hash_later_time(engine):
    payload = {
        "signal_type": "video_stream",
        "identity_claim": "test_user",
        "source": "test_src",
        "confidence_score": 0.9,
        "timestamp": "2024-01-01T12:00:00Z",
        "cryptographic_hash": "b" * 64
    }
    engine.validate_and_ingest(payload)
    
    replay_payload = payload.copy()
    replay_payload["timestamp"] = "2024-01-01T13:00:00Z"
    with pytest.raises(DuplicateSignalError):
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

def test_out_of_order_slotting(engine):
    p1 = {
        "signal_type": "video_stream",
        "identity_claim": "user_2",
        "source": "src",
        "confidence_score": 0.9,
        "timestamp": "2024-01-02T12:00:00Z",
        "cryptographic_hash": "c" * 64
    }
    p2_older = {
        "signal_type": "video_stream",
        "identity_claim": "user_1",
        "source": "src",
        "confidence_score": 0.9,
        "timestamp": "2024-01-01T12:00:00Z",
        "cryptographic_hash": "d" * 64
    }
    engine.validate_and_ingest(p1)
    engine.validate_and_ingest(p2_older)
    
    timeline = engine.get_timeline()
    assert len(timeline) == 2
    assert timeline[0]["identity_claim"] == "user_1" # The older one comes first
    assert timeline[1]["identity_claim"] == "user_2"
