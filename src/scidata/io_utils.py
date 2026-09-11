"""Filesystem helpers for locating and normalising data-file paths."""

import os


def format_windows_path(raw_path: str) -> str:
    """Return *raw_path* with Windows backslashes converted to forward slashes.

    Forward slashes are accepted by the Windows APIs and keep the paths valid
    when the scripts are run on Linux/macOS.
    """
    return raw_path.replace("\\", "/")


def filter_files(directory: str, extensions, name_contains: str = "") -> list[str]:
    """Return full paths of files in *directory* matching an extension and substring.

    Parameters
    ----------
    directory:
        Folder to search (non-recursive).
    extensions:
        Extension or tuple of extensions to match, e.g. ``".tif"`` or
        ``(".tif", ".tiff")``. Passed straight to ``str.endswith``.
    name_contains:
        Substring that must appear in the file name. The empty string (default)
        matches every file.
    """
    return [
        os.path.join(directory, fn)
        for fn in os.listdir(directory)
        if fn.endswith(extensions) and name_contains in fn
    ]
