from playwright.sync_api import sync_playwright
import logging
import json
import re

logger = logging.getLogger(__name__)


def scrape_nofluffjobs(technology: str, experience: str = 'all') -> list:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        base_url = f"https://nofluffjobs.com/pl/{technology.capitalize()}"

        if experience and experience.lower() != 'all':
            url = f"{base_url}?criteria=seniority%3D{experience.lower()}"
        else:
            url = base_url

        try:
            logger.info(f"Przechodzę do URL: {url}")
            page.goto(url, wait_until='domcontentloaded')
            logger.info("Czekam chwilę (1s) po obsłudze cookies na załadowanie reszty strony...")
            page.wait_for_timeout(7000)
            try:
                accept_button = page.locator('.accept')
                logger.info("Próbuję znaleźć przycisk akceptacji cookie na NoFluffJobs...")
                accept_button.wait_for(state='visible', timeout=5000)
                logger.info("Przycisk znaleziony, próbuję kliknąć...")
                accept_button.click()
                logger.info("Banner cookie na NoFluffJobs został zaakceptowany.")
            except Exception as e:
                logger.warning(f"Nie udało się automatycznie zaakceptować cookies na NFJ (możliwe, że już zaakceptowano): {e}")

            results_container = page.locator("div.list-container").first
            results_container.wait_for(state='visible', timeout=15000)

            jobs = results_container.locator("a[nfj-postings-item]").all()
        except Exception as e:
            logger.error(f"Nie udało się załadować strony NoFluffJobs lub znaleźć ofert: {e}")
            browser.close()
            return []

        results = []
        for job_item in jobs:
            try:
                href = job_item.get_attribute("href")
                link = f"https://nofluffjobs.com{href}" if href else None

                raw_title = job_item.locator('h3.posting-title__position').inner_text()
                title = raw_title.replace('NOWA', '').strip()
                company = job_item.locator('h4.company-name').inner_text().strip()

                # --- NOWA LOGIKA POBIERANIA LOKALIZACJI ---
                location_element = job_item.locator('[data-cy="location on the job offer listing"]')
                # Domyślnie używamy skróconego tekstu (np. „Zdalnie +5” albo nazwy miasta)
                summary_text = location_element.inner_text().replace('\xa0', ' ').strip()
                location = summary_text
                try:
                    # Upewniamy się, że element jest w zasięgu widoku i najeżdżamy na niego
                    location_element.scroll_into_view_if_needed()
                    location_element.hover()
                    # Czekamy chwilę, aby pop‑over zdążył się pojawić
                    page.wait_for_timeout(500)
                    # Pop‑over jest osadzony wewnątrz danego elementu oferty
                    popover_body = job_item.locator('popover-content .popover-body')
                    if popover_body.count() > 0:
                        # Najpierw próbujemy pobrać wszystkie linki z pop‑overa – każdy link to osobna lokalizacja
                        anchor_texts = [
                            text.replace('\xa0', ' ').strip()
                            for text in popover_body.locator('a').all_text_contents()
                            if text.strip()
                        ]
                        if anchor_texts:
                            location = ", ".join(sorted(set(anchor_texts)))
                        else:
                            # Jeżeli nie ma linków, czytamy cały tekst pop‑overa i dzielimy po nowych liniach
                            pop_text = popover_body.inner_text().replace('\xa0', ' ').strip()
                            if pop_text:
                                lines = [line.strip() for line in pop_text.split('\n') if line.strip()]
                                if lines:
                                    location = ", ".join(sorted(set(lines)))
                except Exception as e:
                    logger.debug(f"Nie udało się pobrać pełnej listy lokalizacji dla '{title}': {e}")
                # --- KONIEC NOWEJ LOGIKI POBIERANIA LOKALIZACJI ---

                salary = job_item.locator('[data-cy="salary ranges on the job offer listing"]').inner_text().strip()

                skill_elements = job_item.locator('nfj-posting-item-tiles span').all()
                skills_list = [el.inner_text() for el in skill_elements]
                skills_str = ", ".join(skills_list)

                date_posted = None
                logger.debug(f"NFJ: Processing link: {link}")
                if link:
                    details_page = browser.new_page()
                    try:
                        details_page.goto(link, wait_until='domcontentloaded')

                        script_selector = 'script[type="application/ld+json"]'
                        script_handle = details_page.wait_for_selector(script_selector, state='attached', timeout=5000)
                        if script_handle:
                            script_content = script_handle.inner_text()
                            parsed_json = json.loads(script_content)
                            job_posting_data = None
                            if isinstance(parsed_json, dict) and '@graph' in parsed_json:
                                for item in parsed_json['@graph']:
                                    if isinstance(item, dict) and item.get('@type') == 'JobPosting':
                                        job_posting_data = item
                                        break
                            date_string = job_posting_data.get('datePosted') if job_posting_data else None
                            logger.debug(f"NFJ: Raw datePosted from JSON-LD: {date_string}")
                            date_posted = date_string.split('T')[0] if date_string else None
                    except Exception as e:
                        logger.warning(f"Nie udało się pobrać daty dla {link}: {e}")
                    finally:
                        details_page.close()

                if not all([title, company, link, location]):
                    continue

                offer_data = {
                    "title": title, "company": company, "location": location,
                    "salary": salary,
                    "skills": skills_str,
                    "url": link,
                    "source": "NoFluffJobs",
                    "date_posted": date_posted,
                }
                results.append(offer_data)
                logger.debug(f"NFJ: Final offer data for {link}: {{'date_posted': {offer_data.get('date_posted')}}}")
            except Exception as e:
                logger.warning(f"Pominięto ofertę z NoFluffJobs z powodu błędu: {e}")

        browser.close()
        logger.info(f"Znaleziono {len(results)} ofert na NoFluffJobs.")
        return results



