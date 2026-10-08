from django.conf import settings


def auth_context(request):
    """
    Context processor to inject current user and system settings into templates.
    """
    user = getattr(request, 'mongo_user', None)
    return {
        'current_user': user,
        'is_authenticated': user is not None,
        'is_admin': user.get('role') == 'admin' if user else False,
        'system_disclaimer': getattr(settings, 'SYSTEM_DISCLAIMER', ''),
        'app_name': 'CrimeSketch-ID',
    }
