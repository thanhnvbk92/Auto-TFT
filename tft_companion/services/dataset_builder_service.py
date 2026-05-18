import os
import cv2
import numpy as np
import logging
import configparser
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

def load_calibration_config() -> tuple[float, float, int | None, int | None]:
    """
    Đọc cấu hình tỷ lệ rộng/cao của character box và độ rộng/cao thanh máu mẫu từ ocr_coords.ini.
    """
    config_path = Path(__file__).resolve().parents[1] / "config" / "ocr_coords.ini"
    
    width_factor = 1.8
    height_factor = 2.2
    w_ref = None
    h_ref = None
    
    if config_path.exists():
        try:
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            
            if "DatasetBuilder" in config:
                width_factor = float(config["DatasetBuilder"].get("width_factor", "1.8"))
                height_factor = float(config["DatasetBuilder"].get("height_factor", "2.2"))
                
            if "Health_Bar_Ref" in config:
                l = int(config["Health_Bar_Ref"].get("left", "0"))
                r = int(config["Health_Bar_Ref"].get("right", "0"))
                t = int(config["Health_Bar_Ref"].get("top", "0"))
                b = int(config["Health_Bar_Ref"].get("bottom", "0"))
                if r > l:
                    w_ref = r - l
                if b > t:
                    h_ref = b - t
        except Exception as e:
            logger.error(f"[DATASET BUILDER] Lỗi đọc config hiệu chỉnh: {e}")
            
    return width_factor, height_factor, w_ref, h_ref

def detect_health_bars(
    img_bgr: np.ndarray,
    width_factor: float | None = None,
    height_factor: float | None = None,
    w_ref: int | None = None,
    h_ref: int | None = None,
    only_allies: bool = False,
    template_bgr: np.ndarray | None = None
) -> list[tuple[int, int, int, int]]:
    """
    Phát hiện thanh máu của tướng trên sân đấu.
    - Ưu tiên 1: Sử dụng So Khớp Ảnh Mẫu 3 Kênh BGR Toàn Cục (Template Matching) nếu có ảnh mẫu.
    - Ưu tiên 2: Tự động fallback sang quét dải màu HSV xanh lục của đồng minh nếu chưa có ảnh mẫu.
    """
    # Load cấu hình tỷ lệ động nếu không truyền vào trực tiếp
    cfg_w_fact, cfg_h_fact, cfg_w_ref, cfg_h_ref = load_calibration_config()
    if width_factor is None:
        width_factor = cfg_w_fact
    if height_factor is None:
        height_factor = cfg_h_fact
    if w_ref is None:
        w_ref = cfg_w_ref
    if h_ref is None:
        h_ref = cfg_h_ref
        
    # Nạp ảnh mẫu thanh máu thật nếu chưa truyền vào trực tiếp
    if template_bgr is None:
        tpl_path = Path(__file__).resolve().parents[1] / "config" / "health_bar_template.png"
        if tpl_path.exists():
            try:
                template_bgr = cv2.imread(str(tpl_path))
                if template_bgr is not None:
                    w_ref = template_bgr.shape[1]
                    h_ref = template_bgr.shape[0]
            except Exception as e:
                logger.error(f"[DATASET BUILDER] Lỗi đọc ảnh mẫu thanh máu thật: {e}")
    if template_bgr is None:
        return []

    h_img, w_img = img_bgr.shape[:2]
    raw_boxes = []

    # --- SO KHỚP ẢNH MẪU 3 KÊNH BGR TOÀN CỤC ---
    res = cv2.matchTemplate(img_bgr, template_bgr, cv2.TM_CCOEFF_NORMED)
    threshold = 0.50
    loc = np.where(res >= threshold)
    
    peaks = []
    for y_pt, x_pt in zip(*loc):
        peaks.append((x_pt, y_pt, res[y_pt, x_pt]))
        
    peaks = sorted(peaks, key=lambda x: x[2], reverse=True)
    
    filtered_peaks = []
    for peak in peaks:
        px, py, score = peak
        too_close = False
        for fx, fy, _ in filtered_peaks:
            if abs(px - fx) < 15 and abs(py - fy) < 5:
                too_close = True
                break
        if not too_close:
            filtered_peaks.append(peak)
            
    h_tpl = template_bgr.shape[0]
    w_tpl = template_bgr.shape[1]
    
    for px, py, score in filtered_peaks:
        if not (0.05 * h_img <= py <= 0.95 * h_img):
            continue
            
        x_actual = px
        y_actual = py
        
        crop_w = int(w_tpl * width_factor)
        crop_h = int(w_tpl * height_factor)
        
        cx = x_actual + w_tpl // 2
        crop_y = y_actual + h_tpl + 3
        crop_x = cx - crop_w // 2
        
        x1 = max(0, crop_x)
        y1 = max(0, crop_y)
        x2 = min(w_img, crop_x + crop_w)
        y2 = min(h_img, crop_y + crop_h)
        
        if (x2 - x1) >= 20 and (y2 - y1) >= 20:
            raw_boxes.append((x1, y1, x2, y2))
                
    # 2. Bộ lọc Non-Maximum Suppression (NMS) đơn giản để loại bỏ các box trùng lặp
    final_boxes = []
    for box in raw_boxes:
        overlap = False
        for f_box in final_boxes:
            # Tính toán độ giao nhau (Intersection over Union - IoU)
            x1, y1, x2, y2 = box
            x3, y3, x4, y4 = f_box
            
            xi1 = max(x1, x3)
            yi1 = max(y1, y3)
            xi2 = min(x2, x4)
            yi2 = min(y2, y4)
            
            inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
            area1 = (x2 - x1) * (y2 - y1)
            area2 = (x4 - x3) * (y4 - y3)
            
            iou = inter / min(area1, area2)
            if iou > 0.40:
                overlap = True
                break
        if not overlap:
            final_boxes.append(box)
            
    return final_boxes

def build_dataset_from_screenshot(image_path: Path, output_base_dir: Path) -> int:
    """
    1. Đọc ảnh chụp màn hình game.
    2. Quét phát hiện thanh máu theo kích thước đã căn chỉnh động.
    3. Cắt ảnh các tướng ôm khít theo tỷ lệ động.
    4. Lưu trực tiếp tất cả ảnh cắt tướng dạng phẳng (không chia nhóm) vào thư mục output_base_dir.
    """
    img_bgr = cv2.imread(str(image_path))
    if img_bgr is None:
        logger.error(f"[DATASET BUILDER] Không thể đọc ảnh chụp màn hình tại: {image_path}")
        return 0
        
    # Phát hiện thanh máu & lấy tọa độ tướng động
    boxes = detect_health_bars(img_bgr)
    if not boxes:
        logger.info("[DATASET BUILDER] Không phát hiện thấy bất kỳ tướng nào trên sân đấu.")
        return 0
        
    logger.info(f"[DATASET BUILDER] Tìm thấy {len(boxes)} tướng trên màn hình. Đang tiến hành cắt ảnh...")
    
    # Tạo thư mục đầu ra
    output_base_dir.mkdir(parents=True, exist_ok=True)
    
    saved_count = 0
    import time
    timestamp = int(time.time())
    
    for box in boxes:
        x1, y1, x2, y2 = box
        crop = img_bgr[y1:y2, x1:x2]
        
        file_name = f"crop_{timestamp}_{saved_count}.png"
        cv2.imwrite(str(output_base_dir / file_name), crop)
        saved_count += 1
            
    logger.info(f"[DATASET BUILDER SUCCESS] Đã lưu {saved_count} ảnh cắt tướng trực tiếp vào thư mục: {output_base_dir}")
    return saved_count
