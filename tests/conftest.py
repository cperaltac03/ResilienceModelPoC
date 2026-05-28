import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Make imports from the repository root available during pytest runs.
sys.path.insert(0, str(ROOT))

# Disable the pipeline simulator loop during functional test runs.
os.environ.setdefault("SIMULATOR_DISABLE_LOOP", "true")

# Use a temporary rules file so tests do not depend on repository state.
RULES_FILE = Path(tempfile.gettempdir()) / "pytest_rules_manager.json"
RULES_FILE.write_text("[]", encoding="utf-8")
os.environ.setdefault("RULES_FILE", str(RULES_FILE))
