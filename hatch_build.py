"""
Hatchling build hook — automatically builds the React frontend
before the Python wheel is assembled.

Runs:  npm install && npm run build   inside ./frontend/
Output lands in ./fastapi_admin_panel/static/ (included in wheel via pyproject.toml artifacts).
"""

import shutil
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        frontend = Path(self.root) / "frontend"

        npm = shutil.which("npm")
        if npm is None:
            print(
                "WARNING: npm not found — skipping frontend build. "
                "Run `python scripts/build.py` manually.",
                file=sys.stderr,
            )
            return

        self._run([npm, "install"], frontend)
        self._run([npm, "run", "build"], frontend)

    @staticmethod
    def _run(cmd: list[str], cwd: Path) -> None:
        print(f"[hatch-build] $ {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd)
        if result.returncode != 0:
            raise RuntimeError(
                f"Frontend build failed (exit {result.returncode}). "
                "Run `python scripts/build.py` for details."
            )
