## About Assay Bench

**Assay Bench helps you compare how different chemicals behave in a laboratory
test.** It brings together the test results and a picture of each chemical, so
you can see patterns and decide which results deserve a closer look.

You do not need a biology background to understand the main idea:

- A **compound** is a chemical substance being tested.
- An **assay** is a laboratory test that measures a response.
- A **dose-response experiment** tests several concentrations of a compound to
  see how the response changes as more of it is added.

### What the app does

The app matches two CSV files using each compound's ID: one file contains the
test measurements, and the other describes the chemical structures. It flags
IDs that appear in only one file, draws dose-response curves, estimates IC50
values, and shows the chemicals' structures and properties.

### How to read the Assay Results tab

- **Across the chart:** concentration, meaning how much compound is present in
  the test liquid. The unit **nM** means nanomolar, a unit for very small
  concentrations. The axis uses a logarithmic scale, so equal steps represent
  equal multiplication, such as 10 to 100 to 1,000.
- **Up the chart:** the test's response, expressed as a percentage. Whether a
  higher or lower response is desirable depends on the particular test.
- **Dots:** individual measurements and averages where measurements were
  repeated. Vertical bars show how much repeated measurements vary.
- **Smooth lines:** mathematical estimates of the overall pattern. The app
  uses a **four-parameter logistic fit**, which adjusts the curve's lower level,
  upper level, halfway concentration, and steepness.
- **Colors and legend:** each compound has its own color. The legend identifies
  it and shows its estimated IC50 in nM, or says it could not be estimated.
- **Dashed vertical lines:** each marks a compound's estimated IC50 and matches
  its curve's color. The concentration axis expands to include estimates outside
  the tested range; those estimates still require caution.

### What does the curve fitting toggle do?

In the sidebar, under **Curve fitting**, you will find **Fix bottom/top at
0% / 100%**. This changes the assumptions used to draw the fitted curve.

The **bottom** is the curve's lower response level, and the **top** is its upper
response level. These describe the levels where the curve becomes flat; they
are not necessarily the smallest and largest measured values.

| Toggle setting | What the app does |
| --- | --- |
| **Off — default** | Estimates the bottom and top from the measurements, keeping both between 0% and 105%. It also estimates the halfway concentration and the curve's steepness. |
| **On** | Holds the bottom at exactly 0% and the top at exactly 100%. It estimates only the halfway concentration and steepness. |

**When should I turn it on?** Use fixed limits when the test's reference
measurements justify treating 0% as no response and 100% as a full response.
Leave it off when the lower and upper response levels need to be estimated
from the data. Fixing the limits can help comparison between compounds, but
incorrect assumptions can make the fit worse or change the IC50 estimate.

**Why can IC50 change?** With the toggle off, IC50 is halfway between the
estimated bottom and top. With it on, that halfway response is exactly 50%.
Changing the limits changes the fitted model, so the estimated IC50, curve,
fit score, and fit status may change.

The toggle **does not change or rescale your measured data**. It also does not
replace missing measurements or make an incomplete curve reliable. The low-dose
warning can still appear with either setting.

Changing the toggle recalculates the results while keeping your compound
checkbox selections. **Fit status** resets to **All fit statuses** so a changed
classification does not hide a selected compound. **Home** restores the sample
files and turns the toggle off.

### What does IC50 mean here?

**IC50 is the estimated concentration at the halfway point between the fitted
curve's lower and upper response levels.** For example, if those levels are
20% and 60%, the halfway response is 40%—not 50%.

In a test that measures inhibition, this halfway concentration helps describe
how much compound is needed to reduce the measured activity. The app can also
fit curves where the reported response increases with concentration.

When comparing comparable results from the same test, a smaller IC50 means a
lower concentration reaches that halfway point. **It does not, by itself, prove
that a compound is effective, safe, or a better medicine.**

The app warns if the **average response at a compound's lowest tested
concentration is greater than 20%**. For an increasing-response assay, this may
mean the tested doses missed the low-response baseline and the IC50 estimate
is less reliable, even if its fit status is green. This is a screening warning,
not a statistical certainty or an activity classification. A high response
at the lowest dose can be normal for a decreasing-response assay.

### What do fit status and row colors mean?

The compound summary helps you judge how much confidence to place in an estimate:

- **Within tested range — light green:** the estimated IC50 falls within the
  concentrations actually tested, and the curve passes the app's fit-quality
  check.
- **Extrapolated IC50 — light red:** the estimate is outside the tested
  concentrations. It depends on extending the mathematical model beyond the
  measurements and needs extra caution.
- **Low R² — light red:** the fitted curve does not follow the measurements
  closely enough for the app's quality check. R² is a fit score; values closer
  to 1 generally mean a closer match.
- **Other red statuses:** there may be too few different concentrations, an
  unchanged response, or a failed calculation. An IC50 may not be available.

**Green and red describe the mathematical fit, not whether a compound is active
or inactive against a biological target.** A target is a part of a living
system, such as a protein, that scientists want to affect.

### What is in the compound viewer?

This tab shows a **2D molecular structure**: a simplified map of the chemical's
atoms and their connections, not a photograph or its actual 3D shape.

Below each picture is its **SMILES string**, a computer-readable way to write
that structure, and a table of calculated properties:

- **Molecular formula:** which types of atoms it contains and how many.
- **Molecular weight:** a measure of how heavy the molecule is.
- **LogP and TPSA:** estimates related to how a molecule interacts with oily or
  watery environments.
- **Hydrogen-bond donors and acceptors:** features that can form weak
  attractions with other molecules.
- **Rotatable bonds and ring count:** flexible connections and closed loops
  within the molecule.

These properties help describe a chemical; they do not establish its safety
or biological effect.

### A quick way to use the app

1. Start with the supplied sample data, or expand **Upload CSV datasets** in the
   sidebar, choose your files, and click **Upload dataset**. Browsing for a file
   does not change the displayed dataset until you click that button. Each upload
   replaces the previous dataset. You can supply one or both files; a missing
   file stays empty rather than being replaced with sample data.
2. On first load, only the first compound is selected. The **Fit status** filter
   shows that compound's calculated status. These selections reset for each
   successfully uploaded dataset.
3. Change **Fit status** to automatically select all compounds with that status.
   Choosing **All fit statuses** selects every compound.
4. Use the compound checkboxes to narrow the selection. **Select all compounds** checks
   every compound, while the active fit-status filter still limits what is
   shown. **Clear all selections**, above the fit-status filter, resets **Fit status**
   to **All fit statuses** and unchecks every compound, clearing both data tabs.
5. Compare the chart and summary, then open **compound viewer** for the same
   compounds' structures. You can download the selected merged measurements
   from **Assay Results**.
6. Click the **Home** button with the house icon at the top of the sidebar to
   return to the supplied sample files. It clears pending uploads and resets
   the filters to the first sample compound and its fit status.

For your own data, use these exact CSV column names:

- **Dose-response file:** `compound_id`, `conc_nM`, `response_pct`.
- **Chemical structures file:** `compound_id`, `smiles`.

### Keep the limits in mind

A good-looking curve is not proof that a chemical will work in living cells
or people. The app does not identify the biological target or automatically
decide which compounds are active. Those conclusions require understanding the
test, its controls, and additional experiments.
