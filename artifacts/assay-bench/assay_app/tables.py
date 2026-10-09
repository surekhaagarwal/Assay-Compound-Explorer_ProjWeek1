"""Presentation helpers for assay summary tables."""

import pandas as pd
from pandas.io.formats.style import Styler


def style_compound_summary(summary: pd.DataFrame) -> Styler:
    """Highlight reliable in-range fits green and all other statuses red."""
    def highlight_row(row: pd.Series) -> list[str]:
        background = (
            "#e8f5e9"
            if row["Fit status"] == "Within tested range"
            else "#fdecea"
        )
        return [f"background-color: {background}; color: #1f2937"] * len(row)

    return summary.style.apply(highlight_row, axis=1)
