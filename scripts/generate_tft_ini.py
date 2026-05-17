from __future__ import annotations

import argparse
import configparser
import json
import re
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_URL = "https://raw.communitydragon.org/latest/cdragon/tft/en_us.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate TFT INI data from CommunityDragon JSON.")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--set-number", type=int, default=None)
    parser.add_argument("--output-dir", default="data/generated")
    parser.add_argument("--download-assets", action="store_true")
    parser.add_argument(
        "--asset-kinds",
        nargs="+",
        choices=["champions", "traits", "items"],
        default=["champions", "traits", "items"],
    )
    args = parser.parse_args()

    data = download_json(args.source_url)
    set_data = choose_set(data, args.set_number)
    output_dir = Path(args.output_dir) / f"set{set_data['number']}"
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_root = output_dir / "assets" if args.download_assets else None

    write_meta(output_dir / "meta.ini", data, set_data, args.source_url)
    write_champions(
        output_dir / "champions.ini",
        set_data.get("champions", []),
        asset_root if "champions" in args.asset_kinds else None,
    )
    write_traits(
        output_dir / "traits.ini",
        set_data.get("traits", []),
        asset_root if "traits" in args.asset_kinds else None,
    )
    write_items(
        output_dir / "items.ini",
        collect_items(data, set_data),
        asset_root if "items" in args.asset_kinds else None,
    )

    print(f"Generated TFT INI data for set {set_data['number']} ({set_data.get('name', '')})")
    print(output_dir)


def download_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "Auto-TFT-Companion/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def choose_set(data: dict[str, Any], set_number: int | None) -> dict[str, Any]:
    sets = data.get("setData", [])
    if not sets:
        raise RuntimeError("CommunityDragon response did not contain setData.")

    if set_number is None:
        set_number = max(int(s.get("number", 0)) for s in sets)

    candidates = [s for s in sets if int(s.get("number", -1)) == set_number]
    if not candidates:
        raise RuntimeError(f"Set {set_number} was not found in source data.")

    return max(candidates, key=lambda s: (len(s.get("champions", [])), len(s.get("traits", []))))


def write_meta(path: Path, data: dict[str, Any], set_data: dict[str, Any], source_url: str) -> None:
    config = new_config()
    config["source"] = {
        "url": source_url,
        "set_number": str(set_data.get("number", "")),
        "set_name": str(set_data.get("name", "")),
        "champion_count": str(len(set_data.get("champions", []))),
        "trait_count": str(len(set_data.get("traits", []))),
        "item_count": str(len(collect_items(data, set_data))),
    }
    save_config(path, config)


def write_champions(path: Path, champions: list[dict[str, Any]], asset_root: Path | None) -> None:
    config = new_config()
    for champion in sorted(champions, key=lambda c: (int(c.get("cost", 0)), c.get("name", ""))):
        section = section_name(champion.get("apiName") or champion.get("characterName") or champion.get("name"))
        stats = champion.get("stats") or {}
        ability = champion.get("ability") or {}
        icon_source = champion.get("tileIcon") or champion.get("squareIcon") or champion.get("icon")
        local_icon = download_asset(asset_root, "champions", section, icon_source) if asset_root else ""
        ability_local_icon = (
            download_asset(asset_root, "abilities", f"{section}_ability", ability.get("icon"))
            if asset_root
            else ""
        )
        config[section] = {
            "name": text(champion.get("name")),
            "api_name": text(champion.get("apiName")),
            "character_name": text(champion.get("characterName")),
            "cost": text(champion.get("cost")),
            "traits": pipe(champion.get("traits")),
            "role": text(champion.get("role")),
            "icon": text(champion.get("icon")),
            "square_icon": text(champion.get("squareIcon")),
            "tile_icon": text(champion.get("tileIcon")),
            "local_icon": local_icon,
            "hp": text(stats.get("hp")),
            "armor": text(stats.get("armor")),
            "magic_resist": text(stats.get("magicResist")),
            "attack_damage": text(stats.get("damage")),
            "attack_speed": text(stats.get("attackSpeed")),
            "range": text(stats.get("range")),
            "mana": text(stats.get("mana")),
            "initial_mana": text(stats.get("initialMana")),
            "ability_name": text(ability.get("name")),
            "ability_desc": text(ability.get("desc")),
            "ability_icon": text(ability.get("icon")),
            "ability_local_icon": ability_local_icon,
            "ability_variables_json": json.dumps(
                ability.get("variables") or [], ensure_ascii=False, separators=(",", ":")
            ),
            "ability_json": json.dumps(ability, ensure_ascii=False, separators=(",", ":")),
        }
    save_config(path, config)


