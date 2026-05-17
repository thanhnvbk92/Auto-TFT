from __future__ import annotations

import customtkinter as ctk

from tft_companion.views.widgets import action_button, field_grid, single_field


def build_advisor_tab(app: ctk.CTk, parent: ctk.CTkFrame) -> None:
    parent.grid_columnconfigure(0, weight=0)
    parent.grid_columnconfigure(1, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    state_card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16, width=360)
    state_card.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)
    state_card.grid_propagate(False)
    ctk.CTkLabel(
        state_card,
        text="Game State",
        font=ctk.CTkFont(size=20, weight="bold"),
        anchor="w",
    ).pack(fill="x", padx=18, pady=(16, 8))

    inner = ctk.CTkFrame(state_card, fg_color="transparent")
    inner.pack(fill="x", padx=16, pady=(0, 16))
    field_grid(inner, app.fields, [("Stage", "stage"), ("Level", "level"), ("Gold", "gold")])
    field_grid(inner, app.fields, [("HP", "hp"), ("Streak", "streak"), ("Pairs", "pairs")])
    single_field(inner, "Missing core units", app.fields["missing_core_units"])

    ctk.CTkLabel(inner, text="Board strength", text_color="#CBD5E1", anchor="w").pack(
        fill="x", pady=(12, 5)
    )
    ctk.CTkSegmentedButton(
        inner,
        values=["weak", "even", "strong"],
        variable=app.fields["board_strength"],
        height=34,
    ).pack(fill="x")

    flags = ctk.CTkFrame(inner, fg_color="transparent")
    flags.pack(fill="x", pady=(14, 4))
    flags.grid_columnconfigure((0, 1), weight=1)
    ctk.CTkCheckBox(flags, text="Bench full", variable=app.fields["bench_full"]).grid(
        row=0, column=0, sticky="w", padx=(0, 8)
    )
    ctk.CTkCheckBox(flags, text="Contested", variable=app.fields["contested"]).grid(
        row=0, column=1, sticky="w"
    )
    single_field(inner, "Target comp", app.fields["target_comp"])
    action_button(
        inner,
        "Update advice",
        app._update_advice,
        fg="#059669",
        hover="#047857",
        height=42,
    )

    advice_card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
    advice_card.grid(row=0, column=1, sticky="nsew", padx=(8, 12), pady=12)
    advice_card.grid_columnconfigure(0, weight=1)
    advice_card.grid_rowconfigure(1, weight=1)
    ctk.CTkLabel(
        advice_card,
        text="Decision Advice",
        font=ctk.CTkFont(size=20, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
    app.advice = ctk.CTkTextbox(
        advice_card,
        wrap="word",
        font=ctk.CTkFont(family="Segoe UI", size=16),
        fg_color="#0B1220",
        border_width=0,
        corner_radius=14,
    )
    app.advice.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
    app.advice.configure(state="disabled")

