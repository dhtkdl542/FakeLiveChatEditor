# -*- coding: utf-8 -*-
"""ffmpeg 로 영상 정보를 읽고 채팅 자막을 입힌다."""
import json
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

from .ass import AssWriter, OverlayStyle
from .rng import Mulberry32
from .speed import SpeedCurve
from .donations import DonationGenerator, donations_from_payload, merge_into_chat
from .overlay_ass import StickerTrack
from .stickers import ImagePrim, Sticker
from .timeline import EventGenerator, events_from_payload


class ToolMissing(RuntimeError):
    pass


class RenderError(RuntimeError):
    pass


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    duration: float


class HiddenRunner:
    """창 모드 exe 에서 ffmpeg 를 돌릴 때 검은 콘솔 창이 뜨지 않게 한다."""

    def __init__(self, run: Callable = subprocess.run,
                 no_window_flag: int = getattr(subprocess, "CREATE_NO_WINDOW", 0)):
        self._run = run
        self._flag = no_window_flag

    def __call__(self, cmd, **kw):
        return self._run(cmd, creationflags=self._flag, **kw)


class FFmpeg:
    def __init__(self, run: Callable = HiddenRunner(), which: Callable = shutil.which):
        self._run = run
        self._which = which

    def _tool(self, name: str) -> str:
        path = self._which(name)
        if path is None:
            raise ToolMissing(f"{name} 를 찾을 수 없습니다. 앱 폴더의 ffmpeg 폴더에 {name}.exe 가 있는지 확인하세요.")
        return path

    def ensure_available(self) -> None:
        for name in ("ffmpeg", "ffprobe"):
            self._tool(name)

    def probe(self, path: Path) -> VideoInfo:
        cmd = [self._tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,duration", "-show_entries", "format=duration",
               "-of", "json", str(path)]
        proc = self._run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RenderError(f"영상 정보를 읽지 못했습니다: {(proc.stderr or '')[-500:]}")
        data = json.loads(proc.stdout)
        stream = data["streams"][0]
        duration = stream.get("duration") or data["format"]["duration"]
        return VideoInfo(int(stream["width"]), int(stream["height"]), float(duration))

    def burn(self, src: Path, ass_name: str, out: Path, cwd: Path, overlays: Sequence[ImagePrim] = ()) -> None:
        # 자막 경로는 상대 경로로만 넘긴다. ass 필터는 "D:" 의 콜론을 구분자로 읽어버림
        ass = f"ass={ass_name}:fontsdir=."
        if not overlays:
            cmd = [self._tool("ffmpeg"), "-y", "-i", str(src), "-vf", ass, "-c:a", "copy", str(out)]
        else:
            # 그림 스티커는 영상 위에 먼저 얹고, 그 위에 채팅 · 글자 스티커 자막을 입힌다
            inputs, graph, last = [], [], "0:v"
            for i, o in enumerate(overlays, start=1):
                w, h = max(1, round(o.w)), max(1, round(o.h))
                inputs += ["-i", str(Path(o.path))]
                graph.append(f"[{i}:v]scale={w}:{h}[i{i}]")
                graph.append(f"[{last}][i{i}]overlay={round(o.cx - o.w / 2)}:{round(o.cy - o.h / 2)}[v{i}]")
                last = f"v{i}"
            graph.append(f"[{last}]{ass}[vout]")
            cmd = [self._tool("ffmpeg"), "-y", "-i", str(src), *inputs, "-filter_complex", ";".join(graph),
                   "-map", "[vout]", "-map", "0:a?", "-c:a", "copy", str(out)]
        proc = self._run(cmd, cwd=str(cwd), capture_output=True, text=True)
        if proc.returncode != 0:
            raise RenderError((proc.stderr or proc.stdout or "ffmpeg 실패")[-2000:])


class FontCollector:
    """폴더에 있는 ttf 를 ffmpeg 작업 폴더로 모아서 ass 필터가 찾을 수 있게 한다."""

    def __init__(self, sources: Iterable[Path]):
        self._sources = list(sources)

    def copy_into(self, dest: Path, extra: Iterable[Path] = ()) -> None:
        for src in [*self._sources, *extra]:
            if not src.is_dir():
                continue
            for f in list(src.glob("*.ttf")) + list(src.glob("*.otf")):
                target = dest / f.name
                if not target.exists():
                    try:
                        shutil.copy2(f, target)
                    except OSError:
                        pass


