import logging
from pathlib import Path
import shutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TFT_Train")

def train_tft_classifier():
    """
    Kịch bản huấn luyện mô hình phân loại tướng TFT tự động sử dụng YOLOv8 Classification.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error(
            "Chưa cài đặt thư viện 'ultralytics'. Vui lòng chạy lệnh sau để cài đặt:\n"
            "pip install ultralytics"
        )
        return

    # 1. Định nghĩa đường dẫn
    root_dir = Path(__file__).resolve().parent
    dataset_dir = root_dir / "dataset_classification"
    
    # Kiểm tra cấu trúc dataset và tự động chia tập train/val nếu tập val trống
    train_dir = dataset_dir / "train"
    val_dir = dataset_dir / "val"
    
    if not train_dir.exists() or not any(train_dir.iterdir()):
        logger.error(
            f"Thư mục dataset huấn luyện trống hoặc không tồn tại: {train_dir}\n"
            "Vui lòng phân loại các ảnh từ 'dataset_temp' vào các thư mục con tương ứng với tên tướng.\n"
            "Ví dụ:\n"
            "  dataset_classification/train/Teemo/crop_xxx.png\n"
            "  dataset_classification/train/Veiga/crop_yyy.png"
        )
        return

    # Tự động chia dataset train/val nếu tập val trống hoặc chưa có ảnh
    has_val_images = False
    if val_dir.exists():
        for class_dir in val_dir.iterdir():
            if class_dir.is_dir() and any(class_dir.iterdir()):
                has_val_images = True
                break

    if not has_val_images:
        logger.info("Thư mục val đang trống. Tự động trích xuất dữ liệu từ train sang val...")
        import random
        val_dir.mkdir(parents=True, exist_ok=True)
        
        for class_dir in train_dir.iterdir():
            if not class_dir.is_dir():
                continue
            
            images = [f for f in class_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg']]
            if not images:
                continue
                
            val_class_dir = val_dir / class_dir.name
            val_class_dir.mkdir(parents=True, exist_ok=True)
            
            if len(images) == 1:
                # Nếu chỉ có 1 ảnh duy nhất, ta SAO CHÉP sang val để cả hai tập đều có ảnh
                shutil.copy(str(images[0]), str(val_class_dir / images[0].name))
            else:
                # Nếu có từ 2 ảnh trở lên, ta di chuyển 20% (ít nhất 1 ảnh và phải giữ lại ít nhất 1 ảnh ở train)
                val_size = max(1, int(len(images) * 0.2))
                val_size = min(val_size, len(images) - 1)
                
                val_samples = random.sample(images, val_size)
                for img_path in val_samples:
                    dest_path = val_class_dir / img_path.name
                    shutil.move(str(img_path), str(dest_path))
                    
        logger.info("Đã hoàn thành tự động phân chia tập train/val thông minh!")

    logger.info("========== BẮT ĐẦU QUÁ TRÌNH HUẤN LUYỆN YOLOv8 CLASSIFIER ==========")
    logger.info(f"Dataset gốc: {dataset_dir}")
    
    # 2. Khởi tạo mô hình phân loại YOLOv8 Nano Classifier
    # Sử dụng yolov8n-cls.pt (mô hình pretrained siêu nhẹ) để transfer learning
    logger.info("Đang nạp mô hình pretrained yolov8n-cls.pt...")
    model = YOLO("yolov8n-cls.pt")

    # 3. Tiến hành huấn luyện
    # - epochs: Số chu kỳ huấn luyện (mặc định 50 cho tối ưu)
    # - imgsz: Kích thước ảnh (64x64 là kích thước cờ tối ưu cho phân loại tướng TFT)
    # - batch: Số lượng mẫu trong mỗi bước (16 hoặc 32)
    # - workers: Số luồng xử lý dữ liệu
    logger.info("Đang bắt đầu huấn luyện...")
    model.train(
        data=str(dataset_dir),
        epochs=50,
        imgsz=64,
        batch=16,
        workers=4,
        project=str(root_dir / "runs"),
        name="tft_champion_classifier"
    )
    
    # 4. Sao chép mô hình tốt nhất về thư mục data/models của ứng dụng
    # Quét tất cả các thư mục chạy của YOLO và tìm thư mục tft_champion_classifier mới nhất dựa trên thời gian sửa đổi (mtime)
    runs_dir = root_dir / "runs"
    best_model_src = None
    
    if runs_dir.exists():
        matching_dirs = []
        for p in runs_dir.iterdir():
            if p.is_dir() and p.name.startswith("tft_champion_classifier"):
                matching_dirs.append(p)
        if matching_dirs:
            # Chọn thư mục có thời gian sửa đổi mới nhất (mtime mới nhất)
            latest_run_dir = max(matching_dirs, key=lambda x: x.stat().st_mtime)
            best_model_src = latest_run_dir / "weights" / "best.pt"
            logger.info(f"Đã phát hiện thư mục huấn luyện mới nhất: {latest_run_dir.name}")

    dest_model_dir = root_dir / "data" / "models"
    dest_model_dir.mkdir(parents=True, exist_ok=True)
    dest_model_path = dest_model_dir / "tft_champions.pt"
    
    if best_model_src and best_model_src.exists():
        shutil.copy(str(best_model_src), str(dest_model_path))
        logger.info(f"========== HUẤN LUYỆN THÀNH CÔNG ==========")
        logger.info(f"Mô hình tốt nhất được lưu tại ứng dụng: {dest_model_path}")
    else:
        # Fallback tìm kiếm bất kỳ best.pt nào có trong runs/ làm phương án dự phòng khẩn cấp
        logger.warning("Không tìm thấy best.pt trong thư mục huấn luyện mới nhất. Đang tìm kiếm dự phòng...")
        fallback_src = None
        if runs_dir.exists():
            all_best_pts = list(runs_dir.glob("**/best.pt"))
            if all_best_pts:
                fallback_src = max(all_best_pts, key=lambda x: x.stat().st_mtime)
        
        if fallback_src and fallback_src.exists():
            shutil.copy(str(fallback_src), str(dest_model_path))
            logger.info(f"========== HUẤN LUYỆN THÀNH CÔNG (DỰ PHÒNG) ==========")
            logger.info(f"Mô hình tốt nhất dự phòng được lưu tại ứng dụng: {dest_model_path}")
        else:
            logger.error("Hoàn toàn không tìm thấy tệp mô hình best.pt sau khi huấn luyện xong!")

if __name__ == "__main__":
    train_tft_classifier()
