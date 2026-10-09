# Assay Compound Explorer — Project Week 1

The complete source code for **Assay Bench**, a modular Python/Streamlit app
for exploring compound dose-response measurements and chemical structures.

## Features

- Supplied dose-response and structure CSVs for the initial sample dataset.
- Explicit **Upload dataset** action for replacement CSVs, without mixing in
  sample records.
- Join on `compound_id` and flag unmatched IDs.
- Shared compound checkboxes and fit-status filtering across both data tabs.
- SciPy four-parameter logistic fits and Plotly dose-response curves with IC50
  estimates in nM.
- Logarithmic concentration axis and color-matched dashed IC50 reference lines.
- Bounded response limits (0%–105%) and a toggle to fix bottom/top at 0%/100%.
- A warning for mean responses above 20% at the lowest tested concentration,
  with guidance about incomplete curves and response direction.
- Fit-status summary highlighting and selected-data CSV downloads.
- RDKit molecular drawings, SMILES, molecular formula, and descriptor tables.
- A plain-language **About the app** guide.
- **Home** restores the sample files and initial selection.
- **Clear all selections** resets both filters; **Select all compounds** checks
  every compound.

IC50 is the midpoint between the fitted response plateaus, not necessarily
50% of the raw response. Fit-status colors describe the quality and range of
the estimate, not proof of biological activity or safety.

## Run the Python app

Use Python 3.13 or later. From the repository root:

```bash
python -m pip install -r requirements.txt
python -m streamlit run artifacts/assay-bench/app.py
```

Open the local URL printed by Streamlit. The Python application needs no
database or secrets. Keep `attached_assets/` in place for the supplied sample
files.

Alternatively, if you use uv, the supplied `uv.lock` records the Python
dependencies:

```bash
uv sync --frozen
uv run streamlit run artifacts/assay-bench/app.py
```

The `server.py` entry point provides the original `/assay-bench/` routing
when running in the managed Replit workspace.

## CSV formats

| File | Required columns |
| --- | --- |
| Dose-response | `compound_id`, `conc_nM`, `response_pct` |
| Structures | `compound_id`, `smiles` |

Choose one or both files in the sidebar and click **Upload dataset**.
An omitted counterpart remains empty rather than loading sample data.

## Source organization

```text
artifacts/assay-bench/
  app.py                 Streamlit page, controls, and tabs
  server.py              Original server entry point
  ABOUT.md               Plain-language guide
  assay_app/
    data.py              CSV validation, ID matching, and joining
    uploads.py           Submitted-file loading
    fitting.py           Four-parameter logistic fitting
    analysis.py          Compound summaries and fit status
    plots.py             Plotly chart construction
    molecules.py         RDKit structures and descriptors
    tables.py            Summary row highlighting
  tests/                 Fitting, plotting, upload, and selection regression tests
attached_assets/         Supplied sample CSVs
pyproject.toml            Python dependencies
uv.lock                  Python dependency lockfile
```

The other `artifacts/`, `lib/`, and `scripts/` directories preserve the
workspace's supporting code. They are not needed to run the Python app.
Replit-internal metadata, credentials, installed dependencies, generated
caches, and earlier exports are excluded from this source snapshot.

## Tests

```bash
python -m unittest discover -s artifacts/assay-bench/tests -v
```

## Add the code to GitHub

Create a **public** repository named `Assay-Compound-Explorer_ProjWeek1`.
Unzip the source archive and upload its contents, not the ZIP file itself.
Do not add credentials or private datasets to a public repository.
