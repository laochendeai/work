# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Collect hidden imports for Playwright, Pandas, etc.
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
    datas=[
        ('public.pem', '.'),
        ('README.md', '.'),
        ('web', 'web'),
        ('config', 'config'),
        ('data', 'data'), 
        ('C:\\Users\\Administrator\\AppData\\Local\\ms-playwright', 'browsers'), # Bundle browsers
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BidSystem', # Single file name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
