from __future__ import annotations

from typing import Callable
from PyQt6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPushButton, QGridLayout
)
from PyQt6.QtCore import Qt


def metric_card(
    parent: QWidget,
    label: str,
    get_value_callback: Callable[[], str],
    *,
    small: bool = False,
) -> tuple[QFrame, QLabel]:
    """
    Creates a metric card and returns the frame and the value label
    so the parent can update the text when needed.
    """
    card = QFrame(parent)
    card.setObjectName("card")
    
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 12, 16, 14)
    layout.setSpacing(4)
    
    title_label = QLabel(label.upper())
    title_label.setObjectName("metricLabel")
    layout.addWidget(title_label)
    
    value_label = QLabel(get_value_callback())
    value_label.setObjectName("metricValue")
    value_label.setWordWrap(True)
    if small:
        font = value_label.font()
        font.setPointSize(14)
        value_label.setFont(font)
    layout.addWidget(value_label)
    
    return card, value_label


def field_grid(
    parent: QWidget,
    input_widgets: dict[str, QWidget],
    fields: list[tuple[str, str]],
) -> QWidget:
    """
    Creates a grid of input fields.
    Updates `input_widgets` dict with the created QLineEdit mapped to `key`.
    """
    frame = QWidget(parent)
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 8)
    layout.setSpacing(12)
    
    for label, key in fields:
        cell = QWidget()
        cell_layout = QVBoxLayout(cell)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.setSpacing(4)
        
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #CBD5E1;")
        cell_layout.addWidget(lbl)
        
        entry = QLineEdit()
        entry.setMinimumHeight(34)
        cell_layout.addWidget(entry)
        input_widgets[key] = entry
        
        layout.addWidget(cell)
        
    return frame


def single_field(parent: QWidget, label: str, input_widgets: dict[str, QWidget], key: str) -> QWidget:
    """
    Creates a single input field.
    """
    frame = QWidget(parent)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 10, 0, 4)
    layout.setSpacing(4)
    
    lbl = QLabel(label)
    lbl.setStyleSheet("color: #CBD5E1;")
    layout.addWidget(lbl)
    
    entry = QLineEdit()
    entry.setMinimumHeight(36)
    layout.addWidget(entry)
    input_widgets[key] = entry
    
    return frame


def action_button(
    parent: QWidget,
    text: str,
    command: Callable[[], None],
    *,
    is_primary: bool = False,
    height: int = 38,
) -> QPushButton:
    btn = QPushButton(text, parent)
    btn.setMinimumHeight(height)
    if is_primary:
        btn.setObjectName("primaryAction")
    btn.clicked.connect(command)
    return btn
