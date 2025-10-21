from playwright.sync_api import sync_playwright
import logging
import json
import re

logger = logging.getLogger(__name__)


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
        headless_mode = True
        browser = p.chromium.launch(headless=headless_mode, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0.0.0 Safari/537.36"
        ))
        context.set_default_navigation_timeout(30000)  # limit czasu na nawigację
        context.set_default_timeout(10000)  # limit na oczekiwanie elementów
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