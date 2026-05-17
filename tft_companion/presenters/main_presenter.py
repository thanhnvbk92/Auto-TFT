from __future__ import annotations

from pathlib import Path

from tft_companion.models.screen import ScreenReadResult
from tft_companion.services.decision_engine import build_advice
from tft_companion.services.screen_service import (
    list_android_devices,
    list_visible_window_titles,
    read_android_screen,
    read_screen,
    read_scrcpy_window,
    start_scrcpy_mirror,
)


class MainPresenter:
    def __init__(self, view, root_dir: Path) -> None:
        self.view = view
        self.root_dir = root_dir
        self.screenshot_dir = root_dir / "screenshots"

    def update_advice(self) -> None:
        try:
            state = self.view.get_game_state()
        except (TypeError, ValueError):
            return
        advice = build_advice(state)
        self.view.show_advice(advice)

    def read_pc_screen(self) -> None:
        self._read_status("Capturing PC screen...")
        result = read_screen(self.screenshot_dir)
        self._handle_screen_result(result)

    def read_android_screen(self, device_id: str) -> None:
        self._read_status("Reading Android through ADB...")
        result = read_android_screen(self.screenshot_dir, device_id=device_id)
        self._handle_screen_result(result)

    def start_scrcpy_mirror(self, device_id: str) -> None:
        start_scrcpy_mirror(device_id=device_id)
        self._read_status("scrcpy mirror started in no-control mode.")

    def read_scrcpy_window(self) -> None:
        self._read_status("Reading scrcpy window...")
        result = read_scrcpy_window(self.screenshot_dir)
        self._handle_screen_result(result)

    def refresh_android_devices(self) -> list[str]:
        devices = list_android_devices()
        if devices:
            self._read_status(f"Android device selected: {devices[0]}")
        else:
            self._read_status("No authorized Android device found.")
        return devices

    def visible_window_titles(self) -> list[str]:
        return list_visible_window_titles()

    def _handle_screen_result(self, result: ScreenReadResult) -> None:
        self.view.show_screen_result(result)
        for key, value in result.fields.items():
            self.view.set_game_field(key, value)
        self.update_advice()

    def _read_status(self, text: str) -> None:
        self.view.show_status(text)
