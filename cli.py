import argparse
import sys
import time
import urllib.request
from pathlib import Path

from core.logger import get_logger
from veritas.server import run_server

log = get_logger("cli")

def cmd_serve(args):
    run_server(args.port)

def cmd_resolve(args):
    from veritas.storage import Storage
    from veritas.resolver import ConflictResolver
    from core.config import CFG
    storage = Storage(CFG.signals_log_path)
    resolver = ConflictResolver(storage)
    resolutions = resolver.resolve_conflicts()
    print(json.dumps(resolutions, indent=2))

def cmd_simulate(args):
    base_dir = Path(__file__).parent
    samples_dir = base_dir / "samples"
    if not samples_dir.exists():
        log.error("samples/ directory not found.")
        sys.exit(1)

    url = f"http://127.0.0.1:{args.port}/attack_signals"
    
    payloads = [
        ("normal.json", "Normal signal"),
        ("duplicate.json", "Duplicate (same hash, same time)"),
        ("replay.json", "Replay (same hash, later time)"),
        ("malformed.json", "Malformed (missing hash)"),
        ("out_of_order.json", "Out-of-order timestamp"),
        ("conflict_tier1_a.json", "Conflict Tier 1 A (Low Confidence)"),
        ("conflict_tier1_b.json", "Conflict Tier 1 B (High Confidence)"),
        ("conflict_tier2_a.json", "Conflict Tier 2 A (Untrusted Source)"),
        ("conflict_tier2_b.json", "Conflict Tier 2 B (Trusted Source)"),
        ("conflict_tier3_a.json", "Conflict Tier 3 A (Older)"),
        ("conflict_tier3_b.json", "Conflict Tier 3 B (Newer)")
    ]

    for filename, desc in payloads:
        path = samples_dir / filename
        if not path.exists():
            log.warning(f"Sample {filename} not found, skipping.")
            continue
            
        with open(path, 'r') as f:
            data = f.read()

        req = urllib.request.Request(url, data=data.encode('utf-8'), method='POST')
        req.add_header('Content-Type', 'application/json')
        
        log.info(f"Sending {desc} ({filename})...")
        try:
            with urllib.request.urlopen(req) as response:
                log.info(f"Success: {response.status}")
        except urllib.error.HTTPError as e:
            log.info(f"Rejected: {e.code} ({e.read().decode('utf-8')})")
        except Exception as e:
            log.error(f"Failed to send: {e}")
            
        time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description="VERITAS CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    parser_serve = subparsers.add_parser("serve", help="Run the VERITAS server")
    parser_serve.add_argument("--port", type=int, default=8585)
    
    parser_simulate = subparsers.add_parser("simulate", help="Send test payloads")
    parser_simulate.add_argument("--port", type=int, default=8585)
    
    parser_resolve = subparsers.add_parser("resolve", help="Run deterministic conflict resolution")
    
    args = parser.parse_args()
    
    if args.command == "serve":
        cmd_serve(args)
    elif args.command == "simulate":
        cmd_simulate(args)
    elif args.command == "resolve":
        cmd_resolve(args)

if __name__ == "__main__":
    main()