def write_traits(path: Path, traits: list[dict[str, Any]], asset_root: Path | None) -> None:
    config = new_config()
    for trait in sorted(traits, key=lambda t: t.get("name", "")):
        section = section_name(trait.get("apiName") or trait.get("name"))
        effects = trait.get("effects") or []
        local_icon = download_asset(asset_root, "traits", section, trait.get("icon")) if asset_root else ""
        config[section] = {
            "name": text(trait.get("name")),
            "api_name": text(trait.get("apiName")),
            "desc": text(trait.get("desc")),
            "icon": text(trait.get("icon")),
            "local_icon": local_icon,
            "breakpoints": pipe([effect.get("minUnits") for effect in effects if effect.get("minUnits")]),
            "effects_json": json.dumps(effects, ensure_ascii=False, separators=(",", ":")),
        }
    save_config(path, config)


def write_items(path: Path, items: list[dict[str, Any]], asset_root: Path | None) -> None:
    config = new_config()
    for item in sorted(items, key=lambda i: text(i.get("name"))):
        section = section_name(item.get("apiName") or item.get("name") or item.get("id"))
        local_icon = download_asset(asset_root, "items", section, item.get("icon")) if asset_root else ""
        config[section] = {
            "name": text(item.get("name")),
            "api_name": text(item.get("apiName")),
            "id": text(item.get("id")),
            "desc": text(item.get("desc")),
            "composition": pipe(item.get("composition")),
            "from": pipe(item.get("from")),
            "tags": pipe(item.get("tags")),
            "associated_traits": pipe(item.get("associatedTraits")),
            "incompatible_traits": pipe(item.get("incompatibleTraits")),
            "unique": text(item.get("unique")),
            "icon": text(item.get("icon")),
            "local_icon": local_icon,
            "effects_json": json.dumps(item.get("effects") or {}, ensure_ascii=False, separators=(",", ":")),
        }
    save_config(path, config)


def collect_items(data: dict[str, Any], set_data: dict[str, Any]) -> list[dict[str, Any]]:
    set_item_refs = set(text(item) for item in (set_data.get("items") or []) if text(item))
    by_key: dict[str, dict[str, Any]] = {}
    for item in normalize_collection(data.get("items")):
        key = str(item.get("apiName") or item.get("id") or item.get("name") or "")
        if key and (not set_item_refs or key in set_item_refs):
            by_key[key] = item
    return list(by_key.values())


def download_asset(asset_root: Path | None, kind: str, section: str, source_path: Any) -> str:
    if not asset_root or not source_path:
        return ""

    url = communitydragon_asset_url(text(source_path))
    if not url:
        return ""

    target_dir = asset_root / kind
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{section}.png"
    if target.exists() and target.stat().st_size > 0:
        return str(target.as_posix())

    request = urllib.request.Request(url, headers={"User-Agent": "Auto-TFT-Companion/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            target.write_bytes(response.read())
        return str(target.as_posix())
    except Exception:
        return ""


def communitydragon_asset_url(source_path: str) -> str:
    if not source_path:
        return ""
    normalized = source_path.replace("\\", "/").lower()
    if normalized.endswith(".tex"):
        normalized = normalized[:-4] + ".png"
    return f"https://raw.communitydragon.org/latest/game/{normalized}"


def normalize_collection(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    return []


def new_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    return config


def save_config(path: Path, config: configparser.ConfigParser) -> None:
    with path.open("w", encoding="utf-8") as handle:
        config.write(handle)


def section_name(value: Any) -> str:
    name = text(value) or "unknown"
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9_.:-]", "", name)
    return name or "unknown"


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).replace("\n", " ").strip()


def pipe(values: Any) -> str:
    if not values:
        return ""
    if not isinstance(values, list):
        values = [values]
    return "|".join(text(value) for value in values if text(value))


if __name__ == "__main__":
    main()
