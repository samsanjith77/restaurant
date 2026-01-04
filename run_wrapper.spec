# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# -------------------------
# Hidden imports
# -------------------------
hiddenimports = []

# Core Django (keep)
hiddenimports += collect_submodules("django")

# DO NOT collect all django.contrib (it drags in GIS => GDAL warnings).
# Collect only the contrib apps you actually use.
hiddenimports += collect_submodules("django.contrib.admin")
hiddenimports += collect_submodules("django.contrib.auth")
hiddenimports += collect_submodules("django.contrib.contenttypes")
hiddenimports += collect_submodules("django.contrib.sessions")
hiddenimports += collect_submodules("django.contrib.messages")
hiddenimports += collect_submodules("django.contrib.staticfiles")

# Third-party
hiddenimports += collect_submodules("corsheaders")
hiddenimports += collect_submodules("rest_framework")
hiddenimports += collect_submodules("rest_framework_simplejwt")

# Your apps (must contain __init__.py)
hiddenimports += collect_submodules("billing_app")
hiddenimports += collect_submodules("accounts")

# -------------------------
# Data files
# -------------------------
datas = []

# Django admin assets (useful if admin is enabled)
datas += collect_data_files("django.contrib.admin")

# If you use DRF browsable API/static (optional but safe)
datas += collect_data_files("rest_framework")

# If you ran collectstatic (STATIC_ROOT -> staticfiles)
datas += [
    ("staticfiles", "staticfiles"),
]

a = Analysis(
    ["run_wrapper.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyi_rth_django.py"],  # sets DJANGO_SETTINGS_MODULE early
    excludes=[
        "django.contrib.gis",  # avoid GDAL dependency warnings
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="run_wrapper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # IMPORTANT for Electron (no backend console window)
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
    name="run_wrapper",
)
