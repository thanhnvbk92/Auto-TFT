from __future__ import annotations

import tkinter as tk

import customtkinter as ctk


def build_screen_tab(app: ctk.CTk, parent: ctk.CTkFrame) -> None:
    parent.grid_columnconfigure(0, weight=3)
    parent.grid_columnconfigure(1, weight=2)
    parent.grid_rowconfigure(1, weight=1)

    capture_card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
    capture_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 8))
    capture_card.grid_columnconfigure(5, weight=1)
    actions = [
        ("Read scrcpy window", app._capture_scrcpy, "#2563EB", "#1D4ED8"),
        ("Start scrcpy mirror", app._start_scrcpy, "#334155", "#475569"),
        ("Read Android via ADB", app._capture_android, "#1F2937", "#374151"),
        ("Capture PC screen", app._capture_pc, "#1F2937", "#374151"),
        ("Find Android devices", app._refresh_android_devices, "#111827", "#1F2937"),
    ]
    for col, (text, command, fg, hover) in enumerate(actions):
        ctk.CTkButton(
            capture_card,
            text=text,
            command=command,
            height=38,
            corner_radius=10,
            fg_color=fg,
            hover_color=hover,
        ).grid(row=0, column=col, sticky="ew", padx=(14 if col == 0 else 6, 0), pady=14)
    ctk.CTkEntry(
        capture_card,
        textvariable=app.android_device,
        height=38,
        placeholder_text="Android device id",
    ).grid(row=0, column=5, sticky="ew", padx=14, pady=14)

    preview_card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
    preview_card.grid(row=1, column=0, sticky="nsew", padx=(12, 8), pady=(8, 12))
    preview_card.grid_columnconfigure(0, weight=1)
    preview_card.grid_rowconfigure(1, weight=1)
    ctk.CTkLabel(
        preview_card,
        text="Screen Preview",
        font=ctk.CTkFont(size=20, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))
    preview_wrap = ctk.CTkFrame(preview_card, fg_color="#020617", corner_radius=14)
    preview_wrap.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
    preview_wrap.grid_columnconfigure(0, weight=1)
    preview_wrap.grid_rowconfigure(0, weight=1)
    app.preview_label = tk.Label(
        preview_wrap,
        text="No image preview yet",
        fg="#64748B",
        bg="#020617",
        anchor="center",
    )
    app.preview_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    read_card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
    read_card.grid(row=1, column=1, sticky="nsew", padx=(8, 12), pady=(8, 12))
    read_card.grid_columnconfigure(0, weight=1)
    read_card.grid_rowconfigure(1, weight=1)
    ctk.CTkLabel(
        read_card,
        text="Screen Read",
        font=ctk.CTkFont(size=20, weight="bold"),
        anchor="w",
    ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))
    app.readout_box = ctk.CTkTextbox(
        read_card,
        wrap="word",
        font=ctk.CTkFont(family="Consolas", size=13),
        fg_color="#0B1220",
        corner_radius=14,
    )
    app.readout_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
    app.readout_box.insert("1.0", app.ocr_text.get())
    app.readout_box.configure(state="disabled")
    ctk.CTkLabel(
        read_card,
        textvariable=app.image_path,
        text_color="#64748B",
        anchor="w",
        wraplength=420,
    ).grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))

