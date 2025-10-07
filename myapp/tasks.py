from celery import shared_task
from .models import JobOffer
from .scrapers import scrape_justjoinit, scrape_nofluffjobs
import logging

# Ustawienie loggera, aby widzieć postępy w konsoli workera Celery
logger = logging.getLogger(__name__)


@shared_task
def scrape_jobs_task(technology, experience='all', platforms=None):
    """
    Zadanie Celery do scrapowania ofert pracy.
    Wywołuje dedykowane scrapery i zapisuje wyniki do bazy danych.
    """
    if platforms is None:
        platforms = []
    logger.info(f"Rozpoczynam scraping dla: {technology}, poziom: {experience}, na platformach: {platforms}")
    all_offers = []

    # 1. Wywołaj scraper i zbierz dane
    if 'justjoinit' in platforms:
        all_offers.extend(scrape_justjoinit(technology, experience))
    if 'nofluffjobs' in platforms:
        all_offers.extend(scrape_nofluffjobs(technology, experience))

    logger.info(f"Łącznie znaleziono {len(all_offers)} ofert.")

    # 2. Zapisz dane do bazy danych
    # USUŃ POPRZEDNIE WYNIKI WYSZUKIWANIA
    deleted_count, _ = JobOffer.objects.all().delete()
    logger.info(f"Usunięto {deleted_count} poprzednich ofert pracy.")

    offers_added = 0
    for offer_data in all_offers:
        # Używamy update_or_create, aby unikać duplikatów na podstawie unikalnego URL
        # Debugging: Log the offer_data before processing date_posted
        logger.debug(f"TASK: Processing offer_data (raw): {offer_data}")
        
        # Kluczowe: Wyciągamy 'date_posted' ze słownika, aby Django poprawnie
        # zinterpretowało typ danych przy aktualizacji pola DateField.
        date_posted_value = offer_data.pop('date_posted', None)
        logger.debug(f"TASK: Extracted date_posted_value: {date_posted_value}")

        obj, created = JobOffer.objects.update_or_create(
            url=offer_data['url'],
            defaults={
                **offer_data,
                'experience_level': experience if experience != 'all' else None,
                'date_posted': date_posted_value,  # Jawnie przypisujemy przetworzoną datę
            }
        )
        if created:
            offers_added += 1

    final_message = f"Scraping zakończony. Dodano {offers_added} nowych ofert."
    logger.info(final_message)
    return final_message