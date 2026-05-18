from __future__ import annotations

import logging
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

# Mô hình phân loại tướng custom (tft_champions.pt)
_yolo_classifier = None
_yolo_active = False

def init_yolo_detector() -> bool:
    """
    Khởi tạo mô hình nhận diện tướng custom (Classification).
    Nạp tệp data/models/tft_champions.pt.
    """
    global _yolo_classifier, _yolo_active
    try:
        from ultralytics import YOLO
        
        root_dir = Path(__file__).resolve().parents[2]
        custom_model_path = root_dir / "data" / "models" / "tft_champions.pt"
        
        if custom_model_path.exists():
            model = YOLO(str(custom_model_path))
            if hasattr(model, 'task') and model.task == 'classify':
                _yolo_classifier = model
                _yolo_active = True
                logger.info("Custom classification model data/models/tft_champions.pt loaded successfully!")
                return True
            else:
                logger.warning("Loaded custom model but it is not a Classification model.")
        else:
            logger.info("Custom model data/models/tft_champions.pt not found. YOLO detector waiting for training.")
    except ImportError:
        logger.warning("ultralytics package not installed. YOLO detector disabled.")
    except Exception as exc:
        logger.error(f"Failed to initialize YOLO detector: {exc}")
        
    _yolo_classifier = None
    _yolo_active = False
    return False

def is_yolo_active() -> bool:
    return _yolo_active

def detect_bench_champions(
    image: Image.Image, boxes: list[tuple[int, int, int, int]]
) -> tuple[list[str | None], list[tuple[tuple[int, int, int, int], str]]]:
    """
    Nhận diện tướng trên 9 ô hàng chờ (Bench) sử dụng mô hình custom Classification.
    """
    results = [None] * 9
    detected_yolo_boxes: list[tuple[tuple[int, int, int, int], str]] = []
    
    if not _yolo_active or _yolo_classifier is None:
        return results, detected_yolo_boxes
        
    try:
        for i, box in enumerate(boxes):
            crop = image.crop(box)
            predicted_name = classify_champion_crop(crop)
            if predicted_name:
                results[i] = predicted_name
                detected_yolo_boxes.append((box, predicted_name))
    except Exception as exc:
        logger.error(f"YOLO bench detection failed: {exc}")
        
    return results, detected_yolo_boxes

def classify_champion_crop(crop_img: Image.Image) -> str | None:
    """
    Phân loại vị tướng từ ảnh cắt (crop) sử dụng mô hình custom.
    Trả về tên tướng đã làm sạch kèm độ tin cậy, ví dụ: 'Teemo (85%)'
    """
    global _yolo_classifier, _yolo_active
    if not _yolo_active or _yolo_classifier is None:
        init_yolo_detector()
        
    if _yolo_classifier is not None:
        try:
            results = _yolo_classifier.predict(crop_img, verbose=False)
            if results:
                res = results[0]
                if hasattr(res, 'probs') and res.probs is not None:
                    top1_idx = int(res.probs.top1)
                    conf = float(res.probs.top1conf)
                    
                    # Chấp nhận tất cả dự đoán có độ tin cậy từ 1.5% trở lên do tập dữ liệu có tới 84 class
                    if conf >= 0.015:
                        class_name = _yolo_classifier.names[top1_idx]
                        
                        # Làm sạch tên tướng (loại bỏ các tiền tố hệ thống như TFT17_, TFT_, v.v.)
                        clean_name = class_name
                        for prefix in ["TFT17_", "TFT14_", "TFT6_", "TFT9_", "TFT5_", "TFT_"]:
                            if clean_name.startswith(prefix):
                                clean_name = clean_name[len(prefix):]
                                break
                                
                        # Không hiển thị nhãn nếu đoán là ô trống "Empty" hoặc "trong"
                        if clean_name.lower() in ["empty", "trong", "trống"]:
                            return None
                            
                        return f"{clean_name} ({conf:.0%})"
        except Exception as e:
            logger.error(f"Classification failed: {e}")
    return None
