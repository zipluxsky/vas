"""Output-path utilities for file-confirmation reports."""

import os
import logging

logger = logging.getLogger(__name__)


def ensure_output_dir(path: str) -> None:
    """Create *path* (and parents) if it does not exist."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def get_unique_filepath(outprefix: str, ext: str, max_tries: int = 10) -> str:
    """Return a file path that does not yet exist.

    Tries ``outprefix.ext``, then ``outprefix-1.ext``, ``outprefix-2.ext`` …
    """
    outfile = f"{outprefix}.{ext}"
    for i in range(1, max_tries):
        if not os.path.isfile(outfile):
            return outfile
        outfile = f"{outprefix.replace(' ', '').replace('()', '')}-{i}.{ext}"
    return outfile
