from hashlib import sha256
from pathlib import Path

import pandas as pd
import streamlit as st

from assay_app.analysis import analyze_compounds
from assay_app.data import (
    DEFAULT_DOSE_RESPONSE,
    DEFAULT_STRUCTURES,
    load_datasets,
    merge_datasets,
    unmatched_ids,
    valid_dose_rows,
)
from assay_app.molecules import molecule_descriptors, molecule_image
from assay_app.plots import dose_response_figure
from assay_app.tables import style_compound_summary
from assay_app.uploads import load_uploaded_datasets


def clear_compound_selection(
    checkbox_keys: list[str], status_widget_key: str
) -> None:
    st.session_state[status_widget_key] = "All fit statuses"
    for key in checkbox_keys:
        st.session_state[key] = False


def select_all_compounds(checkbox_keys: list[str]) -> None:
    for key in checkbox_keys:
        st.session_state[key] = True


def restore_default_dataset() -> None:
    """Return this session to the initial sample data and clear pending uploads."""
    st.session_state["home_revision"] = st.session_state.get("home_revision", 0) + 1
    dataset_keys = {
        "active_dataset", "dataset_revision", "dataset_names", "dataset_error"
    }
    filter_prefixes = (
        "compound_filter:", "fit_status:", "clear_selection:", "select_all:"
    )
    for key in list(st.session_state):
        if key in dataset_keys or key.startswith(filter_prefixes):
            del st.session_state[key]


def select_compounds_for_fit_status(
    status_widget_key: str,
    fit_summary: pd.DataFrame,
    compound_ids: list[str],
    checkbox_keys: list[str],
) -> None:
    """Apply a status choice to the shared selection before either tab reruns."""
    status = st.session_state[status_widget_key]
    matching_ids = (
        set(compound_ids)
        if status == "All fit statuses"
        else set(fit_summary.loc[fit_summary["Fit status"] == status, "compound_id"])
    )
    for compound_id, key in zip(compound_ids, checkbox_keys, strict=True):
        st.session_state[key] = compound_id in matching_ids


def assay_fingerprint(data: pd.DataFrame) -> str:
    """Hash every measurement; default Streamlit hashing samples large frames."""
    digest = sha256(repr(tuple(data.columns)).encode("utf-8"))
    digest.update(pd.util.hash_pandas_object(data, index=True).values.tobytes())
    return digest.hexdigest()


@st.cache_data(
    show_spinner=False,
    max_entries=8,
    hash_funcs={pd.DataFrame: assay_fingerprint},
)
def cached_compound_analysis(data: pd.DataFrame, compound_ids: list[str]):
    """Reuse dataset-wide fits when only sidebar selections change."""
    return analyze_compounds(data, compound_ids)


def stop_analysis(message: str, analysis_tabs: tuple) -> None:
    """Keep navigation and help visible without rendering invalid analysis."""
    analysis_tabs[0].error(message)
    for tab in analysis_tabs:
        tab.info(
            "Analysis is unavailable. Correct the CSV files in the sidebar "
            "and click Upload dataset again. No previous results are displayed. "
            "See About the app for guidance."
        )
    st.stop()


st.set_page_config(
    page_title="Assay Bench",
    layout="wide",
)

st.title("Assay Bench")

home_revision = st.session_state.get("home_revision", 0)
assay_tab, compound_tab, about_tab = st.tabs(
    ["Assay Results", "compound viewer", "About the app"],
    key=f"result_tabs:{home_revision}",
    default="Assay Results",
)
with about_tab:
    st.markdown(Path(__file__).with_name("ABOUT.md").read_text(encoding="utf-8"))

with st.sidebar:
    st.button(
        "Home",
        icon=":material/home:",
        help="Restore the default sample files and initial compound selection.",
        on_click=restore_default_dataset,
        key="restore_default_dataset",
    )
    st.header("Data")
    with st.expander("Upload CSV datasets", expanded=False):
        # A fresh form/uploader identity clears any staged files on Home without
        # assigning file-uploader values through the Session State API.
        with st.form(f"dataset_upload_form:{home_revision}"):
            dose_upload = st.file_uploader(
                "Dose-response CSV",
                type=["csv"],
                help="Required columns: compound_id, conc_nM, response_pct.",
                key=f"dose_response_upload:{home_revision}",
            )
            structure_upload = st.file_uploader(
                "Chemical structures CSV",
                type=["csv"],
                help="Required columns: compound_id, smiles.",
                key=f"structures_upload:{home_revision}",
            )
            st.caption(
                "Choose one or both files, then click Upload dataset. "
                "A missing file stays empty; sample data will not be added."
            )
            upload_submitted = st.form_submit_button(
                "Upload dataset", width="stretch"
            )
    st.caption("Upload new CSV files to analyze a different dataset.")

