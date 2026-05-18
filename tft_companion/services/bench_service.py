from __future__ import annotations

import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageStat

from tft_companion.services.ocr_service import load_custom_bench_boxes
from tft_companion.services import yolo_service

logger = logging.getLogger(__name__)


def _draw_bench_hud(
    image: Image.Image,
    boxes: list[tuple[int, int, int, int]],
    yolo_names: list[str | None],
    detected_yolo_boxes: list[tuple[tuple[int, int, int, int], str]] = None
) -> None:
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arialbd.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    # Có Bounding Box động từ YOLO hay không
    has_yolo_boxes = detected_yolo_boxes is not None and len(detected_yolo_boxes) > 0
    
    if has_yolo_boxes:
        for box, name in detected_yolo_boxes:
            li, ti, ri, bi = box
            label_h = 20
            
            # Tướng được YOLO phát hiện: Vẽ khung lục bảo Hextech Neon động tuyệt vời ôm khít lấy tướng!
            draw.rectangle(box, outline="#10B981", width=3)
            label_box = (li, max(0, ti - label_h), ri, ti)
            draw.rectangle(label_box, fill="#0F172A")
            draw.rectangle(label_box, outline="#10B981", width=1)
            
            text_str = name
            text_color = "#F8FAFC"
            
            try:
                left, top, right, bottom = draw.textbbox((0, 0), text_str, font=font)
                text_w = right - left
                text_h = bottom - top
            except AttributeError:
                text_w, text_h = draw.textsize(text_str, font=font) if hasattr(draw, 'textsize') else (60, 10)
                
            text_x = li + (ri - li - text_w) // 2
            text_y = max(0, ti - label_h) + (label_h - text_h) // 2 - 1
            draw.text((text_x, text_y), text_str, fill=text_color, font=font)
        return
            
    # Vẽ các ô hàng chờ tĩnh tham chiếu
    for i, box in enumerate(boxes):
        name = yolo_names[i]
        li, ti, ri, bi = box
        label_h = 20
        
        # Nếu đang sử dụng YOLO và đã vẽ khung động cho ô này rồi, ta bỏ qua không vẽ khung tĩnh đè lên
        if has_yolo_boxes and name is not None:
            continue
            
        if name is not None:
            # Chế độ Fallback không YOLO (nhận diện qua StdDev): Vẽ khung xanh lục tĩnh
            draw.rectangle(box, outline="#10B981", width=3)
            label_box = (li, max(0, ti - label_h), ri, ti)
            draw.rectangle(label_box, fill="#0F172A")
            draw.rectangle(label_box, outline="#10B981", width=1)
            
            text_str = name
            text_color = "#F8FAFC"
        else:
            # Ô trống: Vẽ khung xám đá mờ tinh tế
            draw.rectangle(box, outline="#475569", width=1)
            label_box = (li, max(0, ti - label_h), ri, ti)
            draw.rectangle(label_box, fill="#1E293B")
            draw.rectangle(label_box, outline="#475569", width=1)
            
            text_str = f"Ô {i+1}: Trống"
            text_color = "#94A3B8"
            
        try:
            left, top, right, bottom = draw.textbbox((0, 0), text_str, font=font)
            text_w = right - left
            text_h = bottom - top
        except AttributeError:
            text_w, text_h = draw.textsize(text_str, font=font) if hasattr(draw, 'textsize') else (60, 10)
            
        text_x = li + (ri - li - text_w) // 2
        text_y = max(0, ti - label_h) + (label_h - text_h) // 2 - 1
        draw.text((text_x, text_y), text_str, fill=text_color, font=font)


def _detect_bench_occupancy(
    image: Image.Image
) -> tuple[int, bool, list[bool], list[str | None], list[tuple[tuple[int, int, int, int], str]]]:
    boxes = load_custom_bench_boxes(image.size)
    if not boxes:
        return 0, False, [False] * 9, [None] * 9, []
        
    occupied_slots = [False] * 9
    yolo_names = [None] * 9
    detected_yolo_boxes = []
    
    # 1. Chạy YOLO Object Detection lấy bounding box động
    if yolo_service.is_yolo_active():
        yolo_results, detected_yolo_boxes = yolo_service.detect_bench_champions(image, boxes)
        for idx, name in enumerate(yolo_results):
            if name is not None:
                occupied_slots[idx] = True
                yolo_names[idx] = name
                
    # 2. Chạy Center-Cropped StdDev bổ trợ để đảm bảo NHẬN DIỆN 100% TƯỚNG không bỏ sót!
    # Lấy vùng trung tâm 60% để triệt tiêu các biểu tượng gold/shop đè vào góc ô
    for idx, box in enumerate(boxes):
        if occupied_slots[idx]:
            continue  # Đã được YOLO nhận diện, bỏ qua
            
        l, t, r, b = box
        w = r - l
        h = b - t
        cx, cy = l + w // 2, t + h // 2
        cw, ch = int(w * 0.6), int(h * 0.6)
        
        center_box = (cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2)
        crop = image.crop(center_box)
        stat = ImageStat.Stat(crop)
        stddev = sum(stat.stddev) / 3.0
        
        # Nếu độ lệch màu trung tâm > 15.0 -> Chắc chắn có tướng
        if stddev > 15.0:
            occupied_slots[idx] = True
            yolo_names[idx] = "Tướng"
            detected_yolo_boxes.append((box, "Tướng"))
            
    occupied_count = sum(1 for x in occupied_slots if x)
    is_full = occupied_count >= 9
    
    return occupied_count, is_full, occupied_slots, yolo_names, detected_yolo_boxes
