from playwright.sync_api import sync_playwright
import logging
import json
import re

logger = logging.getLogger(__name__)


def scrape_nofluffjobs(technology: str, experience: str = 'all') -> list:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        base_url = f"https://nofluffjobs.com/pl/{technology.capitalize()}"

        if experience and experience.lower() != 'all':
            url = f"{base_url}?criteria=seniority%3D{experience.lower()}"
        else:
            url = base_url

        try:
            logger.info(f"Przechodzę do URL: {url}")
            page.goto(url, wait_until='networkidle')

            # 1. Znajdź główny kontener z wynikami, aby uniknąć sekcji z rekomendacjami.
            results_container = page.locator("div.list-container").first

            # 2. Szukaj ofert ('nfj-list-item') tylko wewnątrz tego kontenera.
            jobs = results_container.locator("a[nfj-postings-item]").all()
        except Exception as e:
            logger.error(f"Nie udało się załadować strony NoFluffJobs lub znaleźć ofert: {e}")
            browser.close()
            return []

        results = []
        for job_item in jobs[:25]:  # pierwsze 5 ofert na czas testów
            try:
                href = job_item.get_attribute("href")
                link = f"https://nofluffjobs.com{href}" if href else None

                raw_title = job_item.locator('h3.posting-title__position').inner_text()
                title = raw_title.replace('NOWA','').strip()
                company = job_item.locator('h4.company-name').inner_text().strip()
                location = job_item.locator('[data-cy="location on the job offer listing"]').inner_text().strip()
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
                            
                            # POPRAWKA: Logika specyficzna dla NoFluffJobs.
                            # Szukamy obiektu 'JobPosting' wewnątrz listy '@graph'.
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

        if technology and technology.lower() !='all':
            url = f"{base_url}/{technology.lower()}"
        else:
            url = base_url

        if experience and experience.lower() !='all':
            url += f"?experience-level={experience.lower()}"

        try:
            logger.info(f"Przechodzę do URL: {url}")
            page.goto(url, wait_until='networkidle')
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
        for job in jobs[:25]:  # Przetwarzamy pierwsze 15 ofert
            try:
                # Link do oferty
                href = job.get_attribute("href")
                link = f"https://justjoin.it{href}" if href else None

                title = job.locator('h3').inner_text()
                company = job.locator('p:near(svg[data-testid="ApartmentRoundedIcon"])').inner_text()
                location = job.locator('span.mui-1o4wo1x').inner_text()
                salary_el = job.locator('span.mui-13a157h').first
                salary = salary_el.inner_text() if salary_el else "Nie podano"
                unwanted_patterns = {r'^new$', r'^1-click$', r'^\d+d left$', r'^Expires tomorrow$'}
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
