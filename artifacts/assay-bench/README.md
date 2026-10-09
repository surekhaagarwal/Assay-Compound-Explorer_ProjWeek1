# Assay Bench

A modular Streamlit app for matching dose-response measurements to compound
SMILES, fitting 4-parameter logistic curves, and viewing 2D structures.

## Run

Start the managed `artifacts/assay-bench: web` workflow. It supplies the port
and routes the Streamlit app to `/assay-bench/`. The old root preview redirects
to that URL. There is no React frontend.

The app uses the supplied CSV files in `attached_assets/` by default. The
sidebar accepts replacement dose-response and structure CSVs. Required columns:

- Dose-response: `compound_id`, `conc_nM`, `response_pct`
- Structures: `compound_id`, `smiles`

CSV uploaders are grouped in a collapsed **Upload CSV datasets** section to
keep the sidebar compact. Choose one or both files and click **Upload dataset**
to apply them together. Browsing does not change the active data. An upload
replaces the previous dataset; an omitted counterpart stays empty rather than
falling back to sample data. Invalid submissions hide previous results, show
the validation error, and keep **About the app** accessible. Each successful
submission resets compound and fit-status selections, including replacements
that reuse the same IDs.

The sidebar **Home** button restores both supplied sample files, clears pending
uploads and upload errors, and returns to the initial first-compound selection,
its corresponding fit status, and the Assay Results tab.

On first load, the **Fit status** dropdown shows the
first selected compound's calculated status. Changing a status automatically
selects every matching compound in both
tabs and downloaded records. Choosing **All fit statuses** selects all compounds.
Checkboxes can then narrow that selection. Its options are calculated from the
complete dataset, not just the current compound selection. Dataset-wide fits are
cached by measurements and compound IDs so sidebar changes do not repeat the
curve fitting.
Cache keys include every measurement, including large datasets, so replacement
values cannot be missed by sampled dataframe hashing.

Only the first compound is selected on first load. Individual sidebar
checkboxes support selecting multiple compounds and filter both tabs. Curves
have stable, distinct compound colors, with compound ID and fitted IC₅₀ in nM
in the legend. Fit quality is shown in a summary below the chart; selected
structures appear in a three-column gallery. Each structure has a table of
RDKit-calculated molecular formula, molecular weight, LogP, TPSA, hydrogen-bond donors/acceptors,
rotatable bonds, ring count, and its input SMILES string.
The **Clear all selections** button sits above **Fit status**, resets that filter to
**All fit statuses**, unchecks every compound, and clears both data tabs.
The **Select all compounds** button selects every available compound for both tabs.

The app does not impose an activity direction or biological response cutoff.
IC₅₀ is the fitted midpoint of the upper and lower plateaus. Poor fits and
estimates outside the tested concentration range are flagged.
Summary rows are light green for **Within tested range** and light red for all
other fit statuses.

The last tab, **About the app**, renders `ABOUT.md`: a plain-language guide to
the app, its chart, IC50 estimates, fit-status colors, molecular structures,
and CSV inputs. Edit that Markdown file to update the guide.

## Modules

- `app.py`: Streamlit page, shared compound filter, tabs, and user-facing states
- `ABOUT.md`: beginner-friendly Markdown content for the last tab
- `server.py`: Streamlit server entry point and root-to-app redirect
- `assay_app/data.py`: CSV validation, cleaning, ID matching, and join
- `assay_app/uploads.py`: submitted-file loading without sample-data fallback
- `assay_app/fitting.py`: SciPy 4PL fitting and fit statistics
- `assay_app/analysis.py`: per-compound fits, response summary, and fit flags
- `assay_app/plots.py`: Plotly dose-response visualization
- `assay_app/tables.py`: fit-status row highlighting for the compound summary
- `assay_app/molecules.py`: RDKit SMILES parsing, 2D rendering, and molecular descriptors
