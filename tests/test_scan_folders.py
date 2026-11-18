import pytest

from duplicate_finder.scan_folders import FolderAlreadyIncludedError, ScanFolders
from duplicate_finder.validation import FolderNotSelectedError, NotAFolderError


@pytest.fixture
def folders(tmp_path):
    for name in ("a", "b", "a/inner"):
        (tmp_path / name).mkdir()
    return ScanFolders()


def test_folders_are_kept_in_the_order_added(tmp_path, folders):
    folders.add(str(tmp_path / "b"))
    folders.add(str(tmp_path / "a"))

    assert folders.folders == ((tmp_path / "b").resolve(), (tmp_path / "a").resolve())


@pytest.mark.parametrize("name", ["a", "a/inner"])
def test_a_folder_already_covered_is_rejected(tmp_path, folders, name):
    folders.add(str(tmp_path / "a"))
    with pytest.raises(FolderAlreadyIncludedError):
        folders.add(str(tmp_path / name))


def test_adding_a_parent_replaces_its_listed_subfolders(tmp_path, folders):
    folders.add(str(tmp_path / "a" / "inner"))
    folders.add(str(tmp_path / "b"))
    folders.add(str(tmp_path / "a"))

    assert folders.folders == ((tmp_path / "b").resolve(), (tmp_path / "a").resolve())


def test_invalid_folder_is_rejected(tmp_path, folders):
    with pytest.raises(NotAFolderError):
        folders.add(str(tmp_path / "missing"))


def test_scanning_requires_a_folder(tmp_path, folders):
    with pytest.raises(FolderNotSelectedError):
        folders.require_any()
    folders.add(str(tmp_path / "a"))
    folders.remove(0)
    assert len(folders) == 0
