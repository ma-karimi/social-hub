#!/usr/bin/env python3
"""One-command local dev startup for SocialHub.

Usage:
    ./scripts/dev_up.sh

Does:
  1. Create/activate virtualenv and install dependencies
  2. Create .env if missing (with ENCRYPTION_KEY)
  3. Create PostgreSQL database if missing
  4. Run Alembic migrations
  5. Seed demo tenant, connection, and sample posts
  6. Start API server (background) + Arq worker (foreground)
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
VENV_PIP = ROOT / ".venv" / "bin" / "pip"

API_PORT = os.environ.get("SOCIALHUB_PORT", "8000")
PROCS: list[subprocess.Popen] = []


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"→ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=ROOT, check=True, **kwargs)


def ensure_venv() -> None:
    if not VENV_PYTHON.exists():
        print("→ Creating virtual environment...")
        run([sys.executable, "-m", "venv", str(ROOT / ".venv")])

    run([str(VENV_PIP), "install", "-e", ".[dev]", "-q"])


def bootstrap() -> None:
    run([str(VENV_PYTHON), str(ROOT / "scripts" / "bootstrap.py")])


def start_process(name: str, cmd: list[str]) -> subprocess.Popen:
    print(f"→ Starting {name}...")
    proc = subprocess.Popen(
        cmd,
        cwd=ROOT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    PROCS.append(proc)
    return proc


def stop_all() -> None:
    for proc in PROCS:
        if proc.poll() is None:
            proc.terminate()
    deadline = time.time() + 5
    for proc in PROCS:
        if proc.poll() is None:
            remaining = max(0, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                proc.kill()


def on_signal(signum, _frame) -> None:
    print(f"\n→ Stopping (signal {signum})...")
    stop_all()
    sys.exit(0)


def wait_for_health(port: str, timeout: float = 30) -> bool:
    import urllib.error
    import urllib.request

    url = f"http://127.0.0.1:{port}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    return False


def main() -> None:
    os.chdir(ROOT)
    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    print()
    print("SocialHub — dev startup")
    print("-" * 40)

    ensure_venv()
    bootstrap()

    start_process(
        "API (uvicorn)",
        [
            str(ROOT / ".venv" / "bin" / "uvicorn"),
            "social_hub.main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            API_PORT,
        ],
    )

    if wait_for_health(API_PORT):
        print(f"✓ API ready at http://localhost:{API_PORT}")
    else:
        print(f"⚠ API health check timed out (port {API_PORT})")

    start_process(
        "Worker (arq)",
        [
            str(ROOT / ".venv" / "bin" / "arq"),
            "social_hub.infrastructure.queue.worker.WorkerSettings",
        ],
    )

    print()
    print("Press Ctrl+C to stop API and worker.")
    print()

    try:
        while True:
            for proc in PROCS:
                code = proc.poll()
                if code is not None and code != 0:
                    print(f"❌ Process exited with code {code}", file=sys.stderr)
                    stop_all()
                    sys.exit(code)
            time.sleep(1)
    except KeyboardInterrupt:
        on_signal(signal.SIGINT, None)


if __name__ == "__main__":
    main()
