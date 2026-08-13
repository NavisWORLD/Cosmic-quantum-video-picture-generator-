from __future__ import annotations

import socket
import threading
import time
import webbrowser

from cosmos_media.config import Settings, load_env_file


def _wait_and_open(host: str, port: int) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                webbrowser.open(f"http://{host}:{port}/app/")
                return
        except OSError:
            time.sleep(0.2)


def main() -> int:
    load_env_file(".env")
    settings = Settings()
    host = "127.0.0.1"
    port = settings.api_port

    opener = threading.Thread(target=_wait_and_open, args=(host, port), daemon=True)
    opener.start()

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("COSMOS desktop build is missing Uvicorn") from exc

    uvicorn.run(
        "cosmos_media.api:app",
        host=host,
        port=port,
        reload=False,
        access_log=False,
        log_level="warning",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
