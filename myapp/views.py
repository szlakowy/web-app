from django.shortcuts import render, HttpResponse, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from celery.result import AsyncResult
from django.urls import reverse
from .models import Project, Skill, JourneyStep, JobOffer, ScraperTechnology
from .tasks import scrape_jobs_task, scrape_full_matrix_task
from .constants import EXPERIENCE_LEVELS_UI as EXPERIENCE_LEVELS, PLATFORMS_UI as PLATFORMS


def home(request):
    """Strona główna - wyświetla podstawowe informacje i najnowsze projekty"""
    # Jawne sortowanie gwarantuje pobranie najnowszych projektów.
    recent_projects = Project.objects.order_by('-created_date')[:3]

    # Pobierz wszystkie umiejętności
    skills = Skill.objects.all()
    journey_steps = JourneyStep.objects.all()

    context = {
        'recent_projects': recent_projects,
        'skills': skills,
        'journey_steps': journey_steps,
    }

    return render(request, 'home.html', context)


def projects(request):
    """Strona ze wszystkimi projektami"""
    all_projects = Project.objects.order_by('-created_date')

    context = {
        'all_projects': all_projects,
    }

    return render(request, 'projects.html', context)


def project_detail(request, slug):
    """Strona ze szczegółami projektu"""
    project = get_object_or_404(Project, slug=slug)
    context = {
        'project': project,
    }
    return render(request, 'project_detail.html', context)


def about(request):
    """Strona o mnie"""
    skills = Skill.objects.all()

    context = {
        'skills': skills,
    }

    return render(request, 'about.html', context)


def job_scraper(request):
    """dedykowana strona dla aplikcaji Job Scraper"""
    task_id = request.GET.get('task_id')
    if request.method == 'POST':
        technology = request.POST.get('technology', '')
        experience = request.POST.get('experience', 'all')
        selected_platforms = request.POST.getlist('platforms')
        if technology and experience and selected_platforms:
            task = scrape_jobs_task.delay(technology, experience, selected_platforms) # odpala zadanie w tle
            messages.success(request, f"Rozpoczęto wyszukiwanie ofert dla technologii '{technology}' "
                                      f"poziom: {experience} na platformie/ach: {', '.join(selected_platforms)}. "
                                      f"Strona odświeży się automatycznie po zakończeniu" )
            return redirect(f"{reverse('job_scraper')}?task_id={task.id}")

    # Ten kod wykona się dla żądania GET (gdy wejdziesz na stronę lub po przekierowaniu)
    # Pobieramy wszystkie technologie z naszego nowego modelu, aby weyświetlić je w formualrzu.
    available_technologies = ScraperTechnology.objects.all()
    # Jawne sortowanie gwarantuje pobranie najnowszych ofert.
    latest_offers = JobOffer.objects.order_by('-scraped_date')[:20]
    context = {
        'available_technologies': available_technologies,
        'experience_levels': EXPERIENCE_LEVELS,
        'platforms': PLATFORMS,
        'offers': latest_offers,
        'task_id': task_id
    }
    return render(request, 'job_scraper.html', context)


def check_task_status(request, task_id):
    """sprawdz status zadania Celery i zwraca go jako JSON"""
    task_result = AsyncResult(task_id)
    result = {'status': task_result.status, 'result': task_result.result}
    return JsonResponse(result)


def job_analysis(request):
    context = {
        'page_title': 'Analiza Rynku Pracy'
    }
    return render(request, 'job_analysis.html', context)


def chart_data_api(request):

    # Użycie values_list jest nieco bardziej wydajne, gdy nie potrzebujemy słowników.
    platform_data = JobOffer.objects.values('source').annotate(count=Count('id')).order_by('-count').values_list('source', 'count')

    labels, data = zip(*platform_data) if platform_data else ([], [])

    chart_data = {
        'labels': list(labels),
        'data': list(data),
    }
    return JsonResponse(chart_data)


def job_offers(request):
    """
    Widok do wyświetlania ofert pracy i uruchamiania pełnego scrapowania.
    GET: Zwraca wszystkie JobOffer posortowane po -scraped_date.
    POST: Odpala scrape_full_matrix_task.delay() i przekierowuje.
    """
    selected_experience = request.GET.get('experience', 'all')
    selected_technology = request.GET.get('technology', 'all')
    offers_qs = JobOffer.objects.all().order_by('-scraped_date')
    if selected_experience and selected_experience != 'all':
        offers_qs = offers_qs.filter(experience_level__iexact=selected_experience)
    if selected_technology and selected_technology != 'all':
        offers_qs = offers_qs.filter(main_technology__iexact=selected_technology)

    if request.method == 'POST':
        # Odpala zadanie Celery w tle
        task = scrape_full_matrix_task.delay()
        messages.success(
            request,
            "Rozpoczęto pełne scrapowanie ofert pracy. Strona odświeży się automatycznie po zakończeniu."
        )
        # Przekieruj na tę samą stronę, aby uniknąć ponownego wysłania formularza
        return redirect('job_offers')
    else:
        # GET request: wyświetl wszystkie oferty pracy
        technologies = (
            JobOffer.objects
            .exclude(main_technology__isnull=True)
            .exclude(main_technology__exact='')
            .values_list('main_technology', flat=True)
            .order_by()
            .distinct()
        )
        context = {
            'offers': offers_qs,
            'experience_levels': EXPERIENCE_LEVELS,
            'selected_experience': selected_experience,
            'technologies': technologies,
            'selected_technology': selected_technology,
        }
        return render(request, 'job_offers.html', context)
