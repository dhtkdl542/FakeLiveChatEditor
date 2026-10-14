@echo off
chcp 65001 >nul
cd /d "%~dp0chat-overlay"
echo [Python] 서버 · 렌더링 · E2E 테스트
python -m unittest discover -s tests -t .
if errorlevel 1 goto fail
echo.
echo [JS] 화면 로직 테스트
cd web
node --test tests/
if errorlevel 1 goto fail
echo.
echo 모든 테스트 통과
pause
exit /b 0
:fail
echo 테스트 실패
pause
exit /b 1
