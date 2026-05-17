from __future__ import annotations

import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

# Active YOLO Model instance holder
_yolo_model = None
_yolo_active = False
_yolo_classes = {}
_yolo_is_custom = False


def init_yolo_detector() -> bool:
    """
    Attempts to initialize the YOLO champion detector.
    Looks for data/models/tft_champions.pt. If not found, falls back to yolov8n.pt.
    Returns True if initialized successfully, False otherwise.
    """
    global _yolo_model, _yolo_active, _yolo_classes, _yolo_is_custom
    try:
        from ultralytics import YOLO
        
        # Determine model path
        root_dir = Path(__file__).resolve().parents[2]
        custom_model_path = root_dir / "data" / "models" / "tft_champions.pt"
        fallback_model_path = root_dir / "data" / "models" / "yolov8n.pt"
        
        model_path = custom_model_path
        if not custom_model_path.exists():
            _yolo_is_custom = False
            custom_model_path.parent.mkdir(parents=True, exist_ok=True)
            # If custom model is not present, use standard yolov8n
            logger.info("Custom model data/models/tft_champions.pt not found. Using standard yolov8n.pt fallback.")
            model_path = fallback_model_path
        else:
            _yolo_is_custom = True
            
        # Initialize model
        _yolo_model = YOLO(str(model_path))
        _yolo_active = True
        
        # Fetch classes
        _yolo_classes = _yolo_model.names
        logger.info(f"YOLO detector successfully initialized with model: {model_path.name}")
        return True
    except ImportError:
        logger.warning("ultralytics package not installed. YOLO detector disabled.")
        _yolo_active = False
        _yolo_is_custom = False
        return False
    except Exception as exc:
        logger.error(f"Failed to initialize YOLO detector: {exc}")
        _yolo_active = False
        _yolo_is_custom = False
        return False


def is_yolo_active() -> bool:
    return _yolo_active and _yolo_is_custom


def detect_bench_champions(
    image: Image.Image, boxes: list[tuple[int, int, int, int]]
) -> tuple[list[str | None], list[tuple[tuple[int, int, int, int], str]]]:
    """
    Detects champions in the bench area using YOLO.
    
    Returns:
        1. A list of 9 elements containing champion names (or None if empty) mapped to slots.
        2. A list of absolute detected bounding boxes (box_xyxy, class_name) for drawing dynamic HUD.
    """
    if not _yolo_active or _yolo_model is None:
        return [None] * 9, []
        
    results = [None] * 9
    detected_yolo_boxes: list[tuple[tuple[int, int, int, int], str]] = []
    
    try:
        # 1. Thử nhận diện toàn bộ màn hình một lần duy nhất (Object Detection)
        # Đây là phương pháp tối ưu mới: chạy 1 lần predict trên toàn ảnh cực nhanh!
        pred_results = _yolo_model.predict(image, conf=0.45, verbose=False)
        if pred_results:
            first_res = pred_results[0]
            
            # Kiểm tra xem có phải là model Object Detection không
            if hasattr(first_res, 'boxes') and first_res.boxes is not None and len(first_res.boxes) > 0:
                yolo_slots_conf = [-1.0] * 9
                
                for b in first_res.boxes:
                    conf = float(b.conf[0])
                    cls_idx = int(b.cls[0])
                    class_name = _yolo_classes.get(cls_idx, "Unknown")
                    if class_name.lower() in ["empty", "trong", "trống"]:
                        continue
                        
                    # Lấy tọa độ pixel tuyệt đối
                    x1, y1, x2, y2 = map(int, b.xyxy[0])
                    det_cx = (x1 + x2) / 2
                    det_cy = (y1 + y2) / 2
                    
                    # Ánh xạ thông minh vào ô hàng chờ gần nhất
                    best_slot_idx = -1
                    min_dist = float('inf')
                    
                    for idx, slot_box in enumerate(boxes):
                        sl, st, sr, sb = slot_box
                        slot_cx = (sl + sr) / 2
                        slot_cy = (st + sb) / 2
                        slot_w = sr - sl
                        slot_h = sb - st
                        
                        dist_x = abs(det_cx - slot_cx)
                        dist_y = abs(det_cy - slot_cy)
                        
                        # Lọc các phát hiện quá xa theo chiều dọc so với hàng chờ
                        if dist_y > slot_h * 1.8:
                            continue
                            
                        # Lọc các phát hiện quá xa theo chiều ngang
                        if dist_x > slot_w * 1.2:
                            continue
                            
                        dist = dist_x + dist_y
                        if dist < min_dist:
                            min_dist = dist
                            best_slot_idx = idx
                            
                    if best_slot_idx != -1:
                        if yolo_slots_conf[best_slot_idx] < conf:
                            yolo_slots_conf[best_slot_idx] = conf
                            results[best_slot_idx] = class_name
                            
                        # Thêm vào danh sách vẽ HUD động
                        detected_yolo_boxes.append(((x1, y1, x2, y2), class_name))
                
                # Trả về kết quả phát hiện toàn màn hình
                return results, detected_yolo_boxes

            # 2. Hỗ trợ Fallback sang mô hình Phân loại (Classification)
            # Cắt 9 ô và dự đoán 9 lần nếu model chỉ hỗ trợ classification
            if hasattr(first_res, 'probs') and first_res.probs is not None:
                for i, box in enumerate(boxes):
                    crop = image.crop(box)
                    crop_results = _yolo_model.predict(crop, conf=0.45, verbose=False)
                    if not crop_results:
                        continue
                    c_res = crop_results[0]
                    if hasattr(c_res, 'probs') and c_res.probs is not None:
                        top1_idx = int(c_res.probs.top1)
                        conf = float(c_res.probs.top1conf)
                        if conf >= 0.45:
                            class_name = _yolo_classes.get(top1_idx, "Unknown")
                            if class_name.lower() not in ["empty", "trong", "trống"]:
                                results[i] = class_name
                                detected_yolo_boxes.append((box, class_name))
                return results, detected_yolo_boxes
                
    except Exception as exc:
        logger.error(f"YOLO detection failed: {exc}")
        
    return results, detected_yolo_boxes
