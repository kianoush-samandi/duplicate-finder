"""Domain-specific exceptions shared by the scanner and the removal layer."""


class FileChangedError(OSError):
    """A file no longer matches what was recorded during the scan."""


class OperationCancelled(Exception):
    """The user cancelled a long-running operation."""
