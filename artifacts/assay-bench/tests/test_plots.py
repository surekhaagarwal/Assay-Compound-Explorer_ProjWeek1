import sys
import unittest
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assay_app.fitting import CurveFit
from assay_app.plots import dose_response_figure


class ConcentrationAxisTests(unittest.TestCase):
    def test_log_axis_has_decade_ticks_units_and_untransformed_measurements(self):
        concentrations = [0.1, 1.0, 10.0, 100.0, 1000.0]
        data = pd.DataFrame(
            {
                "compound_id": ["TEST-1"] * len(concentrations),
                "conc_nM": concentrations,
                "response_pct": [0.0, 10.0, 50.0, 90.0, 100.0],
            }
        )
        figure = dose_response_figure(
            data, {"TEST-1": CurveFit(status="failed")}, ["TEST-1"]
        )
        axis = figure.layout.xaxis
        self.assertEqual(axis.type, "log")
        self.assertEqual(axis.dtick, 1)
        self.assertEqual(axis.tickformat, "~g")
        self.assertEqual(axis.title.text, "Concentration (nM, log₁₀ scale)")
        self.assertAlmostEqual(axis.range[0], -1.1)
        self.assertAlmostEqual(axis.range[1], 3.1)
        self.assertEqual(list(figure.data[0].x), concentrations)
        self.assertFalse(any(trace.line.dash == "dash" for trace in figure.data))

    def test_ic50_lines_match_each_curve_and_include_extrapolated_estimates(self):
        data = pd.DataFrame(
            {
                "compound_id": ["A"] * 3 + ["B"] * 3,
                "conc_nM": [1.0, 10.0, 100.0] * 2,
                "response_pct": [0.0, 50.0, 100.0] * 2,
            }
        )
        fits = {
            compound_id: CurveFit(
                status="success",
                log_ic50=np.log10(ic50),
                curve_x=np.array([1.0, 10.0, 100.0]),
                curve_y=np.array([0.0, 50.0, 100.0]),
            )
            for compound_id, ic50 in [("A", 10.0), ("B", 1000.0)]
        }
        figure = dose_response_figure(data, fits, ["A", "B"])
        lines = [trace for trace in figure.data if trace.line.dash == "dash"]
        self.assertEqual(len(lines), 2)
        for line, compound_id, ic50 in zip(lines, ["A", "B"], [10.0, 1000.0]):
            self.assertEqual(list(line.x), [ic50, ic50])
            self.assertEqual(list(line.y), [0.0, 100.0])
            self.assertEqual(line.legendgroup, compound_id)
            self.assertFalse(line.showlegend)
            self.assertIn("IC₅₀", line.hovertemplate)
            self.assertIn("nM", line.hovertemplate)
            curve = next(
                trace for trace in figure.data
                if trace.legendgroup == compound_id
                and trace.mode == "lines"
                and trace.line.dash != "dash"
            )
            self.assertEqual(line.line.color, curve.line.color)
        self.assertNotEqual(lines[0].line.color, lines[1].line.color)
        self.assertGreater(10 ** figure.layout.xaxis.range[1], 1000.0)


if __name__ == "__main__":
    unittest.main()
