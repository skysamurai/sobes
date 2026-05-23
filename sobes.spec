# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = [('sobes_core', 'sobes_core'), ('sobes_modules', 'sobes_modules')]
datas += collect_data_files('certifi')
binaries = []
hiddenimports = ['PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets', 'pyaudio', 'PyPDF2', 'requests', 'bs4']
tmp_certifi = collect_all('certifi')
datas += tmp_certifi[0]; binaries += tmp_certifi[1]; hiddenimports += tmp_certifi[2]
tmp_ret = collect_all('vosk')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['sobes_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'chromadb', 'sentence_transformers', 'onnxruntime', 'transformers', 'numba', 'llvmlite', 'scipy', 'sklearn', 'tokenizers', 'keras', 'tensorflow', 'PIL', 'pandas', 'grpc'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sobes',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='sobes',
)
