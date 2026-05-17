from __future__ import annotations

from typing import TYPE_CHECKING
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QCheckBox, QComboBox, QLineEdit, QPushButton
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap

from tft_companion.views.widgets import action_button

if TYPE_CHECKING:
    from tft_companion.views.main_window import TFTCompanionWindow


class DashboardTab(QWidget):
    def __init__(self, main_window: TFTCompanionWindow, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_window = main_window
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        
        # --- TOP ROW: GAME STATE ---
        state_card = QWidget()
        state_card.setObjectName("card")
        state_layout = QHBoxLayout(state_card)
        state_layout.setContentsMargins(12, 8, 12, 8)
        state_layout.setSpacing(12)
        
        def _add_field(label: str, key: str, width: int = 40):
            col = QWidget()
            l = QVBoxLayout(col)
            l.setContentsMargins(0, 0, 0, 0)
            l.setSpacing(4)
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
            l.addWidget(lbl)
            
            inp = QLineEdit()
            inp.setFixedWidth(width)
            inp.setMinimumHeight(30)
            l.addWidget(inp)
            self.main_window.input_widgets[key] = inp
            state_layout.addWidget(col)
            
        _add_field("Vòng", "stage", 50)
        _add_field("Cấp", "level")
        _add_field("Vàng", "gold")
        _add_field("Máu", "hp")
        _add_field("Chuỗi", "streak")
        _add_field("Đôi", "pairs")
        _add_field("Thiếu", "missing_core_units")
        
        # Board Strength Dropdown
        bs_col = QWidget()
        bs_layout = QVBoxLayout(bs_col)
        bs_layout.setContentsMargins(0, 0, 0, 0)
        bs_layout.setSpacing(4)
        bs_lbl = QLabel("Đội hình")
        bs_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        bs_layout.addWidget(bs_lbl)
        self.board_strength_combo = QComboBox()
        self.board_strength_combo.addItems(["Yếu", "Cân bằng", "Mạnh"])
        self.board_strength_combo.setCurrentText("Cân bằng")
        self.board_strength_combo.setFixedWidth(80)
        self.board_strength_combo.setMinimumHeight(30)
        bs_layout.addWidget(self.board_strength_combo)
        self.main_window.input_widgets["board_strength"] = self.board_strength_combo
        state_layout.addWidget(bs_col)
        
        # Checkboxes
        cb_col = QWidget()
        cb_layout = QVBoxLayout(cb_col)
        cb_layout.setContentsMargins(0, 0, 0, 0)
        cb_layout.setSpacing(4)
        self.bench_full_cb = QCheckBox("Đầy hàng chờ")
        self.contested_cb = QCheckBox("Bị tranh")
        cb_layout.addWidget(self.bench_full_cb)
        cb_layout.addWidget(self.contested_cb)
        self.main_window.input_widgets["bench_full"] = self.bench_full_cb
        self.main_window.input_widgets["contested"] = self.contested_cb
        state_layout.addWidget(cb_col)
        
        _add_field("Mục tiêu", "target_comp", 120)
        
        state_layout.addStretch()
        update_btn = action_button(state_card, "Cập nhật", self.main_window._update_advice, is_primary=True, height=36)
        update_btn.setStyleSheet("background-color: #0284c7; color: white; margin-top: 12px;")
        state_layout.addWidget(update_btn)
        
        layout.addWidget(state_card)
        
        # --- BENCH GRID CARD ---
        bench_card = QWidget()
        bench_card.setObjectName("card")
        bench_layout = QVBoxLayout(bench_card)
        bench_layout.setContentsMargins(12, 10, 12, 10)
        bench_layout.setSpacing(8)
        
        bench_header_layout = QHBoxLayout()
        bench_title = QLabel("HÀNG CHỜ TƯỚNG (BENCH)")
        bench_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #94A3B8; letter-spacing: 1px;")
        bench_header_layout.addWidget(bench_title)
        
        bench_desc = QLabel("Tự động phát hiện Trống/Đầy. Click để chọn nhanh tướng.")
        bench_desc.setStyleSheet("color: #64748B; font-size: 11px;")
        bench_header_layout.addWidget(bench_desc)
        bench_header_layout.addStretch()
        
        clear_bench_btn = QPushButton("Xóa sạch hàng chờ")
        clear_bench_btn.setFixedWidth(120)
        clear_bench_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                border: 1px solid #334155;
                color: #94A3B8;
                font-size: 10px;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: white;
                border-color: #ef4444;
            }
        """)
        clear_bench_btn.clicked.connect(self._clear_all_bench_slots)
        bench_header_layout.addWidget(clear_bench_btn)
        bench_layout.addLayout(bench_header_layout)
        
        slots_layout = QHBoxLayout()
        slots_layout.setSpacing(8)
        self.bench_buttons = []
        self.bench_occupancy_states = [False] * 9
        self.bench_champions = [None] * 9
        
        for i in range(9):
            btn = QPushButton()
            btn.setFixedWidth(90)
            btn.setMinimumHeight(48)
            btn.setProperty("slot_index", i)
            btn.clicked.connect(self._on_bench_slot_clicked)
            slots_layout.addWidget(btn)
            self.bench_buttons.append(btn)
            
        self._update_bench_buttons_style()
        bench_layout.addLayout(slots_layout)
        layout.addWidget(bench_card)
        
        # --- BOTTOM AREA: LEFT/RIGHT COLUMNS ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(16)
        
        # --- LEFT COLUMN: CAPTURE & PREVIEW ---
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        
        # Capture Card
        capture_card = QWidget()
        capture_card.setObjectName("card")
        capture_layout = QHBoxLayout(capture_card)
        capture_layout.setContentsMargins(18, 14, 18, 14)
        capture_layout.setSpacing(12)
        
        cap_title = QLabel("Chế độ:")
        cap_title.setStyleSheet("font-weight: bold; color: #E2E8F0;")
        capture_layout.addWidget(cap_title)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Chụp màn hình PC", "Chụp qua ADB", "Dùng Scrcpy Mirror"])
        self.mode_combo.setMinimumHeight(36)
        self.mode_combo.setMinimumWidth(180)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        capture_layout.addWidget(self.mode_combo)
        
        # Devices (Hidden by default since PC is selected)
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(36)
        self.device_combo.setMinimumWidth(150)
        self.device_combo.setPlaceholderText("Chọn thiết bị...")
        self.device_combo.hide()
        capture_layout.addWidget(self.device_combo)
        
        self.refresh_btn = action_button(capture_card, "↻", self.main_window._refresh_android_devices, height=36)
        self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.hide()
        capture_layout.addWidget(self.refresh_btn)
        
        self.scrcpy_start_btn = action_button(capture_card, "Mở Mirror", self.main_window._start_scrcpy, height=36)
        self.scrcpy_start_btn.hide()
        capture_layout.addWidget(self.scrcpy_start_btn)
        
        self.calibrate_btn = action_button(capture_card, "Hiệu chỉnh OCR", self._open_calibration_dialog, height=36)
        self.calibrate_btn.setStyleSheet("background-color: #D97706; color: white; font-weight: bold;")
        capture_layout.addWidget(self.calibrate_btn)
        
        capture_layout.addStretch()
        
        self.capture_btn = action_button(capture_card, "Chụp ảnh", self._execute_capture, is_primary=True, height=42)
        self.capture_btn.setMinimumWidth(120)
        self.capture_btn.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        capture_layout.addWidget(self.capture_btn)
        
        left_layout.addWidget(capture_card)
        
        # Preview Card
        preview_card = QWidget()
        preview_card.setObjectName("card")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(18, 16, 18, 16)
        
        preview_title = QLabel("Ảnh vừa chụp")
        preview_title.setObjectName("title")
        preview_layout.addWidget(preview_title)
        
        self.image_path_label = QLabel("")
        self.image_path_label.setStyleSheet("color: #64748B;")
        preview_layout.addWidget(self.image_path_label)
        
        self.preview_label = QLabel("Chưa có ảnh chụp")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #020617; border-radius: 14px; color: #64748B;")
        preview_layout.addWidget(self.preview_label, stretch=1)
        
        left_layout.addWidget(preview_card, stretch=1)
        bottom_layout.addWidget(left_col, stretch=1)
        
        # --- RIGHT COLUMN: DECISION & OCR ---
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        
        advice_card = QWidget()
        advice_card.setObjectName("card")
        advice_layout = QVBoxLayout(advice_card)
        advice_layout.setContentsMargins(18, 16, 18, 16)
        
        advice_title = QLabel("Lời khuyên chiến thuật")
        advice_title.setObjectName("title")
        advice_layout.addWidget(advice_title)
        
        self.advice_text = QTextEdit()
        self.advice_text.setReadOnly(True)
        self.advice_text.setObjectName("adviceText")
        font = self.advice_text.font()
        font.setPointSize(13)
        self.advice_text.setFont(font)
        advice_layout.addWidget(self.advice_text, stretch=2)
        
        right_layout.addWidget(advice_card, stretch=2)
        
        ocr_card = QWidget()
        ocr_card.setObjectName("card")
        ocr_layout = QVBoxLayout(ocr_card)
        ocr_layout.setContentsMargins(18, 16, 18, 16)
        
        ocr_title = QLabel("Kết quả nhận diện (OCR)")
        ocr_title.setObjectName("title")
        ocr_layout.addWidget(ocr_title)
        
        self.readout_box = QTextEdit()
        self.readout_box.setReadOnly(True)
        self.readout_box.setStyleSheet("font-family: Consolas; font-size: 12px; color: #94A3B8;")
        ocr_layout.addWidget(self.readout_box, stretch=1)
        
        right_layout.addWidget(ocr_card, stretch=1)
        
        bottom_layout.addWidget(right_col, stretch=1)
        layout.addLayout(bottom_layout, stretch=1)

    def _on_mode_changed(self) -> None:
        mode = self.mode_combo.currentText()
        if mode == "Chụp màn hình PC":
            self.device_combo.hide()
            self.refresh_btn.hide()
            self.scrcpy_start_btn.hide()
        elif mode == "Chụp qua ADB":
            self.device_combo.show()
            self.refresh_btn.show()
            self.scrcpy_start_btn.hide()
        elif mode == "Dùng Scrcpy Mirror":
            self.device_combo.show()
            self.refresh_btn.show()
            self.scrcpy_start_btn.show()

    def _execute_capture(self) -> None:
        mode = self.mode_combo.currentText()
        if mode == "Chụp màn hình PC":
            self.main_window._capture_pc()
        elif mode == "Chụp qua ADB":
            self.main_window._capture_android()
        elif mode == "Dùng Scrcpy Mirror":
            self.main_window._capture_scrcpy()

    def _open_calibration_dialog(self) -> None:
        from pathlib import Path
        from tft_companion.views.calibration_dialog import OcrCalibratorDialog
        from PyQt6.QtWidgets import QMessageBox

        # Determine which image path to use
        img_path_str = self.image_path_label.text().strip()
        img_path = Path(img_path_str) if img_path_str else None

        # Fallback to latest screenshots in the screenshots directory
        if not img_path or not img_path.exists():
            from tft_companion.views.constants import ROOT
            sc_dir = ROOT / "screenshots"
            scrcpy_sc = sc_dir / "latest_scrcpy_screen.png"
            pc_sc = sc_dir / "latest_screen.png"
            
            if scrcpy_sc.exists():
                img_path = scrcpy_sc
            elif pc_sc.exists():
                img_path = pc_sc
            else:
                QMessageBox.warning(
                    self, "Không có hình ảnh",
                    "Hãy thực hiện Chụp ảnh (PC hoặc Scrcpy) ít nhất 1 lần để hệ thống có ảnh nền làm bản đồ hiệu chỉnh!"
                )
                return

        dialog = OcrCalibratorDialog(img_path, self, self.main_window)
        dialog.exec()

    def show_preview(self, pixmap: QPixmap | None, error_text: str = "") -> None:
        if pixmap:
            scaled = pixmap.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
        else:
            self.preview_label.clear()
            self.preview_label.setText(error_text)
            
    def show_ocr_text(self, text: str) -> None:
        self.readout_box.setPlainText(text)
        
    def set_image_path(self, path: str) -> None:
        self.image_path_label.setText(path)

    def show_advice(self, content: str) -> None:
        self.advice_text.setPlainText(content)

    def _get_champions_grouped_by_cost(self) -> dict[int, list[str]]:
        champions = self.main_window.champion_rows()
        grouped = {1: [], 2: [], 3: [], 4: [], 5: []}
        
        # Fallback list of champions in case static data is not loaded
        fallback_champions = {
            1: ["Ahri", "Amumu", "Blitzcrank", "Darius", "Elise", "Jax", "Lillia", "Lux", "Poppy", "Singed", "Vayne", "Zeri", "Ziggs"],
            2: ["Ashe", "Camille", "Diana", "Ezreal", "Gnar", "Katarina", "Kog'Maw", "Leona", "Nidalee", "Nunu", "Rell", "Shen", "Syndra", "Talon"],
            3: ["Dr. Mundo", "Ekko", "Hecarim", "Illaoi", "Janna", "Kassadin", "Kha'Zix", "Morgana", "Nami", "Neeko", "Renekton", "Riven", "Swain", "Vex"],
            4: ["Caitlyn", "Garen", "Heimerdinger", "Kai'Sa", "Lucian", "Nautilus", "Olaf", "Ornn", "Pyke", "Silco", "Tahm Kench", "Taric", "Vi"],
            5: ["Jayce", "Jinx", "Leblanc", "Milio", "Morgana", "Rum", "Ryze", "Sion", "Twitch", "Udyr", "Viego", "Wukong", "Xerath", "Yasuo"]
        }
        
        if not champions:
            return fallback_champions
            
        for champ_id, details in champions.items():
            cost = 1
            try:
                cost = int(details.get("cost", 1))
            except Exception:
                pass
            name = details.get("name", champ_id)
            if cost in grouped:
                grouped[cost].append(name)
            else:
                grouped[1].append(name)
                
        # Sort each list alphabetically
        for cost in grouped:
            grouped[cost] = list(set(grouped[cost])) # deduplicate
            grouped[cost].sort()
            
        return grouped

    def _on_bench_slot_clicked(self) -> None:
        btn = self.sender()
        if not btn:
            return
        slot_index = btn.property("slot_index")
        
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #F8FAFC;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 16px;
            }
            QMenu::item:selected {
                background-color: #3B82F6;
                color: white;
            }
        """)
        
        action_clear = QAction("❌ Để Trống", self)
        action_clear.triggered.connect(lambda: self._set_bench_slot_champion(slot_index, None))
        menu.addAction(action_clear)
        menu.addSeparator()
        
        grouped = self._get_champions_grouped_by_cost()
        for cost in sorted(grouped.keys()):
            submenu = menu.addMenu(f"💰 Tướng {cost} Vàng")
            submenu.setStyleSheet(menu.styleSheet())
            for name in grouped[cost]:
                action = QAction(name, self)
                # Capture name in lambda correctly by setting as a default argument
                action.triggered.connect(lambda checked, n=name: self._set_bench_slot_champion(slot_index, n))
                submenu.addAction(action)
                
        menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))

    def _set_bench_slot_champion(self, slot_index: int, champ_name: str | None) -> None:
        self.bench_champions[slot_index] = champ_name
        if champ_name is not None:
            self.bench_occupancy_states[slot_index] = True
        else:
            self.bench_occupancy_states[slot_index] = False
            
        self._update_bench_buttons_style()
        self._auto_sync_game_state_with_bench()

    def _clear_all_bench_slots(self) -> None:
        self.bench_occupancy_states = [False] * 9
        self.bench_champions = [None] * 9
        self._update_bench_buttons_style()
        self._auto_sync_game_state_with_bench()

    def _update_bench_buttons_style(self) -> None:
        for i, btn in enumerate(self.bench_buttons):
            is_occupied = self.bench_occupancy_states[i]
            champ = self.bench_champions[i]
            
            if not is_occupied:
                btn.setText(f"Ô {i+1}\n(Trống)")
                btn.setStyleSheet("""
                    QPushButton {
                        border: 2px dashed #475569;
                        border-radius: 8px;
                        background-color: transparent;
                        color: #64748B;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        border-color: #3B82F6;
                        color: #3B82F6;
                    }
                """)
                self.bench_champions[i] = None
            else:
                display_name = champ if champ else "Có Tướng"
                btn.setText(f"Ô {i+1}\n{display_name}")
                btn.setStyleSheet("""
                    QPushButton {
                        border: 2px solid #0EA5E9;
                        border-radius: 8px;
                        background-color: rgba(14, 165, 233, 0.15);
                        color: #F8FAFC;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        border-color: #38BDF8;
                        background-color: rgba(14, 165, 233, 0.25);
                    }
                """)

    def _auto_sync_game_state_with_bench(self) -> None:
        # Calculate pairs (exactly 2 copies)
        counts = {}
        for champ in self.bench_champions:
            if champ:
                counts[champ] = counts.get(champ, 0) + 1
        
        pairs_count = sum(1 for champ, cnt in counts.items() if cnt >= 2)
        
        # Sync to UI text field
        self.main_window.input_widgets["pairs"].setText(str(pairs_count))
        
        # Check if bench is full (all 9 occupied)
        is_bench_full = all(self.bench_occupancy_states)
        self.bench_full_cb.setChecked(is_bench_full)
        
        # Trigger an advice update
        self.main_window._update_advice()

    def update_bench_occupancy_from_ocr(self, states: list[bool], champion_names: list[str | None] | None = None) -> None:
        if len(states) != 9:
            return
        self.bench_occupancy_states = states
        # Clean up slots that are now empty, and populate from YOLO if present
        for i, occupied in enumerate(states):
            if not occupied:
                self.bench_champions[i] = None
            elif champion_names and i < len(champion_names) and champion_names[i] is not None:
                self.bench_champions[i] = champion_names[i]
        self._update_bench_buttons_style()
        self._auto_sync_game_state_with_bench()
