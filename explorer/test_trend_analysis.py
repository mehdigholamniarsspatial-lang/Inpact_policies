"""Focused tests for optional segment-level Trend Analysis diagnostics."""
import json
from unittest.mock import patch

import numpy as np
from django.test import TestCase


class SegmentMannKendallApiTests(TestCase):
    endpoint = "/api/trend/fit/"

    def _fit(self, breakpoints=None, enabled=True):
        return self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "gas": "CO₂",
                    "sector": "Energy Industries",
                    "method": "ols",
                    "confidence": 0.95,
                    "breakpoints": breakpoints or [],
                    "mann_kendall_segments": enabled,
                }
            ),
            content_type="application/json",
        )

    def test_disabled_preserves_existing_fit_without_segment_tests(self):
        response = self._fit(enabled=False)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["segment_mann_kendall_enabled"])
        self.assertEqual(body["segment_mann_kendall"], [])
        self.assertIn("mann_kendall", body)

    def test_one_segment_gets_one_mann_kendall_result(self):
        body = self._fit().json()
        self.assertEqual(len(body["segments"]), 1)
        self.assertEqual(len(body["segment_mann_kendall"]), 1)
        self.assertEqual(body["segment_mann_kendall"][0]["segment"], 1)

    def test_two_segments_get_independent_results(self):
        body = self._fit([2007]).json()
        self.assertEqual(len(body["segments"]), 2)
        self.assertEqual(len(body["segment_mann_kendall"]), 2)
        for segment, mk in zip(body["segments"], body["segment_mann_kendall"]):
            self.assertEqual(mk["segment"], segment["Segment"])
            self.assertEqual(mk["n"], segment["N"])
            self.assertEqual(mk["period"], f'{segment["Start"]:g}–{segment["End"]:g}')

    def test_multiple_segments_each_get_a_result(self):
        body = self._fit([2000, 2010, 2020]).json()
        self.assertEqual(len(body["segments"]), 4)
        self.assertEqual(len(body["segment_mann_kendall"]), 4)
        self.assertEqual(
            [row["segment"] for row in body["segment_mann_kendall"]],
            [1, 2, 3, 4],
        )

    @patch("explorer.trend_views._get_series")
    def test_constant_segment_is_valid_and_not_significant(self, get_series):
        years = np.arange(2000, 2006, dtype=float)
        get_series.return_value = (
            years,
            np.full(years.shape, 4.0),
            {"n_raw": 6, "n_used": 6, "n_dropped": 0},
        )
        body = self._fit().json()
        mk = body["segment_mann_kendall"][0]
        self.assertEqual(mk["S"], 0)
        self.assertEqual(mk["Z"], 0.0)
        self.assertEqual(mk["p_value"], 1.0)
        self.assertFalse(mk["significant"])
        self.assertEqual(mk["sens_slope"], 0.0)

    @patch("explorer.trend_views._get_series")
    def test_insufficient_clean_data_returns_422(self, get_series):
        get_series.return_value = (
            np.array([2000.0, 2002.0]),
            np.array([1.0, 3.0]),
            {"n_raw": 4, "n_used": 2, "n_dropped": 2},
        )
        response = self._fit()
        self.assertEqual(response.status_code, 422)
        self.assertIn("Too few valid data points", response.json()["detail"])
