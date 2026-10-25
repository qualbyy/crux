# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

is_win = sys.platform == "win32"
icon_path = os.path.abspath('resources/zephyrium.ico') if (is_win and os.path.exists('resources/zephyrium.ico')) else None

datas = [('resources', 'resources'), ('style.qss', '.')]
binaries = []
hiddenimports = ['PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtNetwork', 'cryptography', 'requests']

tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
try:
    tmp_ret = collect_all('PyQt6_WebEngine')
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
except Exception:
    pass

# For Windows: ensure all Qt6, MSVC and CRT runtime DLLs are mirrored in the root directory for immediate dynamic link loader resolution
if is_win:
    import site
    for sp in site.getsitepackages():
        qt_bin = os.path.join(sp, 'PyQt6', 'Qt6', 'bin')
        if os.path.isdir(qt_bin):
            for f in os.listdir(qt_bin):
                if f.lower().endswith('.dll'):
                    full_p = os.path.join(qt_bin, f)
                    binaries.append((full_p, '.'))
                    binaries.append((full_p, 'PyQt6/Qt6/bin'))

    # Also collect VC runtime DLLs from System32/SysWOW64 (vcruntime140.dll, vcruntime140_1.dll, msvcp140*.dll, etc.)
    import glob
    sys32 = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')
    if os.path.isdir(sys32):
        for pattern in ('vcruntime140*.dll', 'msvcp140*.dll', 'vcomp140*.dll'):
            for p in glob.glob(os.path.join(sys32, pattern)):
                binaries.append((p, '.'))
                binaries.append((p, 'PyQt6/Qt6/bin'))

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
    upx=False,
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
    upx=False,
    upx_exclude=[],
    name='zephyrium',
)
