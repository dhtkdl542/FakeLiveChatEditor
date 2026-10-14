@echo off
chcp 65001 >nul
rem 공유용 exe 만들기: chat-overlay\dist\FakeLiveChat.zip 이 생깁니다.
cd /d "%~dp0chat-overlay"
if not exist .venv\Scripts\python.exe (
  echo [1/4] 빌드용 가상환경 만드는 중...
  python -m venv .venv || goto fail
)
echo [1/4] 필요한 패키지 설치
.venv\Scripts\python -m pip install -q -r requirements-build.txt || goto fail
echo [2/4] 테스트
.venv\Scripts\python -m unittest discover -s tests -t . || goto fail
where node >nul 2>nul
if not errorlevel 1 (
  pushd web
  node --test tests/
  if errorlevel 1 (
    popd
    goto fail
  )
  popd
)
echo [3/4] exe 빌드
.venv\Scripts\pyinstaller --noconfirm --clean FakeLiveChat.spec || goto fail
echo [4/4] ffmpeg · 안내문 넣고 zip 만들기
.venv\Scripts\python tools\package.py || goto fail
echo.
echo 완료: chat-overlay\dist\FakeLiveChat.zip 을 공유하세요.
pause
exit /b 0
:fail
echo 빌드 실패
pause
exit /b 1
