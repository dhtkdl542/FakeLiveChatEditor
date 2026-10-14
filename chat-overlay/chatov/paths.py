# -*- coding: utf-8 -*-
"""소스로 실행할 때와 exe(PyInstaller)로 실행할 때 파일 위치가 다르다. 그 차이를 한곳에서 정한다."""
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Tuple


@dataclass(frozen=True)
class AppPaths:
    web_root: Path              # 화면 파일 (index.html, js, css)
    app_dir: Path               # 사용자가 ttf 등을 둘 수 있는 앱 폴더
    tool_dirs: Tuple[Path, ...]  # 같이 넣어 배포한 ffmpeg 를 찾을 폴더

    @classmethod
    def detect(cls, frozen: bool, executable: str, meipass: Optional[str], source_dir: Path) -> "AppPaths":
        if frozen:
            app_dir = Path(executable).parent
            bundle = Path(meipass) if meipass else app_dir
            return cls(bundle / "web", app_dir, (app_dir / "ffmpeg", bundle / "ffmpeg"))
        return cls(source_dir / "web", source_dir, (source_dir / "ffmpeg",))


class ToolLocator:
    """같이 배포한 실행 파일을 먼저 찾고, 없으면 PATH 에서 찾는다."""

    def __init__(self, dirs: Iterable[Path], which: Callable[[str], Optional[str]] = shutil.which):
        self._dirs = list(dirs)
        self._which = which

    def __call__(self, name: str) -> Optional[str]:
        for d in self._dirs:
            for candidate in (d / f"{name}.exe", d / name):
                if candidate.is_file():
                    return str(candidate)
        return self._which(name)
