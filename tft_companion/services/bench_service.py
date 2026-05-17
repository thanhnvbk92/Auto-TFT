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
        
    occupied_slots = []
    threshold = 14.0  # Ngưỡng tối ưu cho nửa trên của ô hàng chờ
    
    debug_dir = image.filename.parent / "debug_crops" if hasattr(image, 'filename') and image.filename else None
    if not debug_dir:
        debug_dir = Path(__file__).resolve().parents[2] / "screenshots" / "debug_crops"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    stddevs_list = []
    
    for i, box in enumerate(boxes):
        li, ti, ri, bi = box
        w = ri - li
        h = bi - ti
        
        # Chỉ lấy 60% chiều cao trên của ô hàng chờ
        occupancy_box = (li, ti + int(h * 0.05), ri, ti + int(h * 0.60))
        crop = image.crop(occupancy_box)
        
        # Tính độ lệch chuẩn màu sắc (StdDev) 3D
        stat = ImageStat.Stat(crop)
        mean_stddev = sum(stat.stddev) / len(stat.stddev)
        stddevs_list.append(mean_stddev)
        
        is_occupied = mean_stddev > threshold
        occupied_slots.append(is_occupied)
        
        try:
            crop.save(debug_dir / f"bench_slot_{i}.png")
            
            import time
            timestamp = int(time.time() * 10) % 10000000
            dataset_dir = debug_dir.parent / "dataset_crops"
            dataset_dir.mkdir(parents=True, exist_ok=True)
            crop.save(dataset_dir / f"bench_slot_{i}_{timestamp}.png")
        except Exception:
            pass
            
    print(f"\n[DIAGNOSTIC] === THÔNG SỐ ĐỘ LỆCH MÀU NỬA TRÊN 9 Ô HÀNG CHỜ ===")
    for idx, val in enumerate(stddevs_list):
        print(f" -> Slot {idx}: StdDev = {val:.2f} (Occupied: {occupied_slots[idx]})")
    print(f"===========================================================\n")
    
    yolo_names = [None] * 9
    detected_yolo_boxes = []
    
    # Kích hoạt nhận diện bằng YOLO nếu có model tft_champions.pt
    if yolo_service.is_yolo_active():
        print("[AI ENGINE] YOLO Active! Đang tiến hành nhận diện tướng toàn màn hình...")
        yolo_results, detected_yolo_boxes = yolo_service.detect_bench_champions(image, boxes)
        for idx, name in enumerate(yolo_results):
            if name is not None:
                occupied_slots[idx] = True  # Ưu tiên kết quả thông minh từ YOLO
                yolo_names[idx] = name
                
    occupied_count = sum(1 for x in occupied_slots if x)
    is_full = occupied_count >= 9
    
    return occupied_count, is_full, occupied_slots, yolo_names, detected_yolo_boxes
