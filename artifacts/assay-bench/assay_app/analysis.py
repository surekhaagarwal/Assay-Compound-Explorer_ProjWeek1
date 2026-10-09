import pandas as pd

from assay_app.fitting import CurveFit, fit_four_parameter_logistic


def analyze_compounds(
    data: pd.DataFrame,
    compound_ids: list[str],
) -> tuple[dict[str, CurveFit], pd.DataFrame]:
    """Fit each selected compound independently and retain unreliable-fit flags."""
    fits = {}
    summaries = []
    for compound_id in compound_ids:
        measurements = data.loc[data["compound_id"] == compound_id]
        fit = fit_four_parameter_logistic(measurements)
        fits[compound_id] = fit
        highest_response = None
        if not measurements.empty:
            highest_dose = measurements["conc_nM"].max()
            highest_response = measurements.loc[
                measurements["conc_nM"] == highest_dose, "response_pct"
            ].mean()

        notes = []
        if fit.status == "success":
            if fit.r_squared < 0.8:
                notes.append("Low R² — uncertain estimate")
            if not (
                measurements["conc_nM"].min()
                <= fit.ic50_nM
                <= measurements["conc_nM"].max()
            ):
                notes.append("Extrapolated IC₅₀")
        else:
            notes.append(fit.status)
        summaries.append(
            {
                "compound_id": compound_id,
                "IC₅₀ (nM)": fit.ic50_nM,
                "R²": fit.r_squared,
                "Highest-dose response (%)": highest_response,
                "Fit status": "; ".join(notes) or "Within tested range",
            }
        )
    return fits, pd.DataFrame(summaries)
