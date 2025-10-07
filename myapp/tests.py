from django.test import TestCase
from unittest.mock import patch, MagicMock
from datetime import date
from .tasks import scrape_jobs_task
from .models import JobOffer

# Create your tests here.


class ScraperTaskTest(TestCase):

    # Używamy @patch, aby "zaślepić" (zamienić na atrapy) nasze funkcje scrapujące.
    # Dzięki temu test nie będzie łączył się z prawdziwymi stronami internetowymi.
    @patch('myapp.tasks.scrape_nofluffjobs')
    @patch('myapp.tasks.scrape_justjoinit')
    def test_scrape_jobs_task_saves_data(self, mock_scrape_justjoinit, mock_scrape_nofluffjobs):
        """
        Testuje, czy zadanie Celery 'scrape_jobs_task' poprawnie
        wywołuje scrapery i zapisuje ich wyniki do bazy danych.
        """
        # 1. Przygotowanie "fałszywych" danych, które mają zwrócić nasze scrapery
        mock_jjit_data = [{
            "title": "Junior Python Dev (JJIT)",
            "company": "TestCorp",
            "location": "Remote",
            "salary": "5000 - 7000 PLN",
            "skills": "Python, Django",
            "url": "https://justjoin.it/offers/test1",
            "source": "JustJoin.IT",
            "date_posted": "2025-10-08"
        }]

        mock_nfj_data = [{
            "title": "Junior Python Dev (NFJ)",
            "company": "TestCorp",
            "location": "Remote",
            "salary": "6000 - 8000 PLN",
            "skills": "Python, Flask",
            "url": "https://nofluffjobs.com/pl/job/test2",
            "source": "NoFluffJobs",
            "date_posted": "2025-10-07"
        }]

        # 2. Konfigurujemy nasze atrapy, aby zwracały przygotowane dane
        mock_scrape_justjoinit.return_value = mock_jjit_data
        mock_scrape_nofluffjobs.return_value = mock_nfj_data

        # 3. Wywołujemy nasze zadanie Celery
        #    Używamy .s() zamiast .delay(), aby wykonać zadanie synchronicznie (natychmiast) na potrzeby testu.
        scrape_jobs_task.s('python', 'junior', ['justjoinit', 'nofluffjobs']).apply()

        # 4. Sprawdzamy (asercje), czy wszystko zadziałało zgodnie z oczekiwaniami
        self.assertEqual(JobOffer.objects.count(), 2)

        # Sprawdzamy, czy scrapery zostały wywołane z prawidłowymi argumentami
        mock_scrape_justjoinit.assert_called_once_with('python', 'junior')
        mock_scrape_nofluffjobs.assert_called_once_with('python', 'junior')

        # Sprawdzamy, czy dane zostały poprawnie zapisane w bazie
        offer1 = JobOffer.objects.get(url="https://justjoin.it/offers/test1")
        self.assertEqual(offer1.title, "Junior Python Dev (JJIT)")
        self.assertEqual(offer1.date_posted, date(2025, 10, 8))

        offer2 = JobOffer.objects.get(url="https://nofluffjobs.com/pl/job/test2")
        self.assertEqual(offer2.source, "NoFluffJobs")
