#!/usr/bin/env python3
"""
Build the React frontend and copy it into fastapi_admin_panel/static/.

Usage:
    python scripts/build.py              # install deps + build
    python scripts/build.py --no-install # skip npm install (faster if already done)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
FRONTEND = ROOT / "frontend"
STATIC = ROOT / "fastapi_admin_panel" / "static"


def run(cmd: list[str], cwd: Path) -> None:
    print(f"\n$ {' '.join(cmd)}  (in {cwd})")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\nCommand failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build admin panel frontend")
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Skip npm install (use when node_modules already exists)",
    )
    args = parser.parse_args()

    npm = shutil.which("npm")
    if npm is None:
        print("ERROR: npm not found. Install Node.js first.", file=sys.stderr)
        sys.exit(1)

    if not args.no_install:
        run([npm, "install"], cwd=FRONTEND)

    run([npm, "run", "build"], cwd=FRONTEND)

    print(f"\nFrontend built → {STATIC}")


if __name__ == "__main__":
    main()
