# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

is_win = sys.platform == "win32"
icon_path = os.path.abspath('resources/zephyrium.ico') if (is_win and os.path.exists('resources/zephyrium.ico')) else None

datas = [('resources', 'resources'), ('style.qss', '.')]
binaries = []
hiddenimports = ['PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets', 'cryptography', 'requests']

tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PyQt6_WebEngine')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='zephyrium',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False if is_win else True,
    icon=icon_path,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='zephyrium',
)
