from math import log10

import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative

from assay_app.fitting import CurveFit


def compound_colors(compound_ids: list[str]) -> dict[str, str]:
    """Keep a compound's color stable when the selected subset changes."""
    palette = qualitative.Alphabet
    return {
        compound_id: (
            palette[index]
            if index < len(palette)
            else f"hsl({(index * 137.508) % 360:.3f},65%,45%)"
        )
        for index, compound_id in enumerate(compound_ids)
    }


def dose_response_figure(
    data: pd.DataFrame,
    fits: dict[str, CurveFit],
    compound_ids: list[str],
) -> go.Figure:
    figure = go.Figure()
    colors = compound_colors(compound_ids)
    for compound_id, measurements in data.groupby("compound_id", sort=True):
        fit = fits[compound_id]
        color = colors[compound_id]
        estimated = fit.status == "success" and fit.ic50_nM is not None
        midpoint = (
            f"{fit.ic50_nM:,.3g} nM" if estimated else "not estimated"
        )
        label = f"{compound_id} · IC₅₀ {midpoint}"
        group = {"name": label, "legendgroup": compound_id}
        figure.add_trace(
            go.Scatter(
                x=measurements["conc_nM"],
                y=measurements["response_pct"],
                mode="markers",
                **group,
                showlegend=False,
                marker={"size": 5, "opacity": 0.35, "color": color},
                hovertemplate=(
                    "Concentration: %{x:,.4g} nM<br>Response: %{y:.2f}%"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )
        grouped = measurements.groupby("conc_nM")["response_pct"].agg(
            ["mean", "std"]
        ).reset_index()
        figure.add_trace(
            go.Scatter(
                x=grouped["conc_nM"],
                y=grouped["mean"],
                mode="markers",
                **group,
                showlegend=not estimated,
                marker={"size": 6, "color": color},
                error_y={
                    "type": "data",
                    "array": grouped["std"].fillna(0),
                    "color": color,
                    "visible": True,
                },
                hovertemplate=(
                    "Concentration: %{x:,.4g} nM<br>Mean: %{y:.2f}%"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )
        if estimated and fit.curve_x is not None and fit.curve_y is not None:
            figure.add_trace(
                go.Scatter(
                    x=fit.curve_x,
                    y=fit.curve_y,
                    mode="lines",
                    **group,
                    line={"width": 2.5, "color": color},
                    hovertemplate=(
                        "Concentration: %{x:,.4g} nM<br>Fit: %{y:.2f}%"
                        "<extra>%{fullData.name}</extra>"
                    ),
                )
            )

    figure.update_layout(
        title="Dose–response curves: compound response vs concentration",
        xaxis_title="Concentration (nM)",
        yaxis_title="Response (%)",
        legend={"title": "Compounds", "groupclick": "togglegroup"},
        hovermode="closest",
        height=650 if len(fits) > 10 else 520,
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )
    figure.update_xaxes(
        type="log",
        range=[
            log10(data["conc_nM"].min()) - 0.1,
            log10(data["conc_nM"].max()) + 0.1,
        ],
    )
    return figure
