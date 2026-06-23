# -*- mode: python ; coding: utf-8 -*-
datas = [
    ('assets/icon_dark.png', 'assets'),
    ('assets/icon_light.png', 'assets'),
]
binaries = []
hiddenimports = [
    'keyboard._winkeyboard',
    'pystray._win32',
    'watchdog.observers.read_directory_changes',
    'watchdog.observers.winapi',
    'writeonside_pedigree',
]
excludes = [
    'IPython',
    'jupyter',
    'matplotlib',
    'numpy',
    'pandas',
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'pytest',
    'scipy',
    'keyboard._darwinkeyboard',
    'keyboard._nixkeyboard',
    'PIL.AvifImagePlugin',
    'PIL.ImageCms',
    'PIL._avif',
    'PIL._imagingcms',
    'PIL._imagingft',
    'pystray._appindicator',
    'pystray._darwin',
    'pystray._gtk',
    'pystray._xorg',
    'watchdog.observers.fsevents',
    'watchdog.observers.fsevents2',
    'watchdog.observers.inotify',
    'watchdog.observers.kqueue',
]


a = Analysis(
    ['writeonside.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['scripts/pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name='WriteOnSide',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    version='version_info.txt',
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/WriteOnSide.ico',
)
