# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[("ui/", "ui/")],
    hiddenimports=["cffi", "pkg_resources.py2_warn"],
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
    [],
    exclude_binaries=True,
    name="Cashu",
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
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Cashu",
)
app = BUNDLE(
    coll,
    name="Cashu.app",
    icon="ui/icons/mac.icns",
    bundle_identifier="org.cashu.ui",
    info_plist={
        "NSPrincipalClass": "NSApplication",
        "NSHighResolutionCapable": "True",
        "NSSupportsAutomaticGraphicsSwitching": "True",
        "CFBundleURLTypes": [
            {
                "CFBundleURLSchemes": [
                    "lightning",
                ],
            }
        ],
        "LSMinimumSystemVersion": "10.13.0",
        "NSCameraUsageDescription": "Cashu would like to access the camera to scan for QR codes",
    },
)
