# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for creating a onedir executable.
Structure: BidScraper.exe + _internal/ folder with dependencies
Data files (config, web, public.pem) are copied by build script.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files

# Get the directory where this spec file is located
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))

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

# Collect Playwright Python packages (not browsers, those are copied by build script)
try:
    playwright_datas = collect_data_files('playwright')
except Exception:
    playwright_datas = []

# --- Analysis ---
a = Analysis(
    ['server.py'],
    pathex=[SPEC_DIR],
    binaries=[],
    datas=playwright_datas,  # Only Playwright Python files
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['keygen'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out unwanted files
a.datas = [x for x in a.datas if not (
    'private.pem' in str(x[0]).lower() or
    'license_db.json' in str(x[0]).lower() or
    'keygen.py' in str(x[0]).lower()
)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BidScraper',
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
)

# Collect all binaries and data
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BidScraper',
)
