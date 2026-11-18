from pathlib import PurePosixPath, PureWindowsPath

import pytest

from duplicate_finder.trash_folders import is_trash_folder


@pytest.mark.parametrize(
    "path",
    [
        PureWindowsPath(r"C:\$Recycle.Bin"),
        PureWindowsPath(r"D:\$RECYCLE.BIN"),
        PureWindowsPath(r"E:\RECYCLER"),
        PurePosixPath("/Users/me/.Trash"),
        PurePosixPath("/Volumes/USB/.Trashes"),
        PurePosixPath("/media/usb/.Trash-1000"),
        PurePosixPath("/home/me/.local/share/Trash"),
    ],
)
def test_trash_folders_are_recognized(path):
    assert is_trash_folder(path)


@pytest.mark.parametrize(
    "path",
    [
        PurePosixPath("/home/me/Trash"),  # an ordinary folder that happens to be named so
        PurePosixPath("/home/me/trash-notes"),
        PureWindowsPath(r"C:\Users\me\Documents"),
    ],
)
def test_other_folders_are_not_trash(path):
    assert not is_trash_folder(path)
