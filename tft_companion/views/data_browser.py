from __future__ import annotations

import html
import re
import tkinter as tk
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk

from tft_companion.views.constants import DATA_DIR, ROOT


def build_data_browser(
    app: ctk.CTk,
    parent: ctk.CTkFrame,
    title: str,
    rows: dict[str, dict[str, str]],
    formatter,
) -> None:
    parent.grid_columnconfigure(0, weight=0)
    parent.grid_columnconfigure(1, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    list_card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16, width=330)
    list_card.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)
    list_card.grid_propagate(False)
    ctk.CTkLabel(
        list_card,
        text=title,
        font=ctk.CTkFont(size=20, weight="bold"),
        anchor="w",
    ).pack(fill="x", padx=18, pady=(16, 4))
    ctk.CTkLabel(
        list_card,
        text=f"{len(rows)} records loaded from INI",
        text_color="#94A3B8",
        anchor="w",
    ).pack(fill="x", padx=18, pady=(0, 12))

    detail_card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
    detail_card.grid(row=0, column=1, sticky="nsew", padx=(8, 12), pady=12)
    detail_card.grid_columnconfigure(0, weight=1)
    detail_card.grid_rowconfigure(1, weight=1)

    header = ctk.CTkFrame(detail_card, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
    header.grid_columnconfigure(1, weight=1)
    icon_label = tk.Label(header, text="", bg="#111827", fg="#64748B", width=96, height=96)
    icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 16))
    title_label = ctk.CTkLabel(
        header,
        text="Select a record",
        font=ctk.CTkFont(size=24, weight="bold"),
        anchor="w",
        justify="left",
    )
    title_label.grid(row=0, column=1, sticky="ew")

    detail_box = ctk.CTkTextbox(
        detail_card,
        wrap="word",
        font=ctk.CTkFont(family="Segoe UI", size=14),
        fg_color="#0B1220",
        corner_radius=14,
    )
    detail_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

    display_to_key = display_map(rows)
    displays = list(display_to_key)
    selected = tk.StringVar(value=displays[0] if displays else "No data")

    def show_selected(display: str) -> None:
        key = display_to_key.get(display)
        row = rows.get(key or "", {})
        title_label.configure(text=row.get("name") or key or "Unknown")
        detail_box.configure(state="normal")
        detail_box.delete("1.0", "end")
        detail_box.insert("1.0", formatter(key or "", row))
        detail_box.configure(state="disabled")
        set_data_icon(app, icon_label, row, f"{title}:{key}")

    if displays:
        ctk.CTkOptionMenu(
            list_card,
            values=displays,
            variable=selected,
            command=show_selected,
            height=38,
            fg_color="#0B1220",
            button_color="#2563EB",
            button_hover_color="#1D4ED8",
        ).pack(fill="x", padx=18, pady=(0, 12))

        scroll = ctk.CTkScrollableFrame(list_card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 14))
        for display in displays[:180]:
            ctk.CTkButton(
                scroll,
                text=display,
                command=lambda value=display: (selected.set(value), show_selected(value)),
                height=32,
                corner_radius=8,
                anchor="w",
                fg_color="#0B1220",
                hover_color="#1E293B",
                text_color="#E2E8F0",
            ).pack(fill="x", pady=2)
        if len(displays) > 180:
            ctk.CTkLabel(
                scroll,
                text="Use the dropdown above for the remaining records.",
                text_color="#94A3B8",
                wraplength=260,
                justify="left",
            ).pack(fill="x", pady=8)
        show_selected(displays[0])
    else:
        detail_box.insert("1.0", f"No {title.lower()} data found. Generate INI files first.")
        detail_box.configure(state="disabled")


def display_map(rows: dict[str, dict[str, str]]) -> dict[str, str]:
    pairs: list[tuple[str, str]] = []
    for key, row in rows.items():
        name = row.get("name") or key
        cost = row.get("cost")
        prefix = f"{cost}g " if cost else ""
        label = f"{prefix}{name} [{key}]"
        pairs.append((label, key))
    pairs.sort(key=lambda pair: pair[0].lower())
    return dict(pairs)


def format_champion(key: str, row: dict[str, str]) -> str:
    traits = row.get("traits", "").replace("|", ", ")
    lines = [
        f"Name: {row.get('name', key)}",
        f"API: {row.get('api_name', key)}",
        f"Cost: {row.get('cost', '-')}",
        f"Traits: {traits or '-'}",
        f"Role: {row.get('role', '-')}",
        "",
        "Stats",
        f"HP: {row.get('hp', '-')}",
        f"Armor / MR: {row.get('armor', '-')} / {row.get('magic_resist', '-')}",
        f"AD / AS / Range: {row.get('attack_damage', '-')} / {row.get('attack_speed', '-')} / {row.get('range', '-')}",
        f"Mana: {row.get('initial_mana', '0')} / {row.get('mana', '-')}",
        "",
        "Ability",
        f"Name: {row.get('ability_name', '-')}",
        clean_markup(row.get("ability_desc", "")) or "-",
        "",
        "Assets",
        f"Champion icon: {row.get('local_icon', '-')}",
        f"Ability icon: {row.get('ability_local_icon', '-')}",
    ]
    return "\n".join(lines)


def format_item(key: str, row: dict[str, str]) -> str:
    lines = [
        f"Name: {row.get('name') or key}",
        f"API: {row.get('api_name', key)}",
        f"ID: {row.get('id', '-')}",
        f"Unique: {row.get('unique', '-')}",
        f"Tags: {row.get('tags', '-')}",
        f"Composition: {row.get('composition', '-')}",
        f"From: {row.get('from', '-')}",
        "",
        "Description",
        clean_markup(row.get("desc", "")) or "-",
        "",
        "Traits",
        f"Associated: {row.get('associated_traits', '-')}",
        f"Incompatible: {row.get('incompatible_traits', '-')}",
        "",
        "Assets / Effects",
        f"Icon: {row.get('local_icon', '-')}",
        f"Effects JSON: {row.get('effects_json', '-')}",
    ]
    return "\n".join(lines)


def format_trait(key: str, row: dict[str, str]) -> str:
    lines = [
        f"Name: {row.get('name') or key}",
        f"API: {row.get('api_name', key)}",
        f"Breakpoints: {row.get('breakpoints', '-')}",
        "",
        "Description",
        clean_markup(row.get("desc", "")) or "-",
        "",
        "Assets / Effects",
        f"Icon: {row.get('local_icon', '-')}",
        f"Effects JSON: {row.get('effects_json', '-')}",
    ]
    return "\n".join(lines)


def clean_markup(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(row|expandRow|rules)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def set_data_icon(app: ctk.CTk, label: tk.Label, row: dict[str, str], cache_key: str) -> None:
    path_text = row.get("local_icon") or row.get("ability_local_icon") or ""
    path = resolve_asset_path(path_text)
    if not path or not path.exists():
        label.configure(image="", text="No icon")
        return
    try:
        image = Image.open(path).convert("RGBA")
        image.thumbnail((96, 96), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image.copy(), master=app)
        app.data_images[cache_key] = photo
        label.configure(image=photo, text="")
    except Exception:
        label.configure(image="", text="Icon error")


def resolve_asset_path(path_text: str) -> Path | None:
    if not path_text:
        return None
    path = Path(path_text)
    if path.is_absolute():
        return path
    candidates = [ROOT / path, DATA_DIR / path, DATA_DIR / path.name]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return ROOT / path