# Apply only submitted files. Browsing or changing sidebar filters cannot alter
# the active dataset, and a replacement never inherits a sample counterpart.
if upload_submitted:
    try:
        dataset = load_uploaded_datasets(dose_upload, structure_upload)
    except (ValueError, pd.errors.ParserError, OSError) as exc:
        st.session_state["dataset_error"] = str(exc)
    else:
        st.session_state["active_dataset"] = dataset
        st.session_state["dataset_revision"] = (
            st.session_state.get("dataset_revision", 0) + 1
        )
        st.session_state["dataset_names"] = (
            dose_upload.name if dose_upload is not None else "Not supplied",
            structure_upload.name if structure_upload is not None else "Not supplied",
        )
        st.session_state.pop("dataset_error", None)

if "active_dataset" not in st.session_state and "dataset_error" not in st.session_state:
    try:
        st.session_state["active_dataset"] = load_datasets(
            dose_upload=None,
            structure_upload=None,
            default_dose_path=DEFAULT_DOSE_RESPONSE,
            default_structure_path=DEFAULT_STRUCTURES,
        )
        st.session_state["dataset_revision"] = 0
    except (ValueError, pd.errors.ParserError, OSError) as exc:
        st.session_state["dataset_error"] = str(exc)

if "dataset_error" in st.session_state:
    stop_analysis(st.session_state["dataset_error"], (assay_tab, compound_tab))

dose_df, structure_df, data_notes = st.session_state["active_dataset"]
compound_ids = sorted(
    set(dose_df["compound_id"].dropna())
    | set(structure_df["compound_id"].dropna())
)
if not compound_ids:
    stop_analysis(
        "No valid compound IDs were found in the uploaded datasets.",
        (assay_tab, compound_tab),
    )

dataset_revision = st.session_state["dataset_revision"]
if dataset_revision == 0:
    st.sidebar.caption("Displayed dataset: supplied sample files.")
else:
    dose_name, structure_name = st.session_state["dataset_names"]
    st.sidebar.success("Uploaded dataset loaded.")
    st.sidebar.caption(f"Dose-response: {dose_name}")
    st.sidebar.caption(f"Structures: {structure_name}")

merged = merge_datasets(dose_df, structure_df)
unmatched_dose_ids, unmatched_structure_ids = unmatched_ids(dose_df, structure_df)

for note in data_notes:
    assay_tab.warning(note)

if unmatched_dose_ids or unmatched_structure_ids:
    assay_tab.warning(
        "The compound IDs do not fully match between the two files. "
        "Dose-response-only IDs have no structure; structure-only IDs have no assay data."
    )
    with assay_tab.expander(
        f"Review unmatched IDs ({len(unmatched_dose_ids)} dose-response-only, "
        f"{len(unmatched_structure_ids)} structure-only)"
    ):
        left, right = st.columns(2)
        with left:
            st.markdown("**Dose-response IDs without structures**")
            st.dataframe(
                pd.DataFrame({"compound_id": sorted(unmatched_dose_ids)}),
                hide_index=True,
                width="stretch",
            )
        with right:
            st.markdown("**Structure IDs without dose-response data**")
            st.dataframe(
                pd.DataFrame({"compound_id": sorted(unmatched_structure_ids)}),
                hide_index=True,
                width="stretch",
            )
else:
    st.sidebar.success("All compound IDs match.")

all_assay = valid_dose_rows(dose_df)
all_fits, all_summary = cached_compound_analysis(all_assay, compound_ids)
fit_status_options = sorted(all_summary["Fit status"].unique().tolist())
initial_fit_status = all_summary.loc[
    all_summary["compound_id"] == compound_ids[0], "Fit status"
].iloc[0]
status_key = sha256("\0".join(fit_status_options).encode("utf-8")).hexdigest()[:16]
status_widget_key = f"fit_status:{dataset_revision}:{status_key}"
selection_key = sha256("\0".join(compound_ids).encode("utf-8")).hexdigest()[:16]
selection_key = f"{dataset_revision}:{selection_key}"
checkbox_keys = [
    f"compound_filter:{selection_key}:{compound_id}"
    for compound_id in compound_ids
]
if status_widget_key not in st.session_state:
    st.session_state[status_widget_key] = initial_fit_status
