from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

from duplicate_finder.risk import RiskAssessor, RiskReason, default_system_folders

assessor = RiskAssessor([PurePosixPath("/usr"), PureWindowsPath(r"C:\Windows")])


@pytest.mark.parametrize(
    "path, expected",
    [
        (PurePosixPath("/home/me/report.pdf"), set()),
        (PurePosixPath("/home/me/setup.EXE"), {RiskReason.PROGRAM_FILE}),
        (PurePosixPath("/home/me/lib/plugin.dll"), {RiskReason.PROGRAM_FILE}),
        (PurePosixPath("/usr/share/doc/readme.txt"), {RiskReason.SYSTEM_FOLDER}),
        (PurePosixPath("/usr/lib/libz.so"), {RiskReason.SYSTEM_FOLDER, RiskReason.PROGRAM_FILE}),
        (PureWindowsPath(r"c:\WINDOWS\Fonts\arial.ttf"), {RiskReason.SYSTEM_FOLDER}),
        (PurePosixPath("/home/me/code/.git/objects/ab"), {RiskReason.APP_DATA}),
        (PureWindowsPath(r"D:\Users\me\AppData\Roaming\x.db"), {RiskReason.APP_DATA}),
        # Similar names that are not the folder itself are safe.
        (PurePosixPath("/usrlocal/notes.txt"), set()),
        (PurePosixPath("/home/me/appdata.txt"), set()),
    ],
)
def test_reasons(path, expected):
    assert assessor.reasons(path) == expected


def test_risky_files_keeps_only_the_risky_ones():
    paths = [Path("/home/me/a.txt"), Path("/home/me/a.exe")]
    assert RiskAssessor().risky_files(paths) == {
        Path("/home/me/a.exe"): {RiskReason.PROGRAM_FILE}
    }


def test_windows_system_folders_come_from_the_environment():
    folders = default_system_folders("win32", {"SystemRoot": r"E:\Win", "ProgramFiles": ""})
    assert folders == (Path(r"E:\Win"),)


def test_windows_falls_back_to_the_usual_folders():
    assert Path(r"C:\Windows") in default_system_folders("win32", {})


@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_unix_system_folders_include_usr(platform):
    assert Path("/usr") in default_system_folders(platform, {})