def scrape_justjoinit(technology: str, experience: str = 'all') -> list:
    """
    Scraper ofert pracy z portalu JustJoin.it.
    To jest synchroniczna wersja Twojego oryginalnego skryptu.

    Args:
        technology (str): Technologia do wyszukania (np. 'python').
        experience (str): Poziom doświadczenia (np. 'junior', 'mid', 'senior', 'all').

    Returns:
        list: Lista słowników z danymi ofert pracy.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        base_url = "https://justjoin.it/job-offers/all-locations"

        if technology and technology.lower() != 'all':
            url = f"{base_url}/{technology.lower()}"
        else:
            url = base_url

        if experience and experience.lower() != 'all':
            url += f"?experience-level={experience.lower()}"

        try:
            logger.info(f"Przechodzę do URL: {url}")
            # ZMIANA: 'networkidle' jest często zawodne. Zmieniamy na 'domcontentloaded',
            # co oznacza, że czekamy tylko na załadowanie struktury HTML.
            # Następnie i tak czekamy na konkretny selektor, co jest bardziej niezawodne.
            page.goto(url, wait_until='domcontentloaded')

            # --- OBSŁUGA BANNERA COOKIE ---
            # Banner cookie może blokować kliknięcia. Szukamy przycisku akceptacji i go klikamy.
            try:
                accept_button = page.locator('#cookiescript_accept')
                logger.info("Próbuję znaleźć przycisk akceptacji cookie...")
                accept_button.wait_for(state='visible', timeout=5000)
                logger.info("Przycisk znaleziony, próbuję kliknąć...")
                accept_button.click()
                logger.info("Banner cookie został zaakceptowany.")
            except Exception as e:
                # Zmieniamy logowanie, aby zobaczyć DOKŁADNY błąd, jeśli akceptacja się nie uda
                logger.warning(f"Nie udało się automatycznie zaakceptować cookies: {e}")

            # ZMIANA: Czekamy na link, którego atrybut href zaczyna się od "/job-offer/".
            # To jest obecnie najbardziej stabilny identyfikator oferty.
            page.wait_for_selector("a[href^='/job-offer/']", timeout=20000)
            # ZMIANA: Lokalizujemy wszystkie oferty na podstawie tego samego, stabilnego selektora.
            jobs = page.locator("a[href^='/job-offer/']").all()
        except Exception as e:
            logger.error(f"Nie udało się załadować strony lub znaleźć ofert: {e}")
            browser.close()
            return []

        results = []
        for job in jobs:
            try:
                # Link do oferty
                href = job.get_attribute("href")
                link = f"https://justjoin.it{href}" if href else None

                title = job.locator('h3').inner_text()
                company = job.locator('p:near(svg[data-testid="ApartmentRoundedIcon"])').inner_text()

                # Zaawansowane pobieranie lokalizacji
                # KROK 1: Zawsze pobieramy początkową, widoczną lokalizację.
                # Od razu ją oczyszczamy, biorąc tylko fragment przed przecinkiem.
                initial_location_text = job.locator('span.mui-1o4wo1x').inner_text()
                # Ustawiamy ją jako domyślną.
                location = initial_location_text.split(',')[0].strip()

                # Szukamy przycisku z atrybutem name="multilocation_button"
                multilocation_button = job.locator('button[name="multilocation_button"]')
                if multilocation_button.count() > 0:
                    # Jeśli przycisk istnieje, to znaczy, że jest wiele lokalizacji
                    try:
                        # OSTATECZNA STRATEGIA: Prosta i niezawodna.
                        # 1. Klikamy w przycisk.
                        multilocation_button.click()
                        logger.info(f"[{title}] Kliknięto przycisk multi-lokalizacji. Czekam na pojawienie się listy...")

                        # 2. Czekamy na pojawienie się kontenera z listą (tooltipa).
                        # Używamy selektora klasy, który jest bardziej stabilny.
                        tooltip_locator = page.locator("div.MuiPopper-root").last
                        tooltip_locator.wait_for(state='visible', timeout=3000)

                        # 3. Pobieramy wszystkie lokalizacje z tooltipa, celując w poprawny element.
                        # Na podstawie dostarczonego HTML, wiemy, że lokalizacje są w <span class="mui-1jh5lol">
                        tooltip_locations_raw = tooltip_locator.locator('span.mui-1jh5lol').all_inner_texts()
                        
                        # KROK 2: Oczyszczamy każdą lokalizację z tooltipa.
                        cleaned_locations = {loc.split(',')[0].strip() for loc in tooltip_locations_raw}
                        # Dodajemy również oczyszczoną lokalizację początkową, aby mieć pewność, że jest w zestawie.
                        cleaned_locations.add(location)

                        logger.info(f"[{title}] Znaleziono i oczyszczono {len(cleaned_locations)} unikalnych lokalizacji: {cleaned_locations}")
                        if cleaned_locations:
                            location = ", ".join(sorted(list(cleaned_locations)))
                    except Exception as e:
                        logger.warning(f"Nie udało się rozwinąć listy lokalizacji dla oferty '{title}': {e}. Używam domyślnej.")
                        # W razie błędu, domyślna (już oczyszczona) lokalizacja pozostaje.
                else:
                    # Jeśli nie ma przycisku, pobieramy standardową, pojedynczą lokalizację
                    pass

                salary_el = job.locator('span.mui-13a157h').first
                salary = salary_el.inner_text() if salary_el else "Nie podano"
                unwanted_patterns = {r'^new$', r'^'
                                               r'1-click Apply$', r'^\d+d left$', r'^Expires tomorrow$'}
                skill_elements = job.locator('div.mui-jikuwi').all()
                skills_list = []
                for skill_el in skill_elements:
                    skill_text = skill_el.inner_text()
                    if not any(re.match(pattern, skill_text, re.IGNORECASE) for pattern in unwanted_patterns):
                        skills_list.append(skill_text)
                skills_str = ", ".join(skills_list)

                date_posted = None
                logger.debug(f"JJIT: Processing link: {link}")
                if link:
                    details_page = browser.new_page()
                    try:
                        details_page.goto(link, wait_until='domcontentloaded')

                        script_selector = 'script[type="application/ld+json"]'
                        script_handle = details_page.wait_for_selector(script_selector, state='attached', timeout=5000)
                        if script_handle:
                            script_content = script_handle.inner_text()
                            # POPRAWKA: Sprawdzamy, czy dane są listą, czy pojedynczym obiektem.
                            parsed_json = json.loads(script_content)
                            if isinstance(parsed_json, list):
                                # Jeśli to lista, bierzemy pierwszy element.
                                data = parsed_json[0]
                            else:
                                # Jeśli to pojedynczy obiekt, używamy go bezpośrednio.
                                data = parsed_json
                            logger.debug(f"JJIT: Raw data from JSON-LD: {data}")
                            date_string = data.get('datePosted')
                            date_posted = date_string.split('T')[0] if date_string else None
                    except Exception as e:
                        logger.warning(f"Nie udało się pobrać daty dla {link}: {e}")
                    finally:
                        details_page.close()

                if not all([title, company, link, location]):
                    continue

                # Dodaj wynik
                offer_data = {
                    "title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "skills": skills_str,
                    "url": link,
                    "source": "JustJoin.IT",
                    "date_posted": date_posted,
                }
                results.append(offer_data)
                logger.debug(f"JJIT: Final offer data for {link}: {{'date_posted': {offer_data.get('date_posted')}}}")
            except Exception as e:
                logger.warning(f"Pominięto ofertę z powodu błędu podczas parsowania: {e}")

        browser.close()
        logger.info(f"Znaleziono {len(results)} ofert na JustJoin.IT.")
        return results
