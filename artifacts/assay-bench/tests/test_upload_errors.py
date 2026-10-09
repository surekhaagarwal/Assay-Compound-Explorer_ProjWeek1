"""Run with: .pythonlibs/bin/python -m unittest discover -s artifacts/assay-bench/tests"""

from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest


APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

VALID_DOSE = (
    "compound_id,conc_nM,response_pct\n"
    "A,1,1\nA,10,9\nA,100,50\nA,1000,91\nA,10000,99\nB,10,20\n"
)
VALID_STRUCTURES = "compound_id,smiles\nA,CCO\nB,CC\n"
INVALID_CASES = {
    "missing dose column": (
        "compound_id,conc_nM\nA,10\n",
        VALID_STRUCTURES,
        "dose-response CSV is missing required columns: response_pct.",
    ),
    "missing structure column": (
        VALID_DOSE,
        "compound_id\nA\n",
        "structure CSV is missing required columns: smiles.",
    ),
    "malformed CSV": (
        'compound_id,conc_nM,response_pct\nA,10,"unterminated\n',
        VALID_STRUCTURES,
        "Error tokenizing data",
    ),
    "no compound IDs": (
        "compound_id,conc_nM,response_pct\n",
        "compound_id,smiles\n",
        "The uploaded files contain no compounds.",
    ),
    "blank compound ID": (
        "compound_id,conc_nM,response_pct\n ,10,20\n",
        VALID_STRUCTURES,
        "dose-response CSV has 1 row(s) with a missing compound_id.",
    ),
}


class UploadErrorsTest(unittest.TestCase):
    def setUp(self):
        self.uploads = {}
        original_uploader = st.file_uploader

        def uploaded_csv(*args, **kwargs):
            # AppTest has no uploader setter. Keep the real upload controls,
            # but provide file bytes at that boundary; parsing remains real.
            original_uploader(*args, **kwargs)
            contents = self.uploads.get(kwargs["key"].split(":")[0])
            if contents is None:
                return None
            file = BytesIO(contents.encode("utf-8"))
            file.name = f"{kwargs['key']}.csv"
            return file

        uploader_patch = patch("streamlit.file_uploader", side_effect=uploaded_csv)
        uploader_patch.start()
        self.addCleanup(uploader_patch.stop)
        self.app = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=30)

    def upload(self, dose, structures):
        self.uploads.update(
            dose_response_upload=dose,
            structures_upload=structures,
        )
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        next(
            button for button in self.app.sidebar.button
            if button.label == "Upload dataset"
        ).click().run()
        self.assertEqual(len(self.app.exception), 0)

    def assert_guide(self):
        self.assertEqual(
            [tab.label for tab in self.app.tabs],
            ["Assay Results", "compound viewer", "About the app"],
        )
        self.assertEqual(
            self.app.tabs[2].markdown[0].value,
            (APP_DIR / "ABOUT.md").read_text(encoding="utf-8").strip(),
        )
        self.assertEqual(len(self.app.get("file_uploader")), 2)

    def assert_invalid(self, expected_error):
        self.assert_guide()
        self.assertEqual(len(self.app.error), 1)
        self.assertIn(expected_error, self.app.error[0].value)
        for tab in self.app.tabs[:2]:
            self.assertEqual(len(tab.info), 1)
            self.assertIn("Correct the CSV files", tab.info[0].value)
        for element_type in ("plotly_chart", "dataframe", "table", "image", "download_button"):
            self.assertEqual(len(self.app.get(element_type)), 0, element_type)
        self.assertEqual(len(self.app.sidebar.checkbox), 0)
        self.assertEqual(len(self.app.sidebar.selectbox), 0)
        self.assertEqual(len(self.app.sidebar.success), 0)
        self.assertFalse(any("assay rows" in caption.value for caption in self.app.caption))

    def assert_valid(self, expected_first=None):
        self.assert_guide()
        self.assertEqual(len(self.app.error), 0)
        self.assertEqual(len(self.app.get("plotly_chart")), 1)
        self.assertEqual(len(self.app.tabs[0].dataframe), 2)
        self.assertGreater(len(self.app.tabs[1].get("image")), 0)
        self.assertEqual(len(self.app.tabs[1].table), 1)
        self.assertEqual(len(self.app.get("download_button")), 1)
        boxes = self.app.sidebar.checkbox
        first_id = expected_first or boxes[0].label
        self.assertEqual([box.label for box in boxes if box.value], [first_id])
        summary = self.app.tabs[0].dataframe[0].value
        self.assertEqual(summary["compound_id"].tolist(), [first_id])
        self.assertEqual(self.app.sidebar.selectbox[0].value, summary["Fit status"].iloc[0])

    def test_invalid_uploads_keep_guide_and_hide_analysis(self):
        for name, (dose, structures, error) in INVALID_CASES.items():
            with self.subTest(name=name):
                self.upload(dose, structures)
                self.assert_invalid(error)

    def test_valid_invalid_valid_recovery_never_shows_stale_results(self):
        for name, (dose, structures, error) in INVALID_CASES.items():
            with self.subTest(name=name):
                self.upload(VALID_DOSE, VALID_STRUCTURES)
                self.assert_valid("A")
                # Give both filters non-default state before the invalid rerun.
                self.app.sidebar.selectbox[0].select("All fit statuses").run()
                next(
                    button for button in self.app.sidebar.button
                    if button.label == "Select all compounds"
                ).click().run()
                self.assertEqual(sum(box.value for box in self.app.sidebar.checkbox), 2)
                self.upload(dose, structures)
                self.assert_invalid(error)
                self.upload(VALID_DOSE, VALID_STRUCTURES)
                self.assert_valid("A")

    def test_removing_pending_uploads_does_not_restore_stale_or_sample_data(self):
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assert_valid()
        dose, structures, error = INVALID_CASES["missing dose column"]
        self.upload(dose, structures)
        self.assert_invalid(error)
        self.uploads.clear()
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assert_invalid(error)
        self.upload(VALID_DOSE, VALID_STRUCTURES)
        self.assert_valid("A")

    def test_empty_active_dataset_keeps_guide_and_hides_analysis(self):
        # Cover the defensive no-ID branch independently of upload validation.
        self.app.session_state["active_dataset"] = (
            pd.DataFrame(columns=["compound_id", "conc_nM", "response_pct"]),
            pd.DataFrame(columns=["compound_id", "smiles"]),
            [],
        )
        self.app.session_state["dataset_revision"] = 0
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assert_invalid("No valid compound IDs were found in the uploaded datasets.")


if __name__ == "__main__":
    unittest.main()
