import pytest
from veritas.resolver import ConflictResolver
from veritas.storage import Storage

@pytest.fixture
def mock_storage(tmp_path):
    storage = Storage(tmp_path / "test_signals.jsonl", allowed_dir=tmp_path)
    return storage

@pytest.fixture
def resolver(mock_storage):
    return ConflictResolver(mock_storage)

def test_tier1_confidence(resolver, mock_storage):
    sig_low = {
        "identity_claim": "user_1",
        "confidence_score": 0.5,
        "source": "trusted_source",
        "timestamp": "2024-01-01T10:00:00Z"
    }
    sig_high = {
        "identity_claim": "user_1",
        "confidence_score": 0.9,
        "source": "untrusted_source",
        "timestamp": "2024-01-01T09:00:00Z"
    }
    mock_storage.append_signal(sig_low)
    mock_storage.append_signal(sig_high)
    
    res = resolver.resolve_conflicts()
    assert len(res) == 1
    assert res[0]["resolution_strategy"] == "confidence_score"
    assert res[0]["resolved_signal"]["confidence_score"] == 0.9

def test_tier2_source(resolver, mock_storage):
    sig_untrusted = {
        "identity_claim": "user_2",
        "confidence_score": 0.9,
        "source": "untrusted_source",
        "timestamp": "2024-01-01T10:00:00Z"
    }
    sig_trusted = {
        "identity_claim": "user_2",
        "confidence_score": 0.9,
        "source": "trusted_source",
        "timestamp": "2024-01-01T09:00:00Z"
    }
    mock_storage.append_signal(sig_untrusted)
    mock_storage.append_signal(sig_trusted)
    
    res = resolver.resolve_conflicts()
    assert res[0]["resolution_strategy"] == "source_reliability"
    assert res[0]["resolved_signal"]["source"] == "trusted_source"

def test_tier3_timestamp(resolver, mock_storage):
    sig_older = {
        "identity_claim": "user_3",
        "confidence_score": 0.9,
        "source": "trusted_source",
        "timestamp": "2024-01-01T10:00:00Z"
    }
    sig_newer = {
        "identity_claim": "user_3",
        "confidence_score": 0.9,
        "source": "trusted_source",
        "timestamp": "2024-01-01T11:00:00Z"
    }
    mock_storage.append_signal(sig_older)
    mock_storage.append_signal(sig_newer)
    
    res = resolver.resolve_conflicts()
    assert res[0]["resolution_strategy"] == "timestamp"
    assert res[0]["resolved_signal"]["timestamp"] == "2024-01-01T11:00:00Z"

def test_no_conflict(resolver, mock_storage):
    sig = {
        "identity_claim": "user_4",
        "confidence_score": 0.9,
        "source": "trusted_source",
        "timestamp": "2024-01-01T10:00:00Z"
    }
    mock_storage.append_signal(sig)
    
    res = resolver.resolve_conflicts()
    assert res[0]["resolution_strategy"] == "single_claim"
