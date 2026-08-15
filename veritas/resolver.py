import json
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, Any, List

from core.logger import get_logger
from core.config import CFG

log = get_logger(__name__)

class ConflictResolver:
    """Deterministic conflict resolution engine for identity claims."""
    
    def __init__(self, storage):
        self.storage = storage
        self.reliability = self._load_reliability()
        
    def _load_reliability(self) -> Dict[str, int]:
        path = CFG.base_dir / "veritas" / "config" / "source_reliability.json"
        if not path.exists():
            log.warning(f"Config not found at {path}, using defaults.")
            return {"trusted_source": 2, "untrusted_source": 1}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
            
    def _parse_ts(self, ts_str: str) -> datetime:
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    def resolve_conflicts(self) -> List[Dict[str, Any]]:
        """Resolves all stored signals down to one winning state per identity."""
        signals = self.storage.load_signals()
        
        # Group by identity_claim
        grouped = defaultdict(list)
        for sig in signals:
            grouped[sig["identity_claim"]].append(sig)
            
        results = []
        for identity, claims in grouped.items():
            if not claims:
                continue
                
            if len(claims) == 1:
                results.append({
                    "identity_claim": identity,
                    "resolved_signal": claims[0],
                    "conflicting_signals": [],
                    "resolution_strategy": "single_claim",
                    "resolved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                })
                continue
                
            def get_sort_key(sig):
                conf = float(sig.get("confidence_score", 0.0))
                rel = self.reliability.get(sig.get("source", ""), 0)
                ts = self._parse_ts(sig.get("timestamp", ""))
                return (conf, rel, ts)
                
            # Tie breaking cascade: confidence -> source -> timestamp
            sorted_claims = sorted(claims, key=get_sort_key, reverse=True)
            
            winner = sorted_claims[0]
            losers = sorted_claims[1:]
            runner_up = losers[0]
            
            winner_key = get_sort_key(winner)
            runner_up_key = get_sort_key(runner_up)
            
            if winner_key[0] > runner_up_key[0]:
                strategy = "confidence_score"
            elif winner_key[1] > runner_up_key[1]:
                strategy = "source_reliability"
            else:
                strategy = "timestamp"
                
            results.append({
                "identity_claim": identity,
                "resolved_signal": winner,
                "conflicting_signals": losers,
                "resolution_strategy": strategy,
                "resolved_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            })
            
        return results
