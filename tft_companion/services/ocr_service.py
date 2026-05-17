from __future__ import annotations

import re
import shutil
import difflib
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageChops

_cached_tesseract = None
_cached_champions_list: list[str] = []


def find_tesseract() -> Path | None:
    global _cached_tesseract
    if _cached_tesseract is not None:
        return _cached_tesseract

    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        _cached_tesseract = Path(tesseract_path)
        return _cached_tesseract

    candidates = [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            _cached_tesseract = candidate
            return candidate
    return None


def read_image(image_path: Path, source: str) -> ScreenReadResult:
    from tft_companion.models.screen import ScreenReadResult
    raw_text = ""

    try:
        import pytesseract

        tesseract_path = find_tesseract()
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)

        image = Image.open(image_path)
        raw_text = pytesseract.image_to_string(image)
        return ScreenReadResult(
            image_path=image_path,
            raw_text=raw_text,
            fields=parse_tft_text(raw_text),
            ocr_available=True,
            source=source,
        )
    except Exception as exc:
        return ScreenReadResult(
            image_path=image_path,
            raw_text=raw_text,
            fields={},
            ocr_available=False,
            source=source,
            error=str(exc),
        )


def parse_tft_text(text: str) -> dict[str, str]:
    normalized = " ".join(text.replace("\n", " ").split())
    fields: dict[str, str] = {}

    stage = re.search(r"\b([2-7])\s*[-:]\s*([1-7])\b", normalized)
    if stage:
        fields["stage"] = f"{stage.group(1)}-{stage.group(2)}"

    level = re.search(r"\b(?:level|lvl|cap)\s*(\d{1,2})\b", normalized, re.IGNORECASE)
    if level:
        fields["level"] = level.group(1)

    gold = re.search(r"\b(?:gold|g)\s*(\d{1,3})\b", normalized, re.IGNORECASE)
    if gold:
        fields["gold"] = gold.group(1)

    hp = re.search(r"\b(?:hp|health|life)\s*(\d{1,3})\b", normalized, re.IGNORECASE)
    if hp:
        fields["hp"] = hp.group(1)

    return fields


def load_custom_ocr_box(
    region: str, image_size: tuple[int, int], default_box: tuple[int, int, int, int] | None = None
) -> tuple[int, int, int, int] | None:
    import configparser
    config_path = Path(__file__).resolve().parents[2] / "tft_companion" / "config" / "ocr_coords.ini"
    if not config_path.exists():
        return default_box

    try:
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        if region not in config or 'Resolution' not in config:
            return default_box

        # Read coordinates
        l = int(config[region]['left'])
        t = int(config[region]['top'])
        r = int(config[region]['right'])
        b = int(config[region]['bottom'])

        # Read baseline resolution
        base_w = int(config['Resolution']['width'])
        base_h = int(config['Resolution']['height'])

        # If image resolution matches baseline, return directly
        img_w, img_h = image_size
        if base_w == img_w and base_h == img_h:
            return (l, t, r, b)

        # Scale coordinates if resolutions are different!
        x_scale = img_w / base_w
        y_scale = img_h / base_h
        return (
            int(l * x_scale),
            int(t * y_scale),
            int(r * x_scale),
            int(b * y_scale),
        )
    except Exception:
        return default_box


def _extract_white_pixels(img: Image.Image, min_val: int = 190) -> Image.Image:
    rgb_img = img.convert("RGB")
    r, g, b = rgb_img.split()
    r_mask = r.point(lambda p: 255 if p > min_val else 0)
    g_mask = g.point(lambda p: 255 if p > min_val else 0)
    b_mask = b.point(lambda p: 255 if p > min_val else 0)
    mask = ImageChops.darker(ImageChops.darker(r_mask, g_mask), b_mask)
    return ImageOps.invert(mask)


def _ocr_region(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    psm: int,
    scale: int,
    whitelist: str | None = None,
    threshold: int | None = None,
    debug_path: Path | None = None,
    region_name: str | None = None,
    extract_white: bool = False,
    white_min_val: int = 190,
    crop_box: tuple[int, int, int, int] | None = None,
) -> str:
    custom_box = crop_box
    if custom_box is None and region_name:
        custom_box = load_custom_ocr_box(region_name, image.size)
        
    if custom_box is not None:
        crop = image.crop(custom_box)
    else:
        crop = image.crop(_scale_mobile_box(image, box))
        
    crop = crop.resize((crop.width * scale, crop.height * scale))
    
    if extract_white:
        crop = _extract_white_pixels(crop, white_min_val)
    else:
        crop = ImageOps.grayscale(crop)
        if threshold is not None:
            crop = crop.point(lambda p: 255 if p > threshold else 0)
        else:
            crop = ImageEnhance.Contrast(crop).enhance(2.0)

    if debug_path:
        try:
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            crop.save(debug_path)
        except Exception:
            pass

    import pytesseract

    tesseract_path = find_tesseract()
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)

    config = f"--psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"
    return pytesseract.image_to_string(crop, config=config).strip()


