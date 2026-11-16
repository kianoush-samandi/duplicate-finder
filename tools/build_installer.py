"""Build the Windows installer: freeze the app with PyInstaller, then package it with Inno Setup.

Run on 64-bit Windows, in the project's virtual environment:

    pip install -e ".[trash]" pyinstaller
    python tools/build_icons.py          # only if duplicate_finder/assets/icon.ico is missing
    python tools/build_installer.py      # add --iscc PATH if ISCC.exe is not found automatically

Requires Inno Setup 7.1+. The installer is written to dist/installer/.

Every value the installer needs (version, exe name, taskbar ID, settings folder)
is read from the app's own code or pyproject.toml here and passed to
packaging/installer.iss, so none of them is written down twice.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so the app's constants can be imported below

from duplicate_finder.app_icon import ICO_PATH, WINDOWS_APP_ID  # noqa: E402
from duplicate_finder.settings import APP_DIR_NAME  # noqa: E402

APP_EXE_STEM = "DuplicateFinder"
LAUNCHER = ROOT / "packaging" / "launcher.py"
INSTALLER_SCRIPT = ROOT / "packaging" / "installer.iss"
PYPROJECT = ROOT / "pyproject.toml"
PYINSTALLER_WORK_DIR = ROOT / "build" / "pyinstaller"
DIST_DIR = ROOT / "dist"
INSTALLER_OUTPUT_DIR = DIST_DIR / "installer"
ISCC_INSTALL_DIRS = ("Inno Setup 7",)


class BuildError(Exception):
    """A problem the developer must fix before the build can succeed."""


# ---------------------------------------------------------------- preconditions


def check_build_environment() -> None:
    if sys.platform != "win32":
        raise BuildError("The Windows installer must be built on Windows (PyInstaller cannot cross-compile).")
    if struct.calcsize("P") != 8:
        raise BuildError("Use a 64-bit Python: the installer is declared x64 (SetupArchitecture=x64).")
    if not ICO_PATH.is_file():
        raise BuildError(f"{ICO_PATH} is missing. Generate it with: python tools/build_icons.py")
    for module, install_hint in (("PyInstaller", "pip install pyinstaller"),
                                 ("send2trash", 'pip install -e ".[trash]"')):
        if importlib.util.find_spec(module) is None:
            raise BuildError(f"{module} is not installed. Run: {install_hint}")


# ---------------------------------------------------------------------- version


def read_version() -> str:
    try:
        return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
    except (OSError, KeyError) as exc:
        raise BuildError(f"Could not read [project].version from {PYPROJECT}: {exc}") from exc


def numeric_version(version: str) -> str:
    """'1.2.0rc1' -> '1.2.0'. Windows file version resources accept digits and dots only."""
    match = re.match(r"\d+(?:\.\d+){0,3}", version)
    if not match:
        raise BuildError(f"Version {version!r} does not start with a number.")
    return match.group(0)


# ----------------------------------------------------------------------- freeze


def freeze_app() -> Path:
    """Bundle the app and its Python runtime into a folder; return that folder."""
    run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onedir",    # starts faster than --onefile and triggers fewer antivirus false positives
        "--windowed",  # no console window
        "--noupx",     # UPX-packed DLLs are a common cause of antivirus false positives
        "--name", APP_EXE_STEM,
        "--icon", str(ICO_PATH),
        # app_icon.py looks for the icon next to itself, inside the package.
        "--add-data", f"{ICO_PATH}{os.pathsep}duplicate_finder/assets",
        # send2trash is imported lazily and picks its Windows backend at runtime.
        "--collect-submodules", "send2trash",
        "--paths", str(ROOT),
        "--distpath", str(DIST_DIR),
        "--workpath", str(PYINSTALLER_WORK_DIR),
        "--specpath", str(PYINSTALLER_WORK_DIR),
        str(LAUNCHER),
    ])
    return DIST_DIR / APP_EXE_STEM


# -------------------------------------------------------------------- installer


def find_iscc(explicit: str | None) -> Path:
    candidates = [Path(explicit)] if explicit else _default_iscc_candidates()
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise BuildError("ISCC.exe (Inno Setup 7.1+) was not found. Install it or pass --iscc PATH.")


def _default_iscc_candidates() -> list[Path]:
    on_path = shutil.which("ISCC")
    roots = [os.environ.get(name) for name in ("ProgramFiles", "ProgramFiles(x86)")]
    roots.append(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"))  # per-user install
    installed = [Path(root) / folder / "ISCC.exe"
                 for root in roots if root
                 for folder in ISCC_INSTALL_DIRS]
    return ([Path(on_path)] if on_path else []) + installed


def build_installer(iscc: Path, bundle_dir: Path, version: str) -> None:
    defines = {
        "AppVersion": version,
        "AppNumericVersion": numeric_version(version),
        "AppExeName": f"{APP_EXE_STEM}.exe",
        "AppUserModelID": WINDOWS_APP_ID,
        "SettingsDirName": APP_DIR_NAME,
        "BundleDir": str(bundle_dir),
        "IconFile": str(ICO_PATH),
        "OutputDir": str(INSTALLER_OUTPUT_DIR),
    }
    run([str(iscc), *(f"/D{name}={value}" for name, value in defines.items()), str(INSTALLER_SCRIPT)])


# ------------------------------------------------------------------------- main


def run(command: list[str]) -> None:
    print(">", subprocess.list2cmdline(command), flush=True)
    result = subprocess.run(command)
    if result.returncode != 0:
        raise BuildError(f"{Path(command[0]).name} failed with exit code {result.returncode}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--iscc", help="path to ISCC.exe, if it is not found automatically")
    args = parser.parse_args()
    try:
        check_build_environment()
        version = read_version()
        iscc = find_iscc(args.iscc)  # fail fast, before the slow freeze step
        bundle_dir = freeze_app()
        build_installer(iscc, bundle_dir, version)
    except BuildError as exc:
        sys.exit(f"error: {exc}")
    print(f"Installer written to {INSTALLER_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
