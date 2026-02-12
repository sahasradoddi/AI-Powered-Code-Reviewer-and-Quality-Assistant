from pathlib import Path
from typing import Any, Dict

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore

DEFAULT_CONFIG = {
    "include": ["**/*.py"],
    "exclude": ["**/__init__.py"],
    "fail_on": "high",
    "min_quality_score": 5.0,
    "output_dir": "quality_reports",
    "auto_fix_smells": ["unused_imports"],  # default
}


def load_config() -> Dict[str, Any]:
    """Load configuration from pyproject.toml if available."""
    project_root = Path(__file__).resolve().parent
    pyproject = project_root / "pyproject.toml"

    if not pyproject.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
        cfg = data.get("tool", {}).get("ai_reviewer", {})
        merged = DEFAULT_CONFIG.copy()
        merged.update(cfg)
        return merged
    except Exception as e:
        print(f"⚠️ Could not read pyproject.toml config: {e}")
        return DEFAULT_CONFIG.copy()
