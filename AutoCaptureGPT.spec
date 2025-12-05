# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

project_name = "AutoCaptureGPT"

# 모든 PySide6 모듈 자동 포함
pyside6_hidden = collect_submodules("PySide6")

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/pretendard-light.ttf', 'assets'),
        ('assets/icons/app.ico', 'assets/icons'),
        ('storage', 'storage'),
    ],
    hiddenimports=[
        'PIL',
        'PIL.Image',
        'PIL.ImageGrab',
        'PIL._tkinter_finder',
        'numpy',
        *pyside6_hidden
    ],
    cipher=block_cipher
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=project_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,         # 콘솔창 숨기기(True면 콘솔창 뜸)
    icon='assets/icons/app.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=project_name
)
