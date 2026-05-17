from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageTk

from tft_companion.models.game import Advice, GameState
from tft_companion.models.screen import ScreenReadResult
from tft_companion.presenters.main_presenter import MainPresenter
from tft_companion.services.data_service import TftStaticData, load_tft_static_data
from tft_companion.views.constants import DATA_DIR, ROOT
from tft_companion.views.sidebar import build_sidebar
from tft_companion.views.workspace import build_workspace


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TFTCompanionApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TFT Decision Companion")
        self.geometry("1480x900")
        self.minsize(1180, 760)
        self.configure(fg_color="#07111F")

        self.static_data: TftStaticData | None = self._load_static_data()
        self.data_images: dict[str, ImageTk.PhotoImage] = {}

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
        build_sidebar(self)
        build_workspace(self)

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

    def show_screen_result(self, result: ScreenReadResult) -> None:
        self.tabs.set("Screen")
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
            image.thumbnail((820, 520), Image.Resampling.LANCZOS)
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

    def champion_rows(self) -> dict[str, dict[str, str]]:
        return self.static_data.champions if self.static_data else {}

    def item_rows(self) -> dict[str, dict[str, str]]:
        if not self.static_data:
            return {}
        return {
            key: value
            for key, value in self.static_data.items.items()
            if value.get("name") or value.get("desc") or value.get("id")
        }

    def trait_rows(self) -> dict[str, dict[str, str]]:
        return self.static_data.traits if self.static_data else {}

    def _load_static_data(self) -> TftStaticData | None:
        try:
            return load_tft_static_data(DATA_DIR)
        except Exception:
            return None

    def _build_data_summary(self) -> str:
        data = self.static_data
        if not data:
            return "Static data not loaded"
        return (
            f"Set {data.meta.get('set_number', '?')} | "
            f"{len(data.champions)} champions | "
            f"{len(data.traits)} traits | "
            f"{len(data.items)} items"
        )


def main() -> None:
    app = TFTCompanionApp()
    app.mainloop()


if __name__ == "__main__":
    main()
