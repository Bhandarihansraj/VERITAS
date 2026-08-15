import sys
import json
from pathlib import Path

from core.config import CFG
from veritas.storage import Storage
from veritas.resolver import ConflictResolver
from veritas.audit import AuditTrail, _canonical_json, generate_audit_record, GENESIS_HASH

def run_replay():
    print("--- VERITAS Deterministic Replay Engine ---")
    
    storage = Storage(CFG.signals_log_path, allowed_dir=CFG.base_dir)
    
    resolver = ConflictResolver(storage)
    resolutions = resolver.resolve_conflicts()
    
    fresh_trail = []
    prev = GENESIS_HASH
    for res in resolutions:
        rec = generate_audit_record(res, prev)
        fresh_trail.append(rec)
        prev = rec["audit_hash"]
        
    audit_path = CFG.base_dir / "audit_trail.json"
    if not audit_path.exists():
        print("FAIL: No audit_trail.json found.")
        return False
        
    stored_trail = []
    with open(audit_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                stored_trail.append(json.loads(line.strip()))
                
    if len(fresh_trail) != len(stored_trail):
        print(f"FAIL: Record count mismatch. Replayed {len(fresh_trail)}, stored {len(stored_trail)}")
        return False
        
    for i, (fresh, stored) in enumerate(zip(fresh_trail, stored_trail)):
        fresh_canon = _canonical_json(fresh)
        stored_canon = _canonical_json(stored)
        
        if fresh_canon != stored_canon:
            print(f"FAIL: Divergence at record index {i}!")
            print(f"Expected (Stored): {stored_canon}")
            print(f"Actual (Replayed): {fresh_canon}")
            return False
            
        if fresh["audit_hash"] != stored["audit_hash"]:
            print(f"FAIL: Hash divergence at record index {i}!")
            return False
            
    print("PASS: Replay verification successful. 100% deterministic match.")
    return True

if __name__ == "__main__":
    success = run_replay()
    sys.exit(0 if success else 1)
