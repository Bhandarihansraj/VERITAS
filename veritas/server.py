import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from core.logger import get_logger
from core.exceptions import ValidationError, DuplicateSignalError, IntegrityError
from core.config import CFG
from veritas.storage import Storage
from veritas.ingestion import IngestionEngine
from veritas.resolver import ConflictResolver

log = get_logger(__name__)

class VeritasHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        pass

    def _send_response(self, status: int, payload: dict):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/timeline':
            engine = self.server.engine
            timeline = engine.get_timeline()
            
            self._send_response(200, {
                "timeline": timeline, 
                "feed": self.server.feed[:20],
                "stats": {
                    "ingested": len(timeline),
                    "duplicates": self.server.stats.get("duplicates", 0),
                    "malformed": self.server.stats.get("malformed", 0)
                }
            })
        elif parsed.path == '/resolutions':
            try:
                resolutions = self.server.resolver.resolve_conflicts()
                # Auto-generate audit trail on resolution for Phase 3
                from veritas.audit import AuditTrail
                trail = AuditTrail(CFG.base_dir / "audit_trail.json")
                trail.rebuild_from_resolutions(resolutions)
                
                self._send_response(200, {"resolutions": resolutions})
            except Exception as e:
                log.error(f"Resolution error: {e}")
                self._send_response(500, {"error": "Resolution error"})
        elif parsed.path == '/audit':
            try:
                from veritas.audit import AuditTrail
                trail = AuditTrail(CFG.base_dir / "audit_trail.json")
                records = trail.load_records()
                self._send_response(200, {"audit_trail": records})
            except Exception as e:
                self._send_response(500, {"error": str(e)})
        elif parsed.path == '/replay':
            try:
                import replay
                success = replay.run_replay()
                self._send_response(200, {"success": success})
            except Exception as e:
                self._send_response(500, {"error": str(e)})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/attack_signals':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.server.stats["malformed"] += 1
                self.server.feed.insert(0, {"status": "rejected", "reason": "Empty payload", "payload": {}})
                self._send_response(400, {"error": "Empty payload"})
                return

            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                # Pre-save payload state for feed
                feed_payload = payload.copy()
                
                self.server.engine.validate_and_ingest(payload)
                self.server.feed.insert(0, {"status": "accepted", "reason": "Verified & New", "payload": feed_payload})
                self._send_response(200, {"status": "accepted"})
            except json.JSONDecodeError:
                self.server.stats["malformed"] += 1
                self.server.feed.insert(0, {"status": "rejected", "reason": "Invalid JSON format", "payload": {}})
                self._send_response(400, {"error": "Invalid JSON format"})
            except ValidationError as e:
                self.server.stats["malformed"] += 1
                self.server.feed.insert(0, {"status": "rejected", "reason": str(e), "payload": feed_payload if 'feed_payload' in locals() else {}})
                self._send_response(400, {"error": str(e)})
            except IntegrityError as e:
                self.server.stats["malformed"] += 1
                self.server.feed.insert(0, {"status": "rejected", "reason": str(e), "payload": feed_payload if 'feed_payload' in locals() else {}})
                self._send_response(400, {"error": str(e)})
            except DuplicateSignalError as e:
                self.server.stats["duplicates"] += 1
                self.server.feed.insert(0, {"status": "rejected", "reason": str(e), "payload": feed_payload if 'feed_payload' in locals() else {}})
                self._send_response(409, {"error": str(e)})
            except Exception as e:
                log.error(f"Unexpected error during ingestion: {e}")
                self._send_response(500, {"error": "Internal server error"})
                
            # Cap feed length
            self.server.feed = self.server.feed[:20]
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port: int = 8585):
    storage = Storage(CFG.signals_log_path)
    engine = IngestionEngine(storage)
    resolver = ConflictResolver(storage)
    
    server = HTTPServer(('127.0.0.1', port), VeritasHandler)
    server.engine = engine
    server.resolver = resolver
    server.stats = {"duplicates": 0, "malformed": 0}
    server.feed = []
    
    log.info(f"VERITAS Server listening on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Server shutting down.")
        server.server_close()
