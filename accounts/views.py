from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from utils.mongodb import get_utc_now, get_users_collection, safe_object_id
from utils.decorators import login_required


def verify_user_password(user, raw_password):
    stored = user.get('password') or user.get('password_hash')
    if not stored:
        return False
    try:
        if check_password(raw_password, stored):
            return True
    except Exception:
        pass
    import hashlib
    if hashlib.sha256(raw_password.encode('utf-8')).hexdigest() == stored:
        return True
    return False


def ensure_default_admin():
    """
    Ensure at least one admin user exists in MongoDB with a valid password.
    """
    try:
        users_col = get_users_collection()
        admin = users_col.find_one({'username': 'admin'})
        if not admin:
            users_col.insert_one({
                'username': 'admin',
                'password': make_password('Admin@123'),
                'password_hash': make_password('Admin@123'),
                'email': 'admin@crimesketch.local',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'admin',
                'is_active': True,
                'created_at': get_utc_now(),
                'last_login': None
            })
        elif 'password' not in admin:
            users_col.update_one(
                {'username': 'admin'},
                {'$set': {
                    'password': make_password('Admin@123'),
                    'password_hash': make_password('Admin@123'),
                    'is_active': True,
                    'role': 'admin'
                }}
            )
    except Exception:
        pass


def login_view(request):
    """
    User login view verifying credentials against MongoDB users collection.
    """
    ensure_default_admin()
    
    if request.session.get('user_id'):
        return redirect('dashboard:index')

    error_message = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            error_message = "Please provide both username and password."
        else:
            try:
                users_col = get_users_collection()
                user = users_col.find_one({'username': username})

                if user and verify_user_password(user, password):
                    if not user.get('is_active', True):
                        error_message = "This account has been deactivated. Please contact an administrator."
                    else:
                        request.session['user_id'] = str(user['_id'])
                        request.session['username'] = user['username']
                        request.session['role'] = user.get('role', 'investigator')
                        
                        # Update last_login
                        users_col.update_one(
                            {'_id': user['_id']},
                            {'$set': {'last_login': get_utc_now()}}
                        )
                        
                        next_url = request.POST.get('next') or request.GET.get('next') or 'dashboard:index'
                        return redirect(next_url)
                else:
                    error_message = "Invalid username or password. Please try again."
            except Exception as e:
                error_message = f"Database authentication error: {str(e)}"

    return render(request, 'login.html', {
        'error_message': error_message,
        'next': request.GET.get('next', ''),
    })


def logout_view(request):
    """
    Log out user and clear signed cookie session.
    """
    request.session.flush()
    messages.info(request, "You have been logged out successfully.")
    return redirect('accounts:login')


@login_required
def profile_view(request):
    """
    User profile view allowing viewing and updating account info & password.
    """
    user = request.mongo_user
    users_col = get_users_collection()
    success_msg = None
    error_msg = None

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            
            users_col.update_one(
                {'_id': user['_id']},
                {'$set': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'updated_at': get_utc_now()
                }}
            )
            success_msg = "Profile details updated successfully."
            user['first_name'] = first_name
            user['last_name'] = last_name
            user['email'] = email

        elif action == 'change_password':
            current_pwd = request.POST.get('current_password', '')
            new_pwd = request.POST.get('new_password', '')
            confirm_pwd = request.POST.get('confirm_password', '')

            if not check_password(current_pwd, user.get('password', '')):
                error_msg = "Current password does not match."
            elif len(new_pwd) < 6:
                error_msg = "New password must be at least 6 characters."
            elif new_pwd != confirm_pwd:
                error_msg = "New passwords do not match."
            else:
                users_col.update_one(
                    {'_id': user['_id']},
                    {'$set': {
                        'password': make_password(new_pwd),
                        'updated_at': get_utc_now()
                    }}
                )
                success_msg = "Password updated successfully."

    return render(request, 'profile.html', {
        'user_doc': user,
        'success_msg': success_msg,
        'error_msg': error_msg,
    })
