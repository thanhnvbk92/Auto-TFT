from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReadTiming:
    capture_seconds: float = 0.0
    ocr_seconds: float = 0.0
    total_seconds: float = 0.0

    def summary(self) -> str:
        return (
            f"Capture: {self.capture_seconds:.2f}s | "
            f"OCR: {self.ocr_seconds:.2f}s | "
            f"Total: {self.total_seconds:.2f}s"
        )


@dataclass(frozen=True)
class ScreenReadResult:
    image_path: Path
    raw_text: str
    fields: dict[str, str]
    ocr_available: bool
    source: str = "pc"
    error: str = ""
    timing: ReadTiming = ReadTiming()

