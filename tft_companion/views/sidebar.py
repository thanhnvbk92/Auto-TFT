from __future__ import annotations

import customtkinter as ctk


def build_sidebar(app: ctk.CTk) -> None:
    sidebar = ctk.CTkFrame(app, width=260, corner_radius=0, fg_color="#0B1220")
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)
    sidebar.grid_columnconfigure(0, weight=1)
    sidebar.grid_rowconfigure(1, weight=1)

    brand = ctk.CTkFrame(sidebar, fg_color="transparent")
    brand.grid(row=0, column=0, sticky="ew", padx=22, pady=(24, 18))
    ctk.CTkLabel(
        brand,
        text="TFT Companion",
        font=ctk.CTkFont(size=25, weight="bold"),
        anchor="w",
    ).pack(fill="x")
    ctk.CTkLabel(
        brand,
        text="Decision support",
        text_color="#94A3B8",
        font=ctk.CTkFont(size=13),
        anchor="w",
    ).pack(fill="x", pady=(4, 0))

    nav = ctk.CTkFrame(sidebar, fg_color="transparent")
    nav.grid(row=1, column=0, sticky="new", padx=14, pady=(0, 18))
    for label in ("Advisor", "Screen", "Champions", "Items", "Traits"):
        ctk.CTkButton(
            nav,
            text=label,
            command=lambda tab=label: app.tabs.set(tab),
            height=42,
            corner_radius=10,
            anchor="w",
            fg_color="#111827",
            hover_color="#1E293B",
            text_color="#E2E8F0",
        ).pack(fill="x", pady=5)

    footer = ctk.CTkFrame(sidebar, fg_color="#020617", corner_radius=14)
    footer.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 18))
    ctk.CTkLabel(
        footer,
        text="STATUS",
        text_color="#60A5FA",
        font=ctk.CTkFont(size=12, weight="bold"),
        anchor="w",
    ).pack(fill="x", padx=14, pady=(12, 0))
    ctk.CTkLabel(
        footer,
        textvariable=app.read_status,
        text_color="#E2E8F0",
        anchor="w",
        justify="left",
        wraplength=205,
    ).pack(fill="x", padx=14, pady=(4, 14))

