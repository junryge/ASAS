# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — OHT 월드모델파생 단일 .exe 빌드
#
# 빌드:   pyinstaller --clean --noconfirm oht_world.spec
# 결과:   dist/oht_world.exe
#
# 사용자 데이터(OHT_MAP, OHS_DATA_MD, _logpresso_cache)는 .exe와 같은 폴더에
# 두면 됨 (런타임에 runtime_dir() 가 .exe 폴더를 가리킴). dashboard.html 만
# 번들에 포함.

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden = []
hidden += collect_submodules('uvicorn')
hidden += collect_submodules('fastapi')
hidden += collect_submodules('starlette')
hidden += ['uvicorn.protocols.websockets.auto',
           'uvicorn.protocols.websockets.websockets_impl',
           'uvicorn.protocols.http.auto',
           'uvicorn.protocols.http.h11_impl',
           'uvicorn.lifespan.on',
           'uvicorn.loops.auto',
           'uvicorn.loops.asyncio',
           'websockets',
           'h11', 'anyio']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('dashboard.html', '.'),     # 번들에 dashboard.html 포함
    ],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter', 'PIL', 'scipy', 'IPython',
              'pytest', 'notebook', 'jupyter'],
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
    name='oht_world',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,                 # 콘솔 창 표시 (로그 확인용)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
