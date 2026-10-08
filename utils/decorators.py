from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse
from django.urls import reverse
from utils.mongodb import get_users_collection, safe_object_id


def login_required(view_func):
    """
    Decorator to ensure user is logged in via session.
    Redirects to login page or returns 401 for API calls.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            if request.path.startswith('/api/') or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required. Please log in.'
                }, status=401)
            login_url = f"{reverse('accounts:login')}?next={request.path}"
            return redirect(login_url)
        
        # Attach user document to request.mongo_user for convenience
        if not hasattr(request, 'mongo_user'):
            users_col = get_users_collection()
            user = users_col.find_one({'_id': safe_object_id(user_id)})
            request.mongo_user = user
            if not user:
                # User deleted from database
                request.session.flush()
                return redirect('accounts:login')
                
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """
    Decorator to ensure user has admin role.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        role = request.session.get('role', '')
        if role != 'admin':
            if request.path.startswith('/api/') or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Admin permissions required.'
                }, status=403)
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return wrapper
