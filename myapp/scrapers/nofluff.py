from playwright.sync_api import sync_playwright
import logging
import json

logger = logging.getLogger(__name__)


def scrape_nofluffjobs(technology: str, experience: str = 'all') -> list:
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
        page = context.new_page()

        base_url = f"https://nofluffjobs.com/pl/{technology.capitalize()}"

        if experience and experience.lower() != 'all':
            url = f"{base_url}?criteria=seniority%3D{experience.lower()}"
        else:
            url = base_url

        try:
            logger.info(f"Przechodzę do URL: {url}")
            page.goto(url, wait_until='domcontentloaded')
            """" Obsługa cookies na NFJ w tybie headless_mode=False warto zatrzymac na 7s """
            try:
                page.wait_for_timeout(7000)
                accept_button = page.locator('.accept')
                if accept_button and accept_button.is_visible():
                    accept_button.click()
                    logger.info("Banner cookie na NoFluffJobs został zaakceptowany.")
            except Exception as e:
                logger.warning(f"Nie udało się automatycznie zaakceptować cookies na NFJ: {e}")

            all_containers = page.locator("div.list-container").all()
            results_container = all_containers[:2]

            jobs = []
            for container in results_container:
                container.wait_for(state='visible', timeout=15000)
                jobs_container = container.locator("a[nfj-postings-item]").all()
                jobs.extend(jobs_container)

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