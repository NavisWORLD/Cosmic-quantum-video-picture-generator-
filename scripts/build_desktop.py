from __future__ import annotations

import os
from pathlib import Path
import sys


def main() -> int:
    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller is required: pip install -e '.[desktop]'", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
    entry = root / "scripts" / "desktop_entry.py"
    pwa = root / "apps" / "pwa"
    args = [
        str(entry),
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name", "cosmos-media",
        "--paths", str(root / "src"),
        "--collect-submodules", "cosmos_media",
        "--collect-submodules", "uvicorn",
        "--collect-submodules", "fastapi",
        "--add-data", f"{pwa}{os.pathsep}apps/pwa",
    ]
    PyInstaller.__main__.run(args)
    print(f"Desktop executable created under {root / 'dist'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
