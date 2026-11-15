"""Human-readable formatting helpers."""

_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def format_size(size: int) -> str:
    """Format a byte count with binary (1024-based) units, e.g. ``1.50 MB``."""
    value = float(size)
    for unit in _UNITS[:-1]:
        if abs(value) < 1024:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} {_UNITS[-1]}"
