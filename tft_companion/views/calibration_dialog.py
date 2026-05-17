import os
import configparser
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QScrollArea, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont


class CalibrationCanvas(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_drawing = False
        
        # Store displays coords (normalized inside 1000px scale)
        self.rects = {} # key: QRect
        self.current_region = "Level"
        
        # Dimensions
        self.original_width = 1600
        self.original_height = 740
        self.display_width = 1000
        self.display_height = 462 # Will be calculated on pixmap load

    def set_screenshot(self, image_path: Path):
        if not image_path.exists():
            self.setText("Không tìm thấy tệp ảnh.")
            return
        
        pixmap = QPixmap(str(image_path))
        self.original_width = pixmap.width()
        self.original_height = pixmap.height()
        
        # Scale to fixed display width of 1000
        self.display_width = 1000
        self.display_height = int(1000 * self.original_height / self.original_width)
        
        scaled_pixmap = pixmap.scaled(
            self.display_width, self.display_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)
        self.setFixedSize(self.display_width, self.display_height)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.position().toPoint()
            self.end_point = self.start_point
            self.is_drawing = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing:
            # Constrain within canvas bounds
            pos = event.position().toPoint()
            x = max(0, min(pos.x(), self.display_width))
            y = max(0, min(pos.y(), self.display_height))
            self.end_point = QPoint(x, y)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_drawing:
            pos = event.position().toPoint()
            x = max(0, min(pos.x(), self.display_width))
            y = max(0, min(pos.y(), self.display_height))
            self.end_point = QPoint(x, y)
            self.is_drawing = False
            
            rect = QRect(self.start_point, self.end_point).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self.rects[self.current_region] = rect
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        colors = {
            "Level": QColor(239, 68, 68),       # Red
            "Gold_Shop": QColor(245, 158, 11),   # Amber/Gold
            "Gold_Combat": QColor(249, 115, 22), # Orange
            "Stage_Shop": QColor(16, 185, 129),  # Emerald/Green
            "Stage_Combat": QColor(34, 197, 94), # Light Green
            "Shop_Card_0_Name": QColor(168, 85, 247), # Purple
            "Shop_Card_4_Name": QColor(139, 92, 246), # Indigo/Violet
            "Bench_Slot_0": QColor(236, 72, 153),    # Pink
            "Bench_Slot_8": QColor(219, 39, 119)     # Dark Pink
        }
        
        # Draw existing rects
        for region, rect in self.rects.items():
            color = colors.get(region, QColor(255, 255, 255))
            # Fill box transparently
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 40))
            painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(rect)
            
            # Draw label
            painter.setPen(Qt.GlobalColor.white)
            painter.setBrush(QColor(15, 23, 42, 200)) # Dark back for label
            label_rect = QRect(rect.left(), max(0, rect.top() - 20), max(80, rect.width()), 20)
            painter.drawRect(label_rect)
            painter.setPen(color)
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, region)

        # Draw current active drawing
        if self.is_drawing:
            color = colors.get(self.current_region, QColor(255, 255, 255))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 20))
            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            current_rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawRect(current_rect)


