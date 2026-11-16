import pytest

from duplicate_finder.validation import (
    FolderNotSelectedError,
    NotAFolderError,
    parse_scan_folder,
)


@pytest.mark.parametrize("text", ["", "   ", "\t\n"])
def test_empty_field_is_rejected_instead_of_scanning_cwd(text):
    with pytest.raises(FolderNotSelectedError):
        parse_scan_folder(text)


def test_missing_folder_is_rejected(tmp_path):
    with pytest.raises(NotAFolderError):
        parse_scan_folder(str(tmp_path / "missing"))


def test_file_is_rejected(tmp_path):
    file = tmp_path / "file.txt"
    file.write_text("x")
    with pytest.raises(NotAFolderError):
        parse_scan_folder(str(file))


def test_valid_folder_is_resolved(tmp_path):
    assert parse_scan_folder(f"  {tmp_path}  ") == tmp_path.resolve()
