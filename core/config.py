import os
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Config:
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "0") == "1")
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    signals_log_path: Path = field(init=False)

    def __post_init__(self):
        self.signals_log_path = self.data_dir / "signals_log.jsonl"

    @classmethod
    def from_env(cls) -> "Config":
        return cls()

CFG = Config.from_env()
