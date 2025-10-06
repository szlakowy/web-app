from celery import shared_task
from .models import JobOffer
from .scrapers import scrape_justjoinit  # <-- IMPORTUJEMY NASZ SCRAPER
import logging

# Ustawienie loggera, aby widzieć postępy w konsoli workera Celery
logger = logging.getLogger(__name__)


@shared_task
def scrape_jobs_task(keyword):
    """
    Zadanie Celery do scrapowania ofert pracy.
    Wywołuje dedykowane scrapery i zapisuje wyniki do bazy danych.
    """
    logger.info(f"Rozpoczynam scraping dla słowa kluczowego: {keyword}")

    # 1. Wywołaj scraper i zbierz dane
    justjoinit_offers = scrape_justjoinit(keyword)

    # W przyszłości możesz tu dodać inne scrapery
    # all_offers = justjoinit_offers + nofluff_offers
    all_offers = justjoinit_offers

    # 2. Zapisz dane do bazy danych
    # USUŃ POPRZEDNIE WYNIKI WYSZUKIWANIA
    deleted_count, _ = JobOffer.objects.all().delete()
    logger.info(f"Usunięto {deleted_count} poprzednich ofert pracy.")

    offers_added = 0
    for offer_data in all_offers:
        # Używamy update_or_create, aby unikać duplikatów na podstawie unikalnego URL
        obj, created = JobOffer.objects.update_or_create(
            url=offer_data['url'],
            defaults=offer_data
        )
        if created:
            offers_added += 1

    final_message = f"Scraping zakończony. Dodano {offers_added} nowych ofert."
    logger.info(final_message)
    return final_message