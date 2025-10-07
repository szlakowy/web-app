# /Users/jakublanda/Desktop/web_app/demo/myapp/debug_scraper.py

import json
import logging
from playwright.sync_api import sync_playwright

# Prosta konfiguracja loggera, aby widzieć komunikaty w konsoli
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def debug_single_offer_date(url: str):
    """
    Otwiera pojedynczą stronę oferty, znajduje dane strukturalne
    i drukuje w konsoli znalezioną zawartość oraz przetworzoną datę.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        logger.info(f"Otwieram stronę: {url}")

        try:
            page.goto(url, wait_until='domcontentloaded')

            script_selector = 'script[type="application/ld+json"]'

            # Czekamy, aż skrypt będzie w DOM (nie musi być widoczny)
            logger.info(f"Szukam na stronie elementu: {script_selector}")
            script_handle = page.wait_for_selector(script_selector, state='attached', timeout=10000)

            if script_handle:
                logger.info(">>> SUKCES: Znaleziono tag <script> z danymi strukturalnymi.")
                script_content = script_handle.inner_text()

                # --- TO JEST NAJWAŻNIEJSZA CZĘŚĆ DLA CIEBIE ---
                print("\n" + "=" * 20 + " SUROWA ZAWARTOŚĆ SKRYPTU " + "=" * 20)
                print(script_content)
                print("=" * 64 + "\n")
                # ---------------------------------------------

                try:
                    logger.info("Próbuję sparsować zawartość jako JSON...")
                    # Sprawdzamy, czy to JustJoin.IT (JSON w liście)
                    if "justjoin.it" in url:
                        data = json.loads(script_content)[0]
                        logger.info("Wykryto JustJoin.IT (dane w liście).")
                    else:  # Zakładamy, że to NoFluffJobs (pojedynczy obiekt JSON)
                        data = json.loads(script_content)
                        logger.info("Wykryto NoFluffJobs (pojedynczy obiekt).")

                    date_string = data.get('datePosted')

                    if date_string:
                        logger.info(f">>> SUKCES: Znaleziono klucz 'datePosted' z wartością: '{date_string}'")
                        final_date = date_string.split('T')[0]
                        logger.info(f">>> SUKCES: Przetworzona data (YYYY-MM-DD): '{final_date}'")
                    else:
                        logger.warning(">>> BŁĄD: Nie znaleziono klucza 'datePosted' w danych JSON.")

                except (json.JSONDecodeError, IndexError) as e:
                    logger.error(f">>> BŁĄD: Nie udało się sparsować danych JSON: {e}")
            else:
                logger.error(">>> BŁĄD: Nie znaleziono na stronie tagu <script> z danymi strukturalnymi.")

        except Exception as e:
            logger.error(f"Wystąpił błąd podczas próby otwarcia strony lub szukania elementu: {e}")
        finally:
            logger.info("Zamykam przeglądarkę.")
            browser.close()


if __name__ == '__main__':
    # --- ZMIEŃ TEN URL, ABY PRZETESTOWAĆ INNĄ OFERTĘ ---

    # Przykład dla JustJoin.IT
    # Wklej tutaj link do konkretnej oferty z JustJoin.IT, która sprawia problemy
    test_url_jjit = "https://justjoin.it/job-offer/revolt-junior-python-developer-remote"

    # Przykład dla NoFluffJobs
    # Wklej tutaj link do konkretnej oferty z NoFluffJobs, która sprawia problemy
    test_url_nfj = "https://nofluffjobs.com/pl/job/junior-python-developer-apius-technologies-warszawa"

    print("=" * 50)
    print("Rozpoczynam test dla JustJoin.IT...")
    print("=" * 50)
    debug_single_offer_date(test_url_jjit)

    print("\n" + "=" * 50)
    print("Rozpoczynam test dla NoFluffJobs...")
    print("=" * 50)
    debug_single_offer_date(test_url_nfj)
