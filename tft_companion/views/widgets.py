from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk


def metric_card(
    parent: ctk.CTkFrame,
    label: str,
    variable: tk.StringVar,
    column: int,
    *,
    small: bool = False,
) -> None:
    card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
    card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0))
    ctk.CTkLabel(card, text=label.upper(), text_color="#94A3B8", anchor="w").pack(
        fill="x", padx=16, pady=(12, 0)
    )
    ctk.CTkLabel(
        card,
        textvariable=variable,
        text_color="#F8FAFC",
        font=ctk.CTkFont(size=14 if small else 24, weight="bold"),
        anchor="w",
        wraplength=220,
    ).pack(fill="x", padx=16, pady=(3, 14))


def field_grid(
    parent: ctk.CTkFrame,
    variables: dict[str, tk.Variable],
    fields: list[tuple[str, str]],
) -> None:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", pady=(0, 8))
    frame.grid_columnconfigure(tuple(range(len(fields))), weight=1)
    for col, (label, key) in enumerate(fields):
        cell = ctk.CTkFrame(frame, fg_color="transparent")
        cell.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
        ctk.CTkLabel(cell, text=label, text_color="#CBD5E1", anchor="w").pack(fill="x")
        ctk.CTkEntry(cell, textvariable=variables[key], height=34).pack(fill="x", pady=(3, 0))


def single_field(parent: ctk.CTkFrame, label: str, variable: tk.Variable) -> None:
    ctk.CTkLabel(parent, text=label, text_color="#CBD5E1", anchor="w").pack(
        fill="x", pady=(10, 4)
    )
    ctk.CTkEntry(parent, textvariable=variable, height=36).pack(fill="x")


def action_button(
    parent: ctk.CTkFrame,
    text: str,
    command: Callable[[], None],
    *,
    fg: str,
    hover: str,
    height: int = 38,
) -> None:
    ctk.CTkButton(
        parent,
        text=text,
        command=command,
        height=height,
        corner_radius=10,
        fg_color=fg,
        hover_color=hover,
    ).pack(fill="x", pady=4)

