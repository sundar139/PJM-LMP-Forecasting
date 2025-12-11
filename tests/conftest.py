from pathlib import Path
import sys

# Ensure project root is on sys.path so imports like `ingestion.*` work under pytest
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