def _scale_mobile_box(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    base_width = 2772
    base_height = 1280
    width, height = image.size
    x_scale = width / base_width
    y_scale = height / base_height
    return (
        int(box[0] * x_scale),
        int(box[1] * y_scale),
        int(box[2] * x_scale),
        int(box[3] * y_scale),
    )


def _get_champions_list() -> list[str]:
    global _cached_champions_list
    if _cached_champions_list:
        return _cached_champions_list
        
    try:
        root_dir = Path(__file__).resolve().parents[2]
        ini_paths = list(root_dir.glob("**/champions.ini"))
        if ini_paths:
            path = ini_paths[0]
            names = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("name ="):
                        name = line.split("=", 1)[1].strip()
                        if name and name not in names:
                            names.append(name)
            if names:
                _cached_champions_list = names
                return names
    except Exception:
        pass

    # Fallback list
    return [
        "Ahri", "Amumu", "Blitzcrank", "Darius", "Elise", "Jax", "Lillia", "Lux", "Poppy", 
        "Singed", "Vayne", "Zeri", "Ziggs", "Ashe", "Camille", "Diana", "Ezreal", "Gnar", 
        "Katarina", "KogMaw", "Leona", "Nidalee", "Nunu", "Rell", "Shen", "Syndra", "Talon", 
        "DrMundo", "Ekko", "Hecarim", "Illaoi", "Janna", "Kassadin", "KhaZix", "Morgana", 
        "Nami", "Neeko", "Renekton", "Riven", "Swain", "Vex", "Caitlyn", "Garen", 
        "Heimerdinger", "KaiSa", "Lucian", "Nautilus", "Olaf", "Ornn", "Pyke", "Silco", 
        "TahmKench", "Taric", "Jayce", "Jinx", "Leblanc", "Milio", "Rum", "Ryze", 
        "Sion", "Twitch", "Udyr", "Viego", "Wukong", "Xerath", "Yasuo"
    ]


def _clean_unit_name(text: str) -> str:
    text = re.sub(r"[^A-Za-z .'-]", "", text)
    text = " ".join(text.split())
    if not text:
        return ""
        
    champs = _get_champions_list()
    matches = difflib.get_close_matches(text, champs, n=1, cutoff=0.55)
    if matches:
        return matches[0]
    return text.strip().title()


def _read_mobile_stage(image: Image.Image, debug_dir: Path | None = None) -> str:
    custom_stage_shop = load_custom_ocr_box("Stage_Shop", image.size)
    if custom_stage_shop is not None:
        text = _ocr_region(
            image,
            (0, 0, 0, 0),
            psm=7,
            whitelist="0123456789-",
            scale=5,
            threshold=None,
            debug_path=debug_dir / "stage_shop_custom.png" if debug_dir else None,
            region_name="Stage_Shop",
        )
        matches = re.findall(r"\d-\d", text)
        if matches:
            return matches[-1]

    custom_stage_combat = load_custom_ocr_box("Stage_Combat", image.size)
    if custom_stage_combat is not None:
        text = _ocr_region(
            image,
            (0, 0, 0, 0),
            psm=7,
            whitelist="0123456789-",
            scale=5,
            threshold=None,
            debug_path=debug_dir / "stage_combat_custom.png" if debug_dir else None,
            region_name="Stage_Combat",
        )
        matches = re.findall(r"\d-\d", text)
        if matches:
            return matches[-1]

    candidate_boxes = [
        (780, 0, 875, 58),
        (755, 0, 900, 62),
        (725, 0, 950, 68),
    ]
    for i, box in enumerate(candidate_boxes):
        text = _ocr_region(
            image,
            box,
            psm=7,
            whitelist="0123456789-",
            scale=5,
            threshold=None,
            debug_path=debug_dir / f"stage_{i}.png" if debug_dir else None,
        )
        matches = re.findall(r"\d-\d", text)
        if matches:
            return matches[-1]
    return ""


def _read_mobile_gold(image: Image.Image, debug_dir: Path | None = None) -> str:
    custom_gold_shop = load_custom_ocr_box("Gold_Shop", image.size)
    if custom_gold_shop is not None:
        for mode in [("white", 190), ("white", 160), ("normal", None), ("normal", 180)]:
            style, val = mode
            text = _ocr_region(
                image,
                (0, 0, 0, 0),
                psm=7,
                whitelist="0123456789",
                scale=6,
                threshold=val if style == "normal" else None,
                debug_path=debug_dir / f"gold_shop_custom_{style}_{val}.png" if debug_dir else None,
                region_name="Gold_Shop",
                extract_white=(style == "white"),
                white_min_val=val if style == "white" else 190,
            )
            match = re.search(r"\d{1,3}", text)
            if match:
                return match.group(0)

    custom_gold_combat = load_custom_ocr_box("Gold_Combat", image.size)
    if custom_gold_combat is not None:
        for mode in [("white", 190), ("white", 160), ("normal", None), ("normal", 180)]:
            style, val = mode
            text = _ocr_region(
                image,
                (0, 0, 0, 0),
                psm=7,
                whitelist="0123456789",
                scale=6,
                threshold=val if style == "normal" else None,
                debug_path=debug_dir / f"gold_combat_custom_{style}_{val}.png" if debug_dir else None,
                region_name="Gold_Combat",
                extract_white=(style == "white"),
                white_min_val=val if style == "white" else 190,
            )
            match = re.search(r"\d{1,3}", text)
            if match:
                return match.group(0)

    candidate_boxes = [
        ((1890, 0, 2025, 80), None, "shop"),
        ((2485, 1100, 2565, 1205), 180, "combat_1"),
        ((2490, 1090, 2570, 1210), 180, "combat_2"),
    ]
    for i, (box, threshold, label) in enumerate(candidate_boxes):
        for mode in [("white", 190), ("normal", threshold)]:
            style, val = mode
            text = _ocr_region(
                image,
                box,
                psm=7,
                whitelist="0123456789",
                scale=6,
                threshold=val if style == "normal" else None,
                debug_path=debug_dir / f"gold_{label}_{style}_{val}.png" if debug_dir else None,
                extract_white=(style == "white"),
                white_min_val=val if style == "white" else 190,
            )
            match = re.search(r"\d{1,3}", text)
            if match:
                return match.group(0)
    return ""


def load_custom_shop_boxes(image_size: tuple[int, int]) -> list[tuple[int, int, int, int]] | None:
    box0 = load_custom_ocr_box("Shop_Card_0_Name", image_size)
    box4 = load_custom_ocr_box("Shop_Card_4_Name", image_size)
    
    if box0 is None or box4 is None:
        return None
        
    l0, t0, r0, b0 = box0
    l4, t4, r4, b4 = box4
    
    w0 = r0 - l0
    h0 = b0 - t0
    
    x_step = (l4 - l0) / 4.0
    y_step = (t4 - t0) / 4.0
    
    boxes = []
    for i in range(5):
        li = int(l0 + i * x_step)
        ti = int(t0 + i * y_step)
        ri = li + w0
        bi = ti + h0
        boxes.append((li, ti, ri, bi))
    return boxes


def load_custom_bench_boxes(image_size: tuple[int, int]) -> list[tuple[int, int, int, int]] | None:
    box0 = load_custom_ocr_box("Bench_Slot_0", image_size)
    box8 = load_custom_ocr_box("Bench_Slot_8", image_size)
    
    if box0 is None or box8 is None:
        return None
        
    l0, t0, r0, b0 = box0
    l8, t8, r8, b8 = box8
    
    w0 = r0 - l0
    h0 = b0 - t0
    
    x_step = (l8 - l0) / 8.0
    y_step = (t8 - t0) / 8.0
    
    boxes = []
    for i in range(9):
        li = int(l0 + i * x_step)
        ti = int(t0 + i * y_step)
        ri = li + w0
        bi = ti + h0
        boxes.append((li, ti, ri, bi))
    return boxes


def _read_mobile_shop(image: Image.Image) -> list[str]:
    custom_boxes = load_custom_shop_boxes(image.size)
    
    # 5 candidates for fallback shop card names (scaled boxes)
    default_names = [
        (480, 1170, 710, 1225),
        (915, 1170, 1145, 1225),
        (1350, 1170, 1580, 1225),
        (1785, 1170, 2015, 1225),
        (2220, 1170, 2450, 1225),
    ]
    # 5 candidates for shop card gold/costs
    default_costs = [
        (480, 1225, 710, 1265),
        (915, 1225, 1145, 1265),
        (1350, 1225, 1580, 1265),
        (1785, 1225, 2015, 1265),
        (2220, 1225, 2450, 1265),
    ]

    debug_dir = image.filename.parent / "debug_crops" if hasattr(image, 'filename') and image.filename else None
    if not debug_dir:
        debug_dir = Path(__file__).resolve().parents[2] / "screenshots" / "debug_crops"
    debug_dir.mkdir(parents=True, exist_ok=True)

    units = []
    for i in range(5):
        # 1. Quét tên tướng
        raw_name = _ocr_region(
            image,
            default_names[i],
            psm=7,
            whitelist=None,
            scale=5,
            debug_path=debug_dir / f"shop_name_{i}.png",
            extract_white=True,
            white_min_val=185,  # Tối ưu lọc chữ trắng cực mạnh
            crop_box=custom_boxes[i] if custom_boxes else None,
        )
        
        # 2. Quét giá tiền (Cost)
        cost_box = default_costs[i]
        if custom_boxes:
            # Tính tương quan giá tiền so với ô tên tướng đã căn chỉnh
            # Chiều rộng giữ nguyên, dịch chuyển chiều cao xuống một khoảng
            li, ti, ri, bi = custom_boxes[i]
            h = bi - ti
            cost_box = (li, bi - 5, ri, bi + int(h * 0.75))
            
        raw_cost = _ocr_region(
            image,
            cost_box,
            psm=7,
            whitelist="0123456789gG",
            scale=5,
            debug_path=debug_dir / f"shop_cost_{i}.png",
            crop_box=cost_box if custom_boxes else None,
        )

        name = _clean_unit_name(raw_name)
        cost_match = re.search(r"[1-5]", raw_cost)
        
        if name and cost_match:
            units.append(f"{name} ({cost_match.group(0)}g)")
        elif name:
            units.append(name)
    return units
