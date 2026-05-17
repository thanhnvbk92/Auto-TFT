from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TftStaticData:
    meta: dict[str, str]
    champions: dict[str, dict[str, str]]
    traits: dict[str, dict[str, str]]
    items: dict[str, dict[str, str]]


def load_tft_static_data(data_dir: Path) -> TftStaticData:
    return TftStaticData(
        meta=load_ini(data_dir / "meta.ini").get("source", {}),
        champions=load_ini(data_dir / "champions.ini"),
        traits=load_ini(data_dir / "traits.ini"),
        items=load_ini(data_dir / "items.ini"),
    )


def load_ini(path: Path) -> dict[str, dict[str, str]]:
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    config.read(path, encoding="utf-8")
    return {section: dict(config[section]) for section in config.sections()}

