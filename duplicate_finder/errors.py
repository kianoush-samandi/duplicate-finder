"""Domain-specific exceptions shared by the scanner and the removal layer."""

from .models import IssueKind


class FileChangedError(OSError):
    """A file no longer matches what was recorded during the scan."""

    def __init__(self, kind: IssueKind) -> None:
        super().__init__(kind.value)
        self.kind = kind


class OperationCancelled(Exception):
    """The user cancelled a long-running operation."""
