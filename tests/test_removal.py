import json
import os

import pytest

from duplicate_finder.models import IssueKind, Selection
from duplicate_finder.removal import MANIFEST_NAME, QuarantineRemover, remove_duplicates
from duplicate_finder.scanner import find_duplicates


class RecordingRemover:
    """Test double: records calls instead of touching the disk."""

    def __init__(self):
        self.removed = []

    def remove(self, path):
        self.removed.append(path)


@pytest.fixture
def scan_dir(tmp_path):
    root = tmp_path / "scan"
    root.mkdir()
    return root


def _single_group(root):
    (group,) = find_duplicates(root).groups
    return group


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_quarantine_moves_non_keepers_and_writes_manifest(tmp_path, scan_dir):
    keep = _write(scan_dir / "a.txt", b"payload")
    extra = _write(scan_dir / "sub" / "b.txt", b"payload")
    quarantine = tmp_path / "quarantine"
    remover = QuarantineRemover(quarantine, [scan_dir])

    report = remove_duplicates([Selection(_single_group(scan_dir), (keep,))], remover)

    assert report.removed == (extra,) and report.failures == ()
    assert keep.exists() and not extra.exists()
    assert (quarantine / "sub" / "b.txt").read_bytes() == b"payload"
    entry = json.loads((quarantine / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert entry["original"] == str(extra)


def test_group_is_skipped_when_keeper_changed(scan_dir):
    keep = _write(scan_dir / "a.txt", b"payload")
    _write(scan_dir / "b.txt", b"payload")
    group = _single_group(scan_dir)
    keep.write_bytes(b"PAYLOAD")  # same size, different content
    remover = RecordingRemover()

    report = remove_duplicates([Selection(group, (keep,))], remover)

    assert remover.removed == []
    assert [(f.path, f.kind) for f in report.failures] == [(keep, IssueKind.KEEPER_CHANGED)]


def test_group_is_skipped_when_keeper_deleted(scan_dir):
    keep = _write(scan_dir / "a.txt", b"payload")
    _write(scan_dir / "b.txt", b"payload")
    group = _single_group(scan_dir)
    keep.unlink()
    remover = RecordingRemover()

    remove_duplicates([Selection(group, (keep,))], remover)

    assert remover.removed == []


def test_changed_duplicate_is_not_removed(scan_dir):
    keep = _write(scan_dir / "a.txt", b"payload")
    extra = _write(scan_dir / "b.txt", b"payload")
    group = _single_group(scan_dir)
    extra.write_bytes(b"PAYLOAD")
    remover = RecordingRemover()

    report = remove_duplicates([Selection(group, (keep,))], remover)

    assert remover.removed == []
    assert [(f.path, f.kind) for f in report.failures] == [(extra, IssueKind.CONTENT_CHANGED)]


def test_user_chosen_keeper_is_respected(scan_dir):
    first = _write(scan_dir / "a.txt", b"payload")
    chosen = _write(scan_dir / "b.txt", b"payload")
    remover = RecordingRemover()

    remove_duplicates([Selection(_single_group(scan_dir), (chosen,))], remover)

    assert remover.removed == [first]


def test_duplicate_hard_linked_to_keeper_after_scan_is_not_removed(scan_dir):
    keep = _write(scan_dir / "a.txt", b"payload")
    extra = _write(scan_dir / "b.txt", b"payload")
    group = _single_group(scan_dir)
    extra.unlink()
    os.link(keep, extra)
    remover = RecordingRemover()

    report = remove_duplicates([Selection(group, (keep,))], remover)

    assert remover.removed == []
    assert report.failures[0].kind is IssueKind.HARD_LINKED


def test_quarantine_never_overwrites_existing_files(tmp_path, scan_dir):
    keep = _write(scan_dir / "a.txt", b"payload")
    _write(scan_dir / "b.txt", b"payload")
    quarantine = tmp_path / "quarantine"
    _write(quarantine / "b.txt", b"older quarantined file")

    remove_duplicates(
        [Selection(_single_group(scan_dir), (keep,))], QuarantineRemover(quarantine, [scan_dir])
    )

    assert (quarantine / "b.txt").read_bytes() == b"older quarantined file"
    assert (quarantine / "b_duplicate_1.txt").read_bytes() == b"payload"


@pytest.mark.parametrize("relation", ["inside", "parent"])
def test_quarantine_cannot_overlap_scan_root(tmp_path, scan_dir, relation):
    quarantine = scan_dir / "q" if relation == "inside" else tmp_path
    with pytest.raises(ValueError):
        QuarantineRemover(quarantine, [scan_dir])


def test_selection_rejects_keeper_outside_group(scan_dir, tmp_path):
    _write(scan_dir / "a.txt", b"payload")
    _write(scan_dir / "b.txt", b"payload")
    with pytest.raises(ValueError):
        Selection(_single_group(scan_dir), (tmp_path / "elsewhere.txt",))


def test_selection_requires_at_least_one_keeper(scan_dir):
    _write(scan_dir / "a.txt", b"payload")
    _write(scan_dir / "b.txt", b"payload")
    with pytest.raises(ValueError):
        Selection(_single_group(scan_dir), ())


def test_several_kept_copies_are_all_left_in_place(scan_dir):
    a = _write(scan_dir / "a.txt", b"payload")
    b = _write(scan_dir / "b.txt", b"payload")
    c = _write(scan_dir / "c.txt", b"payload")
    remover = RecordingRemover()

    remove_duplicates([Selection(_single_group(scan_dir), (a, c))], remover)

    assert remover.removed == [b]


def test_group_is_skipped_when_any_kept_copy_changed(scan_dir):
    a = _write(scan_dir / "a.txt", b"payload")
    _write(scan_dir / "b.txt", b"payload")
    c = _write(scan_dir / "c.txt", b"payload")
    group = _single_group(scan_dir)
    c.write_bytes(b"PAYLOAD")
    remover = RecordingRemover()

    report = remove_duplicates([Selection(group, (a, c))], remover)

    assert remover.removed == []
    assert [(f.path, f.kind) for f in report.failures] == [(c, IssueKind.KEEPER_CHANGED)]


def test_quarantine_keeps_files_from_several_folders_apart(tmp_path):
    first, second = tmp_path / "photos", tmp_path / "backup"
    keep = _write(first / "a.jpg", b"payload")
    extra = _write(second / "a.jpg", b"payload")
    quarantine = tmp_path / "quarantine"
    (group,) = find_duplicates(first, second).groups

    remove_duplicates([Selection(group, (keep,))],
                      QuarantineRemover(quarantine, [first, second]))

    assert not extra.exists()
    assert (quarantine / "backup" / "a.jpg").read_bytes() == b"payload"


def test_quarantine_cannot_overlap_any_scanned_folder(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    first.mkdir(), second.mkdir()
    with pytest.raises(ValueError):
        QuarantineRemover(second / "q", [first, second])
