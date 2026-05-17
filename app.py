from __future__ import annotations

import tkinter as tk
from pathlib import Path
from time import perf_counter
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from tft_companion.decision_engine import GameState, build_advice
from tft_companion.screen_reader import (
    list_android_devices,
    list_visible_window_titles,
    read_android_screen,
    read_screen,
    read_scrcpy_window,
    start_scrcpy_mirror,
)


ROOT = Path(__file__).resolve().parent


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TFTCompanionApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TFT Decision Companion")
        self.geometry("1360x860")
        self.minsize(1060, 720)

        self.fields: dict[str, tk.Variable] = {
            "stage": tk.StringVar(value="2-1"),
            "level": tk.IntVar(value=4),
            "gold": tk.IntVar(value=0),
            "hp": tk.IntVar(value=100),
            "streak": tk.IntVar(value=0),
            "pairs": tk.IntVar(value=0),
            "missing_core_units": tk.IntVar(value=0),
            "board_strength": tk.StringVar(value="even"),
            "bench_full": tk.BooleanVar(value=False),
            "contested": tk.BooleanVar(value=False),
            "target_comp": tk.StringVar(value=""),
        }
        self.android_device = tk.StringVar(value="")
        self.read_status = tk.StringVar(value="Ready")
        self.ocr_text = tk.StringVar(value="No screen has been captured yet.")
        self.image_path = tk.StringVar(value="")
        self.capture_time = tk.StringVar(value="Read time: -")
        self.preview_image: ImageTk.PhotoImage | None = None

        self._build_ui()
        self._update_advice()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=340, corner_radius=0, fg_color="#111827")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(22, 10))
        ctk.CTkLabel(
            header,
            text="TFT Companion",
            font=ctk.CTkFont(size=24, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            header,
            text="Read the board. Make the call.",
            text_color="#9CA3AF",
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        controls = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        controls.grid_columnconfigure(0, weight=1)

        self._section_label(controls, "Game State").pack(fill="x", pady=(4, 8))
        self._field_grid(controls, [("Stage", "stage"), ("Level", "level"), ("Gold", "gold")])
        self._field_grid(controls, [("HP", "hp"), ("Streak", "streak"), ("Pairs", "pairs")])
        self._single_field(controls, "Missing core units", "missing_core_units")

        ctk.CTkLabel(controls, text="Board strength", text_color="#D1D5DB", anchor="w").pack(
            fill="x", pady=(10, 4)
        )
        ctk.CTkSegmentedButton(
            controls,
            values=["weak", "even", "strong"],
            variable=self.fields["board_strength"],
        ).pack(fill="x")

        flags = ctk.CTkFrame(controls, fg_color="transparent")
        flags.pack(fill="x", pady=(12, 4))
        flags.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkCheckBox(flags, text="Bench full", variable=self.fields["bench_full"]).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ctk.CTkCheckBox(flags, text="Contested", variable=self.fields["contested"]).grid(
            row=0, column=1, sticky="w"
        )

        self._single_field(controls, "Target comp", "target_comp")

        self._section_label(controls, "Capture").pack(fill="x", pady=(20, 8))
        self._action_button(
            controls, "Read scrcpy window", self._capture_scrcpy, fg="#2563EB", hover="#1D4ED8"
        )
        self._action_button(
            controls, "Start scrcpy mirror", self._start_scrcpy, fg="#334155", hover="#475569"
        )
        self._action_button(
            controls, "Read Android via ADB", self._capture_android, fg="#374151", hover="#4B5563"
        )
        self._action_button(
            controls, "Capture PC screen", self._capture_pc, fg="#374151", hover="#4B5563"
        )
        self._action_button(
            controls, "Find Android devices", self._refresh_android_devices, fg="#1F2937", hover="#374151"
        )

        self._single_custom_field(controls, "Android device id", self.android_device)
        ctk.CTkLabel(
            controls,
            text="Leave blank when only one ADB device is connected.",
            text_color="#9CA3AF",
            wraplength=280,
            justify="left",
        ).pack(fill="x", pady=(4, 8))

        self._action_button(
            controls, "Update advice", self._update_advice, fg="#059669", hover="#047857"
        )

        footer = ctk.CTkFrame(sidebar, fg_color="#0B1220", corner_radius=12)
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        ctk.CTkLabel(
            footer,
            textvariable=self.read_status,
            text_color="#CBD5E1",
            anchor="w",
            wraplength=280,
        ).pack(fill="x", padx=14, pady=12)

        main = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        main.grid_rowconfigure(2, weight=0)

        topbar = ctk.CTkFrame(main, fg_color="transparent")
        topbar.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 14))
        topbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            topbar,
            text="Decision Advice",
            font=ctk.CTkFont(size=26, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            topbar,
            textvariable=self.capture_time,
            text_color="#93C5FD",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=1, sticky="e")

        advice_card = ctk.CTkFrame(main, fg_color="#111827", corner_radius=16)
        advice_card.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 14))
        advice_card.grid_columnconfigure(0, weight=1)
        advice_card.grid_rowconfigure(0, weight=1)
        self.advice = ctk.CTkTextbox(
            advice_card,
            wrap="word",
            font=ctk.CTkFont(family="Segoe UI", size=15),
            fg_color="#111827",
            border_width=0,
            corner_radius=14,
        )
        self.advice.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        self.advice.configure(state="disabled")

        result_card = ctk.CTkFrame(main, fg_color="#111827", corner_radius=16)
        result_card.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 24))
        result_card.grid_columnconfigure(0, weight=3)
        result_card.grid_columnconfigure(1, weight=2)

        preview_wrap = ctk.CTkFrame(result_card, fg_color="#020617", corner_radius=12)
        preview_wrap.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        preview_wrap.grid_columnconfigure(0, weight=1)
        self.preview_label = tk.Label(
            preview_wrap,
            text="No image preview yet",
            fg="#64748B",
            bg="#020617",
            anchor="center",
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        readout = ctk.CTkFrame(result_card, fg_color="transparent")
        readout.grid(row=0, column=1, sticky="nsew", padx=(0, 14), pady=14)
        readout.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            readout,
            text="Screen Read",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            readout,
            textvariable=self.ocr_text,
            text_color="#D1D5DB",
            justify="left",
            anchor="nw",
            wraplength=420,
        ).grid(row=1, column=0, sticky="nsew", pady=(8, 10))
        ctk.CTkLabel(
            readout,
            textvariable=self.image_path,
            text_color="#64748B",
            anchor="w",
            wraplength=420,
        ).grid(row=2, column=0, sticky="ew")

    def _section_label(self, parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent,
            text=text.upper(),
            text_color="#60A5FA",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )

    def _field_grid(self, parent: ctk.CTkFrame, fields: list[tuple[str, str]]) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 8))
        frame.grid_columnconfigure(tuple(range(len(fields))), weight=1)
        for col, (label, key) in enumerate(fields):
            cell = ctk.CTkFrame(frame, fg_color="transparent")
            cell.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
            ctk.CTkLabel(cell, text=label, text_color="#D1D5DB", anchor="w").pack(fill="x")
            ctk.CTkEntry(cell, textvariable=self.fields[key], height=34).pack(fill="x", pady=(3, 0))

    def _single_field(self, parent: ctk.CTkFrame, label: str, key: str) -> None:
        self._single_custom_field(parent, label, self.fields[key])

    def _single_custom_field(self, parent: ctk.CTkFrame, label: str, variable: tk.Variable) -> None:
        ctk.CTkLabel(parent, text=label, text_color="#D1D5DB", anchor="w").pack(
            fill="x", pady=(10, 4)
        )
        ctk.CTkEntry(parent, textvariable=variable, height=36).pack(fill="x")

    def _action_button(
        self,
        parent: ctk.CTkFrame,
        text: str,
        command,
        *,
        fg: str,
        hover: str,
    ) -> None:
        ctk.CTkButton(
            parent,
            text=text,
            command=command,
            height=38,
            corner_radius=10,
            fg_color=fg,
            hover_color=hover,
        ).pack(fill="x", pady=4)

    def _capture_pc(self) -> None:
        self._read_status("Capturing PC screen...")
        start = perf_counter()
        result = read_screen(ROOT / "screenshots")
        self._apply_screen_result(result, elapsed=perf_counter() - start)

    def _capture_android(self) -> None:
        self._read_status("Reading Android through ADB...")
        start = perf_counter()
        result = read_android_screen(ROOT / "screenshots", device_id=self.android_device.get())
        self._apply_screen_result(result, elapsed=perf_counter() - start)

    def _start_scrcpy(self) -> None:
        try:
            start_scrcpy_mirror(device_id=self.android_device.get())
            self._read_status("scrcpy mirror started in no-control mode.")
            messagebox.showinfo(
                "scrcpy",
                "Started scrcpy mirror in no-control mode. Wait for the mirror window, then click Read scrcpy window.",
            )
        except Exception as exc:
            self._read_status("scrcpy failed.")
            titles = "\n".join(list_visible_window_titles()[:20])
            messagebox.showerror("scrcpy error", f"{exc}\n\nVisible windows:\n{titles}")

    def _capture_scrcpy(self) -> None:
        self._read_status("Reading scrcpy window...")
        start = perf_counter()
        result = read_scrcpy_window(ROOT / "screenshots")
        self._apply_screen_result(result, elapsed=perf_counter() - start)

    def _apply_screen_result(self, result, elapsed: float) -> None:
        self.image_path.set(str(result.image_path))
        self.capture_time.set(f"Read time: {elapsed:.2f}s")
        self._show_image_preview(result.image_path)

        for key, value in result.fields.items():
            if key in self.fields:
                self.fields[key].set(value)

        if result.ocr_available:
            preview = result.raw_text.strip()[:700] or "OCR ran, but no clear text was detected."
            self.ocr_text.set(f"{result.source.upper()} result\n{preview}")
            self._read_status(f"Read complete from {result.source.upper()} in {elapsed:.2f}s.")
        else:
            self.ocr_text.set(
                f"{result.source.upper()} screenshot was not readable.\n{result.error}"
            )
            self._read_status(f"Read failed from {result.source.upper()}.")
            if result.error:
                messagebox.showinfo("Screen read issue", result.error)

        self._update_advice()

    def _show_image_preview(self, image_path: Path) -> None:
        if not image_path.exists():
            self.preview_image = None
            self.preview_label.configure(image="", text="No screenshot file found")
            return

        try:
            image = Image.open(image_path).convert("RGB")
            image.thumbnail((520, 250), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(image.copy(), master=self)
            self.preview_label.configure(image=self.preview_image, text="")
        except Exception as exc:
            self.preview_image = None
            self.preview_label.configure(image="", text=f"Could not load preview: {exc}")

    def _refresh_android_devices(self) -> None:
        devices = list_android_devices()
        if not devices:
            self._read_status("No authorized Android device found.")
            messagebox.showinfo(
                "No Android device",
                "No authorized Android device was found through ADB. "
                "Check platform-tools, USB debugging, and the authorization prompt on the phone.",
            )
            return

        self.android_device.set(devices[0])
        self._read_status(f"Android device selected: {devices[0]}")
        messagebox.showinfo("Android devices", "\n".join(devices))

    def _update_advice(self) -> None:
        try:
            state = GameState(
                stage=str(self.fields["stage"].get()),
                level=int(self.fields["level"].get()),
                gold=int(self.fields["gold"].get()),
                hp=int(self.fields["hp"].get()),
                streak=int(self.fields["streak"].get()),
                pairs=int(self.fields["pairs"].get()),
                missing_core_units=int(self.fields["missing_core_units"].get()),
                board_strength=str(self.fields["board_strength"].get()),  # type: ignore[arg-type]
                bench_full=bool(self.fields["bench_full"].get()),
                contested=bool(self.fields["contested"].get()),
                target_comp=str(self.fields["target_comp"].get()).strip(),
            )
        except (TypeError, ValueError):
            messagebox.showerror("Invalid data", "Check numeric fields before updating advice.")
            return

        advice = build_advice(state)
        content = "\n\n".join(
            [
                advice.headline,
                f"Economy: {advice.economy}",
                f"Roll/Level: {advice.roll_level}",
                f"Shop: {advice.shop}",
                f"Item: {advice.items}",
                f"Positioning: {advice.positioning}",
                f"Risk: {advice.risk}",
            ]
        )

        self.advice.configure(state="normal")
        self.advice.delete("1.0", "end")
        self.advice.insert("1.0", content)
        self.advice.configure(state="disabled")

    def _read_status(self, text: str) -> None:
        self.read_status.set(text)
        self.update_idletasks()


def main() -> None:
    app = TFTCompanionApp()
    app.mainloop()


if __name__ == "__main__":
    main()
