# -*- coding: utf-8 -*-
"""앱 창(pywebview) 모드: 화면 JS 가 Python 을 직접 부르는 브리지와 웹뷰 탐색기 창.
pywebview 는 여기서 import 하지 않는다 (테스트와 브라우저 모드는 pywebview 없이 돈다)."""
from pathlib import Path
from typing import Any, Callable

from .server import ApiError, App


WEBVIEW2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
WEBVIEW2_DOWNLOAD = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
_WEBVIEW2_KEYS = (
    ("HKLM", rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}"),
    ("HKLM", rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}"),
    ("HKCU", rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_GUID}"),
)


def read_registry_version(hive: str, key: str):
    try:
        import winreg
        root = winreg.HKEY_LOCAL_MACHINE if hive == "HKLM" else winreg.HKEY_CURRENT_USER
        with winreg.OpenKey(root, key) as k:
            return winreg.QueryValueEx(k, "pv")[0]
    except (OSError, ImportError):
        return None


def has_webview2(read: Callable[[str, str], Any] = read_registry_version) -> bool:
    """앱 창에 쓰는 Microsoft WebView2 런타임이 깔려 있는지 (윈도우 10/11 대부분 기본 설치)."""
    for hive, key in _WEBVIEW2_KEYS:
        version = read(hive, key)
        if version and version != "0.0.0.0":
            return True
    return False


class Bridge:
    """JS 에서 window.pywebview.api.call(path, payload) 로 부른다. 예외는 JS 로 새지 않게 결과로 바꾼다."""

    def __init__(self, app: App):
        self._app = app  # 밑줄로 시작해야 pywebview 가 JS 쪽에 노출하지 않는다

    def call(self, path: str, payload: Any = None) -> dict:
        if not isinstance(path, str) or not path.startswith("/api/"):
            return {"ok": False, "error": "not found", "status": 404}
        try:
            return {"ok": True, **self._app.call(path, payload if isinstance(payload, dict) else {})}
        except ApiError as e:
            return {"ok": False, "error": str(e), "status": e.status}
        except Exception as e:  # 기능 객체의 오류 메시지는 사용자에게 그대로 보여준다
            return {"ok": False, "error": str(e) or e.__class__.__name__, "status": 500}


class WebviewDialogs:
    """NativeDialogs 와 같은 모양. 웹뷰가 제공하는 윈도우 기본 파일 창을 쓴다."""

    VIDEO_TYPES = ("영상 파일 (*.mp4;*.mov;*.mkv;*.webm;*.avi;*.m4v)", "모든 파일 (*.*)")
    MP4_TYPES = ("MP4 영상 (*.mp4)",)
    IMAGE_TYPES = ("그림 파일 (*.png;*.jpg;*.jpeg;*.gif;*.webp)", "모든 파일 (*.*)")

    def __init__(self, get_window: Callable[[], Any], open_type: Any, save_type: Any):
        self._get_window = get_window
        self._open, self._save = open_type, save_type

    @staticmethod
    def _first(result) -> str:
        if not result:
            return ""
        return str(result if isinstance(result, str) else result[0])

    def open_video(self) -> str:
        return self._first(self._get_window().create_file_dialog(self._open, file_types=self.VIDEO_TYPES))

    def open_image(self) -> str:
        return self._first(self._get_window().create_file_dialog(self._open, file_types=self.IMAGE_TYPES))

    def save_mp4(self, suggest: str) -> str:
        path = self._first(self._get_window().create_file_dialog(
            self._save, save_filename=suggest, file_types=self.MP4_TYPES))
        if path and Path(path).suffix.lower() != ".mp4":
            path = str(Path(path).with_suffix(".mp4"))
        return path
