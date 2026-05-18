import os
import cv2
import configparser
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QScrollArea, QMessageBox, QWidget, QDoubleSpinBox, QSlider
)
from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QFont, QImage
from tft_companion.services.dataset_builder_service import detect_health_bars

logger = logging.getLogger(__name__)



class CalibrationCanvas(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_drawing = False
        
        # Store rects in ORIGINAL screen resolution coordinates
        self.rects = {} # key: QRect
        self.current_region = "Level"
        
        # Original screen resolution dimensions
        self.original_width = 1920
        self.original_height = 1080
        
        # Baseline dimensions at 100% zoom
        self.base_display_width = 1000
        self.base_display_height = 562
        
        # Active display dimensions accounting for current zoom
        self.display_width = 1000
        self.display_height = 562

        # Scale factors for champion crop preview
        self.width_factor = 1.8
        self.height_factor = 2.2

        # CV image fields
        self.image_path = None
        self.cv_img_bgr = None

        # Zoom level
        self.zoom_factor = 1.0

    def set_zoom(self, zoom_factor: float):
        self.zoom_factor = zoom_factor
        if hasattr(self, "base_display_width"):
            self.display_width = int(self.base_display_width * self.zoom_factor)
            self.display_height = int(self.base_display_height * self.zoom_factor)
            
            # Reload scaled pixmap
            if self.image_path and self.image_path.exists():
                pixmap = QPixmap(str(self.image_path))
                scaled_pixmap = pixmap.scaled(
                    self.display_width, self.display_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.setPixmap(scaled_pixmap)
                self.setFixedSize(self.display_width, self.display_height)
                self.update()

    def set_screenshot(self, image_path: Path):
        if not image_path.exists():
            self.setText("Không tìm thấy tệp ảnh.")
            return
        
        self.image_path = image_path
        self.cv_img_bgr = cv2.imread(str(image_path))
        
        pixmap = QPixmap(str(image_path))
        self.original_width = pixmap.width()
        self.original_height = pixmap.height()
        
        # Base dimensions at 100% zoom (width 1000)
        self.base_display_width = 1000
        self.base_display_height = int(1000 * self.original_height / self.original_width)
        
        # Active display dimensions accounting for current zoom
        self.display_width = int(self.base_display_width * self.zoom_factor)
        self.display_height = int(self.base_display_height * self.zoom_factor)
        
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
                # Convert to original screen coordinates
                x_factor = self.original_width / self.display_width
                y_factor = self.original_height / self.display_height
                
                l = int(rect.left() * x_factor)
                t = int(rect.top() * y_factor)
                r = int(rect.right() * x_factor)
                b = int(rect.bottom() * y_factor)
                
                self.rects[self.current_region] = QRect(QPoint(l, t), QPoint(r, b))
                
                # Trigger parent dialog to refresh crop preview!
                dialog = self.window()
                if hasattr(dialog, "_update_crop_preview"):
                    dialog._update_crop_preview()
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
            "Bench_Slot_8": QColor(219, 39, 119),     # Dark Pink
            "Health_Bar_Ref": QColor(6, 182, 212)    # Cyan
        }
        
        x_factor = self.original_width / self.display_width
        y_factor = self.original_height / self.display_height
        
        # Draw existing rects (stored in original screen coords)
        for region, orig_rect in self.rects.items():
            color = colors.get(region, QColor(255, 255, 255))
            
            # Convert original screen coords to active display coords
            dl = int(orig_rect.left() / x_factor)
            dt = int(orig_rect.top() / y_factor)
            dr = int(orig_rect.right() / x_factor)
            db = int(orig_rect.bottom() / y_factor)
            
            rect_display = QRect(QPoint(dl, dt), QPoint(dr, db))
            
            # Fill box transparently
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 40))
            painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(rect_display)
            
            # Draw label
            painter.setPen(Qt.GlobalColor.white)
            painter.setBrush(QColor(15, 23, 42, 200)) # Dark back for label
            label_rect = QRect(rect_display.left(), max(0, rect_display.top() - 20), max(80, rect_display.width()), 20)
            painter.drawRect(label_rect)
            painter.setPen(color)
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, region)

        # Draw live champion preview box under Health_Bar_Ref
        if "Health_Bar_Ref" in self.rects:
            orig_hb_rect = self.rects["Health_Bar_Ref"]
            
            # Convert to display coords
            hb_display_l = int(orig_hb_rect.left() / x_factor)
            hb_display_t = int(orig_hb_rect.top() / y_factor)
            hb_display_r = int(orig_hb_rect.right() / x_factor)
            hb_display_b = int(orig_hb_rect.bottom() / y_factor)
            
            hb_w = hb_display_r - hb_display_l
            hb_h = hb_display_b - hb_display_t
            
            # Calculate dynamic crop box dimensions based on scale factors
            preview_w = int(hb_w * getattr(self, "width_factor", 1.8))
            preview_h = int(hb_w * getattr(self, "height_factor", 2.2))
            
            # Center preview box under health bar
            cx = hb_display_l + hb_w // 2
            preview_left = cx - preview_w // 2
            preview_top = hb_display_b + 3
            
            preview_rect = QRect(preview_left, preview_top, preview_w, preview_h)
            
            # Draw preview box in premium Magenta with transparent pink fill
            painter.setBrush(QColor(236, 72, 153, 30))
            painter.setPen(QPen(QColor(236, 72, 153), 2, Qt.PenStyle.DashLine))
            painter.drawRect(preview_rect)
            
            # Label for preview
            painter.setPen(Qt.GlobalColor.white)
            painter.setBrush(QColor(15, 23, 42, 220))
            lbl_r = QRect(preview_left, max(0, preview_top - 20), max(90, preview_w), 20)
            painter.drawRect(lbl_r)
            painter.setPen(QColor(236, 72, 153))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(lbl_r, Qt.AlignmentFlag.AlignCenter, "Cờ Preview")

            # --- DYNAMICALLY DRAW ALL DETECTED CHAMPIONS ---
            if hasattr(self, "cv_img_bgr") and self.cv_img_bgr is not None:
                # Get raw width/height reference on original size
                orig_w_ref = orig_hb_rect.width()
                orig_h_ref = orig_hb_rect.height()
                
                # Trích xuất mẫu động trực tiếp từ nét vẽ trên canvas (kèm 2px padding viền đen)
                live_template = None
                try:
                    padding = 2
                    l_pad = max(0, orig_hb_rect.left() - padding)
                    t_pad = max(0, orig_hb_rect.top() - padding)
                    r_pad = min(self.original_width, orig_hb_rect.right() + padding)
                    b_pad = min(self.original_height, orig_hb_rect.bottom() + padding)
                    if r_pad > l_pad and b_pad > t_pad:
                        live_template = self.cv_img_bgr[t_pad:b_pad, l_pad:r_pad]
                except Exception:
                    pass

                try:
                    # Run live detection with current UI scale factors and the dynamic live template
                    detected_boxes_orig = detect_health_bars(
                        self.cv_img_bgr,
                        width_factor=getattr(self, "width_factor", 1.8),
                        height_factor=getattr(self, "height_factor", 2.2),
                        w_ref=orig_w_ref,
                        h_ref=orig_h_ref,
                        only_allies=True,
                        template_bgr=live_template
                    )
                    
                    # Draw each detected bounding box in sleek Hextech Cyan
                    for box_orig in detected_boxes_orig:
                        ox1, oy1, ox2, oy2 = box_orig
                        
                        dx1 = int(ox1 / x_factor)
                        dy1 = int(oy1 / y_factor)
                        dx2 = int(ox2 / x_factor)
                        dy2 = int(oy2 / y_factor)
                        
                        rect_display = QRect(QPoint(dx1, dy1), QPoint(dx2, dy2))
                        
                        # Only draw if it's not the exact active reference box to avoid double borders
                        inter = rect_display.intersected(preview_rect)
                        if inter.width() * inter.height() > 0.85 * (preview_rect.width() * preview_rect.height()):
                            continue
                            
                        # Draw dynamic bounding boxes in gorgeous Cyan
                        painter.setBrush(QColor(6, 182, 212, 15))  # Light transparent cyan fill
                        painter.setPen(QPen(QColor(6, 182, 212), 1.5, Qt.PenStyle.DashLine))
                        painter.drawRect(rect_display)
                except Exception as detect_err:
                    pass

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
        self.image_path = image_path
        self.dashboard_tab = dashboard_tab
        self.loaded_coords = {}
        
        self.setWindowTitle("Hiệu Chỉnh Vùng Quét OCR & Kích Thước Tướng")
        self.resize(1320, 800)
        self.setStyleSheet("""
            QDialog {
                background-color: #0B1329;
                color: #F8FAFC;
            }
            QLabel {
                color: #E2E8F0;
            }
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #475569;
            }
            QPushButton:pressed {
                background-color: #0F172A;
            }
            QListWidget {
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 6px;
                color: #E2E8F0;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #1E293B;
            }
            QListWidget::item:selected {
                background-color: #2563EB;
                color: white;
                font-weight: bold;
            }
        """)
        
        self._load_existing_coords()
        self._build_ui()
        self.canvas.set_screenshot(image_path)

    def _build_ui(self):
        layout = QHBoxLayout(self)
        
        # --- LEFT PANEL (Controls) ---
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Zoom Section
        zoom_layout = QHBoxLayout()
        lbl_zoom_title = QLabel("Phóng to:")
        lbl_zoom_title.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: bold;")
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 30) # 10 means 100%, 30 means 300%
        self.zoom_slider.setValue(10)
        self.zoom_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #1E293B;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #38BDF8;
                width: 14px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 7px;
            }
        """)
        self.lbl_zoom_val = QLabel("100%")
        self.lbl_zoom_val.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: bold; width: 40px;")
        
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        
        zoom_layout.addWidget(lbl_zoom_title)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.lbl_zoom_val)
        left_layout.addLayout(zoom_layout)

        # Region List Widget
        lbl_title = QLabel("CHỌN VÙNG CẦN HIỆU CHỈNH:")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #38BDF8; margin-top: 5px;")
        left_layout.addWidget(lbl_title)
        
        self.list_widget = QListWidget()
        regions = [
            ("🔴 Cấp độ (Level)", "Level"),
            ("🟡 Vàng - Shop (Gold_Shop)", "Gold_Shop"),
            ("🟠 Vàng - Trận đấu (Gold_Combat)", "Gold_Combat"),
            ("🟢 Stage - Shop (Stage_Shop)", "Stage_Shop"),
            ("🔵 Stage - Trận đấu (Stage_Combat)", "Stage_Combat"),
            ("🟣 Tên Bài Shop 1 (Shop_Card_0_Name)", "Shop_Card_0_Name"),
            ("🟣 Tên Bài Shop 5 (Shop_Card_4_Name)", "Shop_Card_4_Name"),
            ("🌸 Hàng chờ - Ô 1 (Bench_Slot_0)", "Bench_Slot_0"),
            ("🌸 Hàng chờ - Ô 9 (Bench_Slot_8)", "Bench_Slot_8"),
            ("🔵 Thanh Máu Tướng (Mẫu)", "Health_Bar_Ref")
        ]
        for name, key in regions:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.list_widget.addItem(item)
            
        self.list_widget.setCurrentRow(0)
        self.list_widget.currentItemChanged.connect(self._on_region_selection_changed)
        left_layout.addWidget(self.list_widget)

        # Crop Preview Section
        lbl_preview_title = QLabel("ẢNH CẮT THỰC TẾ (CROP PREVIEW)")
        lbl_preview_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #10B981; margin-top: 10px;")
        left_layout.addWidget(lbl_preview_title)
        
        self.lbl_crop_preview = QLabel("Chưa vẽ vùng này")
        self.lbl_crop_preview.setFixedSize(260, 95)
        self.lbl_crop_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_crop_preview.setStyleSheet("""
            background-color: #0F172A;
            border: 2px dashed #334155;
            border-radius: 6px;
            color: #64748B;
            font-size: 12px;
            font-weight: bold;
        """)
        left_layout.addWidget(self.lbl_crop_preview)

        # Character Crop Box adjustment section
        lbl_scale_title = QLabel("CĂN CHỈNH KÍCH THƯỚC CỜ")
        lbl_scale_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #38BDF8; margin-top: 8px;")
        left_layout.addWidget(lbl_scale_title)
        
        # Width scale factor
        w_layout = QHBoxLayout()
        lbl_w = QLabel("Tỷ lệ Rộng:")
        lbl_w.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        self.spin_width = QDoubleSpinBox()
        self.spin_width.setRange(0.5, 4.0)
        self.spin_width.setSingleStep(0.1)
        self.spin_width.setValue(1.8)
        self.spin_width.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; color: white; padding: 2px;")
        self.spin_width.valueChanged.connect(self._on_scale_factors_changed)
        w_layout.addWidget(lbl_w)
        w_layout.addWidget(self.spin_width)
        left_layout.addLayout(w_layout)
        
        # Height scale factor
        h_layout = QHBoxLayout()
        lbl_h = QLabel("Tỷ lệ Cao:")
        lbl_h.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(0.5, 5.0)
        self.spin_height.setSingleStep(0.1)
        self.spin_height.setValue(2.2)
        self.spin_height.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; color: white; padding: 2px;")
        self.spin_height.valueChanged.connect(self._on_scale_factors_changed)
        h_layout.addWidget(lbl_h)
        h_layout.addWidget(self.spin_height)
        left_layout.addLayout(h_layout)

        # Instruction info
        lbl_info = QLabel("HD: Kéo chuột để vẽ hình hộp hiệu chỉnh trên ảnh bản đồ bên phải.")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 5px;")
        left_layout.addWidget(lbl_info)

        # Buttons
        self.btn_capture = QPushButton("Chụp Ảnh Bản Đồ Mới")
        self.btn_capture.setStyleSheet("background-color: #2563EB; color: white; font-size: 12px; margin-top: 5px;")
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
        self.scroll_area.setWidgetResizable(False) # False so QFixedSize of canvas triggers scrollbars perfectly
        
        self.canvas = CalibrationCanvas()
        self.scroll_area.setWidget(self.canvas)
        layout.addWidget(self.scroll_area, stretch=1)

    def _on_zoom_changed(self, val):
        zoom_fact = val / 10.0
        self.lbl_zoom_val.setText(f"{int(zoom_fact * 100)}%")
        self.canvas.set_zoom(zoom_fact)

    def _on_region_selection_changed(self, current, previous):
        if current:
            key = current.data(Qt.ItemDataRole.UserRole)
            self.canvas.current_region = key
            self._update_crop_preview()

    def _update_crop_preview(self):
        key = self.canvas.current_region
        if key in self.canvas.rects and hasattr(self.canvas, "cv_img_bgr") and self.canvas.cv_img_bgr is not None:
            rect = self.canvas.rects[key] # in original screen coordinates
            l, t, r, b = rect.left(), rect.top(), rect.right(), rect.bottom()
            
            h_img, w_img = self.canvas.cv_img_bgr.shape[:2]
            # Bounds checking
            l = max(0, min(l, w_img - 1))
            r = max(0, min(r, w_img - 1))
            t = max(0, min(t, h_img - 1))
            b = max(0, min(b, h_img - 1))
            
            if r > l and b > t:
                # Crop using OpenCV
                crop = self.canvas.cv_img_bgr[t:b, l:r]
                if crop.size > 0:
                    # Convert BGR to RGB
                    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                    # Convert to QImage
                    h_c, w_c, ch_c = crop_rgb.shape
                    bytes_per_line = ch_c * w_c
                    q_img = QImage(crop_rgb.data, w_c, h_c, bytes_per_line, QImage.Format.Format_RGB888)
                    
                    # Convert to QPixmap
                    pix = QPixmap.fromImage(q_img)
                    
                    # Scale to fit label size while keeping aspect ratio
                    scaled_pix = pix.scaled(
                        self.lbl_crop_preview.width() - 10,
                        self.lbl_crop_preview.height() - 10,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.lbl_crop_preview.setPixmap(scaled_pix)
                    self.lbl_crop_preview.setStyleSheet("""
                        background-color: #0F172A;
                        border: 2px solid #10B981;
                        border-radius: 6px;
                    """)
                    return
                    
        # Placeholder state
        self.lbl_crop_preview.clear()
        self.lbl_crop_preview.setText("Chưa vẽ vùng này")
        self.lbl_crop_preview.setStyleSheet("""
            background-color: #0F172A;
            border: 2px dashed #334155;
            border-radius: 6px;
            color: #64748B;
            font-size: 12px;
            font-weight: bold;
        """)

    def _on_scale_factors_changed(self) -> None:
        w_fact = self.spin_width.value()
        h_fact = self.spin_height.value()
        self.canvas.width_factor = w_fact
        self.canvas.height_factor = h_fact
        self.canvas.update()

    def _clear_current_region(self):
        key = self.canvas.current_region
        if key in self.canvas.rects:
            del self.canvas.rects[key]
            self.canvas.update()
            self._update_crop_preview()

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
                "Shop_Card_0_Name", "Shop_Card_4_Name", "Bench_Slot_0", "Bench_Slot_8",
                "Health_Bar_Ref"
            ]
            for key in regions_to_load:
                if key in config:
                    l = int(config[key]['left'])
                    t = int(config[key]['top'])
                    r = int(config[key]['right'])
                    b = int(config[key]['bottom'])
                    self.loaded_coords[key] = (l, t, r, b, base_w, base_h)
                    
            # Load scale factors
            self.width_factor = 1.8
            self.height_factor = 2.2
            if "DatasetBuilder" in config:
                self.width_factor = float(config["DatasetBuilder"].get("width_factor", "1.8"))
                self.height_factor = float(config["DatasetBuilder"].get("height_factor", "2.2"))
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        # Set loaded scale factors to GUI elements
        if hasattr(self, "width_factor"):
            self.spin_width.setValue(self.width_factor)
            self.canvas.width_factor = self.width_factor
        if hasattr(self, "height_factor"):
            self.spin_height.setValue(self.height_factor)
            self.canvas.height_factor = self.height_factor

        if hasattr(self, 'loaded_coords') and self.loaded_coords:
            self.canvas.rects = {}
            for key, (l, t, r, b, base_w, base_h) in self.loaded_coords.items():
                # Scale loaded coordinates from base resolution to current screenshot original resolution
                x_factor = self.canvas.original_width / base_w
                y_factor = self.canvas.original_height / base_h
                ol = int(l * x_factor)
                ot = int(t * y_factor)
                or_right = int(r * x_factor)
                ob = int(b * y_factor)
                self.canvas.rects[key] = QRect(QPoint(ol, ot), QPoint(or_right, ob))
            self.canvas.update()
            self._update_crop_preview()

    def _save_coordinates(self):
        if not self.canvas.rects:
            QMessageBox.warning(self, "Cảnh báo", "Bạn chưa vẽ vùng hiệu chỉnh nào!")
            return
        
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
                l = rect.left()
                t = rect.top()
                r = rect.right()
                b = rect.bottom()
                
                config[key] = {
                    'left': str(l),
                    'top': str(t),
                    'right': str(r),
                    'bottom': str(b)
                }
                
            # Save scale factors
            config['DatasetBuilder'] = {
                'width_factor': f"{self.spin_width.value():.2f}",
                'height_factor': f"{self.spin_height.value():.2f}"
            }
            
            # If the user saved a health bar reference, save its actual cropped BGR image as a template
            if "Health_Bar_Ref" in self.canvas.rects and hasattr(self.canvas, "cv_img_bgr") and self.canvas.cv_img_bgr is not None:
                rect = self.canvas.rects["Health_Bar_Ref"]
                # Tự động nới rộng thêm 2px về mọi phía để chắc chắn bắt trọn vẹn viền chữ nhật màu đen bao quanh thanh máu xanh lục
                padding = 2
                l = max(0, rect.left() - padding)
                t = max(0, rect.top() - padding)
                r = min(self.canvas.original_width, rect.right() + padding)
                b = min(self.canvas.original_height, rect.bottom() + padding)
                if r > l and b > t:
                    try:
                        tpl_img = self.canvas.cv_img_bgr[t:b, l:r]
                        tpl_path = Path(__file__).resolve().parents[2] / "tft_companion" / "config" / "health_bar_template.png"
                        tpl_path.parent.mkdir(parents=True, exist_ok=True)
                        cv2.imwrite(str(tpl_path), tpl_img)
                        logger.info(f"[CALIBRATION] Đã lưu tệp ảnh mẫu thanh máu thật tại: {tpl_path}")
                    except Exception as e:
                        logger.error(f"[CALIBRATION] Lỗi lưu tệp ảnh mẫu thanh máu: {e}")
                        
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
                            x_factor = self.canvas.original_width / base_w
                            y_factor = self.canvas.original_height / base_h
                            ol = int(l * x_factor)
                            ot = int(t * y_factor)
                            or_right = int(r * x_factor)
                            ob = int(b * y_factor)
                            self.canvas.rects[key] = QRect(QPoint(ol, ot), QPoint(or_right, ob))
                            
                    self.canvas.update()
                    self._update_crop_preview()
                    QMessageBox.information(self, "Thành công", "Đã chụp và cập nhật ảnh bản đồ hiệu chỉnh mới!")
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", f"Không thể chụp ảnh mới: {exc}")
