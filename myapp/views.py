from django.shortcuts import render, HttpResponse, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from celery.result import AsyncResult
from django.urls import reverse
from .models import Project, Skill, JourneyStep, JobOffer, ScraperTechnology
from .tasks import scrape_jobs_task


def home(request):
    """Strona główna - wyświetla podstawowe informacje i najnowsze projekty"""
    # Pobierz 3 najnowsze projekty
    recent_projects = Project.objects.all()[:3]

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
    all_projects = Project.objects.all()

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
    EXPERIENCE_LEVELS = [
        ('all', 'Wszystkie'),
        ('junior', 'Junior'),
        ('mid', 'Mid'),
        ('senior', 'Senior'),
    ]

    PLATFORMS = [
        ('justjoinit', 'JustJoin.it'),
        ('nofluffjobs', 'NoFluffJobs'),
    ]
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
    latest_offers = JobOffer.objects.all()[:20]
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

