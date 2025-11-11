from .models import ScraperTechnology, ScraperTechnologyFilter


def resolve_platform_technology(technology_name: str, platform: str) -> str:
    """
    Zwraca filtr z bazy; jeśli brak wpisu, zwraca oryginalną nazwę.
    """
    if not technology_name:
        return technology_name

    normalized_name = technology_name.strip()
    normalized_platform = platform.strip().lower()

    try:
        tech = ScraperTechnology.objects.get(name__iexact=normalized_name)
    except ScraperTechnology.DoesNotExist:
        return normalized_name

    try:
        filter_entry = tech.platform_filters.get(platform__iexact=normalized_platform)
    except ScraperTechnologyFilter.DoesNotExist:
        return normalized_name

    return filter_entry.value