class OverlayRenderer:
    ASS_NAME = "chat.ass"

    def __init__(self, ffmpeg: FFmpeg, fonts: FontCollector):
        self._ffmpeg = ffmpeg
        self._fonts = fonts

    @staticmethod
    def default_output(src: Path) -> Path:
        return src.parent / (src.stem + "_chat.mp4")

    @staticmethod
    def _seed(settings: dict) -> int:
        seed = settings.get("SEED")
        return int(seed) if seed is not None else random.getrandbits(32)

    def donations(self, settings: dict, duration: float, seed: int):
        """브라우저 미리보기에서 만든 후원이 오면 그대로, 아니면 설정대로 새로 만든다."""
        if settings.get("DONATIONS") is not None:
            return donations_from_payload(settings["DONATIONS"], duration)
        if settings.get("DONATIONS_ON"):
            return DonationGenerator.from_settings(settings, seed).generate(duration)
        return []

    def events(self, settings: dict, duration: float, seed: int = None, donations=()):
        if settings.get("EVENTS"):
            return events_from_payload(settings["EVENTS"], duration)  # 브라우저가 후원 줄까지 넣어서 보낸다
        rng = Mulberry32(self._seed(settings) if seed is None else seed)
        chat = EventGenerator(
            curve=SpeedCurve.from_settings(settings),
            nicks=settings["NICKS"], msgs=settings["MSGS"], palette=settings.get("COLORS") or [],
            start=float(settings.get("CHAT_START", 0.5)),
            interval_min=float(settings.get("INTERVAL_MIN", 0.25)),
            interval_max=float(settings.get("INTERVAL_MAX", 0.7)),
            rng=rng,
        ).generate(duration)
        unit = settings.get("DONATION_UNIT") or "하트"
        return merge_into_chat(chat, donations, settings.get("COLORS") or [], unit) if donations else chat

    def render(self, src: Path, settings: dict, dest: Optional[Path] = None) -> Path:
        self._ffmpeg.ensure_available()
        src = Path(src).resolve()
        if not src.exists():
            raise RenderError(f"영상 파일이 없습니다: {src}")
        if not settings.get("NICKS") or not settings.get("MSGS"):
            raise RenderError("닉네임/대사가 비었습니다.")
        out = Path(dest).resolve() if dest else self.default_output(src)
        if out.suffix.lower() != ".mp4":
            out = out.with_suffix(".mp4")
        out.parent.mkdir(parents=True, exist_ok=True)

        info = self._ffmpeg.probe(src)
        seed = self._seed(settings)
        donations = self.donations(settings, info.duration, seed)
        events = self.events(settings, info.duration, seed, donations)
        stickers = [Sticker.from_dict(d) for d in settings.get("STICKERS") or []]
        track = StickerTrack(info.width, info.height, stickers, donations, info.duration,
                             unit=settings.get("DONATION_UNIT") or "하트", platform=settings.get("PLATFORM") or "panda")
        # 둥근 · 알약 박스는 브라우저가 잰 줄 글자 폭으로 그린다 (없으면 각진 박스)
        widths = settings.get("TEXT_WIDTHS") if settings.get("EVENTS") else None
        ass = AssWriter(info.width, info.height, OverlayStyle.from_settings(settings), text_widths=widths).build(
            events, info.duration, extra=track.dialogues())
        overlays = [o for o in track.images() if Path(o.path).is_file()]
        with tempfile.TemporaryDirectory(prefix="chatov_") as work:
            work_dir = Path(work)
            (work_dir / self.ASS_NAME).write_text(ass, encoding="utf-8")
            self._fonts.copy_into(work_dir, extra=[src.parent])
            self._ffmpeg.burn(src, self.ASS_NAME, out, cwd=work_dir, overlays=overlays)
        if not out.exists():
            raise RenderError("ffmpeg 가 끝났지만 결과 파일이 없습니다.")
        return out
