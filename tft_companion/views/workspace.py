from __future__ import annotations

from typing import TYPE_CHECKING
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget
)

from tft_companion.views.dashboard_tab import DashboardTab
from tft_companion.views.data_browser import DataBrowserTab, format_champion, format_item, format_trait

if TYPE_CHECKING:
    from tft_companion.views.main_window import TFTCompanionWindow


class Workspace(QWidget):
    def __init__(self, main_window: TFTCompanionWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Stacked Widget (Tabs)
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget, stretch=1)
        
        # Initialize Tabs
        self.dashboard_tab = DashboardTab(main_window)
        
        self.stacked_widget.addWidget(self.dashboard_tab)
        
        self.champions_tab = DataBrowserTab(main_window, "Champions", main_window.champion_rows(), format_champion)
        self.items_tab = DataBrowserTab(main_window, "Items", main_window.item_rows(), format_item)
        self.traits_tab = DataBrowserTab(main_window, "Traits", main_window.trait_rows(), format_trait)
        
        self.stacked_widget.addWidget(self.champions_tab)
        self.stacked_widget.addWidget(self.items_tab)
        self.stacked_widget.addWidget(self.traits_tab)

    def set_tab(self, index: int) -> None:
        self.stacked_widget.setCurrentIndex(index)
