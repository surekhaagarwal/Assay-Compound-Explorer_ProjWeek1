from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import OptimizeWarning, curve_fit
import warnings


@dataclass
class CurveFit:
    status: str
    bottom: float | None = None
    top: float | None = None
    log_ic50: float | None = None
    hill_slope: float | None = None
    r_squared: float | None = None
    curve_x: np.ndarray | None = None
    curve_y: np.ndarray | None = None

    @property
    def ic50_nM(self) -> float | None:
        if self.log_ic50 is None:
            return None
        return float(10**self.log_ic50)


def four_parameter_logistic(
    concentration_nM: np.ndarray | float,
    bottom: float,
    top: float,
    log_ic50: float,
    hill_slope: float,
) -> np.ndarray:
    log_concentration = np.log10(np.asarray(concentration_nM, dtype=float))
    exponent = np.clip((log_ic50 - log_concentration) * hill_slope, -300, 300)
    return bottom + (top - bottom) / (1 + np.power(10.0, exponent))


def fit_four_parameter_logistic(data: pd.DataFrame) -> CurveFit:
    if data.empty:
        return CurveFit("No dose-response measurements are available.")

    x = data["conc_nM"].to_numpy(dtype=float)
    y = data["response_pct"].to_numpy(dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & (x > 0)
    x, y = x[valid], y[valid]

    if len(np.unique(x)) < 4:
        return CurveFit("At least four distinct positive concentrations are required.")

    log_min, log_max = float(np.log10(x.min())), float(np.log10(x.max()))
    y_min, y_max = float(y.min()), float(y.max())
    if np.isclose(y_min, y_max):
        return CurveFit("The responses are constant; an IC₅₀ cannot be identified.")
    low_mean = float(np.mean(y[x <= np.median(x)]))
    high_mean = float(np.mean(y[x > np.median(x)]))
    initial_slope = 1.0 if high_mean >= low_mean else -1.0

    initial = [
        float(np.percentile(y, 10)),
        float(np.percentile(y, 90)),
        float(np.median([log_min, log_max])),
        initial_slope,
    ]
    lower_bounds = [-200.0, -200.0, log_min - 3.0, -8.0]
    upper_bounds = [300.0, 300.0, log_max + 3.0, 8.0]

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", OptimizeWarning)
            parameters, _ = curve_fit(
                four_parameter_logistic,
                x,
                y,
                p0=initial,
                bounds=(lower_bounds, upper_bounds),
                maxfev=30_000,
            )
        predicted = four_parameter_logistic(x, *parameters)
        residual_sum = float(np.sum((y - predicted) ** 2))
        total_sum = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = (
            1.0 - residual_sum / total_sum if total_sum > 0 else float("nan")
        )
        curve_x = np.logspace(log_min, log_max, 250)
        curve_y = four_parameter_logistic(curve_x, *parameters)
        return CurveFit(
            status="success",
            bottom=float(parameters[0]),
            top=float(parameters[1]),
            log_ic50=float(parameters[2]),
            hill_slope=float(parameters[3]),
            r_squared=r_squared,
            curve_x=curve_x,
            curve_y=curve_y,
        )
    except (RuntimeError, ValueError, OptimizeWarning, FloatingPointError) as exc:
        return CurveFit(f"The 4PL optimizer could not converge ({exc}).")
