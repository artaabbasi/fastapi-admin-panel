"""
Discovers the SQLAlchemy Base class by AST-parsing alembic/env.py.

Strategy:
  1. Find alembic.ini → locate the alembic script directory
  2. Parse env.py with ast to find:  target_metadata = <expr>
  3. Resolve <expr> back to its import statement
  4. Dynamically import the module and return the Base / MetaData object

Supported alembic.ini layouts
------------------------------
  script_location = alembic                    (default)
  script_location = database/migrations        (nested)
  script_location = %(here)s/database/migrations  (%(here)s interpolation)
"""

import ast
import importlib.util
import re
import sys
from pathlib import Path
from typing import Optional


def _parse_ini_value(raw: str) -> str:
    """Strip inline comments and whitespace from an .ini value."""
    # Remove inline # or ; comments (but not inside quoted strings)
    val = re.split(r"\s+[#;]", raw)[0]
    return val.strip()


def find_alembic_env(project_root: Path) -> Optional[Path]:
    """
    Locate alembic/env.py by reading script_location from alembic.ini.
    Searches project_root and its immediate parent.
    """
    ini: Optional[Path] = None
    for candidate in (project_root / "alembic.ini", project_root.parent / "alembic.ini"):
        if candidate.exists():
            ini = candidate
            ini_dir = candidate.parent
            break

    if ini is None:
        return None

    script_location = "alembic"
    for line in ini.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        # skip comments and section headers
        if not stripped or stripped.startswith(("#", ";", "[")):
            continue
        if stripped.lower().startswith("script_location"):
            _, _, raw = stripped.partition("=")
            val = _parse_ini_value(raw)
            # resolve %(here)s → directory containing alembic.ini
            val = val.replace("%(here)s", str(ini_dir))
            script_location = val
            break

    # script_location may be absolute or relative to the ini directory
    loc = Path(script_location)
    if not loc.is_absolute():
        loc = ini_dir / loc

    env_py = loc / "env.py"
    return env_py if env_py.exists() else None


def _resolve_attribute_chain(node: ast.expr) -> list[str]:
    """ast.Attribute chain → ['pkg', 'sub', 'attr']"""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return list(reversed(parts))


def _find_target_metadata_source(tree: ast.Module) -> Optional[ast.expr]:
    """Return the RHS of  target_metadata = <expr>"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "target_metadata":
                return node.value
    return None


def _build_import_map(tree: ast.Module) -> dict[str, tuple[str, Optional[str]]]:
    """
    Returns {local_name: (module, original_name_or_None)}
    e.g. 'Base' -> ('myapp.models', 'Base')
         'models' -> ('myapp.models', None)   # import myapp.models as models
    """
    mapping: dict[str, tuple[str, Optional[str]]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local = alias.asname if alias.asname else alias.name
                mapping[local] = (node.module, alias.name if alias.asname else alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname if alias.asname else alias.name.split(".")[0]
                mapping[local] = (alias.name, None)
    return mapping


def find_base_from_alembic(project_root: Path):
    """
    Returns the SQLAlchemy DeclarativeBase (or MetaData) discovered from
    alembic/env.py.  Returns None if discovery fails.
    """
    env_py = find_alembic_env(project_root)
    if env_py is None:
        return None

    source = env_py.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    rhs = _find_target_metadata_source(tree)
    if rhs is None:
        return None

    import_map = _build_import_map(tree)

    # rhs is either:
    #   Base.metadata          → Attribute(Name('Base'), 'metadata')
    #   metadata               → Name('metadata')
    #   some.module.Base.metadata
    chain = _resolve_attribute_chain(rhs)

    if not chain:
        return None

    root_name = chain[0]
    if root_name not in import_map:
        return None

    module_name, original_name = import_map[root_name]

    # Ensure the project root is on sys.path so the user's package imports work
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    try:
        mod = importlib.import_module(module_name)
    except Exception:
        return None

    # Navigate the remaining chain after the imported name
    # e.g. chain = ['Base', 'metadata'] → we imported Base, skip 'metadata'
    obj = getattr(mod, original_name, None) if original_name else mod
    if obj is None:
        return None

    for attr in chain[1:]:
        if attr == "metadata":
            # return the object BEFORE .metadata so callers get Base/MetaData
            break
        obj = getattr(obj, attr, None)
        if obj is None:
            return None

    return obj
