# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 설정. 빌드.bat 이 사용한다.
# 화면 파일(web)만 넣고, 테스트·개발용 파일은 뺀다. ffmpeg 는 tools/package.py 가 exe 옆에 넣는다.

a = Analysis(
    ["chat_app.py"],
    pathex=[],
    datas=[
        ("web/index.html", "web"),
        ("web/styles.css", "web"),
        ("web/js", "web/js"),
    ],
    hiddenimports=[],
    excludes=["tests", "tools"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FakeLiveChat",
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="FakeLiveChat", upx=False)
