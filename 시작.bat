@echo off
chcp 65001 >nul
cd /d "%~dp0chat-overlay"
rem 빌드용 가상환경(.venv)에 pywebview 가 있으면 앱 창으로, 없으면 브라우저로 열립니다.
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python chat_app.py %*
) else (
  python chat_app.py %*
)
if errorlevel 1 (
  echo 실행 실패. python 이 설치돼 있는지 확인하세요.
  pause
)
