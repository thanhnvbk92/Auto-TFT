from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


BoardStrength = Literal["weak", "even", "strong"]


@dataclass(frozen=True)
class GameState:
    stage: str = "2-1"
    level: int = 4
    gold: int = 0
    hp: int = 100
    streak: int = 0
    pairs: int = 0
    missing_core_units: int = 0
    board_strength: BoardStrength = "even"
    bench_full: bool = False
    contested: bool = False
    target_comp: str = ""


@dataclass(frozen=True)
class Advice:
    headline: str
    economy: str
    roll_level: str
    shop: str
    items: str
    positioning: str
    risk: str

