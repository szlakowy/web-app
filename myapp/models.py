from django.db import models
from django.urls import reverse
from django.utils.text import slugify


# Create your models here.


class PersonalInfo(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    bio = models.TextField()
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text='Wgraj swoje zdjęcie profilowe',
    )

    def __str__(self):
        return f'{self.first_name} {self.last_name}'


class Project(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    technologies = models.CharField(max_length=200)
    github_url = models.URLField(blank=True)
    created_date = models.DateField(auto_now_add=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    class Meta:
        ordering = ['-created_date']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('project_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            base_slug = slugify(self.title)
            unique_slug = base_slug
            counter = 1

            queryset = Project.objects.all()
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            # append a number if the slug already exists
            while queryset.filter(slug=unique_slug).exists():
                unique_slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = unique_slug
        super().save(*args, **kwargs)


class Skill(models.Model):
    name = models.CharField(max_length=200)
    level = models.IntegerField()

    def __str__(self):
        return f'{self.name} (poziom {self.level})'


class JourneyStep(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    date = models.DateField(help_text='Estimated start date')
    order = models.PositiveIntegerField(
        default=0,
        blank=False,
        null=False,
        help_text='The displaying order (0 as the first)'
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Stage {self.order}: {self.title}'


class JobOffer(models.Model):
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    salary = models.CharField(max_length=100, blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    url = models.URLField(max_length=500, unique=True)
    source = models.CharField(max_length=100)
    scraped_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scraped_date']

    def __str__(self):
        return f'{self.title} at {self.company}'
