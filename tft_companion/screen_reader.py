from __future__ import annotations

import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps


@dataclass(frozen=True)
class ScreenReadResult:
    image_path: Path
    raw_text: str
    fields: dict[str, str]
    ocr_available: bool
    source: str = "pc"
    error: str = ""


def capture_screen(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / "latest_screen.png"

    try:
        import mss

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.rgb)
            image.save(image_path)
    except Exception:
        from PIL import ImageGrab

        image = ImageGrab.grab()
        image.save(image_path)

    return image_path


def read_screen(output_dir: Path) -> ScreenReadResult:
    image_path = capture_screen(output_dir)
    return read_image(image_path, source="pc")


def capture_android_screen(output_dir: Path, device_id: str = "") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / "latest_android_screen.png"

    adb_path = find_adb()
    if not adb_path:
        raise RuntimeError("ADB was not found in PATH. Install Android platform-tools first.")

    command = [adb_path]
    if device_id.strip():
        command.extend(["-s", device_id.strip()])
    command.extend(["exec-out", "screencap", "-p"])

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        timeout=15,
    )
    if completed.returncode != 0:
        error = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or "ADB screencap failed. Check USB debugging and device authorization.")

    image_path.write_bytes(completed.stdout)
    return image_path


def start_scrcpy_mirror(device_id: str = "") -> None:
    scrcpy_path = find_scrcpy()
    if not scrcpy_path:
        raise RuntimeError("scrcpy.exe was not found. Install scrcpy or add it to PATH.")

    command = [
        str(scrcpy_path),
        "--no-control",
        "--window-title=TFT-Mobile-Mirror",
    ]
    if device_id.strip():
        command.append(f"--serial={device_id.strip()}")

    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def capture_scrcpy_window(output_dir: Path, title_keyword: str = "TFT-Mobile-Mirror") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / "latest_scrcpy_screen.png"
    hwnd = _find_process_window_handle("scrcpy") or _find_window_handle(title_keyword)
    if hwnd:
        _bring_window_to_front(hwnd)
        time.sleep(0.08)
        rect = _client_rect_for_window(hwnd)
    else:
        rect = _find_window_client_rect(title_keyword) or _find_window_client_rect("scrcpy")
    if not rect:
        titles = "\n".join(list_visible_window_titles()[:20])
        raise RuntimeError(f"Could not find a visible scrcpy mirror window.\nVisible windows:\n{titles}")

    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise RuntimeError("scrcpy window is minimized or has an invalid size.")

    import mss

    with mss.mss() as sct:
        shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        image.save(image_path)
    return image_path


def read_scrcpy_window(output_dir: Path) -> ScreenReadResult:
    try:
        image_path = capture_scrcpy_window(output_dir)
        fields, text = read_tft_mobile_state(image_path, read_shop=False)
        return ScreenReadResult(
            image_path=image_path,
            raw_text=text,
            fields=fields,
            ocr_available=True,
            source="scrcpy",
        )
    except Exception as exc:
        return ScreenReadResult(
            image_path=output_dir / "latest_scrcpy_screen.png",
            raw_text="",
            fields={},
            ocr_available=False,
            source="scrcpy",
            error=str(exc),
        )


def read_android_screen(output_dir: Path, device_id: str = "") -> ScreenReadResult:
    try:
        image_path = capture_android_screen(output_dir, device_id=device_id)
    except Exception as exc:
        return ScreenReadResult(
            image_path=output_dir / "latest_android_screen.png",
            raw_text="",
            fields={},
            ocr_available=False,
            source="android",
            error=str(exc),
        )

    try:
        mobile_fields, mobile_text = read_tft_mobile_state(image_path, read_shop=False)
        return ScreenReadResult(
            image_path=image_path,
            raw_text=mobile_text,
            fields=mobile_fields,
            ocr_available=True,
            source="android",
        )
    except Exception as exc:
        return ScreenReadResult(
            image_path=image_path,
            raw_text="",
            fields={},
            ocr_available=False,
            source="android",
            error=str(exc),
        )


