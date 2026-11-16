import subprocess
from pathlib import Path

import pytest

from duplicate_finder import file_opener
from duplicate_finder.file_opener import FileOpenError, is_launchable, open_command, open_file


@pytest.mark.parametrize("name", ["setup.exe", "RUN.BAT", "script.ps1", "install.sh"])
def test_programs_and_scripts_are_launchable(name):
    assert is_launchable(Path(name))


@pytest.mark.parametrize("name", ["photo.jpg", "report.PDF", "notes.txt", "no_suffix"])
def test_documents_are_not_launchable(name):
    assert not is_launchable(Path(name))


@pytest.mark.parametrize("platform, opener", [("darwin", "open"), ("linux", "xdg-open")])
def test_open_command_passes_the_path_as_one_argument(platform, opener):
    path = Path("/data/my file; rm -rf ~.txt")
    assert open_command(path, platform) == [opener, str(path)]


def test_missing_file_is_reported_without_launching(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", _fail_if_called)
    with pytest.raises(FileNotFoundError):
        open_file(tmp_path / "gone.txt", platform="linux")


def test_existing_file_is_handed_to_the_opener(make_file, monkeypatch):
    path = make_file("a.txt", b"x")
    launched = []
    monkeypatch.setattr(subprocess, "Popen", lambda args, **_kw: launched.append(args))

    open_file(path, platform="linux")

    assert launched == [["xdg-open", str(path)]]


def test_windows_uses_startfile(make_file, monkeypatch):
    path = make_file("a.txt", b"x")
    opened = []
    monkeypatch.setattr(file_opener.os, "startfile", opened.append, raising=False)

    open_file(path, platform="win32")

    assert opened == [path]


def test_launch_failure_becomes_file_open_error(make_file, monkeypatch):
    path = make_file("a.txt", b"x")

    def missing_opener(*_args, **_kwargs):
        raise FileNotFoundError("xdg-open")

    monkeypatch.setattr(subprocess, "Popen", missing_opener)
    with pytest.raises(FileOpenError):
        open_file(path, platform="linux")


def _fail_if_called(*_args, **_kwargs):
    raise AssertionError("nothing should be launched")
