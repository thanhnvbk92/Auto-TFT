from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMessageBox, QLineEdit, QCheckBox, QComboBox
from PyQt6.QtGui import QPixmap

from tft_companion.models.game import Advice, GameState
from tft_companion.models.screen import ScreenReadResult
from tft_companion.presenters.main_presenter import MainPresenter
from tft_companion.services.data_service import TftStaticData, load_tft_static_data
from tft_companion.views.constants import DATA_DIR, ROOT
from tft_companion.views.sidebar import Sidebar
from tft_companion.views.workspace import Workspace


class TFTCompanionWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Trợ lý TFT (Hextech UI)")
        self.resize(1480, 900)
        self.setMinimumSize(1180, 760)

        # Apply QSS
        qss_path = Path(__file__).parent / "theme.qss"
        if qss_path.exists():
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())
        
        # Data
        self.static_data: TftStaticData | None = self._load_static_data()
        
        # Store widgets for values retrieval
        self.input_widgets: dict[str, QWidget] = {}
        
        self.presenter = MainPresenter(self, ROOT)
        
        self._build_ui()
        self._populate_initial_data()
        self.presenter.update_advice()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.add_nav_button("Bảng điều khiển", lambda: self.workspace.set_tab(0))
        self.sidebar.add_nav_button("Tướng", lambda: self.workspace.set_tab(1))
        self.sidebar.add_nav_button("Trang bị", lambda: self.workspace.set_tab(2))
        self.sidebar.add_nav_button("Tộc Hệ", lambda: self.workspace.set_tab(3))
        layout.addWidget(self.sidebar)
        
        # Workspace
        self.workspace = Workspace(self)
        layout.addWidget(self.workspace, stretch=1)
        
    def _populate_initial_data(self) -> None:
        defaults = {
            "stage": "", "level": "", "gold": "", "hp": "", 
            "streak": "", "pairs": "", "missing_core_units": "", "target_comp": ""
        }
        for k, v in defaults.items():
            if k in self.input_widgets and isinstance(self.input_widgets[k], QLineEdit):
                self.input_widgets[k].setText(v)

    # --- Presenter Actions ---
    def _capture_pc(self) -> None:
        self.presenter.read_pc_screen()

    def _capture_android(self) -> None:
        device_id = self.workspace.dashboard_tab.device_combo.currentText()
        self.presenter.read_android_screen(device_id=device_id)

    def _start_scrcpy(self) -> None:
        try:
            device_id = self.workspace.dashboard_tab.device_combo.currentText()
            self.presenter.start_scrcpy_mirror(device_id=device_id)
            QMessageBox.information(
                self, "scrcpy",
                "Đã mở cửa sổ mirror scrcpy. Hãy đợi hình ảnh lên, sau đó bấm Chụp."
            )
        except Exception as exc:
            self.show_status("scrcpy thất bại.")
            titles = "\n".join(self.presenter.visible_window_titles()[:20])
            QMessageBox.critical(self, "Lỗi scrcpy", f"{exc}\n\nCác cửa sổ hiện tại:\n{titles}")

    def _capture_scrcpy(self) -> None:
        self.presenter.read_scrcpy_window()

    def _refresh_android_devices(self) -> None:
        devices = self.presenter.refresh_android_devices()
        if not devices:
            QMessageBox.information(
                self, "Không tìm thấy thiết bị",
                "Không tìm thấy thiết bị Android nào qua ADB. Hãy kiểm tra kết nối cáp, bật USB debugging và cấp quyền trên điện thoại."
            )
            return

        self.workspace.dashboard_tab.device_combo.clear()
        self.workspace.dashboard_tab.device_combo.addItems(devices)
        QMessageBox.information(self, "Thiết bị Android", "\n".join(devices))

    def _update_advice(self) -> None:
        self.presenter.update_advice()

    # --- View Interface for Presenter ---
    def get_game_state(self) -> GameState:
        try:
            def _get_text(key: str) -> str:
                w = self.input_widgets.get(key)
                if isinstance(w, QLineEdit): return w.text()
                if isinstance(w, QComboBox): return w.currentText()
                return ""
            
            def _get_bool(key: str) -> bool:
                w = self.input_widgets.get(key)
                if isinstance(w, QCheckBox): return w.isChecked()
                return False

            strength_map = {"Yếu": "weak", "Cân bằng": "even", "Mạnh": "strong"}
            return GameState(
                stage=_get_text("stage"),
                level=int(_get_text("level") or "0"),
                gold=int(_get_text("gold") or "0"),
                hp=int(_get_text("hp") or "0"),
                streak=int(_get_text("streak") or "0"),
                pairs=int(_get_text("pairs") or "0"),
                missing_core_units=int(_get_text("missing_core_units") or "0"),
                board_strength=strength_map.get(_get_text("board_strength"), "even"),  # type: ignore[arg-type]
                bench_full=_get_bool("bench_full"),
                contested=_get_bool("contested"),
                target_comp=_get_text("target_comp").strip(),
            )
        except (TypeError, ValueError):
            QMessageBox.critical(self, "Invalid data", "Check numeric fields before updating advice.")
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
        self.workspace.dashboard_tab.show_advice(content)

    def show_screen_result(self, result: ScreenReadResult) -> None:
        self.workspace.set_tab(0) # Switch to Dashboard tab
        self.workspace.dashboard_tab.set_image_path(str(result.image_path))
        
        if result.image_path.exists():
            pixmap = QPixmap(str(result.image_path))
            self.workspace.dashboard_tab.show_preview(pixmap)
        else:
            self.workspace.dashboard_tab.show_preview(None, "Không tìm thấy file ảnh")

        if result.ocr_available:
            preview = result.raw_text.strip()[:1200] or "Đã chạy OCR nhưng không nhận diện được chữ nào."
            text = f"Kết quả chụp từ {result.source.upper()} [{result.timing.summary()}]\n\n{preview}"
            self.workspace.dashboard_tab.show_ocr_text(text)
            self.show_status(f"Đọc thành công từ {result.source.upper()}.")
        else:
            text = f"Ảnh từ {result.source.upper()} không thể đọc được.\n{result.error}"
            self.workspace.dashboard_tab.show_ocr_text(text)
            self.show_status(f"Đọc thất bại từ {result.source.upper()}.")
            if result.error:
                QMessageBox.information(self, "Lỗi đọc màn hình", result.error)

    def set_game_field(self, key: str, value: str) -> None:
        w = self.input_widgets.get(key)
        if isinstance(w, QLineEdit):
            w.setText(str(value))
        elif isinstance(w, QComboBox):
            w.setCurrentText(str(value))
        elif isinstance(w, QCheckBox):
            w.setChecked(bool(value))

    def show_status(self, text: str) -> None:
        self.sidebar.set_status(text)

    # --- Data Providers ---
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

def main() -> None:
    import sys
    from PyQt6.QtWidgets import QApplication
    from threading import Thread
    from tft_companion.services.yolo_service import init_yolo_detector
    
    app = QApplication(sys.argv)
    
    # Khởi tạo YOLO ngầm để tối ưu hóa tốc độ mở ứng dụng
    Thread(target=init_yolo_detector, daemon=True).start()
    
    window = TFTCompanionWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
