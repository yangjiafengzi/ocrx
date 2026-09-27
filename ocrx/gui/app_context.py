# -- coding: utf-8 --
"""Shared application services for GUI layers."""

from pathlib import Path

from ..clipboard import ClipboardHistory
from ..config import ConfigManager
from ..example_library import ExampleLibrary
from ..logger import StructuredLogger
from ..processing_service import ProcessingService
from .session_state import SessionState


class AppContext:
    """Owns long-lived services and session state shared across the GUI."""

    def __init__(self, config_path=None, example_path=None, log_path=None, root=None):
        self.config = ConfigManager(config_path)
        self.config.load()
        self.examples = ExampleLibrary(example_path)
        self.logger = StructuredLogger(log_file_path=log_path)
        self.clipboard = ClipboardHistory(root=root)
        self.state = SessionState()
        self.service: ProcessingService | None = None
        self.rebuild_service()

    def rebuild_service(self) -> None:
        """Recreate ProcessingService from the current config values."""
        cfg = self.config.config
        self.service = ProcessingService(
            api_key=cfg.get("API_KEY", ""),
            base_url=cfg.get("BASE_URL", ""),
            model_name=cfg.get("MODEL_NAME", ""),
            output_dir=cfg.get("OUTPUT_DIR", ""),
            max_workers=int(cfg.get("MAX_WORKERS", "10")),
            pdf_scale=float(cfg.get("PDF_SCALE_FACTOR", "3.0")),
            logger_inst=self.logger,
        )

    def load_example_images(self, example_ids: list[str]) -> list[tuple[str, bytes]]:
        """Load (text, image bytes) pairs for the given example ids."""
        loaded: list[tuple[str, bytes]] = []
        for ex_id in example_ids:
            example = self.examples.get_example(ex_id)
            if not example:
                continue
            path = Path(example.image_path)
            if path.exists():
                loaded.append((example.text, path.read_bytes()))
        return loaded
