import logging
from typing import Iterable
from celery import shared_task

from .constants import EXPERIENCE_LEVELS_TASK, PLATFORMS_IDS
from .models import JobOffer, ScraperTechnology
from .scrapers.justjoinit import scrape_justjoinit
from .scrapers.nofluff import scrape_nofluffjobs
from .utils import resolve_platform_technology

# Ustawienie loggera, aby widzieć postępy w konsoli workera Celery
logger = logging.getLogger(__name__)


def collect_offers_for_combination(technology: str, experience: str, platforms: Iterable[str]) -> list[dict]:
    """Zbiera oferty dla jednej kombinacji technologii/poziomu i listy platform."""
    logger.info("Start kombinacji tech=%s, exp=%s, platf=%s", technology, experience, platforms)
    offers = []
    if 'justjoinit' in platforms:
        # Dopasuj slug z bazy, aby scraper dostał poprawne parametry dla danej platformy.
        slug = resolve_platform_technology(technology, 'justjoinit')
        logger.info("JJIT: używam sluga %s", slug)
        offers.extend(scrape_justjoinit(slug, experience))
    if 'nofluffjobs' in platforms:
        slug = resolve_platform_technology(technology, 'nofluffjobs')
        logger.info("NFJ: używam sluga %s", slug)
        offers.extend(scrape_nofluffjobs(slug, experience))
    logger.info("Koniec kombinacji tech=%s exp=%s -> %s ofert", technology, experience, len(offers))
    return offers


def persist_offers(offers: list[dict], technology_label: str, experience_label: str) -> int:
    """Zapisuje oferty w bazie, zwracając liczbę nowych rekordów."""
    added = 0
    for offer_data in offers:
        date_posted_value = offer_data.pop('date_posted', None)
        # update_or_create pozwala nam uniknąć duplikatów bazując na unikalnym URL.
        obj, created = JobOffer.objects.update_or_create(
            url=offer_data['url'],
            defaults={
                **offer_data,
                'main_technology': technology_label,
                'experience_level': experience_label if experience_label != 'all' else "Nie określono",
                'date_posted': date_posted_value,
            }
        )
        if created:
            added += 1
    return added


@shared_task
def scrape_jobs_task(technology, experience='all', platforms=None):
    """
    Zadanie Celery do scrapowania ofert pracy.
    Wywołuje dedykowane scrapery i zapisuje wyniki do bazy danych.
    """
    if platforms is None:
        platforms = []

    logger.info(f"Rozpoczynam scraping dla: {technology}, poziom: {experience}, na platformach: {platforms}")
    # Pobierz oferty dla zadanej kombinacji technologii, poziomu i platform.
    offers = collect_offers_for_combination(technology, experience, platforms)
    logger.info(f"Łącznie znaleziono {len(offers)} ofert.")

    # Czyścimy poprzednie wyniki, aby mieć w bazie tylko aktualne dane z tego wyszukania.
    deleted_count, _ = JobOffer.objects.all().delete()
    logger.info(f"Usunięto {deleted_count} poprzednich ofert pracy.")

    # Zapisz oferty i policz, ile nowych rekordów powstało.
    offers_added = persist_offers(offers, technology, experience)
    logger.info(f"Dodano {offers_added} nowych ofert.")

    final_message = f"Scraping zakończony. Dodano {offers_added} nowych ofert."
    logger.info(final_message)
    return final_message

@shared_task
def scrape_full_matrix_task():
    technology_names = list(ScraperTechnology.objects.values_list('name', flat=True))
    if not technology_names:
        logger.info("Brak technologii do scrapowania. Przerywam scrape_full_matrix_task.")
        return "No technologies configured"
    logger.info(f"Rozpoczynam scraping dla wszystkich technologii: {technology_names}")

    deleted_count, _ = JobOffer.objects.all().delete()
    logger.info("Globalne czyszczenie JobOffer: usunięto %s rekordów.", deleted_count)

    total_added = 0

    for tech_name in technology_names:
        for experience in EXPERIENCE_LEVELS_TASK:
            offers = collect_offers_for_combination(tech_name, experience, PLATFORMS_IDS)
            offers_added = persist_offers(offers, tech_name, experience)
            total_added += offers_added
            logger.info(
                "Kombinacja %s/%s: zapisano %s nowych ofert.",
                tech_name,
                experience,
                offers_added,
            )
    logger.info("Zakończono pełne scrapowanie. Łącznie nowych ofert: %s.", total_added)
    return f"Full matrix done. Added {total_added} new offers."
