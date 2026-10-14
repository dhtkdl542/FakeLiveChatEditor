# -*- coding: utf-8 -*-
"""화면 파일(web/)과 미리보기 영상을 안전하게 내보낸다."""
import re
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple
from urllib.parse import unquote

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
}


def mime_for(path: Path) -> str:
    return MIME.get(path.suffix.lower(), "application/octet-stream")


class StaticFiles:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def resolve(self, url_path: str) -> Optional[Tuple[Path, str]]:
        rel = unquote(url_path.split("?", 1)[0]).lstrip("/") or "index.html"
        target = (self.root / rel).resolve()
        if self.root not in target.parents and target != self.root:
            return None
        if not target.is_file():
            return None
        return target, mime_for(target)


class VideoRegistry:
    """탐색기로 고른 파일(영상, 스티커 그림)만 추측할 수 없는 토큰 주소로 내보낸다. 아무 경로나 읽히지 않게."""

    def __init__(self, token_factory: Callable[[], str] = lambda: secrets.token_hex(12), prefix: str = "/video/"):
        self._new_token = token_factory
        self.prefix = prefix
        self._url = re.compile("^" + re.escape(prefix) + r"([0-9a-zA-Z]+)(?:\.[0-9a-zA-Z]+)?$")
        self._files: Dict[str, Path] = {}

    def register(self, path: Path) -> str:
        token = self._new_token()
        self._files[token] = Path(path)
        return f"{self.prefix}{token}{Path(path).suffix.lower()}"

    def resolve_url(self, url_path: str) -> Optional[Path]:
        m = self._url.match(url_path.split("?", 1)[0])
        return self._files.get(m.group(1)) if m else None


class RangeNotSatisfiable(ValueError):
    pass


@dataclass(frozen=True)
class ByteRange:
    """브라우저가 영상 탐색(시킹)할 때 보내는 Range 헤더."""
    start: int
    end: int
    size: int
    partial: bool

    @classmethod
    def parse(cls, header: str, size: int) -> "ByteRange":
        whole = cls(0, size - 1, size, False)
        if not header or not header.startswith("bytes="):
            return whole
        first, _, last = header[6:].split(",", 1)[0].strip().partition("-")
        try:
            if first:
                start = int(first)
                end = min(int(last), size - 1) if last else size - 1
            else:
                start, end = max(0, size - int(last)), size - 1
        except ValueError:
            return whole
        if start >= size or start > end:
            raise RangeNotSatisfiable(header)
        return cls(start, end, size, True)

    @property
    def length(self) -> int:
        return self.end - self.start + 1

    @property
    def content_range(self) -> str:
        return f"bytes {self.start}-{self.end}/{self.size}"
