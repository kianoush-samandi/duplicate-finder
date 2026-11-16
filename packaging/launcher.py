"""Entry point that PyInstaller freezes into DuplicateFinder.exe.

The package uses relative imports, so ``duplicate_finder/gui.py`` cannot be
frozen as a top-level script; this file imports it as a package instead.
"""

from duplicate_finder.gui import main

if __name__ == "__main__":
    main()
