"""Optional CSV data loading hooks for future calibration work."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_optional_csv(path: Path) -> tuple[pd.DataFrame | None, str]:
    """Load a CSV if present and return a source label."""

    if path.exists():
        return pd.read_csv(path), "historical_data"
    return None, "fallback_assumption"
