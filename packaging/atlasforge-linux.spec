# Build on Linux: pyinstaller -y packaging/atlasforge-linux.spec
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

HERE = os.path.dirname(os.path.abspath(SPEC))
datas = collect_data_files("atlasforge") + collect_data_files("archspec")
hidden = collect_submodules("atlasforge") + collect_submodules("etcpak") + collect_submodules("archspec")

a = Analysis(
    [os.path.join(HERE, "forge_linux.py")],
    pathex=[os.path.dirname(HERE)],
    datas=datas,
    hiddenimports=hidden,
    excludes=["webview", "tkinter", "matplotlib", "IPython", "pytest", "lupa",
              "PyQt5", "PyQt6", "PySide2", "PySide6"],
    noarchive=False,
    module_collection_mode={"archspec": "py"},
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="AtlasMapForge",
    console=True,
    upx=False,
    runtime_tmpdir=None,
)
