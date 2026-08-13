from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys


def _common(root: Path, pwa: Path) -> list[str]:
    return [
        "--noconfirm",
        "--clean",
        "--paths",
        str(root / "src"),
        "--collect-submodules",
        "cosmos_media",
        "--collect-submodules",
        "uvicorn",
        "--collect-submodules",
        "fastapi",
        "--collect-all",
        "imageio_ffmpeg",
        "--add-data",
        f"{pwa}{os.pathsep}apps/pwa",
    ]


def main() -> int:
    try:
        import PyInstaller.__main__
    except ImportError:
        print("PyInstaller is required: pip install -e '.[desktop]'", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
    pwa = root / "apps" / "pwa"
    dist = root / "dist"
    build = root / "build"
    shutil.rmtree(dist, ignore_errors=True)
    shutil.rmtree(build, ignore_errors=True)

    cli_entry = root / "scripts" / "desktop_entry.py"
    launcher_entry = root / "scripts" / "desktop_launcher.py"

    PyInstaller.__main__.run(
        [
            str(cli_entry),
            "--onefile",
            "--name",
            "cosmos-media",
            *_common(root, pwa),
        ]
    )

    launcher_args = [
        str(launcher_entry),
        "--onefile",
        "--windowed",
        "--name",
        "COSMOS-Media",
        *_common(root, pwa),
    ]
    PyInstaller.__main__.run(launcher_args)

    print(f"COSMOS desktop app and CLI created under {dist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
