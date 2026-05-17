from __future__ import annotations

from typing import Callable
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QWidget
from PyQt6.QtCore import Qt


class Sidebar(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(260)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(22, 24, 22, 18)
        self.layout.setSpacing(18)
        
        # Brand
        brand_frame = QWidget()
        brand_layout = QVBoxLayout(brand_frame)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(4)
        
        title = QLabel("Trợ lý TFT")
        title.setObjectName("title")
        brand_layout.addWidget(title)
        
        subtitle = QLabel("Hỗ trợ chiến thuật")
        subtitle.setObjectName("subtitle")
        brand_layout.addWidget(subtitle)
        
        self.layout.addWidget(brand_frame)
        
        # Navigation
        self.nav_frame = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_frame)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(8)
        self.layout.addWidget(self.nav_frame)
        
        self.layout.addStretch(1)
        
        # Footer / Status
        self.footer = QFrame()
        self.footer.setStyleSheet("background-color: #020617; border-radius: 14px;")
        footer_layout = QVBoxLayout(self.footer)
        footer_layout.setContentsMargins(14, 12, 14, 14)
        footer_layout.setSpacing(4)
        
        status_label = QLabel("TRẠNG THÁI")
        status_label.setStyleSheet("color: #60A5FA; font-weight: bold; font-size: 12px;")
        footer_layout.addWidget(status_label)
        
        self.status_text = QLabel("Sẵn sàng")
        self.status_text.setWordWrap(True)
        self.status_text.setStyleSheet("color: #E2E8F0;")
        footer_layout.addWidget(self.status_text)
        
        self.layout.addWidget(self.footer)
        
        self.nav_buttons: list[QPushButton] = []

    def add_nav_button(self, label: str, command: Callable[[], None]) -> None:
        btn = QPushButton(label)
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        btn.clicked.connect(lambda _, b=btn: self._on_nav_clicked(b, command))
        self.nav_layout.addWidget(btn)
        self.nav_buttons.append(btn)
        if len(self.nav_buttons) == 1:
            btn.setChecked(True)

    def _on_nav_clicked(self, clicked_btn: QPushButton, command: Callable[[], None]) -> None:
        for btn in self.nav_buttons:
            if btn != clicked_btn:
                btn.setChecked(False)
        clicked_btn.setChecked(True)
        command()

    def set_status(self, text: str) -> None:
        self.status_text.setText(text)
