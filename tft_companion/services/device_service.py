from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from PIL import Image

from tft_companion.services.window_service import (
    list_visible_window_titles,
    _find_process_window_handle,
    _find_window_handle,
    _bring_window_to_front,
    _client_rect_for_window,
    _find_window_client_rect,
)

_cached_scrcpy = None
_cached_adb = None


def find_adb() -> str | None:
    global _cached_adb
    if _cached_adb is not None:
        return _cached_adb

    adb_path = shutil.which("adb")
    if adb_path:
        _cached_adb = adb_path
        return adb_path

    # Check next to scrcpy if available
    scrcpy_path = find_scrcpy()
    if scrcpy_path:
        adb_next_to_scrcpy = scrcpy_path.parent / "adb.exe"
        if adb_next_to_scrcpy.exists():
            _cached_adb = str(adb_next_to_scrcpy)
            return _cached_adb

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
            _cached_adb = str(candidate)
            return _cached_adb
    return None


def find_scrcpy() -> Path | None:
    global _cached_scrcpy
    if _cached_scrcpy is not None:
        return _cached_scrcpy

    scrcpy_path = shutil.which("scrcpy")
    if scrcpy_path:
        _cached_scrcpy = Path(scrcpy_path)
        return scrcpy_path

    # Local workspace path candidate
    local_scrcpy = Path(__file__).resolve().parents[2] / "scrcpy-win64" / "scrcpy.exe"
    if local_scrcpy.exists():
        _cached_scrcpy = local_scrcpy
        return local_scrcpy

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
            _cached_scrcpy = candidate
            return candidate
    return None


def list_android_devices() -> list[str]:
    adb_path = find_adb()
    if not adb_path:
        return []

    try:
        completed = subprocess.run(
            [adb_path, "devices"],
            check=True,
            capture_output=True,
            timeout=5,
        )
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        lines = stdout.splitlines()[1:]
        devices: list[str] = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices
    except Exception:
        return []


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
        "--window-x=0",
        "--window-y=0",
        "--window-width=1600",
        "--window-height=740",
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
    
    import ctypes
    user32 = ctypes.windll.user32
    prev_hwnd = user32.GetForegroundWindow()

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

    try:
        with mss.mss() as sct:
            shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
            image = Image.frombytes("RGB", shot.size, shot.rgb)
            image.save(image_path)
    finally:
        if hwnd and prev_hwnd and prev_hwnd != hwnd:
            user32.SetForegroundWindow(prev_hwnd)
            
    return image_path
