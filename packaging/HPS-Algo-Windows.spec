# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "config"), "config"),
    (str(ROOT / "src" / "hps_algo" / "ui" / "static"), "hps_algo/ui/static"),
    (str(ROOT / "src" / "hps_algo" / "ui" / "templates"), "hps_algo/ui/templates"),
]

a = Analysis(
    [str(ROOT / "src" / "hps_algo" / "desktop_app.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn.lifespan.on",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HPS-Algo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HPS-Algo",
)
