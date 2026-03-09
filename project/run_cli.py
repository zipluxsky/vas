#!/usr/bin/env python
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.absolute()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.cli.__main__ import cli

if __name__ == "__main__":
    cli()
