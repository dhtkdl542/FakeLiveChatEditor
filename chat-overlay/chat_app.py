# -*- coding: utf-8 -*-
"""가짜 라이브 채팅 앱. 실행하면 앱 창이 뜬다.

    python chat_app.py            앱 창 (pywebview, WebView2)
    python chat_app.py --browser  기본 브라우저로 열기 (개발용, WebView2 가 없을 때 자동 사용)

여기서는 객체를 조립하고 창을 띄우기만 한다. 기능은 chatov 패키지에 있다."""
import os
import sys
import tempfile
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Optional, Tuple

from chatov.files import StaticFiles, VideoRegistry
from chatov.jobs import JobRunner
from chatov.llm import LlmService
from chatov.media import FFmpeg, FontCollector, OverlayRenderer
from chatov.native import WEBVIEW2_DOWNLOAD, Bridge, WebviewDialogs, has_webview2
from chatov.ollama import (OllamaApi, OllamaInstaller, OllamaLauncher, OllamaLocator, OllamaManager,
                           UrlDownloader, run_and_wait)
from chatov.paths import AppPaths, ToolLocator
from chatov.server import App, make_handler
from chatov.transport import HttpTransport

APP_TITLE = "가짜 라이브 채팅"
PATHS = AppPaths.detect(frozen=getattr(sys, "frozen", False), executable=sys.executable,
                        meipass=getattr(sys, "_MEIPASS", None), source_dir=Path(__file__).resolve().parent)


def build_app(paths: AppPaths = PATHS, dialogs=None) -> App:
    if dialogs is None:
        from chatov.dialogs import NativeDialogs
        dialogs = NativeDialogs()
    transport = HttpTransport()
    ffmpeg = FFmpeg(which=ToolLocator(paths.tool_dirs))
    api = OllamaApi(transport)
    locator = OllamaLocator(os.environ)
    launcher = OllamaLauncher(api, locator)
    installer = OllamaInstaller(launcher, UrlDownloader().download, run_and_wait, Path(tempfile.gettempdir()))
    return App(
        static=StaticFiles(paths.web_root),
        videos=VideoRegistry(),
        dialogs=dialogs,
        probe=ffmpeg,
        renderer=OverlayRenderer(ffmpeg, FontCollector([paths.app_dir])),
        llm=LlmService(transport),
        ollama=OllamaManager(api, locator, launcher, installer, JobRunner()),
    )


def start_server(app: App, allow_post: bool, port: int = 0) -> Tuple[ThreadingHTTPServer, str]:
    """내 PC 안에서만 접속되는 서버를 빈 포트로 띄운다. 앱 창 모드에서는 화면 파일과 영상만 내보낸다."""
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, allow_post=allow_post, log=allow_post))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


def run_browser(reason: Optional[str] = None) -> None:
    server, url = start_server(build_app(), allow_post=True)
    if reason:
        print(reason)
    print(f"브라우저를 엽니다: {url}")
    print("이 창은 닫지 마세요. 끝나면 창만 닫으면 됩니다.")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()


def show_message(text: str) -> None:
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, APP_TITLE, 0x40)
    except Exception:
        print(text)


def run_native(webview=None, exit_fn=os._exit) -> None:
    if webview is None:
        import webview

    holder = {}
    app = build_app(dialogs=WebviewDialogs(lambda: holder["window"], webview.FileDialog.OPEN, webview.FileDialog.SAVE))
    server, url = start_server(app, allow_post=False)
    holder["window"] = webview.create_window(APP_TITLE, url + "?native=1", js_api=Bridge(app),
                                             width=1500, height=950, min_size=(980, 640), background_color="#0e1016")
    try:
        webview.start(gui="edgechromium", private_mode=False,
                      storage_path=str(Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "FakeLiveChat"))
    finally:
        server.shutdown()
        server.server_close()
    # 창이 닫히면 바로 끝낸다. pywebview 의 .NET 런타임(pythonnet)은 파이썬이 정리하며 끝날 때 가끔 예외를 낸다.
    exit_fn(0)


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if not (PATHS.web_root / "index.html").exists():
        show_message(f"화면 파일이 없습니다: {PATHS.web_root}")
        return
    if "--browser" in argv:
        run_browser()
        return
    if not has_webview2():
        show_message("이 PC에는 앱 창에 필요한 Microsoft WebView2 가 없어서 기본 브라우저로 엽니다.\n"
                     f"앱 창으로 쓰려면 WebView2 를 설치하세요:\n{WEBVIEW2_DOWNLOAD}")
        webbrowser.open(WEBVIEW2_DOWNLOAD)
        run_browser()
        return
    try:
        import webview  # noqa: F401
    except ImportError:
        run_browser("pywebview 가 없어 브라우저로 엽니다. (pip install pywebview)")
        return
    run_native()


if __name__ == "__main__":
    main()
