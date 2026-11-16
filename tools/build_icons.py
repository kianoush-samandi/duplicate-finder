"""Render the app icon masters (SVG) into the files the app ships with.

Run after editing an SVG in ``duplicate_finder/assets``:

    pip install cairosvg pillow
    python tools/build_icons.py

This is a developer tool; the app itself only needs the generated files.
"""

from __future__ import annotations

import io
from pathlib import Path

import cairosvg
from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "duplicate_finder" / "assets"
DETAILED_MASTER = ASSETS / "icon.svg"
SMALL_MASTER = ASSETS / "icon-small.svg"  # hand-simplified, legible at tiny sizes

ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)  # Windows title bar, taskbar, Explorer
SMALL_SIZE_LIMIT = 32  # at or below this size the simplified master is used
PNG_SIZE = 256  # for iconphoto on macOS/Linux


def render(master: Path, size: int) -> Image.Image:
    png = cairosvg.svg2png(url=str(master), output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def master_for(size: int) -> Path:
    return SMALL_MASTER if size <= SMALL_SIZE_LIMIT else DETAILED_MASTER


def build_ico(target: Path) -> None:
    frames = [render(master_for(size), size) for size in ICO_SIZES]
    largest = frames[-1]
    largest.save(target, format="ICO", sizes=[f.size for f in frames], append_images=frames[:-1])


def build_png(target: Path) -> None:
    render(DETAILED_MASTER, PNG_SIZE).save(target, format="PNG", optimize=True)


def main() -> None:
    build_ico(ASSETS / "icon.ico")
    build_png(ASSETS / "icon.png")
    print(f"Icons written to {ASSETS}")


if __name__ == "__main__":
    main()
