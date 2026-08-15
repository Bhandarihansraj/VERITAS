import json
from pathlib import Path
from typing import Dict, Any, List

from core.config import CFG
from core.exceptions import StorageError
from core.logger import get_logger

log = get_logger(__name__)

class Storage:
    """Secure append-only JSONL storage adapter."""
    
    def __init__(self, file_path: Path, allowed_dir: Path = None):
        self.allowed_dir = allowed_dir or CFG.data_dir
        self.file_path = self._secure_path(file_path, self.allowed_dir)
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.touch()

    def _secure_path(self, target_path: Path, allowed_dir: Path) -> Path:
        """Security: Path sanitization to prevent path traversal CVEs."""
        resolved = target_path.resolve()
        if not str(resolved).startswith(str(allowed_dir.resolve())):
            raise StorageError(f"Path traversal detected: {target_path}", code=403)
        return resolved

    def append_signal(self, signal: Dict[str, Any]) -> None:
        """Appends a single JSON signal to the log."""
        try:
            with open(self.file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(signal) + '\n')
        except IOError as e:
            raise StorageError(f"Failed to write signal: {e}")

    def load_signals(self) -> List[Dict[str, Any]]:
        """Loads all signals from the log."""
        signals = []
        if not self.file_path.exists():
            return signals
            
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        signals.append(json.loads(line))
        except IOError as e:
            raise StorageError(f"Failed to read signals: {e}")
        return signals
