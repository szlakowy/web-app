from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('projects/', views.projects, name='projects'),
    path('projects/<slug:slug>/', views.project_detail, name='project_detail'),
    path('about/', views.about, name='about'),
    path('job-scraper/', views.job_scraper, name='job_scraper'),
    path('job-scraper/task-status/<str:task_id>/', views.check_task_status, name='check_task_status'),
    path('job-scraper/analysis/', views.job_analysis, name='job_analysis'),
    path('job-scraper/api/chart-data/', views.chart_data_api, name='chart_data_api')
]
