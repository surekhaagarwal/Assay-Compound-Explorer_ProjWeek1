"""Regression checks for explicit dataset replacement and shared selection."""

import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from assay_app.uploads import load_uploaded_datasets


def upload(content: str, name: str) -> BytesIO:
    file = BytesIO(content.encode("utf-8"))
    file.name = name
    return file


def dose_csv(ids=("NEW-A", "NEW-B"), midpoint=100.0) -> str:
    rows = ["compound_id,conc_nM,response_pct"]
    for compound_id in ids:
        for concentration in (1, 10, 100, 1000, 10000, 100000):
            response = 100 / (1 + concentration / midpoint)
            rows.append(f"{compound_id},{concentration},{response}")
    return "\n".join(rows) + "\n"


class UploadLoadingTests(unittest.TestCase):
    def test_dose_only_does_not_load_sample_structures(self):
        dose, structures, _ = load_uploaded_datasets(
            upload(dose_csv(), "dose.csv"), None
        )
        self.assertEqual(set(dose["compound_id"]), {"NEW-A", "NEW-B"})
        self.assertTrue(structures.empty)

    def test_structure_only_does_not_load_sample_assay(self):
        dose, structures, _ = load_uploaded_datasets(
            None, upload("compound_id,smiles\nSTRUCTURE-ONLY,CCO\n", "structures.csv")
        )
        self.assertTrue(dose.empty)
        self.assertEqual(set(structures["compound_id"]), {"STRUCTURE-ONLY"})

    def test_requires_at_least_one_nonempty_valid_file(self):
        with self.assertRaisesRegex(ValueError, "Choose at least one"):
            load_uploaded_datasets(None, None)
        with self.assertRaisesRegex(ValueError, "no compounds"):
            load_uploaded_datasets(
                upload("compound_id,conc_nM,response_pct\n", "empty.csv"), None
            )
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            load_uploaded_datasets(upload("compound_id,value\nA,10\n", "bad.csv"), None)


class HomeResetTests(unittest.TestCase):
    def test_home_restores_samples_after_upload_and_validation_error(self):
        app = AppTest.from_file(str(APP_DIR / "app.py")).run(timeout=60)
        self.assertFalse(app.exception)
        initial_status = app.sidebar.selectbox[0].value
        initial_upload_ids = [item.proto.id for item in app.get("file_uploader")]
        original_dose, original_structures, _ = app.session_state["active_dataset"]
        app.sidebar.selectbox[0].select("All fit statuses").run(timeout=60)
        self.assertTrue(all(box.value for box in app.checkbox))

        app.session_state["active_dataset"] = load_uploaded_datasets(
            upload(dose_csv(), "new-dose.csv"),
            upload("compound_id,smiles\nNEW-A,C\nNEW-B,CC\n", "new-structures.csv"),
        )
        app.session_state["dataset_revision"] = 4
        app.session_state["dataset_names"] = ("new-dose.csv", "new-structures.csv")
        app.run(timeout=60)
        self.assertEqual([box.label for box in app.checkbox], ["NEW-A", "NEW-B"])

        def home():
            next(
                button for button in app.sidebar.button if button.label == "Home"
            ).click().run(timeout=60)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertEqual(app.session_state["dataset_revision"], 0)
            dose, structures, _ = app.session_state["active_dataset"]
            self.assertTrue(dose.equals(original_dose))
            self.assertTrue(structures.equals(original_structures))
            self.assertEqual(app.checkbox[0].label, "CPD-0001")
            self.assertEqual(sum(box.value for box in app.checkbox), 1)
            self.assertTrue(app.checkbox[0].value)
            self.assertEqual(app.sidebar.selectbox[0].value, initial_status)
            self.assertEqual(len(app.tabs[1].table), 1)

        home()
        self.assertEqual(app.session_state["home_revision"], 1)
        self.assertTrue(
            set(initial_upload_ids).isdisjoint(
                item.proto.id for item in app.get("file_uploader")
            )
        )
        with self.assertRaises(KeyError):
            app.session_state["dataset_names"]

        # Home remains available when a failed upload has hidden the results.
        app.session_state["dataset_error"] = "Invalid uploaded CSV."
        app.run(timeout=60)
        self.assertTrue(app.error)
        home()
        self.assertEqual(app.session_state["home_revision"], 2)
        with self.assertRaises(KeyError):
            app.session_state["dataset_error"]
        next(
            button for button in app.sidebar.button
            if button.label == "Clear all selections"
        ).click().run(timeout=60)
        self.assertFalse(any(box.value for box in app.checkbox))
        home()
        self.assertEqual(app.session_state["home_revision"], 3)


