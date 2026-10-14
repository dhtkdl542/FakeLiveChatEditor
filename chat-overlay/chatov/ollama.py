# -*- coding: utf-8 -*-
"""Ollama 설치 · 실행 · 모델 관리."""
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Callable, List, Mapping, Optional
from urllib.parse import urlparse

from .jobs import JobContext, JobRunner
from .transport import HttpTransport, ServiceError


class OllamaApi:
    def __init__(self, transport: HttpTransport, base: str = "http://127.0.0.1:11434"):
        self._t = transport
        self.base = base

    def version(self) -> Optional[str]:
        try:
            return self._t.json("GET", self.base + "/api/version", timeout=2).get("version") or "?"
        except ServiceError:
            return None

    def models(self) -> List[dict]:
        tags = self._t.json("GET", self.base + "/api/tags", timeout=5)
        return [{"name": m["name"], "size": m.get("size", 0)} for m in tags.get("models", [])]

    def delete(self, name: str) -> None:
        self._t.json("DELETE", self.base + "/api/delete", {"model": name}, timeout=30)

    def pull(self, name: str, ctx: JobContext) -> str:
        layers = {}
        ctx.report(message=f"{name} 받는 중...")
        for ev in self._t.stream_lines(self.base + "/api/pull", {"model": name, "stream": True}):
            ctx.check_cancel()
            if ev.get("error"):
                raise ServiceError(f"모델 다운로드 실패: {ev['error']}")
            if ev.get("digest") and ev.get("total"):
                layers[ev["digest"]] = (ev.get("completed", 0), ev["total"])
            ctx.report(message=f"{name}: {ev.get('status', '')}",
                       completed=sum(c for c, _ in layers.values()),
                       total=sum(t for _, t in layers.values()))
            if ev.get("status") == "success":
                return f"{name} 설치 완료"
        raise ServiceError("다운로드가 중간에 끊겼습니다. 다시 시도하면 이어서 받습니다.")


class OllamaLocator:
    def __init__(self, env: Mapping[str, str], which: Callable = shutil.which):
        self._dir = Path(env["LOCALAPPDATA"]) / "Programs" / "Ollama" if env.get("LOCALAPPDATA") else None
        self._which = which

    def exe(self) -> Optional[Path]:
        found = self._which("ollama")
        if found:
            return Path(found)
        if self._dir and (self._dir / "ollama.exe").exists():
            return self._dir / "ollama.exe"
        return None


def detached_popen(cmd: List[str]) -> None:
    """창 없이 백그라운드로 실행. 이 앱을 닫아도 계속 돈다 (모델은 Ollama가 5분 쉬면 알아서 내린다)."""
    flags = (getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
             | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    subprocess.Popen(cmd, creationflags=flags, close_fds=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class OllamaLauncher:
    def __init__(self, api: OllamaApi, locator: OllamaLocator, popen: Callable[[List[str]], None] = detached_popen,
                 sleep: Callable[[float], None] = time.sleep, timeout: int = 30):
        self._api, self._locator, self._popen, self._sleep, self._timeout = api, locator, popen, sleep, timeout

    def launch(self) -> str:
        """트레이 앱(채팅 창)이 아니라 API 서버(ollama serve)만 창 없이 켠다."""
        if self._api.version():
            return "Ollama가 이미 실행 중입니다."
        exe = self._locator.exe()
        if not exe:
            raise ServiceError("Ollama가 설치되어 있지 않습니다.")
        self._popen([str(exe), "serve"])
        for _ in range(self._timeout * 2):
            if self._api.version():
                return "Ollama가 켜졌습니다."
            self._sleep(0.5)
        raise ServiceError(f"Ollama를 켰지만 {self._timeout}초 안에 응답이 없습니다. 작업표시줄 트레이를 확인하세요.")


class UrlDownloader:
    def __init__(self, chunk: int = 1 << 20, opener: Callable = urllib.request.urlopen):
        self._chunk, self._open = chunk, opener

    def download(self, url: str, dest: Path, ctx: JobContext) -> None:
        with self._open(url, timeout=60) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                ctx.check_cancel()
                chunk = r.read(self._chunk)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                ctx.report(completed=done, total=total)


def run_and_wait(cmd: List[str]) -> int:
    return subprocess.run(cmd).returncode


class OllamaInstaller:
    SETUP_URL = "https://ollama.com/download/OllamaSetup.exe"

    def __init__(self, launcher: OllamaLauncher, download: Callable, run: Callable[[List[str]], int],
                 temp_dir: Path):
        self._launcher, self._download, self._run, self._temp = launcher, download, run, Path(temp_dir)

    def install(self, ctx: JobContext) -> str:
        setup = self._temp / "OllamaSetup.exe"
        ctx.report(message="Ollama 설치 파일 다운로드 중...")
        self._download(self.SETUP_URL, setup, ctx)
        ctx.report(message="백그라운드에서 설치하는 중... (1~2분)", completed=0, total=0)
        # Inno Setup 설치기: /VERYSILENT 는 창 없이 설치. 사용자 폴더에 설치돼서 관리자 권한 불필요
        code = self._run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
        if code != 0:
            raise ServiceError(f"설치 프로그램이 오류로 끝났습니다 (코드 {code}).")
        ctx.report(message="Ollama 서버가 켜지기를 기다리는 중...")
        self._launcher.launch()
        return "Ollama 설치 완료"


class OllamaManager:
    """화면에서 쓰는 Ollama 기능을 한곳에 모은 창구."""

    def __init__(self, api: OllamaApi, locator: OllamaLocator, launcher: OllamaLauncher,
                 installer: OllamaInstaller, jobs: JobRunner):
        self._api, self._locator, self._launcher, self._installer, self._jobs = api, locator, launcher, installer, jobs

    def status(self) -> dict:
        version = self._api.version()
        return {
            "installed": bool(self._locator.exe() or version),
            "running": bool(version),
            "version": version,
            "models": self._api.models() if version else [],
            "job": self._jobs.snapshot(),
        }

    @staticmethod
    def _name(name: str) -> str:
        name = (name or "").strip()
        if not name:
            raise ServiceError("모델 이름이 비었습니다.")
        return name

    def start_install(self) -> None:
        self._jobs.start("install", self._installer.install)

    def start_launch(self) -> None:
        self._jobs.start("start", lambda ctx: self._launcher.launch())

    def start_pull(self, name: str) -> None:
        name = self._name(name)
        self._jobs.start("pull", lambda ctx: self._api.pull(name, ctx))

    def delete(self, name: str) -> None:
        self._api.delete(self._name(name))

    def cancel(self) -> None:
        self._jobs.cancel()

    def _is_own_address(self, base: str) -> bool:
        mine, other = urlparse(self._api.base), urlparse((base or "").strip())
        local = {"127.0.0.1", "localhost"}
        return other.port == mine.port and other.hostname in local and mine.hostname in local

    def ensure_running(self, base: str) -> None:
        """대사 생성 요청이 Ollama 로 가면, 꺼져 있을 때 창 없이 켜 둔다. 실패는 LLM 호출 쪽에서 알려준다."""
        if not self._is_own_address(base):
            return
        try:
            self._launcher.launch()
        except ServiceError:
            pass
