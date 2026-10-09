"""Load a submitted upload without falling back to either sample file."""

from io import BytesIO
from typing import Any

import pandas as pd

from assay_app.data import DEFAULT_DOSE_RESPONSE, DEFAULT_STRUCTURES, load_datasets


def load_uploaded_datasets(
    dose_upload: Any, structure_upload: Any
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """A missing counterpart is empty, never the supplied sample dataset."""
    if dose_upload is None and structure_upload is None:
        raise ValueError("Choose at least one CSV file, then click Upload dataset.")

    dose_source = BytesIO(
        dose_upload.getvalue()
        if dose_upload is not None
        else b"compound_id,conc_nM,response_pct\n"
    )
    structure_source = BytesIO(
        structure_upload.getvalue()
        if structure_upload is not None
        else b"compound_id,smiles\n"
    )
    dataset = load_datasets(
        dose_source, structure_source, DEFAULT_DOSE_RESPONSE, DEFAULT_STRUCTURES
    )
    dose_df, structure_df, _ = dataset
    if dose_df.empty and structure_df.empty:
        raise ValueError("The uploaded files contain no compounds. Supply CSV files with data rows.")
    return dataset