def list_android_devices() -> list[str]:
    adb_path = find_adb()
    if not adb_path:
        return []

    completed = subprocess.run(
        [adb_path, "devices"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if completed.returncode != 0:
        return []

    devices: list[str] = []
    for line in completed.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def read_image(image_path: Path, source: str) -> ScreenReadResult:
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


def read_tft_mobile_state(image_path: Path, read_shop: bool = False) -> tuple[dict[str, str], str]:
    image = Image.open(image_path).convert("RGB")
    fields: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=3) as executor:
        stage_future = executor.submit(_read_mobile_stage, image.copy())
        gold_future = executor.submit(
            _ocr_region,
            image.copy(),
            (1890, 0, 2025, 80),
            psm=10,
            whitelist="0123456789",
            scale=6,
            threshold=None,
        )
        level_future = executor.submit(
            _ocr_region,
            image.copy(),
            (360, 1120, 460, 1270),
            psm=10,
            whitelist="0123456789",
            scale=6,
            threshold=120,
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

    return fields, "\n".join(summary)


def _read_mobile_stage(image: Image.Image) -> str:
    # Stage text is near the top center, but it shifts a little between devices.
    # Try small crops first to avoid the gold value and progress bar.
    candidate_boxes = [
        (780, 0, 875, 58),
        (755, 0, 900, 62),
        (725, 0, 950, 68),
    ]
    for box in candidate_boxes:
        text = _ocr_region(
            image,
            box,
            psm=7,
            whitelist="0123456789-",
            scale=5,
            threshold=None,
        )
        matches = re.findall(r"\d-\d", text)
        if matches:
            return matches[-1]
    return ""


def _read_mobile_shop(image: Image.Image) -> list[str]:
    name_boxes = [
        (650, 445, 880, 505),
        (1050, 445, 1260, 505),
        (1445, 445, 1680, 505),
        (1840, 445, 2030, 505),
        (2240, 445, 2440, 505),
    ]
    cost_boxes = [
        (935, 452, 1010, 500),
        (1325, 452, 1405, 500),
        (1720, 452, 1800, 500),
        (2115, 452, 2195, 500),
        (2510, 452, 2590, 500),
    ]

    units: list[str] = []
    for name_box, cost_box in zip(name_boxes, cost_boxes):
        name = _ocr_region(image, name_box, psm=7, scale=4, threshold=None)
        name = _clean_unit_name(name)
        cost = _ocr_region(
            image,
            cost_box,
            psm=7,
            whitelist="0123456789",
            scale=5,
            threshold=145,
        )
        cost_match = re.search(r"\d", cost)
        if name and cost_match:
            units.append(f"{name} ({cost_match.group(0)}g)")
        elif name:
            units.append(name)
    return units


def _ocr_region(
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    psm: int,
    scale: int,
    whitelist: str | None = None,
    threshold: int | None = None,
) -> str:
    crop = image.crop(_scale_mobile_box(image, box))
    crop = crop.resize((crop.width * scale, crop.height * scale))
    crop = ImageOps.grayscale(crop)
    if threshold is not None:
        crop = crop.point(lambda p: 255 if p > threshold else 0)
    else:
        crop = ImageEnhance.Contrast(crop).enhance(2.0)

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


def _clean_unit_name(text: str) -> str:
    text = re.sub(r"[^A-Za-z .'-]", "", text)
    text = " ".join(text.split())
    compact = text.replace(" ", "")
    if compact.lower() == "aatrox":
        return "Aatrox"
    return text.strip()


def find_adb() -> str | None:
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path

    candidates = [
        Path.home()
        / "AppData"
        / "Local"
        / "Microsoft"
        / "WinGet"
        / "Packages"
        / "Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "platform-tools"
        / "adb.exe",
        Path.home() / "Downloads" / "xiaomi" / "xiaomi" / "scrcpy-win64-v1.25" / "adb.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def find_tesseract() -> Path | None:
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        return Path(tesseract_path)

    candidates = [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def find_scrcpy() -> Path | None:
    scrcpy_path = shutil.which("scrcpy")
    if scrcpy_path:
        return Path(scrcpy_path)

    candidates = [
        Path.home()
        / "AppData"
        / "Local"
        / "Microsoft"
        / "WinGet"
        / "Packages"
        / "Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "scrcpy-win64-v4.0"
        / "scrcpy.exe",
        Path.home()
        / "AppData"
        / "Local"
        / "Microsoft"
        / "WinGet"
        / "Packages"
        / "Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe"
        / "scrcpy-win64-v3.3.3"
        / "scrcpy.exe",
        Path.home() / "Downloads" / "xiaomi" / "xiaomi" / "scrcpy-win64-v1.25" / "scrcpy.exe",
        Path("C:/Program Files/scrcpy/scrcpy.exe"),
        Path("C:/Program Files (x86)/scrcpy/scrcpy.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def list_visible_window_titles() -> list[str]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    titles: list[str] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if title:
            titles.append(title)
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return titles


def _find_window_client_rect(title_keyword: str) -> tuple[int, int, int, int] | None:
    if not title_keyword:
        return None

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    matches: list[tuple[int, int, int, int]] = []

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value
        if title_keyword.lower() not in title.lower():
            return True

        rect = wintypes.RECT()
        if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
            return True

        point = wintypes.POINT(0, 0)
        if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
            return True

        matches.append(
            (
                int(point.x),
                int(point.y),
                int(point.x + rect.right),
                int(point.y + rect.bottom),
            )
        )
        return False

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return matches[0] if matches else None


def _find_window_handle(title_keyword: str) -> int | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    matches: list[int] = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if title_keyword.lower() in buffer.value.lower():
            matches.append(hwnd)
            return False
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return matches[0] if matches else None


def _find_process_client_rect(process_keyword: str) -> tuple[int, int, int, int] | None:
    hwnd = _find_process_window_handle(process_keyword)
    return _client_rect_for_window(hwnd) if hwnd else None


def _find_process_window_handle(process_keyword: str) -> int | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    matches: list[int] = []

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def get_process_path(pid: int) -> str:
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid)
        if not handle:
            return ""
        try:
            buffer = ctypes.create_unicode_buffer(1024)
            if psapi.GetModuleFileNameExW(handle, None, buffer, len(buffer)):
                return buffer.value
        finally:
            kernel32.CloseHandle(handle)
        return ""

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_path = get_process_path(int(pid.value))
        if process_keyword.lower() not in process_path.lower():
            return True

        rect = _client_rect_for_window(hwnd)
        if not rect:
            return True
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        if width < 200 or height < 200:
            return True

        matches.append(hwnd)
        return False

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return matches[0] if matches else None


def _client_rect_for_window(hwnd: int) -> tuple[int, int, int, int] | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None

    point = wintypes.POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(point)):
        return None

    return (
        int(point.x),
        int(point.y),
        int(point.x + rect.right),
        int(point.y + rect.bottom),
    )


def _bring_window_to_front(hwnd: int) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_SHOWWINDOW = 0x0040
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)


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
