# ABOUTME: Fixture for STRUCT-010 — a script under scripts/ bootstrapping sys.path.
# ABOUTME: Files under scripts/ are entrypoints; a self-locating bootstrap is by design.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
