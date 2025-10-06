from django.contrib import admin
from .models import PersonalInfo, Project, Skill, JourneyStep

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
