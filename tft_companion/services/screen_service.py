from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image

# ==========================================
# RE-EXPORTS FOR BACKWARD COMPATIBILITY
# ==========================================
from tft_companion.models.screen import ReadTiming, ScreenReadResult

# Window handles & API
from tft_companion.services.window_service import (
    list_visible_window_titles,
    _find_window_handle,
    _find_window_client_rect,
    _find_process_window_handle,
    _client_rect_for_window,
    _bring_window_to_front,
)

# Device screens capture
from tft_companion.services.device_service import (
    find_adb,
    find_scrcpy,
    list_android_devices,
    capture_screen,
    capture_android_screen,
    start_scrcpy_mirror,
    capture_scrcpy_window,
)

# OCR engine & helpers
from tft_companion.services.ocr_service import (
    find_tesseract,
    read_image,
    parse_tft_text,
    load_custom_ocr_box,
    load_custom_shop_boxes,
    load_custom_bench_boxes,
    _ocr_region,
    _read_mobile_stage,
    _read_mobile_gold,
    _read_mobile_shop,
)

# Bench & Bounding Box HUD
from tft_companion.services.bench_service import (
    _detect_bench_occupancy,
    _draw_bench_hud,
)


# ==========================================
# CORE FACADE CAPTURE PROCESS FLOWS
# ==========================================

def read_screen(output_dir: Path) -> ScreenReadResult:
    started = time.perf_counter()
    try:
        capture_started = time.perf_counter()
        image_path = capture_screen(output_dir)
        capture_seconds = time.perf_counter() - capture_started
        ocr_started = time.perf_counter()
        fields, text = read_tft_mobile_state(image_path, read_shop=True)
        ocr_seconds = time.perf_counter() - ocr_started
        return ScreenReadResult(
            image_path=image_path,
            raw_text=text,
            fields=fields,
            ocr_available=True,
            source="pc",
            timing=ReadTiming(capture_seconds, ocr_seconds, time.perf_counter() - started),
        )
    except Exception as exc:
        return ScreenReadResult(
            image_path=output_dir / "latest_screen.png",
            raw_text="",
            fields={},
            ocr_available=False,
            source="pc",
            error=str(exc),
            timing=ReadTiming(total_seconds=time.perf_counter() - started),
        )


def read_scrcpy_window(output_dir: Path) -> ScreenReadResult:
    started = time.perf_counter()
    try:
        capture_started = time.perf_counter()
        image_path = capture_scrcpy_window(output_dir)
        capture_seconds = time.perf_counter() - capture_started
        ocr_started = time.perf_counter()
        fields, text = read_tft_mobile_state(image_path, read_shop=True)
        ocr_seconds = time.perf_counter() - ocr_started
        return ScreenReadResult(
            image_path=image_path,
            raw_text=text,
            fields=fields,
            ocr_available=True,
            source="scrcpy",
            timing=ReadTiming(capture_seconds, ocr_seconds, time.perf_counter() - started),
        )
    except Exception as exc:
        return ScreenReadResult(
            image_path=output_dir / "latest_scrcpy_screen.png",
            raw_text="",
            fields={},
            ocr_available=False,
            source="scrcpy",
            error=str(exc),
            timing=ReadTiming(total_seconds=time.perf_counter() - started),
        )


def read_android_screen(output_dir: Path, device_id: str = "") -> ScreenReadResult:
    started = time.perf_counter()
    try:
        capture_started = time.perf_counter()
        image_path = capture_android_screen(output_dir, device_id=device_id)
        capture_seconds = time.perf_counter() - capture_started
    except Exception as exc:
        return ScreenReadResult(
            image_path=output_dir / "latest_android_screen.png",
            raw_text="",
            fields={},
            ocr_available=False,
            source="android",
            error=str(exc),
            timing=ReadTiming(total_seconds=time.perf_counter() - started),
        )

    try:
        ocr_started = time.perf_counter()
        mobile_fields, mobile_text = read_tft_mobile_state(image_path, read_shop=True)
        ocr_seconds = time.perf_counter() - ocr_started
        return ScreenReadResult(
            image_path=image_path,
            raw_text=mobile_text,
            fields=mobile_fields,
            ocr_available=True,
            source="android",
            timing=ReadTiming(capture_seconds, ocr_seconds, time.perf_counter() - started),
        )
    except Exception as exc:
        return ScreenReadResult(
            image_path=image_path,
            raw_text="",
            fields={},
            ocr_available=False,
            source="android",
            error=str(exc),
            timing=ReadTiming(capture_seconds, total_seconds=time.perf_counter() - started),
        )


def read_tft_mobile_state(image_path: Path, read_shop: bool = False) -> tuple[dict[str, str], str]:
    image = Image.open(image_path).convert("RGB")
    fields: dict[str, str] = {}
    debug_dir = image_path.parent / "debug_crops"

    with ThreadPoolExecutor(max_workers=3) as executor:
        stage_future = executor.submit(_read_mobile_stage, image.copy(), debug_dir)
        gold_future = executor.submit(_read_mobile_gold, image.copy(), debug_dir)
        level_future = executor.submit(
            _ocr_region,
            image.copy(),
            (385, 1160, 445, 1245),
            psm=7,
            whitelist="0123456789",
            scale=6,
            threshold=120,
            debug_path=debug_dir / "level.png",
            region_name="Level",
        )

        stage = stage_future.result()
        gold = gold_future.result()
        level = level_future.result()

    if stage:
        fields["stage"] = stage

    gold_match = re.search(r"\d{1,3}", gold)
    if gold_match:
        fields["gold"] = gold_match.group(0)

    level_match = re.search(r"\d{1,2}", level)
    if level_match:
        fields["level"] = level_match.group(0)

    summary = [
        "TFT Mobile fast structured read:",
        f"Stage: {fields.get('stage', '?')}",
        f"Gold: {fields.get('gold', '?')}",
        f"Level: {fields.get('level', '?')}",
    ]

    if read_shop:
        shop_units = _read_mobile_shop(image)
        if shop_units:
            summary.append("Shop: " + ", ".join(shop_units))

    try:
        bench_boxes = load_custom_bench_boxes(image.size)
        if bench_boxes is not None:
            occupied_count, is_full, occupied_slots, yolo_names, detected_yolo_boxes = _detect_bench_occupancy(image)
            fields["bench_full"] = is_full
            fields["bench_occupancy"] = ",".join("1" if x else "0" for x in occupied_slots)
            fields["bench_champions"] = ",".join(x if x else "None" for x in yolo_names)
            
            # Tự động vẽ HUD nhãn đối tượng lên ảnh gốc
            try:
                _draw_bench_hud(image, bench_boxes, yolo_names, detected_yolo_boxes)
                image.save(image_path)
            except Exception as draw_exc:
                pass
            
            yolo_info = ""
            detected_champs = [x for x in yolo_names if x is not None]
            if detected_champs:
                yolo_info = f" (YOLO: {', '.join(detected_champs)})"
                
            summary.append(f"Bench: {occupied_count}/9 occupied (Full: {is_full}){yolo_info}")
    except Exception as exc:
        summary.append(f"Bench detection error: {exc}")

    return fields, "\n".join(summary)
