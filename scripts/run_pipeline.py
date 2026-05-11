from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run(script: str) -> None:
    print(f"Running {script}...")
    subprocess.run([sys.executable, str(ROOT / "scripts" / script)], check=True)


def main() -> None:
    run("fetch_data.py")
    run("prepare_data.py")
    run("setup_duckdb.py")
    run("analyze.py")
    print("Global Fuel Shocks Intelligence pipeline completed.")


if __name__ == "__main__":
    main()
