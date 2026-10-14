# -*- coding: utf-8 -*-
"""JSON HTTP 통신. 오류는 사용자에게 보여줄 수 있는 ServiceError 하나로 모은다."""
import json
import urllib.error
import urllib.request
from typing import Callable, Iterator, Optional


class ServiceError(RuntimeError):
    pass


class HttpTransport:
    def __init__(self, opener: Callable = urllib.request.urlopen):
        self._open = opener

    def _request(self, method: str, url: str, body: Optional[dict]):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        return urllib.request.Request(url, data=data, method=method,
                                      headers={"Content-Type": "application/json"})

    def _call(self, req, timeout):
        try:
            return self._open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise ServiceError(f"서버 오류 {e.code}: {detail}")
        except urllib.error.URLError as e:
            raise ServiceError(f"서버에 연결할 수 없습니다 ({req.full_url}). 서버가 켜져 있는지 확인하세요. [{e.reason}]")
        except TimeoutError:
            raise ServiceError("응답이 너무 오래 걸립니다.")

    def json(self, method: str, url: str, body: Optional[dict] = None, timeout: float = 300) -> dict:
        with self._call(self._request(method, url, body), timeout) as resp:
            try:
                text = resp.read().decode("utf-8")
            except TimeoutError:
                raise ServiceError("응답이 너무 오래 걸립니다.")
        if not text.strip():
            return {}
        try:
            return json.loads(text)
        except ValueError:
            raise ServiceError(f"JSON 이 아닌 응답: {text[:200]}")

    def stream_lines(self, url: str, body: dict, timeout: float = 120) -> Iterator[dict]:
        """한 줄에 JSON 하나씩 오는 응답(Ollama pull 등)을 차례로 넘겨준다. 중간에 멈추면 연결을 닫는다."""
        with self._call(self._request("POST", url, body), timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if line:
                    yield json.loads(line)
