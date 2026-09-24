# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for the Lot Management System.

Produces a WINDOWED (no black console window) ONE-FOLDER build:

    dist/LotManagementSystem/
        LotManagementSystem.exe   <- the OQC user double-clicks this
        _internal/                <- Python runtime + libraries (leave it alone)

One-folder (not one-file) is chosen on purpose:
  * The database (lot_management.db) ends up right next to the .exe, in a
    permanent folder - not a temp folder that gets wiped on exit.
  * Faster startup, and reportlab's bundled fonts/QR support unpack cleanly.

reportlab ships data files (fonts) and some pieces get imported dynamically,
so we explicitly collect them; otherwise PDF/QR generation can fail only in
the packaged build.

Build with:  build.bat   (or:  pyinstaller LotManagementSystem.spec)
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("reportlab")
hiddenimports = (
    collect_submodules("reportlab.graphics.barcode")
    + collect_submodules("openpyxl")
)


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LotManagementSystem",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # windowed app - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # To use a custom icon, put an .ico next to this spec and set:
    # icon="app_icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LotManagementSystem",
)
