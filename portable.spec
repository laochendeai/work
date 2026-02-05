# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules
import os

block_cipher = None

# Collect hidden imports
hidden_imports = [
    'playwright',
    'pandas',
    'openpyxl',
    'sqlite3',
    'uvicorn',
    'fastapi',
    'pydantic',
    'websockets',
    'openpyxl.cell',
    'openpyxl.styles',
    'license_utils',
    'scraper',
    'storage',
    'extractor',
    'utils',
    'config'
]

a = Analysis(
    ['server.py'],
    pathex=[],
    binaries=[],
    datas=[],  # Cleared to prevent auto-packaging into _internal
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['keygen', 'private.pem', '.git', '.gitignore', 'build', 'dist'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BidSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='_internal',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    # Assets at ROOT
    Tree('config', prefix='config'),
    Tree('data', prefix='data', excludes=['gp.db', '*.log', 'exports']),
    Tree('web', prefix='web'),
    Tree('C:\\Users\\Administrator\\AppData\\Local\\ms-playwright', prefix='browsers'),
    [('public.pem', 'public.pem', 'DATA')],
    [('README.md', 'README.md', 'DATA')],
    
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BidSystemPortable',
)
