"""
query_templates/loader.py

Dynamically discovers and loads every template module inside query_templates/.
Adding a new template type = just drop a new .py file in the folder.

Each module must define:
  TEMPLATE_TYPE : str        — display label for the dropdown (e.g. "Single Hop")
  TEMPLATES     : List[dict] — list of template dicts
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List

# Package directory
_PKG_DIR = Path(__file__).parent


def load_all_templates() -> Dict[str, List[dict]]:
    """
    Scan query_templates/ for .py modules (excluding __init__ and loader),
    import each one, and return a dict:
        { "Single Hop": [...templates...], "Multi Hop": [...], ... }
    """
    result: Dict[str, List[dict]] = {}

    for finder, module_name, _ in pkgutil.iter_modules([str(_PKG_DIR)]):
        if module_name in ("loader",):
            continue

        try:
            module = importlib.import_module(f"query_templates.{module_name}")
            template_type = getattr(module, "TEMPLATE_TYPE", None)
            templates     = getattr(module, "TEMPLATES", None)

            if template_type and templates:
                result[template_type] = templates

        except Exception as e:
            # Don't crash the whole app if one template file has a bug
            print(f"[template loader] Skipped {module_name}: {e}")

    return result