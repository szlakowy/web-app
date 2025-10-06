from .models import PersonalInfo


def add_personal_info_to_context(request):
    try:
        personal_info = PersonalInfo.objects.first()
    except PersonalInfo.DoesNotExist:
        personal_info = None

    return {
        'personal_info': personal_info,
    }