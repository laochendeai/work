
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
]

# --- BidServer Analysis ---
a_server = Analysis(
    ['server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('public.pem', '.'),
        ('README.md', '.'),
        ('config', 'config'),
        ('data', 'data'), # Include initial data folder if needed, though we copy it in build.bat usually. 
                          # Including it here makes it read-only inside the helper if one-file.
                          # Since we are doing one-dir (default), we can also manage it externally.
                          # But let's include 'public.pem' and 'README.md' for sure.
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['keygen', 'private.pem'], # Explicitly exclude keygen and private key
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_server = PYZ(a_server.pure, a_server.zipped_data, cipher=block_cipher)

exe_server = EXE(
    pyz_server,
    a_server.scripts,
    [],
    exclude_binaries=True,
    name='BidSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Keep console for now to see logs/license checks
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# --- BidScraper Analysis ---
a_scraper = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[], # Config/Data shared in the root dir
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['keygen', 'private.pem'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_scraper = PYZ(a_scraper.pure, a_scraper.zipped_data, cipher=block_cipher)

exe_scraper = EXE(
    pyz_scraper,
    a_scraper.scripts,
    [],
    exclude_binaries=True,
    name='BidWorker',
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

# --- MERGE ---
coll = COLLECT(
    exe_server,
    a_server.binaries,
    a_server.zipfiles,
    a_server.datas,
    
    exe_scraper,
    a_scraper.binaries,
    a_scraper.zipfiles,
    a_scraper.datas,
    
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BidSystem', # Output folder name
)
