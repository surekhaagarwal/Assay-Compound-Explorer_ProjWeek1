from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DOSE_RESPONSE = (
    PROJECT_ROOT / "attached_assets" / "assay_dose_response_1791499364192.csv"
)
DEFAULT_STRUCTURES = (
    PROJECT_ROOT / "attached_assets" / "compound_structures_1791499364215.csv"
)

DOSE_COLUMNS = {"compound_id", "conc_nM", "response_pct"}
STRUCTURE_COLUMNS = {"compound_id", "smiles"}


def _read_csv(source: Any, fallback_path: Path, required: set[str], label: str) -> pd.DataFrame:
    if source is None:
        if not fallback_path.exists():
            raise OSError(f"The default {label} file is missing: {fallback_path}")
        frame = pd.read_csv(fallback_path, dtype={"compound_id": "string"})
    else:
        frame = pd.read_csv(
            BytesIO(source.getvalue()), dtype={"compound_id": "string"}
        )

    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            f"{label} CSV is missing required columns: {', '.join(sorted(missing))}."
        )

    frame = frame.copy()
    frame["compound_id"] = frame["compound_id"].astype("string").str.strip()
    missing_ids = frame["compound_id"].isna() | frame["compound_id"].eq("")
    if missing_ids.any():
        raise ValueError(
            f"{label} CSV has {int(missing_ids.sum())} row(s) with a missing compound_id."
        )
    return frame


def load_datasets(
    dose_upload: Any,
    structure_upload: Any,
    default_dose_path: Path,
    default_structure_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    notes: list[str] = []
    dose_df = _read_csv(
        dose_upload, default_dose_path, DOSE_COLUMNS, "dose-response"
    )
    structure_df = _read_csv(
        structure_upload, default_structure_path, STRUCTURE_COLUMNS, "structure"
    )

    for column in ("conc_nM", "response_pct"):
        dose_df[column] = pd.to_numeric(dose_df[column], errors="coerce")
    invalid_count = len(dose_df) - len(valid_dose_rows(dose_df))
    if invalid_count:
        notes.append(
            f"{invalid_count} assay row(s) have missing/non-finite numeric values or "
            "non-positive concentrations. They remain in the merged records but "
            "are excluded from plots, fitting, and activity calls."
        )

    structure_df["smiles"] = structure_df["smiles"].fillna("").astype(str).str.strip()
    duplicate_ids = structure_df.loc[
        structure_df["compound_id"].duplicated(keep=False), "compound_id"
    ].drop_duplicates()
    if not duplicate_ids.empty:
        conflicting = (
            structure_df.groupby("compound_id")["smiles"].nunique().gt(1)
        )
        if conflicting.any():
            raise ValueError(
                "The structure file has conflicting SMILES for compound IDs: "
                + ", ".join(conflicting.index[conflicting].astype(str))
                + ". Supply one structure per compound."
            )
        notes.append(
            "Identical duplicate structures were collapsed to one record per "
            "compound ID to avoid multiplying assay rows. IDs: "
            + ", ".join(sorted(duplicate_ids.astype(str)))
            + "."
        )
        structure_df = structure_df.drop_duplicates("compound_id", keep="first")

    return dose_df, structure_df, notes


def valid_dose_rows(dose_df: pd.DataFrame) -> pd.DataFrame:
    valid = (
        np.isfinite(dose_df["conc_nM"])
        & np.isfinite(dose_df["response_pct"])
        & dose_df["conc_nM"].gt(0)
    )
    return dose_df.loc[valid].copy()


def merge_datasets(
    dose_df: pd.DataFrame, structure_df: pd.DataFrame
) -> pd.DataFrame:
    """Keep every assay measurement and attach its matching structure, if present."""
    structure_columns = structure_df[["compound_id", "smiles"]]
    return dose_df.merge(
        structure_columns,
        on="compound_id",
        how="left",
        validate="many_to_one",
    )


def unmatched_ids(
    dose_df: pd.DataFrame, structure_df: pd.DataFrame
) -> tuple[set[str], set[str]]:
    dose_ids = set(dose_df["compound_id"].dropna().astype(str))
    structure_ids = set(structure_df["compound_id"].dropna().astype(str))
    return dose_ids - structure_ids, structure_ids - dose_ids
