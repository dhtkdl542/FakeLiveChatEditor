# -*- coding: utf-8 -*-
"""HTTP 요청을 각 기능 객체로 연결한다. App 은 소켓 없이 테스트할 수 있게 순수한 요청→응답 변환만 한다."""
import json
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Mapping, Optional
from urllib.parse import urlparse

from .files import ByteRange, RangeNotSatisfiable, StaticFiles, VideoRegistry, mime_for


@dataclass
class Response:
    status: int
    body: bytes = b""
    ctype: str = "text/plain; charset=utf-8"
    file: Optional[Path] = None           # 영상처럼 파일을 그대로 흘려보낼 때
    byte_range: Optional[ByteRange] = None
    headers: dict = field(default_factory=dict)

    @classmethod
    def json(cls, data: dict, status: int = 200) -> "Response":
        return cls(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    @classmethod
    def text(cls, message: str, status: int) -> "Response":
        return cls(status, message.encode("utf-8", "replace"))


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".gif", ".webp")


class App:
    def __init__(self, static: StaticFiles, videos: VideoRegistry, dialogs, probe, renderer, llm, ollama,
                 images: VideoRegistry = None):
        self.static = static
        self.videos = videos
        self.images = images or VideoRegistry(prefix="/media/")
        self.dialogs = dialogs
        self.probe = probe
        self.renderer = renderer
        self.llm = llm
        self.ollama = ollama

    # ---------- GET ----------
    def get(self, path: str, headers: Mapping[str, str]) -> Response:
        for registry in (self.videos, self.images):
            file = registry.resolve_url(path)
            if file is not None:
                return self._video(file, headers.get("Range", ""))
        found = self.static.resolve(path)
        if not found:
            return Response.text("not found", 404)
        file, ctype = found
        return Response(200, file.read_bytes(), ctype, headers={"Cache-Control": "no-cache"})

    def _video(self, video: Path, range_header: str) -> Response:
        if not video.exists():
            return Response.text("not found", 404)
        size = video.stat().st_size
        try:
            rng = ByteRange.parse(range_header, size)
        except RangeNotSatisfiable:
            return Response(416, headers={"Content-Range": f"bytes */{size}"})
        headers = {"Accept-Ranges": "bytes"}
        if rng.partial:
            headers["Content-Range"] = rng.content_range
        return Response(206 if rng.partial else 200, ctype=mime_for(video), file=video, byte_range=rng,
                        headers=headers)

    # ---------- POST ----------
    @staticmethod
    def _check_same_site(headers: Mapping[str, str]) -> None:
        """다른 웹사이트가 이 앱에 요청을 보내 설치·삭제를 일으키지 못하게 막는다."""
        if "application/json" not in (headers.get("Content-Type") or ""):
            raise ApiError(415, "JSON 요청만 받습니다.")
        if (headers.get("Sec-Fetch-Site") or "") == "cross-site":
            raise ApiError(403, "다른 사이트의 요청은 받지 않습니다.")
        origin = headers.get("Origin")
        if origin and urlparse(origin).netloc != (headers.get("Host") or ""):
            raise ApiError(403, "다른 사이트의 요청은 받지 않습니다.")

    def call(self, path: str, payload: dict) -> dict:
        """API 하나를 실행한다. HTTP(브라우저 모드)와 브리지(앱 창 모드)가 함께 쓴다."""
        return self._route(path, payload or {})

    def post(self, path: str, headers: Mapping[str, str], raw: bytes) -> Response:
        try:
            self._check_same_site(headers)
            try:
                payload = json.loads(raw.decode("utf-8") or "{}") if raw else {}
            except ValueError:
                raise ApiError(400, "JSON 형식이 잘못됐습니다.")
            return Response.json({"ok": True, **self.call(path, payload)})
        except ApiError as e:
            return Response.text(str(e), e.status)
        except Exception as e:  # 기능 객체의 오류 메시지는 사용자에게 그대로 보여준다
            return Response.text(str(e) or e.__class__.__name__, 500)

    def _route(self, path: str, p: dict) -> dict:
        if path == "/api/pick-video":
            return self._pick_video()
        if path == "/api/pick-image":
            chosen = self.dialogs.open_image()
            return {"path": chosen, "url": self.images.register(Path(chosen))} if chosen else {"path": ""}
        if path == "/api/register-image":
            return {"url": self._register_image(p.get("path") or "")}
        if path == "/api/pick-save":
            return {"path": self.dialogs.save_mp4(p.get("suggest") or "output_chat.mp4")}
        if path == "/api/render":
            return self._render(p)
        if path == "/api/llm-models":
            self.ollama.ensure_running(p.get("base"))
            return {"models": self.llm.models(p.get("base"))}
        if path == "/api/generate":
            self.ollama.ensure_running(p.get("base"))
            return self.llm.generate(p)
        if path.startswith("/api/ollama/"):
            return self._ollama(path.rsplit("/", 1)[1], p)
        raise ApiError(404, "not found")

    def _pick_video(self) -> dict:
        chosen = self.dialogs.open_video()
        if not chosen:
            return {"path": ""}
        result = {"path": chosen, "url": self.videos.register(Path(chosen))}
        try:
            info = self.probe.probe(Path(chosen))
            result.update(width=info.width, height=info.height, duration=info.duration)
        except Exception:
            pass  # 정보를 못 읽어도 브라우저가 직접 읽을 수 있으면 미리보기는 된다
        return result

    def _register_image(self, path: str) -> str:
        """앱을 다시 켰을 때 저장해 둔 스티커 그림을 다시 보여주기 위한 등록. 그림 파일만 받는다."""
        file = Path(path)
        if file.suffix.lower() not in IMAGE_TYPES or not file.is_file():
            raise ApiError(400, f"그림 파일을 찾을 수 없습니다: {path}")
        return self.images.register(file)

    def _render(self, p: dict) -> dict:
        video = p.get("videoPath")
        if not video:
            raise ApiError(400, "영상이 선택되지 않았습니다.")
        out = p.get("outputPath")
        result = self.renderer.render(Path(video), p.get("settings") or {}, Path(out) if out else None)
        return {"output": str(result)}

    def _ollama(self, action: str, p: dict) -> dict:
        actions = {
            "status": lambda: None,
            "install": self.ollama.start_install,
            "start": self.ollama.start_launch,
            "pull": lambda: self.ollama.start_pull(p.get("model")),
            "delete": lambda: self.ollama.delete(p.get("model")),
            "cancel": self.ollama.cancel,
        }
        if action not in actions:
            raise ApiError(404, "not found")
        actions[action]()
        return self.ollama.status()


