from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QComboBox, QScrollArea, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from tft_companion.views.constants import DATA_DIR, ROOT

if TYPE_CHECKING:
    from tft_companion.views.main_window import TFTCompanionWindow


class DataBrowserTab(QWidget):
    def __init__(self, main_window: TFTCompanionWindow, title: str, rows: dict[str, dict[str, str]], formatter: Callable, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        self.title_text = title
        self.rows = rows
        self.formatter = formatter
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        
        # List Card
        list_card = QWidget()
        list_card.setObjectName("card")
        list_card.setFixedWidth(330)
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(18, 16, 18, 16)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("title")
        list_layout.addWidget(title_lbl)
        
        subtitle = QLabel(f"{len(rows)} records loaded from INI")
        subtitle.setObjectName("subtitle")
        list_layout.addWidget(subtitle)
        list_layout.addSpacing(12)
        
        self.display_to_key = self._display_map()
        displays = list(self.display_to_key.keys())
        
        self.combo = QComboBox()
        self.combo.addItems(displays)
        self.combo.setMinimumHeight(38)
        self.combo.currentTextChanged.connect(self.show_selected)
        list_layout.addWidget(self.combo)
        list_layout.addSpacing(14)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(2)
        
        for display in displays[:180]:
            btn = QPushButton(display)
            btn.setStyleSheet("text-align: left; padding: 8px; background-color: #0B1220; border-radius: 8px;")
            btn.clicked.connect(lambda _, value=display: self._on_list_clicked(value))
            self.scroll_layout.addWidget(btn)
            
        if len(displays) > 180:
            lbl = QLabel("Use the dropdown above for the remaining records.")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #94A3B8; margin-top: 8px;")
            self.scroll_layout.addWidget(lbl)
            
        self.scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        list_layout.addWidget(scroll)
        
        layout.addWidget(list_card)
        
        # Detail Card
        detail_card = QWidget()
        detail_card.setObjectName("card")
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(18, 16, 18, 16)
        
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 8)
        
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(96, 96)
        self.icon_label.setStyleSheet("background-color: #111827; border-radius: 12px;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icon_label)
        
        self.detail_title = QLabel("Select a record")
        self.detail_title.setObjectName("title")
        self.detail_title.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(self.detail_title, stretch=1)
        
        detail_layout.addWidget(header)
        
        self.detail_box = QTextEdit()
        self.detail_box.setReadOnly(True)
        font = self.detail_box.font()
        font.setPointSize(12)
        self.detail_box.setFont(font)
        detail_layout.addWidget(self.detail_box)
        
        layout.addWidget(detail_card)
        
        if displays:
            self.show_selected(displays[0])
        else:
            self.detail_box.setPlainText(f"No {title.lower()} data found. Generate INI files first.")

    def _display_map(self) -> dict[str, str]:
        pairs: list[tuple[str, str]] = []
        for key, row in self.rows.items():
            name = row.get("name") or key
            cost = row.get("cost")
            prefix = f"{cost}g " if cost else ""
            label = f"{prefix}{name} [{key}]"
            pairs.append((label, key))
        pairs.sort(key=lambda pair: pair[0].lower())
        return dict(pairs)

    def _on_list_clicked(self, display: str) -> None:
        self.combo.setCurrentText(display)

    def show_selected(self, display: str) -> None:
        key = self.display_to_key.get(display)
        row = self.rows.get(key or "", {})
        self.detail_title.setText(row.get("name") or key or "Unknown")
        self.detail_box.setPlainText(self.formatter(key or "", row))
        self._set_data_icon(row)

    def _set_data_icon(self, row: dict[str, str]) -> None:
        path_text = row.get("local_icon") or row.get("ability_local_icon") or ""
        path = resolve_asset_path(path_text)
        if not path or not path.exists():
            self.icon_label.setText("No icon")
            self.icon_label.setPixmap(QPixmap())
            return
        
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            scaled = pixmap.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(scaled)
        else:
            self.icon_label.setText("Icon error")


# Formatters and Helpers (Unchanged Logic, purely text formatting)
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
