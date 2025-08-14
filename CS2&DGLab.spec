# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# 获取项目路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的exe文件运行
    project_path = os.path.dirname(sys.executable)
else:
    # 如果是python脚本运行
    project_path = os.path.dirname(os.path.abspath(sys.argv[0]))

a = Analysis(
    [os.path.join(project_path, 'src/desktop.py')],
    pathex=[project_path],
    binaries=[],
    datas=[
        (os.path.join(project_path, 'src/frontend'), 'src/frontend'),
    ],
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'pydantic',
        'webview',
        'aiohttp',
        'qrcode',
        'PIL',
        'PIL._tkinter_finder',
        'numpy',
        'pydglab_ws',
        'src.api.main',
        'src.core.dglab_controller',
        'src.core.game_listener',
        'src.config.config_manager',
        'src.utils.network',
        'src.utils.qrcode',
        'src.utils.cs2_path',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CS2&DGLab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False以避免显示命令行窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)