st.sidebar.button(
    "Clear all selections",
    on_click=clear_compound_selection,
    args=(checkbox_keys, status_widget_key),
    key=f"clear_selection:{selection_key}",
    width="stretch",
)
selected_status = st.sidebar.selectbox(
    "Fit status",
    ["All fit statuses", *fit_status_options],
    key=status_widget_key,
    on_change=select_compounds_for_fit_status,
    args=(status_widget_key, all_summary, compound_ids, checkbox_keys),
    help=(
        "Choosing a fit status selects all matching compounds in both tabs. "
        "Use the checkboxes to narrow the selection."
    ),
)

with st.sidebar.container():
    st.markdown("**Compounds**")
    # Each submitted dataset starts with its first compound and corresponding
    # fit status, even when the replacement reuses the same compound IDs.
    st.button(
        "Select all compounds",
        on_click=select_all_compounds,
        args=(checkbox_keys,),
        key=f"select_all:{selection_key}",
        width="stretch",
    )
    selected_ids = []
    with st.container(height=min(320, max(90, len(compound_ids) * 40 + 20)), border=False):
        for index, compound_id in enumerate(compound_ids):
            checkbox_key = checkbox_keys[index]
            if checkbox_key not in st.session_state:
                st.session_state[checkbox_key] = index == 0
            if st.checkbox(
                compound_id,
                key=checkbox_key,
            ):
                selected_ids.append(compound_id)

checked_ids = selected_ids
if selected_status != "All fit statuses":
    matching_ids = set(
        all_summary.loc[
            all_summary["Fit status"] == selected_status, "compound_id"
        ]
    )
    selected_ids = [
        compound_id for compound_id in checked_ids if compound_id in matching_ids
    ]

empty_selection_message = (
    "No selected compounds match this fit status. Change the fit-status filter "
    "or select matching compounds."
    if checked_ids and not selected_ids
    else "Select one or more compounds in the sidebar."
)
selected_assay = all_assay.loc[all_assay["compound_id"].isin(selected_ids)]
selected_merged = merged.loc[merged["compound_id"].isin(selected_ids)].copy()
fits = {compound_id: all_fits[compound_id] for compound_id in selected_ids}
summary = all_summary.loc[
    all_summary["compound_id"].isin(selected_ids)
].reset_index(drop=True)

with assay_tab:
    if not selected_ids:
        st.info(empty_selection_message)
    else:
        if selected_assay.empty:
            st.info("The selected compounds have no valid dose-response measurements.")
        else:
            st.plotly_chart(
                dose_response_figure(
                    selected_assay,
                    fits,
                    compound_ids=compound_ids,
                ),
                width="stretch",
            )
        st.markdown("**Compound summary**")
        st.dataframe(
            style_compound_summary(summary),
            hide_index=True,
            width="stretch",
            row_height=88,
            column_config={
                "IC₅₀ (nM)": st.column_config.NumberColumn(format="%.3g"),
                "R²": st.column_config.NumberColumn(format="%.3f"),
                "Highest-dose response (%)": st.column_config.NumberColumn(format="%.1f"),
                "Fit status": st.column_config.TextColumn(
                    "Fit status",
                    width=240,
                ),
            },
        )
        st.markdown("**Merged assay records**")
        st.dataframe(
            selected_merged,
            hide_index=True,
            width="stretch",
        )
        st.download_button(
            "Download selected compound data",
            data=selected_merged.to_csv(index=False).encode("utf-8"),
            file_name="selected_compounds_assay_data.csv",
            mime="text/csv",
        )

with compound_tab:
    if not selected_ids:
        st.info(empty_selection_message)
    else:
        for start in range(0, len(selected_ids), 3):
            columns = st.columns(3)
            for column, compound_id in zip(columns, selected_ids[start:start + 3]):
                with column:
                    st.markdown(f"**{compound_id}**")
                    structures = structure_df.loc[
                        structure_df["compound_id"] == compound_id
                    ]
                    smiles = structures.iloc[0]["smiles"] if not structures.empty else None
                    if not smiles:
                        st.info("No matching SMILES record.")
                        continue
                    descriptors = {"SMILES": smiles}
                    try:
                        image = molecule_image(smiles)
                        if image is None:
                            st.error("RDKit could not parse this SMILES string.")
                        else:
                            st.image(image, width="stretch")
                            descriptors = molecule_descriptors(smiles)
                    except (ValueError, RuntimeError) as exc:
                        st.error(f"Could not analyze this structure: {exc}")
                    st.table(
                        pd.DataFrame(
                            descriptors.items(),
                            columns=["Descriptor", "Value"],
                        ),
                        hide_index=True,
                        width="stretch",
                    )

st.divider()
st.caption(
    f"{len(dose_df):,} assay rows · {len(compound_ids):,} compounds · "
    f"{len(selected_ids):,} selected"
)
