"""헤드리스 Chrome 을 개발자 프로토콜(CDP)로 조작하는 작은 도우미. 화면 테스트에서만 쓴다."""
import asyncio
import base64
import json
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

BROWSERS = [
    Path(os.environ.get("PROGRAMFILES", "C:/Program Files"), "Google/Chrome/Application/chrome.exe"),
    Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)"), "Microsoft/Edge/Application/msedge.exe"),
]
BROWSER = next((b for b in BROWSERS if b.exists()), None)

try:
    import websockets
except ImportError:  # 빌드용 가상환경 등에는 없을 수 있다
    websockets = None


class HeadlessChrome:
    def __init__(self, port: int = 9337, size=(1600, 1100)):
        self.port = port
        self._proc = subprocess.Popen([str(BROWSER), "--headless=new", f"--remote-debugging-port={port}",
                                       f"--user-data-dir={tempfile.mkdtemp()}", f"--window-size={size[0]},{size[1]}",
                                       "--hide-scrollbars", "about:blank"],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def close(self):
        self._proc.terminate()
        self._proc.wait(10)

    def page_ws(self) -> str:
        for _ in range(100):
            try:
                pages = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=1).read())
                return next(p for p in pages if p["type"] == "page")["webSocketDebuggerUrl"]
            except Exception:
                time.sleep(0.2)
        raise RuntimeError("Chrome 페이지를 찾지 못했습니다")


class Page:
    def __init__(self, ws):
        self._ws, self._n = ws, 0

    async def cmd(self, method, **params):
        self._n += 1
        my = self._n
        await self._ws.send(json.dumps({"id": my, "method": method, "params": params}))
        while True:
            msg = json.loads(await self._ws.recv())
            if msg.get("id") == my:
                return msg.get("result", {})

    async def js(self, expr):
        r = await self.cmd("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        return r.get("result", {}).get("value")

    async def wait_for(self, expr, timeout=60):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if await self.js(expr):
                return
            await asyncio.sleep(0.25)
        raise TimeoutError(expr)

    async def screenshot_element(self, selector, out_width) -> bytes:
        rect = await self.js(f"(() => {{ const r = document.querySelector('{selector}').getBoundingClientRect(); "
                             f"return [r.left, r.top, r.width, r.height]; }})()")
        data = await self.cmd("Page.captureScreenshot", format="png", clip={
            "x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3], "scale": out_width / rect[2]})
        return base64.b64decode(data["data"])
