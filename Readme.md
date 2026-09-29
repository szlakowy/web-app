# Job Market Scraper & Portfolio

A Django web application that combines a personal portfolio with an on-demand **job offer scraper** for Polish IT job boards (JustJoin.it and NoFluffJobs). Scraping runs as background tasks, results are stored in a database, and a simple analytics view visualizes the collected data.

<!-- Live demo: add link here if the app is deployed -->
<!-- Screenshot: add an image here, e.g. ![Job Scraper](docs/screenshot.png) -->

## Features

- **Job Scraper**: pick a technology, seniority level (junior / mid / senior / all) and platforms, then start a scrape.
  - Scrapers for **JustJoin.it** and **NoFluffJobs**, built with **Playwright** (headless Chromium, cookie banner handling, timeouts).
  - Each offer is stored with: title, company, locations, salary, experience level, skills, publication date, source and URL.
  - Duplicates are avoided with `update_or_create` keyed on the offer URL.
- **Background processing**: scraping runs as a **Celery** task with **Redis** as broker; the UI polls a JSON endpoint for task status and refreshes when done.
- **Analytics**: job market analysis page with a **Chart.js** chart, fed by a JSON API endpoint (`/job-scraper/api/chart-data/`).
- **Portfolio**: home, projects (with slug-based detail pages), about, skills and career timeline — all content managed through the Django admin.
- **Production-ready setup**: Docker, Gunicorn, WhiteNoise for static files, PostgreSQL via `DATABASE_URL`, Cloudinary for media; configured for deployment on Railway.

## Tech stack

| Area | Tools |
|---|---|
| Backend | Python 3.12, Django 5.2 |
| Scraping | Playwright (Chromium) |
| Async tasks | Celery, Redis |
| Database | PostgreSQL (production), SQLite (local) |
| Frontend | Django templates, Bootstrap, Chart.js |
| Deployment | Docker, Gunicorn, WhiteNoise, Cloudinary, Railway |

## Project structure

```
demo/                 # Django project: settings, URLs, Celery config
myapp/
  scrapers/
    justjoinit.py     # JustJoin.it scraper
    nofluff.py        # NoFluffJobs scraper
  tasks.py            # Celery task: run scrapers and save offers
  models.py           # JobOffer, ScraperTechnology, Project, Skill, JourneyStep, PersonalInfo
  views.py            # pages, task status and chart data endpoints
  templates/          # HTML templates
Dockerfile
Procfile              # web (Gunicorn) + worker (Celery) processes
```

## Running locally

Requirements: Python 3.12+, Redis running locally (e.g. `docker run -p 6379:6379 redis`).

```bash
git clone https://github.com/szlakowy/web-app.git
cd web-app
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

python manage.py migrate
python manage.py createsuperuser   # to manage content and scraper technologies in /admin
python manage.py runserver
```

In a second terminal, start the Celery worker:

```bash
celery -A demo.celery worker -l info
```

Then add at least one technology (e.g. `python`) under **Scraper technologies** in the admin panel and open `/job-scraper/`.

## Configuration

Settings are read from environment variables (a `.env` file is supported):

| Variable | Description | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Django secret key | local dev key |
| `DJANGO_DEBUG` | `True` / `False` | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated origins | `http://localhost,http://127.0.0.1` |
| `DATABASE_URL` | Database connection string | SQLite |
| `REDIS_URL` | Celery broker and result backend | `redis://localhost:6379/0` |
| `CLOUDINARY_URL` | Enables Cloudinary media storage | — |

## Deployment

The app is containerized (`Dockerfile` installs Playwright's Chromium and collects static files) and runs as two processes defined in the `Procfile`:

- `web` — Gunicorn serving the Django app
- `worker` — Celery worker executing scraping tasks

On Railway, add PostgreSQL and Redis services and set the environment variables above.

## Notes

- Each scrape run replaces previously stored offers, so the database always shows the results of the latest search.
- Scrapers depend on the current structure of the job boards and may need updates when those sites change.
- This project is for learning and portfolio purposes.
