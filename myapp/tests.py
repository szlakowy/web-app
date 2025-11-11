from unittest.mock import call, patch

from django.test import TestCase

from myapp.constants import EXPERIENCE_LEVELS_TASK, PLATFORMS_IDS
from myapp.models import ScraperTechnology
from myapp.tasks import scrape_full_matrix_task


class ScrapeFullMatrixTaskTests(TestCase):
    @patch("myapp.tasks.persist_offers")
    @patch("myapp.tasks.collect_offers_for_combination")
    def test_scrape_full_matrix_task_iterates_over_matrix(
        self,
        mock_collect_offers_for_combination,
        mock_persist_offers,
    ):
        ScraperTechnology.objects.create(name="Python")
        ScraperTechnology.objects.create(name="Java")

        mock_collect_offers_for_combination.return_value = [{"url": "http://example.com"}]
        mock_persist_offers.return_value = 3

        result = scrape_full_matrix_task.run()

        technology_names = list(ScraperTechnology.objects.values_list("name", flat=True))
        expected_call_count = len(technology_names) * len(EXPERIENCE_LEVELS_TASK)

        self.assertEqual(mock_collect_offers_for_combination.call_count, expected_call_count)
        self.assertEqual(mock_persist_offers.call_count, expected_call_count)

        expected_collect_calls = [
            call(tech_name, experience, PLATFORMS_IDS)
            for tech_name in technology_names
            for experience in EXPERIENCE_LEVELS_TASK
        ]
        mock_collect_offers_for_combination.assert_has_calls(expected_collect_calls, any_order=False)

        expected_total_added = expected_call_count * mock_persist_offers.return_value
        self.assertEqual(result, f"Full matrix done. Added {expected_total_added} new offers.")