class FilterResetTests(unittest.TestCase):
    def test_clear_resets_both_filters_without_selecting_all_compounds(self):
        app = AppTest.from_file(str(APP_DIR / "app.py")).run(timeout=60)
        self.assertFalse(app.exception)
        self.assertEqual(sum(box.value for box in app.checkbox), 1)
        self.assertNotEqual(app.sidebar.selectbox[0].value, "All fit statuses")

        def clear():
            next(
                button for button in app.sidebar.button
                if button.label == "Clear all selections"
            ).click().run(timeout=60)
            self.assertFalse(app.exception)
            self.assertEqual(app.sidebar.selectbox[0].value, "All fit statuses")
            self.assertFalse(any(box.value for box in app.checkbox))
            self.assertEqual(len(app.tabs[0].dataframe), 0)
            self.assertEqual(len(app.tabs[1].table), 0)
            self.assertTrue(app.tabs[0].info)
            self.assertTrue(app.tabs[1].info)

        clear()
        app.run(timeout=60)
        self.assertFalse(any(box.value for box in app.checkbox))
        # Resetting the status programmatically must not invoke its select-all
        # callback. The user can still manually select compounds afterward.
        app.checkbox[-1].check().run(timeout=60)
        self.assertEqual(len(app.tabs[0].dataframe[0].value), 1)
        self.assertEqual(len(app.tabs[1].table), 1)
        status = next(
            option for option in app.sidebar.selectbox[0].options
            if option != "All fit statuses"
        )
        app.sidebar.selectbox[0].select(status).run(timeout=60)
        self.assertTrue(any(box.value for box in app.checkbox))
        clear()


class DatasetReplacementTests(unittest.TestCase):
    def test_submit_replace_reset_and_invalid_recovery(self):
        # AppTest cannot operate native file uploaders. Patch only their values;
        # exercise the real form button, state, filters, tables, and fit pipeline.
        pending = {"Dose-response CSV": None, "Chemical structures CSV": None}
        with patch("streamlit.file_uploader", side_effect=lambda label, **_: pending[label]):
            app = AppTest.from_file(str(APP_DIR / "app.py")).run(timeout=60)
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["dataset_revision"], 0)
            self.assertEqual(sum(box.value for box in app.checkbox), 1)

            pending["Dose-response CSV"] = upload(dose_csv(), "new-dose.csv")
            pending["Chemical structures CSV"] = upload(
                "compound_id,smiles\nNEW-A,C\nNEW-B,CC\n", "new-structures.csv"
            )
            app.run(timeout=60)
            self.assertEqual(app.session_state["dataset_revision"], 0)
            self.assertIn("CPD-0001", set(app.session_state["active_dataset"][0]["compound_id"]))

            def submit():
                next(button for button in app.button if button.label == "Upload dataset").click().run(timeout=60)
                self.assertFalse(app.exception)

            submit()
            self.assertFalse(app.error)
            self.assertEqual([box.label for box in app.checkbox], ["NEW-A", "NEW-B"])
            self.assertEqual([box.value for box in app.checkbox], [True, False])
            self.assertEqual(app.dataframe[0].value.iloc[0]["compound_id"], "NEW-A")
            self.assertAlmostEqual(app.dataframe[0].value.iloc[0]["IC₅₀ (nM)"], 100, places=2)
            self.assertEqual(len(app.tabs[1].table), 1)
            self.assertEqual(app.sidebar.selectbox[0].value, app.dataframe[0].value.iloc[0]["Fit status"])

            app.sidebar.selectbox[0].select("All fit statuses").run(timeout=60)
            self.assertEqual(len(app.dataframe[0].value), 2)
            pending["Dose-response CSV"] = upload(dose_csv(midpoint=1000), "replacement-dose.csv")
            pending["Chemical structures CSV"] = upload(
                "compound_id,smiles\nNEW-A,CCC\nNEW-B,CCCC\n", "replacement-structures.csv"
            )
            submit()
            self.assertEqual([box.value for box in app.checkbox], [True, False])
            self.assertNotEqual(app.sidebar.selectbox[0].value, "All fit statuses")
            self.assertAlmostEqual(app.dataframe[0].value.iloc[0]["IC₅₀ (nM)"], 1000, places=2)
            self.assertEqual(set(app.dataframe[1].value["smiles"]), {"CCC"})
            self.assertIn("C3H8", app.tabs[1].table[0].value["Value"].tolist())

            pending["Dose-response CSV"] = upload("compound_id,value\nBAD,5\n", "invalid.csv")
            submit()
            self.assertTrue(app.tabs[0].error)
            self.assertEqual(len(app.dataframe), 0)
            self.assertEqual(len(app.tabs[1].table), 0)
            self.assertTrue(app.tabs[2].markdown)

            pending["Dose-response CSV"] = upload(dose_csv(("ONLY-NEW",)), "dose-only.csv")
            pending["Chemical structures CSV"] = None
            submit()
            self.assertFalse(app.error)
            self.assertEqual([box.label for box in app.checkbox], ["ONLY-NEW"])
            dose, structures, _ = app.session_state["active_dataset"]
            self.assertTrue(structures.empty)
            self.assertEqual(set(dose["compound_id"]), {"ONLY-NEW"})
            records = next(
                frame.value for frame in app.dataframe
                if "smiles" in frame.value.columns
            )
            self.assertTrue(records["smiles"].isna().all())
            self.assertEqual(len(app.tabs[1].table), 0)

            pending["Dose-response CSV"] = None
            pending["Chemical structures CSV"] = upload(
                "compound_id,smiles\nSTRUCTURE-ONLY,CCO\n", "structure-only.csv"
            )
            submit()
            self.assertFalse(app.error)
            self.assertEqual([box.label for box in app.checkbox], ["STRUCTURE-ONLY"])
            self.assertTrue(app.session_state["active_dataset"][0].empty)
            self.assertEqual(len(app.tabs[1].table), 1)
            self.assertTrue(app.tabs[0].info)


if __name__ == "__main__":
    unittest.main()
