from django.contrib import admin
from .models import PersonalInfo, JobOffer, Project, Skill, JourneyStep, ScraperTechnology, ScraperTechnologyFilter

# Register your models here.

admin.site.register(PersonalInfo)
admin.site.register(Project)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'level')
    list_editable = ('level',)


@admin.register(JourneyStep)
class JourneyStepAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'order')
    list_editable = ('order',)


@admin.register(ScraperTechnology)
class ScraperTechnologyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ScraperTechnologyFilter)
class ScraperTechnologyFilterAdmin(admin.ModelAdmin):
    list_display = ('technology', 'platform', 'value')
    list_filter = ('platform',)
    search_fields = ('technology__name', 'platform', 'value')


@admin.register(JobOffer)
class JobOfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'main_technology', 'experience_level', 'source', 'scraped_date')
    list_filter = ('main_technology', 'experience_level', 'source')
    search_fields = ('title', 'company', 'main_technology', 'experience_level', 'skills')