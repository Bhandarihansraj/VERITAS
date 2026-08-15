import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple

from core.logger import get_logger
from core.config import CFG

log = get_logger(__name__)

GENESIS_HASH = "VERITAS_GENESIS"

def _canonical_json(data: Dict[str, Any]) -> str:
    """Canonical JSON serialization for reproducible hashing."""
    clean_data = {k: v for k, v in data.items() if k != "audit_hash"}
    return json.dumps(clean_data, sort_keys=True, separators=(',', ':'))

def compute_audit_hash(data: Dict[str, Any]) -> str:
    """Computes SHA-256 of the canonical record."""
    canonical = _canonical_json(data)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

def generate_audit_record(resolved_state: Dict[str, Any], prev_hash: str) -> Dict[str, Any]:
    """Builds a single immutable audit record from a Phase 2 resolution."""
    record = {
        "original_signals": [resolved_state["resolved_signal"]] + resolved_state["conflicting_signals"],
        "conflicting_signals": resolved_state["conflicting_signals"],
        "resolution_strategy": resolved_state["resolution_strategy"],
        "resolved_identity": resolved_state["resolved_signal"],
        "timestamp": resolved_state["resolved_at"],
        "prev_hash": prev_hash
    }
    record["audit_hash"] = compute_audit_hash(record)
    return record

class AuditTrail:
    """Append-only immutable audit log manager."""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.touch()

    def append_record(self, record: Dict[str, Any]):
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def load_records(self) -> list:
        if not self.file_path.exists():
            return []
        records = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def get_last_hash(self) -> str:
        records = self.load_records()
        if not records:
            return GENESIS_HASH
        return records[-1].get("audit_hash", GENESIS_HASH)
        
    def rebuild_from_resolutions(self, resolutions: list):
        """Clears trail and rebuilds from scratch (for replay testing or initial generation)."""
        if self.file_path.exists():
            open(self.file_path, 'w').close() # Truncate
            
        prev = GENESIS_HASH
        for res in resolutions:
            rec = generate_audit_record(res, prev)
            self.append_record(rec)
            prev = rec["audit_hash"]

def verify_chain(file_path: Path) -> Tuple[bool, Dict[str, Any]]:
    """Walks the entire audit trail to verify cryptographic links and integrity."""
    trail = AuditTrail(file_path)
    records = trail.load_records()
    
    proof = {
        "first_hash": None,
        "last_hash": None,
        "record_count": len(records),
        "verified": True,
        "error": None
    }
    
    if not records:
        return True, proof
        
    proof["first_hash"] = records[0].get("audit_hash")
    
    prev = GENESIS_HASH
    for i, rec in enumerate(records):
        # 1. Verify prev_hash link
        if rec.get("prev_hash") != prev:
            proof["verified"] = False
            proof["error"] = f"Broken chain at index {i}: prev_hash mismatch. Expected {prev}, got {rec.get('prev_hash')}"
            break
            
        # 2. Verify audit_hash integrity
        expected_hash = compute_audit_hash(rec)
        if rec.get("audit_hash") != expected_hash:
            proof["verified"] = False
            proof["error"] = f"Tampered record at index {i}: audit_hash mismatch. Expected {expected_hash}, got {rec.get('audit_hash')}"
            break
            
        prev = rec["audit_hash"]
        
    if proof["verified"]:
        proof["last_hash"] = prev
    
    # Save chain proof
    proof_path = file_path.parent / "chain_proof.json"
    with open(proof_path, "w", encoding="utf-8") as f:
        json.dump(proof, f, indent=2)
        
    return proof["verified"], proof
