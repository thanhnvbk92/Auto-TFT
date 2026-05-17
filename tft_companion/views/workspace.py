from __future__ import annotations

import customtkinter as ctk

from tft_companion.views.advisor_tab import build_advisor_tab
from tft_companion.views.data_browser import (
    build_data_browser,
    format_champion,
    format_item,
    format_trait,
)
from tft_companion.views.screen_tab import build_screen_tab
from tft_companion.views.widgets import metric_card


def build_workspace(app: ctk.CTk) -> None:
    workspace = ctk.CTkFrame(app, corner_radius=0, fg_color="#07111F")
    workspace.grid(row=0, column=1, sticky="nsew")
    workspace.grid_columnconfigure(0, weight=1)
    workspace.grid_rowconfigure(2, weight=1)

    topbar = ctk.CTkFrame(workspace, fg_color="transparent")
    topbar.grid(row=0, column=0, sticky="ew", padx=26, pady=(24, 14))
    topbar.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(
        topbar,
        text="Live Coach Dashboard",
        font=ctk.CTkFont(size=30, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(
        topbar,
        textvariable=app.capture_time,
        text_color="#93C5FD",
        font=ctk.CTkFont(size=14, weight="bold"),
    ).grid(row=0, column=1, sticky="e")

    metrics = ctk.CTkFrame(workspace, fg_color="transparent")
    metrics.grid(row=1, column=0, sticky="ew", padx=26, pady=(0, 16))
    metrics.grid_columnconfigure((0, 1, 2, 3), weight=1)
    metric_card(metrics, "Capture", app.capture_metric, 0)
    metric_card(metrics, "OCR / Recognition", app.ocr_metric, 1)
    metric_card(metrics, "Total", app.total_metric, 2)
    metric_card(metrics, "Data", app.data_summary, 3, small=True)

    app.tabs = ctk.CTkTabview(
        workspace,
        fg_color="#0B1220",
        segmented_button_fg_color="#111827",
    )
    app.tabs.grid(row=2, column=0, sticky="nsew", padx=26, pady=(0, 24))
    advisor_tab = app.tabs.add("Advisor")
    screen_tab = app.tabs.add("Screen")
    champions_tab = app.tabs.add("Champions")
    items_tab = app.tabs.add("Items")
    traits_tab = app.tabs.add("Traits")

    build_advisor_tab(app, advisor_tab)
    build_screen_tab(app, screen_tab)
    build_data_browser(app, champions_tab, "Champions", app.champion_rows(), format_champion)
    build_data_browser(app, items_tab, "Items", app.item_rows(), format_item)
    build_data_browser(app, traits_tab, "Traits", app.trait_rows(), format_trait)

