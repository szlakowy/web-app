from playwright.sync_api import sync_playwright
import logging

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
        for job_item in jobs[:15]:  # Przetwarzamy pierwsze 15 ofert
            try:
                # POPRAWKA: Pobieramy atrybut 'href' bezpośrednio z elementu oferty ('job_item'),
                # ponieważ to on jest tagiem <a>.
                href = job_item.get_attribute("href")
                link = f"https://nofluffjobs.com{href}" if href else None

                # POPRAWKA: Używamy bardziej stabilnych selektorów opartych na atrybutach 'data-cy' i poprawnej strukturze HTML.
                title = job_item.locator('[data-cy="title position on the job offer listing"]').inner_text()
                company = job_item.locator('h4.company-name').inner_text().strip()
                location = job_item.locator('[data-cy="location on the job offer listing"]').inner_text().strip()
                salary = job_item.locator('[data-cy="salary ranges on the job offer listing"]').inner_text().strip()

                # POPRAWKA: Umiejętności to tagi <span> wewnątrz komponentu <nfj-posting-item-tiles>.
                skill_elements = job_item.locator('nfj-posting-item-tiles span').all()
                skills_list = [el.inner_text() for el in skill_elements]
                skills_str = ", ".join(skills_list)

                if not all([title, company, link, location]):
                    continue

                results.append({
                    "title": title, "company": company, "location": location,
                    "salary": salary,
                    "skills": skills_str,
                    "url": link,
                    "source": "NoFluffJobs"
                })
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
        for job in jobs[:15]:  # Przetwarzamy pierwsze 15 ofert
            try:
                # Link do oferty
                href = job.get_attribute("href")
                link = f"https://justjoin.it{href}" if href else None

                # Tytuł stanowiska
                title = job.locator('h3').inner_text()

                # Firma
                # ZMIANA: Lokalizujemy firmę na podstawie ikony, która jest jej stałym sąsiadem.
                company = job.locator('p:near(svg[data-testid="ApartmentRoundedIcon"])').inner_text()

                # Lokalizacja
                location = job.locator('span.mui-1o4wo1x').inner_text()

                # Widełki płacowe (przywrócone z Twojego kodu)
                # ZMIANA: Używamy bardziej ogólnego, ale wciąż skutecznego selektora.
                salary_el = job.locator('span.mui-13a157h').first
                salary = salary_el.inner_text() if salary_el else "Nie podano"

                # Skille (przywrócone z Twojego kodu, zaktualizowane selektory)
                unwanted_texts = {'new', '1-click apply'}
                skill_elements = job.locator('div.mui-jikuwi').all()
                skills_list = []
                for skill_el in skill_elements:
                    skill_text = skill_el.inner_text()
                    if skill_text.lower() not in unwanted_texts:
                        skills_list.append(skill_text)
                skills_str = ", ".join(skills_list)

                if not all([title, company, link, location]):
                    continue

                # Dodaj wynik
                results.append({"title": title, "company": company, "location": location, "salary": salary, "skills": skills_str, "url": link, "source": "JustJoin.IT"})
            except Exception as e:
                logger.warning(f"Pominięto ofertę z powodu błędu podczas parsowania: {e}")

        browser.close()
        logger.info(f"Znaleziono {len(results)} ofert na JustJoin.IT.")
        return results
