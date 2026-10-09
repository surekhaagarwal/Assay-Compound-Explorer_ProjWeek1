import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from assay_app.analysis import analyze_compounds, lowest_dose_warnings
from assay_app.fitting import fit_four_parameter_logistic, four_parameter_logistic


def measurements(bottom=0, top=100, log_ic50=2, slope=1.2, compound_id="A"):
    x = np.logspace(-2, 5, 16)
    return pd.DataFrame(
        {
            "compound_id": compound_id,
            "conc_nM": x,
            "response_pct": four_parameter_logistic(x, bottom, top, log_ic50, slope),
        }
    )


class ResponseLimitTests(unittest.TestCase):
    def test_default_fits_constrain_both_response_limits(self):
        for bottom, top, slope in [(-20, 130, 1.2), (-10, 120, -1.2)]:
            with self.subTest(slope=slope):
                fit = fit_four_parameter_logistic(
                    measurements(bottom=bottom, top=top, slope=slope)
                )
                self.assertEqual(fit.status, "success")
                self.assertGreaterEqual(fit.bottom, 0)
                self.assertLessEqual(fit.bottom, fit.top)
                self.assertLessEqual(fit.top, 105)
                self.assertGreaterEqual(float(fit.curve_y.min()), 0)
                self.assertLessEqual(float(fit.curve_y.max()), 105)

    def test_fixed_limits_fit_both_increasing_and_decreasing_curves(self):
        for slope in [1.2, -1.2]:
            with self.subTest(slope=slope):
                fit = fit_four_parameter_logistic(
                    measurements(log_ic50=2.3, slope=slope),
                    fix_response_limits=True,
                )
                self.assertEqual(fit.status, "success")
                self.assertEqual((fit.bottom, fit.top), (0, 100))
                self.assertAlmostEqual(fit.log_ic50, 2.3, places=5)
                self.assertAlmostEqual(fit.hill_slope, slope, places=5)

    def test_initial_guess_is_bounded_when_measured_responses_exceed_105(self):
        fit = fit_four_parameter_logistic(measurements(bottom=110, top=140))
        self.assertEqual(fit.status, "success")
        self.assertLessEqual(fit.top, 105)

    def test_analysis_uses_fix_setting_without_changing_the_measurements(self):
        data = measurements(bottom=40, top=90)
        original = data.copy(deep=True)
        free, _ = analyze_compounds(data, ["A"])
        fixed, _ = analyze_compounds(data, ["A"], fix_response_limits=True)
        self.assertAlmostEqual(free["A"].bottom, 40, places=3)
        self.assertAlmostEqual(free["A"].top, 90, places=3)
        self.assertEqual((fixed["A"].bottom, fixed["A"].top), (0, 100))
        self.assertFalse(np.allclose(free["A"].curve_y, fixed["A"].curve_y))
        pd.testing.assert_frame_equal(data, original)

    def test_unidentifiable_data_remains_an_explicit_fit_failure(self):
        for fixed in [False, True]:
            for data in [
                measurements().iloc[:3],
                measurements().assign(response_pct=50.0),
                measurements().iloc[:0],
            ]:
                self.assertNotEqual(
                    fit_four_parameter_logistic(data, fixed).status, "success"
                )


class LowDoseWarningTests(unittest.TestCase):
    def test_low_dose_warning_uses_replicate_mean_and_strict_20_percent_cutoff(self):
        data = pd.DataFrame(
            {
                "compound_id": ["A", "A", "A", "B", "B", "C", "C", "C"],
                "conc_nM": [1, 1, 100, 1, 100, 1, 1, 100],
                "response_pct": [35, 45, 100, 20, 100, 100, -80, 100],
            }
        )
        warning = lowest_dose_warnings(data)
        self.assertEqual(warning["compound_id"].tolist(), ["A"])
        self.assertEqual(warning["response_pct"].tolist(), [40])
        self.assertEqual(warning["conc_nM"].tolist(), [1])
        self.assertTrue(lowest_dose_warnings(data.iloc[:0]).empty)


class FitSettingUITests(unittest.TestCase):
    def test_toggle_recalculates_selected_compounds_and_home_restores_defaults(self):
        app = AppTest.from_file(str(APP_DIR / "app.py"))
        data = pd.concat(
            [
                measurements(bottom=40, top=90, log_ic50=3),
                measurements(compound_id="B"),
            ],
            ignore_index=True,
        )
        structures = pd.DataFrame(
            {"compound_id": ["A", "B"], "smiles": ["CCO", "CC"]}
        )
        app.session_state["active_dataset"] = (data, structures, [])
        app.session_state["dataset_revision"] = 1
        app.session_state["dataset_names"] = ("test-dose.csv", "test-structures.csv")
        app.run(timeout=60)
        self.assertFalse(app.exception)
        initial_ic50 = app.dataframe[0].value.iloc[0]["IC₅₀ (nM)"]
        self.assertAlmostEqual(initial_ic50, 1000, places=2)
        self.assertTrue(any("A:" in warning.value for warning in app.warning))

        app.checkbox[1].check().run(timeout=60)
        app.sidebar.toggle[0].set_value(True).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(app.sidebar.selectbox[0].value, "All fit statuses")
        self.assertTrue(all(box.value for box in app.checkbox))
        summary = app.dataframe[0].value
        self.assertEqual(set(summary["compound_id"]), {"A", "B"})
        fixed_ic50 = summary.loc[
            summary["compound_id"] == "A", "IC₅₀ (nM)"
        ].iloc[0]
        self.assertFalse(np.isclose(initial_ic50, fixed_ic50))

        app.sidebar.toggle[0].set_value(False).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertAlmostEqual(
            app.dataframe[0].value.iloc[0]["IC₅₀ (nM)"], initial_ic50, places=3
        )
        app.checkbox[0].uncheck().run(timeout=60)
        self.assertFalse(any("Large response" in warning.value for warning in app.warning))

        app.sidebar.toggle[0].set_value(True).run(timeout=60)
        next(button for button in app.sidebar.button if button.label == "Home").click().run(
            timeout=60
        )
        self.assertFalse(app.exception)
        self.assertFalse(app.sidebar.toggle[0].value)
        self.assertEqual(app.checkbox[0].label, "CPD-0001")
        self.assertEqual(sum(box.value for box in app.checkbox), 1)


if __name__ == "__main__":
    unittest.main()
