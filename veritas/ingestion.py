import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List

from core.logger import get_logger
from core.exceptions import ValidationError, DuplicateSignalError, IntegrityError
from veritas.storage import Storage

log = get_logger(__name__)

# Valid schema structure
REQUIRED_FIELDS = {
    "signal_type": str,
    "identity_claim": str,
    "source": str,
    "confidence_score": (float, int),
    "timestamp": str,
    "cryptographic_hash": str
}

VALID_SIGNAL_TYPES = {"video_stream", "behavioral_log", "device_fingerprint"}

def _compute_content_hash(payload: Dict[str, Any]) -> str:
    """Compute SHA-256 of the signal content (all fields except cryptographic_hash)."""
    content = {k: v for k, v in payload.items() if k != "cryptographic_hash"}
    canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

class IngestionEngine:
    """Core logic for signal validation, dedup, and timeline management."""
    
    def __init__(self, storage: Storage):
        self.storage = storage
        self.seen_hashes = set()
        self._load_existing()

    def _load_existing(self):
        try:
            existing = self.storage.load_signals()
            for sig in existing:
                self.seen_hashes.add(sig["cryptographic_hash"])
        except Exception as e:
            log.error(f"Could not load existing signals: {e}")

    def validate_and_ingest(self, payload: Dict[str, Any]) -> None:
        """Validates schema, checks hash integrity, deduplicates, and stores."""
        
        # 1. Schema Validation
        for field, ftype in REQUIRED_FIELDS.items():
            if field not in payload:
                raise ValidationError(f"Missing required field: {field}", code=400)
            if not isinstance(payload[field], ftype):
                raise ValidationError(f"Invalid type for {field}, expected {ftype}", code=400)

        if payload["signal_type"] not in VALID_SIGNAL_TYPES:
            raise ValidationError(f"Invalid signal_type: {payload['signal_type']}", code=400)

        if "fingerprint_value" in payload:
            if not isinstance(payload["fingerprint_value"], str):
                raise ValidationError("Invalid type for fingerprint_value, expected str", code=400)

        provided_hash = payload["cryptographic_hash"]
        if not provided_hash or not isinstance(provided_hash, str) or len(provided_hash) != 64:
            raise ValidationError("Missing or invalid cryptographic_hash", code=400)
            
        # 2. Cryptographic integrity verification — SHA-256 of content must match provided hash
        expected_hash = _compute_content_hash(payload)
        if provided_hash != expected_hash:
            raise IntegrityError(
                f"Cryptographic integrity failure: provided hash does not match signal content "
                f"(expected {expected_hash[:16]}..., got {provided_hash[:16]}...)",
                code=400
            )

        # 3. Hash-based replay/duplicate detection
        if provided_hash in self.seen_hashes:
            raise DuplicateSignalError(f"Duplicate signal detected with hash: {provided_hash}", code=409)

        # 4. Storage
        self.seen_hashes.add(provided_hash)
        self.storage.append_signal(payload)
        log.info(f"Ingested signal: {payload['identity_claim']} ({provided_hash[:8]}...)")

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Reconstruct the attack timeline using true chronological order."""
        signals = self.storage.load_signals()
        
        def parse_timestamp(sig):
            try:
                # Handle basic ISO 8601 parsing
                ts_str = sig["timestamp"].replace('Z', '+00:00')
                return datetime.fromisoformat(ts_str)
            except ValueError:
                return datetime.min

        return sorted(signals, key=parse_timestamp)
