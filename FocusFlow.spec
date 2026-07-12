# -*- mode: python ; coding: utf-8 -*-
# FocusFlow v3.1 - PyInstaller Spec
# Build command: pyinstaller FocusFlow.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect non-Python resource files bundled inside these packages
customtkinter_datas = collect_data_files('customtkinter')
plotly_datas = collect_data_files('plotly')

a = Analysis(
    ['src/focusflow/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('sound', 'sound'),
        ('images', 'images'),
        *customtkinter_datas,   # customtkinter themes & assets
        *plotly_datas,          # plotly template & locale files
    ],
    hiddenimports=[
        # first-party package modules
        *collect_submodules('focusflow'),
        # customtkinter loads themes at runtime via importlib
        'customtkinter',
        # pandas internal C extensions
        'pandas',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.timedeltas',
        # plotly graph objects (used by analysis_manager)
        'plotly.graph_objects',
        'plotly.express',
        'plotly.io',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Heavy packages not used by this app
        'matplotlib',
        'scipy',
        'IPython',
        'notebook',
        'PIL',
        'cv2',
        'sklearn',
        'tensorflow',
        'torch',
        # tkinter test suite
        'tkinter.test',
        'unittest',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FocusFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/Microsoft-Fluentui-Emoji-Flat-Tomato-Flat.512.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # UPX can corrupt these DLLs - exclude them
        'python311.dll',
        'vcruntime140.dll',
        'SDL2.dll',
        'SDL2_mixer.dll',
    ],
    name='FocusFlow',
)
