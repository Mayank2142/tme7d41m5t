"""Verify deployable wheel resources without relying on the source checkout."""

import sys
import zipfile
from pathlib import Path

file = Path(sys.argv[1])
with zipfile.ZipFile(file) as wheel:
    names = set(wheel.namelist())
    required = {
        "backend/app/cli.py",
        "backend/app/main.py",
        "backend/migrations/env.py",
        "backend/migrations/versions/0001_source_releases.py",
        "backend/migrations/versions/0002_freeze_release_versions.py",
    }
    assert required <= names, required - names
    assert not any(name.startswith("backend/tests/") for name in names)
    entry = next(name for name in names if name.endswith(".dist-info/entry_points.txt"))
    assert b"winddesk = backend.app.cli:main" in wheel.read(entry)
print(f"Wheel includes CLI and migrations and excludes tests: {file.name}")
