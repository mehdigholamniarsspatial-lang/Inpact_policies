"""Smoke and integrity tests. Run with: python manage.py test policies"""
import re
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import PolicySeries, PolicyYear, SelectionCandidate


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("load_policy_data", verbosity=0)

    def test_dataset_shape_matches_release(self):
        self.assertEqual(PolicySeries.objects.count(), 47)
        self.assertEqual(PolicyYear.objects.count(), 1128)
        self.assertEqual(SelectionCandidate.objects.count(), 115)
        core = PolicySeries.objects.exclude(layer="residual").values("policy_id").distinct().count()
        self.assertEqual(core, 34)

    def test_every_series_has_24_years(self):
        for s in PolicySeries.objects.all():
            self.assertEqual(s.years.count(), 24, s.slug)

    def test_intensity_formula_for_core_rows(self):
        for y in PolicyYear.objects.select_related("series").exclude(series__layer="residual")[:400]:
            s = y.series
            expected = y.implementation_level * s.coverage_share * s.bindingness
            self.assertAlmostEqual(y.intensity_index, expected, places=4, msg=s.slug)

    def test_pages_render(self):
        slug = PolicySeries.objects.first().slug
        for name, kwargs in [("overview", {}), ("timeline", {}), ("categories", {}), ("explorer", {}),
                             ("capmf", {}), ("method", {}), ("detail", {"slug": slug})]:
            r = self.client.get(reverse(f"policies:{name}", kwargs=kwargs))
            self.assertEqual(r.status_code, 200, name)

    def test_api_and_export(self):
        r = self.client.get(reverse("policies:api_series"))
        self.assertEqual(len(r.json()["series"]), 47)
        r = self.client.get(reverse("policies:api_capmf") + "?level=3")
        self.assertEqual(len(r.json()["categories"]), 56)
        r = self.client.get(reverse("policies:api_year", args=[2015]))
        self.assertEqual(len(r.json()["rows"]), 47)
        r = self.client.get(reverse("policies:export_csv") + "?sector=Waste")
        lines = r.content.decode().strip().splitlines()
        self.assertEqual(len(lines), 25)  # header + 24 years


class PublicationTextTests(TestCase):
    """Public pages, the API and the download must contain no internal build wording."""

    BANNED = re.compile(r"(\w+\.csv\b|\.xlsx|\bprompt|requested schema|claude|chatgpt|attached (csv|workbook)|"
                        r"excel row|snapshot inferred|_raw_data|indexed_primary|user rubric|user-specified)", re.I)

    @classmethod
    def setUpTestData(cls):
        call_command("load_policy_data", verbosity=0)

    def test_no_internal_wording_in_public_output(self):
        urls = [reverse(f"policies:{n}") for n in ("overview", "timeline", "categories", "instruments", "explorer",
                                                   "capmf", "method", "about", "api_series", "api_selection", "export_csv")]
        urls += [reverse("policies:detail", kwargs={"slug": s.slug}) for s in PolicySeries.objects.all()]
        for url in urls:
            body = self.client.get(url).content.decode("utf-8", "ignore")
            match = self.BANNED.search(body)
            self.assertIsNone(match, f"{url}: {match and body[max(0, match.start() - 60):match.end() + 30]}")

    def test_citation_formatting(self):
        from .editorial import format_citations
        raw = ("EEA. Ireland PaMs report 1849, PaM 5, Excel row 6; attached Ireland Pams(3).xlsx. "
               "https://pam.apps.eea.europa.eu/ (source snapshot inferred 2026). | Revenue Commissioners. X. "
               "https://www.revenue.ie/x (accessed 2026-09-25; full_page)")
        out = format_citations(raw)
        self.assertEqual(len(out), 2)
        self.assertIn("PaM 5", out[0])
        self.assertIn("(accessed 25 September 2026)", out[1])