class OcrCalibratorDialog(QDialog):
    def __init__(self, image_path: Path, dashboard_tab, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hiệu chỉnh Vùng Chụp OCR")
        self.resize(1200, 750)
        self.image_path = image_path
        self.dashboard_tab = dashboard_tab
        
        # Set styled background similar to theme.qss
        self.setStyleSheet("""
            QDialog {
                background-color: #0B0F19;
                color: #F8FAFC;
            }
            QListWidget {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #F8FAFC;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #334155;
            }
            QListWidget::item:selected {
                background-color: #3B82F6;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #1E293B;
                border: 1px solid #475569;
                border-radius: 6px;
                color: #F8FAFC;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        
        self._build_ui()
        self._load_existing_coords()
        self.canvas.set_screenshot(self.image_path)

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # --- LEFT PANEL (Controls) ---
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        lbl_title = QLabel("CÁC VÙNG CẦN HIỆU CHỈNH")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #94A3B8;")
        left_layout.addWidget(lbl_title)
        
        self.list_widget = QListWidget()
        # Items mapped internally to config keys
        self.regions_map = {
            "Level": "🔴 Cấp độ (Level)",
            "Gold_Shop": "🟡 Vàng - Shop (Gold_Shop)",
            "Gold_Combat": "🟠 Vàng - Đấu (Gold_Combat)",
            "Stage_Shop": "🟢 Vòng đấu - Shop (Stage_Shop)",
            "Stage_Combat": "🟢 Vòng đấu - Thường (Stage_Combat)",
            "Shop_Card_0_Name": "🔮 Thẻ 1 - Tên Tướng (Trái)",
            "Shop_Card_4_Name": "🔮 Thẻ 5 - Tên Tướng (Phải)",
            "Bench_Slot_0": "🔮 Hàng Chờ Ô 1 (Trái)",
            "Bench_Slot_8": "🔮 Hàng Chờ Ô 9 (Phải)"
        }
        
        for key, display_name in self.regions_map.items():
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.list_widget.addItem(item)
            
        self.list_widget.setCurrentRow(0)
        self.list_widget.currentItemChanged.connect(self._on_region_selection_changed)
        left_layout.addWidget(self.list_widget)
        
        # Instructions
        lbl_inst = QLabel(
            "💡 Hướng dẫn vẽ:\n"
            "1. Chọn vùng cần vẽ ở danh sách trên.\n"
            "2. Nhấn giữ và kéo chuột vẽ hình chữ nhật trên ảnh bên phải.\n"
            "3. Vẽ xong từng vùng sẽ có màu sắc và nhãn riêng biệt.\n"
            "4. Nhấn [Lưu Tọa Độ] sau khi hoàn tất."
        )
        lbl_inst.setWordWrap(True)
        lbl_inst.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.4;")
        left_layout.addWidget(lbl_inst)
        
        left_layout.addStretch()
        
        # Buttons
        self.btn_capture = QPushButton("Chụp Ảnh Mới")
        self.btn_capture.setStyleSheet("background-color: #3B82F6; color: white; font-size: 13px; font-weight: bold;") # Blue
        self.btn_capture.clicked.connect(self._capture_new_screenshot)
        left_layout.addWidget(self.btn_capture)

        self.btn_save = QPushButton("Lưu Tọa Độ")
        self.btn_save.setStyleSheet("background-color: #10B981; color: white; font-size: 13px;") # Green
        self.btn_save.clicked.connect(self._save_coordinates)
        left_layout.addWidget(self.btn_save)
        
        self.btn_clear = QPushButton("Xóa Vùng Vẽ")
        self.btn_clear.clicked.connect(self._clear_current_region)
        left_layout.addWidget(self.btn_clear)
        
        self.btn_close = QPushButton("Đóng")
        self.btn_close.clicked.connect(self.reject)
        left_layout.addWidget(self.btn_close)
        
        layout.addWidget(left_panel)
        
        # --- RIGHT PANEL (Canvas in ScrollArea) ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("background-color: #020617; border: 1px solid #1E293B; border-radius: 8px;")
        self.scroll_area.setWidgetResizable(True)
        
        self.canvas = CalibrationCanvas()
        self.scroll_area.setWidget(self.canvas)
        layout.addWidget(self.scroll_area, stretch=1)

    def _on_region_selection_changed(self, current, previous):
        if current:
            key = current.data(Qt.ItemDataRole.UserRole)
            self.canvas.current_region = key

    def _clear_current_region(self):
        key = self.canvas.current_region
        if key in self.canvas.rects:
            del self.canvas.rects[key]
            self.canvas.update()

    def _load_existing_coords(self):
        config_path = Path(__file__).resolve().parents[2] / "tft_companion" / "config" / "ocr_coords.ini"
        if not config_path.exists():
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            
            # Check resolution baseline
            if 'Resolution' not in config:
                return
            base_w = int(config['Resolution']['width'])
            base_h = int(config['Resolution']['height'])
            
            self.loaded_coords = {}
            regions_to_load = [
                "Level", "Gold_Shop", "Gold_Combat", "Stage_Shop", "Stage_Combat",
                "Shop_Card_0_Name", "Shop_Card_4_Name", "Bench_Slot_0", "Bench_Slot_8"
            ]
            for key in regions_to_load:
                if key in config:
                    l = int(config[key]['left'])
                    t = int(config[key]['top'])
                    r = int(config[key]['right'])
                    b = int(config[key]['bottom'])
                    self.loaded_coords[key] = (l, t, r, b, base_w, base_h)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'loaded_coords') and self.loaded_coords:
            for key, (l, t, r, b, base_w, base_h) in self.loaded_coords.items():
                x_factor = self.canvas.display_width / base_w
                y_factor = self.canvas.display_height / base_h
                dl = int(l * x_factor)
                dt = int(t * y_factor)
                dr = int(r * x_factor)
                db = int(b * y_factor)
                self.canvas.rects[key] = QRect(QPoint(dl, dt), QPoint(dr, db))
            self.canvas.update()

    def _save_coordinates(self):
        if not self.canvas.rects:
            QMessageBox.warning(self, "Cảnh báo", "Bạn chưa vẽ vùng hiệu chỉnh nào!")
            return
        
        x_factor = self.canvas.original_width / self.canvas.display_width
        y_factor = self.canvas.original_height / self.canvas.display_height
        
        config_path = Path(__file__).resolve().parents[2] / "tft_companion" / "config" / "ocr_coords.ini"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            config = configparser.ConfigParser()
            if config_path.exists():
                config.read(config_path, encoding='utf-8')
            
            config['Resolution'] = {
                'width': str(self.canvas.original_width),
                'height': str(self.canvas.original_height)
            }
            
            for key, rect in self.canvas.rects.items():
                l = int(rect.left() * x_factor)
                t = int(rect.top() * y_factor)
                r = int(rect.right() * x_factor)
                b = int(rect.bottom() * y_factor)
                
                config[key] = {
                    'left': str(l),
                    'top': str(t),
                    'right': str(r),
                    'bottom': str(b)
                }
                
            with open(config_path, 'w', encoding='utf-8') as f:
                config.write(f)
                
            QMessageBox.information(
                self, "Thành công", 
                f"Đã lưu tọa độ hiệu chỉnh thành công vào:\n{config_path.name}\n\nĐộ phân giải lưu: {self.canvas.original_width}x{self.canvas.original_height}"
            )
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể ghi file config:\n{exc}")

    def _capture_new_screenshot(self):
        try:
            self.dashboard_tab._execute_capture()
            # Wait a split second for file write to fully settle
            import time
            time.sleep(0.1)
            
            img_path_str = self.dashboard_tab.image_path_label.text().strip()
            if img_path_str:
                new_path = Path(img_path_str)
                if new_path.exists():
                    self.image_path = new_path
                    self.canvas.set_screenshot(new_path)
                    
                    # Also reload existing loaded coordinates to match new resolution if display metrics changed
                    self._load_existing_coords()
                    if hasattr(self, 'loaded_coords') and self.loaded_coords:
                        self.canvas.rects = {}
                        for key, (l, t, r, b, base_w, base_h) in self.loaded_coords.items():
                            x_factor = self.canvas.display_width / base_w
                            y_factor = self.canvas.display_height / base_h
                            dl = int(l * x_factor)
                            dt = int(t * y_factor)
                            dr = int(r * x_factor)
                            db = int(b * y_factor)
                            self.canvas.rects[key] = QRect(QPoint(dl, dt), QPoint(dr, db))
                            
                    self.canvas.update()
                    QMessageBox.information(self, "Thành công", "Đã chụp và cập nhật ảnh bản đồ hiệu chỉnh mới!")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể chụp ảnh mới: {exc}")
