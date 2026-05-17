from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from tft_companion.models.game import Advice, GameState
from tft_companion.models.screen import ScreenReadResult
from tft_companion.presenters.main_presenter import MainPresenter
from tft_companion.services.data_service import load_tft_static_data


ROOT = Path(__file__).resolve().parents[2]


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TFTCompanionApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TFT Decision Companion")
        self.geometry("1480x900")
        self.minsize(1180, 760)
        self.configure(fg_color="#07111F")

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
        self.capture_time = tk.StringVar(value="Capture: - | OCR: - | Total: -")
        self.capture_metric = tk.StringVar(value="-")
        self.ocr_metric = tk.StringVar(value="-")
        self.total_metric = tk.StringVar(value="-")
        self.data_summary = tk.StringVar(value=self._build_data_summary())
        self.preview_image: ImageTk.PhotoImage | None = None
        self.presenter = MainPresenter(self, ROOT)

        self._build_ui()
        self.presenter.update_advice()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_workspace()

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=360, corner_radius=0, fg_color="#0B1220")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(1, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=22, pady=(24, 14))
        ctk.CTkLabel(
            brand,
            text="TFT Companion",
            font=ctk.CTkFont(size=28, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            brand,
            text="Decision support, not autopilot.",
            text_color="#94A3B8",
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        controls = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

        state_card = self._side_card(controls, "Game State")
        self._field_grid(state_card, [("Stage", "stage"), ("Level", "level"), ("Gold", "gold")])
        self._field_grid(state_card, [("HP", "hp"), ("Streak", "streak"), ("Pairs", "pairs")])
        self._single_field(state_card, "Missing core units", "missing_core_units")

        ctk.CTkLabel(state_card, text="Board strength", text_color="#CBD5E1", anchor="w").pack(
            fill="x", pady=(12, 5)
        )
        ctk.CTkSegmentedButton(
            state_card,
            values=["weak", "even", "strong"],
            variable=self.fields["board_strength"],
            height=34,
        ).pack(fill="x")

        flags = ctk.CTkFrame(state_card, fg_color="transparent")
        flags.pack(fill="x", pady=(14, 4))
        flags.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkCheckBox(flags, text="Bench full", variable=self.fields["bench_full"]).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ctk.CTkCheckBox(flags, text="Contested", variable=self.fields["contested"]).grid(
            row=0, column=1, sticky="w"
        )
        self._single_field(state_card, "Target comp", "target_comp")

        capture_card = self._side_card(controls, "Capture")
        self._button(
            capture_card,
            "Read scrcpy window",
            self._capture_scrcpy,
            fg="#2563EB",
            hover="#1D4ED8",
            height=42,
        )
        self._button(
            capture_card,
            "Start scrcpy mirror",
            self._start_scrcpy,
            fg="#334155",
            hover="#475569",
        )
        self._button(
            capture_card,
            "Read Android via ADB",
            self._capture_android,
            fg="#1F2937",
            hover="#374151",
        )
        self._button(
            capture_card,
            "Capture PC screen",
            self._capture_pc,
            fg="#1F2937",
            hover="#374151",
        )
        self._button(
            capture_card,
            "Find Android devices",
            self._refresh_android_devices,
            fg="#111827",
            hover="#1F2937",
        )
        self._single_custom_field(capture_card, "Android device id", self.android_device)
        ctk.CTkLabel(
            capture_card,
            text="Leave blank when only one ADB device is connected.",
            text_color="#94A3B8",
            wraplength=280,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(4, 8))
        self._button(capture_card, "Update advice", self._update_advice, fg="#059669", hover="#047857")

        footer = ctk.CTkFrame(sidebar, fg_color="#020617", corner_radius=14)
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        ctk.CTkLabel(
            footer,
            text="Status",
            text_color="#60A5FA",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(
            footer,
            textvariable=self.read_status,
            text_color="#E2E8F0",
            anchor="w",
            justify="left",
            wraplength=290,
        ).pack(fill="x", padx=14, pady=(4, 14))

    def _build_workspace(self) -> None:
        workspace = ctk.CTkFrame(self, corner_radius=0, fg_color="#07111F")
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
            textvariable=self.capture_time,
            text_color="#93C5FD",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=1, sticky="e")

        metrics = ctk.CTkFrame(workspace, fg_color="transparent")
        metrics.grid(row=1, column=0, sticky="ew", padx=26, pady=(0, 16))
        metrics.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self._metric_card(metrics, "Capture", self.capture_metric, 0)
        self._metric_card(metrics, "OCR / Recognition", self.ocr_metric, 1)
        self._metric_card(metrics, "Total", self.total_metric, 2)
        self._metric_card(metrics, "Data", self.data_summary, 3, small=True)

        tabs = ctk.CTkTabview(workspace, fg_color="#0B1220", segmented_button_fg_color="#111827")
        tabs.grid(row=2, column=0, sticky="nsew", padx=26, pady=(0, 24))
        advisor_tab = tabs.add("Advisor")
        screen_tab = tabs.add("Screen")
        data_tab = tabs.add("Data")
        for tab in (advisor_tab, screen_tab, data_tab):
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)

        self._build_advisor_tab(advisor_tab)
        self._build_screen_tab(screen_tab)
        self._build_data_tab(data_tab)

    def _build_advisor_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
        card.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            card,
            text="Decision Advice",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        self.advice = ctk.CTkTextbox(
            card,
            wrap="word",
            font=ctk.CTkFont(family="Segoe UI", size=16),
            fg_color="#0B1220",
            border_width=0,
            corner_radius=14,
        )
        self.advice.grid(row=1, column=0, sticky="nsew", padx=16, pady=16)
        self.advice.configure(state="disabled")

    def _build_screen_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=3)
        parent.grid_columnconfigure(1, weight=2)
        parent.grid_rowconfigure(0, weight=1)

        preview_card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
        preview_card.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)
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
        self.preview_label = tk.Label(
            preview_wrap,
            text="No image preview yet",
            fg="#64748B",
            bg="#020617",
            anchor="center",
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        read_card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
        read_card.grid(row=0, column=1, sticky="nsew", padx=(8, 12), pady=12)
        read_card.grid_columnconfigure(0, weight=1)
        read_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            read_card,
            text="Screen Read",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))
        self.readout_box = ctk.CTkTextbox(
            read_card,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#0B1220",
            corner_radius=14,
        )
        self.readout_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.readout_box.insert("1.0", self.ocr_text.get())
        self.readout_box.configure(state="disabled")
        ctk.CTkLabel(
            read_card,
            textvariable=self.image_path,
            text_color="#64748B",
            anchor="w",
            wraplength=420,
        ).grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))

    def _build_data_tab(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
        card.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        ctk.CTkLabel(
            card,
            text="Static Data",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(
            card,
            textvariable=self.data_summary,
            text_color="#E2E8F0",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 12))
        ctk.CTkLabel(
            card,
            text=(
                "Generated data lives in data/generated/set17. "
                "Champion, ability, trait, and item images are cached under assets/."
            ),
            text_color="#94A3B8",
            justify="left",
            wraplength=760,
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 16))

    def _side_card(self, parent: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=16)
        card.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(
            card,
            text=title.upper(),
            text_color="#60A5FA",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(14, 8))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=(0, 14))
        return inner

    def _metric_card(
        self,
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

    def _field_grid(self, parent: ctk.CTkFrame, fields: list[tuple[str, str]]) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(0, 8))
        frame.grid_columnconfigure(tuple(range(len(fields))), weight=1)
        for col, (label, key) in enumerate(fields):
            cell = ctk.CTkFrame(frame, fg_color="transparent")
            cell.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
            ctk.CTkLabel(cell, text=label, text_color="#CBD5E1", anchor="w").pack(fill="x")
            ctk.CTkEntry(cell, textvariable=self.fields[key], height=34).pack(fill="x", pady=(3, 0))

    def _single_field(self, parent: ctk.CTkFrame, label: str, key: str) -> None:
        self._single_custom_field(parent, label, self.fields[key])

    def _single_custom_field(self, parent: ctk.CTkFrame, label: str, variable: tk.Variable) -> None:
        ctk.CTkLabel(parent, text=label, text_color="#CBD5E1", anchor="w").pack(
            fill="x", pady=(10, 4)
        )
        ctk.CTkEntry(parent, textvariable=variable, height=36).pack(fill="x")

    def _button(
        self,
        parent: ctk.CTkFrame,
        text: str,
        command,
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

    def _capture_pc(self) -> None:
        self.presenter.read_pc_screen()

    def _capture_android(self) -> None:
        self.presenter.read_android_screen(device_id=self.android_device.get())

    def _start_scrcpy(self) -> None:
        try:
            self.presenter.start_scrcpy_mirror(device_id=self.android_device.get())
            messagebox.showinfo(
                "scrcpy",
                "Started scrcpy mirror in no-control mode. Wait for the mirror window, then click Read scrcpy window.",
            )
        except Exception as exc:
            self.show_status("scrcpy failed.")
            titles = "\n".join(self.presenter.visible_window_titles()[:20])
            messagebox.showerror("scrcpy error", f"{exc}\n\nVisible windows:\n{titles}")

    def _capture_scrcpy(self) -> None:
        self.presenter.read_scrcpy_window()

    def show_screen_result(self, result: ScreenReadResult) -> None:
        self.image_path.set(str(result.image_path))
        self.capture_time.set(result.timing.summary())
        self.capture_metric.set(f"{result.timing.capture_seconds:.2f}s")
        self.ocr_metric.set(f"{result.timing.ocr_seconds:.2f}s")
        self.total_metric.set(f"{result.timing.total_seconds:.2f}s")
        self._show_image_preview(result.image_path)

        if result.ocr_available:
            preview = result.raw_text.strip()[:1200] or "OCR ran, but no clear text was detected."
            text = f"{result.source.upper()} result\n{preview}"
            self.ocr_text.set(text)
            self._set_readout_text(text)
            self.show_status(
                f"Read complete from {result.source.upper()}. {result.timing.summary()}"
            )
        else:
            text = f"{result.source.upper()} screenshot was not readable.\n{result.error}"
            self.ocr_text.set(text)
            self._set_readout_text(text)
            self.show_status(f"Read failed from {result.source.upper()}.")
            if result.error:
                messagebox.showinfo("Screen read issue", result.error)

    def _show_image_preview(self, image_path: Path) -> None:
        if not image_path.exists():
            self.preview_image = None
            self.preview_label.configure(image="", text="No screenshot file found")
            return

        try:
            image = Image.open(image_path).convert("RGB")
            image.thumbnail((760, 460), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(image.copy(), master=self)
            self.preview_label.configure(image=self.preview_image, text="")
        except Exception as exc:
            self.preview_image = None
            self.preview_label.configure(image="", text=f"Could not load preview: {exc}")

    def _set_readout_text(self, text: str) -> None:
        if not hasattr(self, "readout_box"):
            return
        self.readout_box.configure(state="normal")
        self.readout_box.delete("1.0", "end")
        self.readout_box.insert("1.0", text)
        self.readout_box.configure(state="disabled")

    def _refresh_android_devices(self) -> None:
        devices = self.presenter.refresh_android_devices()
        if not devices:
            messagebox.showinfo(
                "No Android device",
                "No authorized Android device was found through ADB. "
                "Check platform-tools, USB debugging, and the authorization prompt on the phone.",
            )
            return

        self.android_device.set(devices[0])
        messagebox.showinfo("Android devices", "\n".join(devices))

    def _update_advice(self) -> None:
        self.presenter.update_advice()

    def get_game_state(self) -> GameState:
        try:
            return GameState(
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
            raise

    def show_advice(self, advice: Advice) -> None:
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

    def set_game_field(self, key: str, value: str) -> None:
        if key in self.fields:
            self.fields[key].set(value)

    def show_status(self, text: str) -> None:
        self.read_status.set(text)
        self.update_idletasks()

    def _build_data_summary(self) -> str:
        data_dir = ROOT / "data" / "generated" / "set17"
        try:
            data = load_tft_static_data(data_dir)
            return (
                f"Set {data.meta.get('set_number', '?')} | "
                f"{len(data.champions)} champions | "
                f"{len(data.traits)} traits | "
                f"{len(data.items)} items"
            )
        except Exception:
            return "Static data not loaded"


def main() -> None:
    app = TFTCompanionApp()
    app.mainloop()


if __name__ == "__main__":
    main()
