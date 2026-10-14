# -*- coding: utf-8 -*-
"""PyInstaller 빌드 결과(dist/FakeLiveChat)에 ffmpeg 와 안내문을 넣고 공유용 zip 을 만든다.

    python tools/package.py
"""
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "FakeLiveChat"

SOURCE_NOTE = """이 폴더의 ffmpeg.exe / ffprobe.exe 는 FFmpeg 프로젝트의 프로그램입니다 (GPL v3, LICENSE.txt 참고).
가짜 라이브 채팅 앱이 영상에 채팅을 입힐 때 사용합니다.

FFmpeg 소스 코드: https://ffmpeg.org/download.html
이 빌드를 만든 곳: https://www.gyan.dev/ffmpeg/builds/
"""

README = """가짜 라이브 채팅
================

[실행]
  압축을 푼 폴더에서 FakeLiveChat.exe 를 더블클릭하세요. 설치할 것은 없습니다.
  폴더 안의 파일(ffmpeg 폴더, _internal 폴더)은 지우거나 옮기지 마세요.

  처음 실행할 때 "Windows의 PC 보호" 파란 창이 뜰 수 있습니다.
  서명되지 않은 개인 제작 프로그램이라 그렇습니다. [추가 정보] → [실행] 을 누르세요.

[필요한 것]
  - Windows 10 / 11 (64비트)
  - Microsoft WebView2 : 윈도우 11과 대부분의 윈도우 10에 이미 있습니다.
    없으면 실행할 때 안내가 뜨고, 그동안은 기본 브라우저에서 열립니다.
  - 영상 처리 프로그램(ffmpeg)은 폴더에 들어 있어서 따로 설치할 필요가 없습니다.

[쓰는 법]
  1. [영상 불러오기] 로 영상을 고릅니다.
  2. 오른쪽 탭에서 글꼴 · 위치 · 대사 · 닉네임 색을 정합니다.
  3. 아래 타임라인을 드래그하면 그 구간만 채팅을 빠르게/느리게 할 수 있습니다.
  4. [mp4로 저장] 을 누르면 채팅이 입혀진 영상이 만들어집니다.

[방송 꾸미기]
  꾸미기 탭의 '템플릿' 카드에서 세 가지를 따로 고릅니다.
    - 플랫폼: 팬더티비(하트) / 아프리카TV(별풍선) / 유튜브(₩). 후원 단위와 후원창 모양이 바뀝니다.
      단위는 '가짜 후원' 칸에서 직접 바꿀 수도 있습니다.
    - 방송 템플릿: 팬더티비 · 엑셀방송 · 아프리카TV 분위기의 스티커 배치가 한 번에 들어갑니다.
    - 채팅창 템플릿: 채팅 줄 모양(박스, 아이콘, 굵기)만 바꿉니다.
  미리보기에서 스티커를 끌어 옮기고, 마우스 휠로 크기를 바꿀 수 있습니다.
  가짜 후원을 켜면 채팅창에 후원 줄이 섞이고, 순위판과 목표 게이지가 따라 올라갑니다.
  내 PNG 그림도 스티커로 올릴 수 있습니다.

[AI 대사 만들기 (선택)]
  AI 탭에서 Ollama 를 설치하고 모델을 받으면, 주제만 적어도 대사를 만들어 줍니다.
  Ollama 는 창 없이 백그라운드에서만 돌아갑니다.
  모델 크기가 수 GB 라서 그래픽카드(VRAM 6GB 이상 권장)가 있는 PC에서 쓰세요.
  사양이 낮으면 AI 없이 대사 탭에 직접 적어도 똑같이 쓸 수 있습니다.

[글꼴]
  원하는 ttf 파일을 FakeLiveChat.exe 옆에 두면 결과 영상에서도 그 글꼴을 쓸 수 있습니다.
"""


class Packager:
    TOOLS = ("ffmpeg.exe", "ffprobe.exe")

    def __init__(self, app_dir: Path, ffmpeg_bin: Optional[Path]):
        self.app_dir = Path(app_dir)
        self.ffmpeg_bin = Path(ffmpeg_bin) if ffmpeg_bin else None

    @staticmethod
    def find_ffmpeg_bin(which: Callable[[str], Optional[str]] = shutil.which) -> Optional[Path]:
        found = which("ffmpeg")
        return Path(found).parent if found else None

    def _license(self) -> Optional[Path]:
        for folder in (self.ffmpeg_bin, self.ffmpeg_bin.parent):
            for name in ("LICENSE", "LICENSE.txt", "COPYING.GPLv3"):
                if (folder / name).is_file():
                    return folder / name
        return None

    def add_ffmpeg(self) -> None:
        if not self.ffmpeg_bin or not all((self.ffmpeg_bin / t).is_file() for t in self.TOOLS):
            raise FileNotFoundError(f"ffmpeg.exe / ffprobe.exe 를 찾을 수 없습니다: {self.ffmpeg_bin}")
        dest = self.app_dir / "ffmpeg"
        dest.mkdir(exist_ok=True)
        for tool in self.TOOLS:
            shutil.copy2(self.ffmpeg_bin / tool, dest / tool)
        lic = self._license()
        if lic:
            shutil.copy2(lic, dest / "LICENSE.txt")
        (dest / "SOURCE.txt").write_text(SOURCE_NOTE, encoding="utf-8")

    def add_readme(self) -> None:
        (self.app_dir / "읽어주세요.txt").write_text(README, encoding="utf-8")

    def make_zip(self) -> Path:
        zip_path = self.app_dir.parent / f"{self.app_dir.name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for f in sorted(self.app_dir.rglob("*")):
                if f.is_file():
                    z.write(f, Path(self.app_dir.name) / f.relative_to(self.app_dir))
        return zip_path


def main() -> int:
    app_dir = ROOT / "dist" / APP_NAME
    if not (app_dir / f"{APP_NAME}.exe").exists():
        print(f"먼저 PyInstaller 로 빌드하세요: {app_dir}")
        return 1
    packager = Packager(app_dir, Packager.find_ffmpeg_bin())
    packager.add_ffmpeg()
    packager.add_readme()
    zip_path = packager.make_zip()
    print(f"완료: {zip_path} ({zip_path.stat().st_size / 1e6:.0f}MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
