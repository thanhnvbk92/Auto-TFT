from __future__ import annotations

import ctypes
from ctypes import wintypes


def list_visible_window_titles() -> list[str]:
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
