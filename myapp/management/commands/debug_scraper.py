# /Users/jakublanda/Desktop/web_app/demo/myapp/management/commands/debug_scraper.py

from django.core.management.base import BaseCommand
from myapp.scrapers import scrape_justjoinit
import logging

# Ustawiamy logger, aby widzieć komunikaty w terminalu
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Uruchamia scraper JustJoin.it w trybie debugowania (z widoczną przeglądarką).'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Uruchamiam scraper w trybie podglądu... ---"))
        self.stdout.write("Obserwuj otwierające się okno przeglądarki!")

        # Ta linia otworzy widoczne okno przeglądarki.
        try:
            offers = scrape_justjoinit(technology='python', experience='junior')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Wystąpił błąd podczas scrapowania: {e}"))
            return

        self.stdout.write(self.style.SUCCESS("--- Scraper zakończył pracę. Analizuję wyniki... ---"))

        # Ten kod sprawdzi, czy udało się pobrać wiele lokalizacji
        found_multi_location = False
        for offer in offers:
            if "," in offer.get("location", ""):
                self.stdout.write(self.style.SUCCESS(
                    f"[SUKCES] Znaleziono wiele lokalizacji: '{offer['location']}' dla oferty '{offer['title']}'"
                ))
                found_multi_location = True

        if not found_multi_location:
            self.stdout.write(self.style.WARNING("[INFO] Nie znaleziono żadnej oferty z wieloma lokalizacjami."))