def make_handler(app: App, allow_post: bool = True, log: bool = True):
    """allow_post=False 면 화면 파일과 영상만 내보내는 읽기 전용 서버 (앱 창 모드)."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if log:
                print("[app]", fmt % args)

        def _send(self, resp: Response) -> None:
            self.send_response(resp.status)
            self.send_header("Content-Type", resp.ctype)
            for k, v in resp.headers.items():
                self.send_header(k, v)
            if resp.file is not None:
                self.send_header("Content-Length", str(resp.byte_range.length))
                self.end_headers()
                self._stream(resp.file, resp.byte_range)
                return
            self.send_header("Content-Length", str(len(resp.body)))
            self.end_headers()
            self.wfile.write(resp.body)

        def _stream(self, file: Path, rng: ByteRange) -> None:
            try:
                with open(file, "rb") as f:
                    f.seek(rng.start)
                    left = rng.length
                    while left > 0:
                        chunk = f.read(min(1 << 20, left))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        left -= len(chunk)
            except (ConnectionError, OSError):
                pass  # 브라우저가 탐색하면서 연결을 끊는 건 정상

        def do_GET(self):
            self._send(app.get(self.path, self.headers))

        def do_POST(self):
            # 거절하더라도 본문은 먼저 읽는다. 안 읽고 닫으면 윈도우가 연결을 끊어(RST) 응답이 안 간다
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if not allow_post:
                self._send(Response.text("method not allowed", 405))
                return
            self._send(app.post(self.path.split("?", 1)[0], self.headers, raw))

    return Handler
