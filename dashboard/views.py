from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from utils.mongodb import (
    get_utc_now,
    get_candidates_collection,
    get_history_collection,
    get_settings_collection,
    check_mongo_connection
)
from utils.decorators import login_required, admin_required


@login_required
def dashboard_index(request):
    """
    Main CrimeSketch-ID dashboard view displaying real-time metrics, system health,
    and recent activity.
    """
    candidates_col = get_candidates_collection()
    history_col = get_history_collection()
    
    # 1. Total Candidates
    total_candidates = candidates_col.count_documents({})
    
    # 2. Total Searches
    total_searches = history_col.count_documents({})
    
    # 3. Today's Searches
    today_start = get_utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_searches = history_col.count_documents({'created_at': {'$gte': today_start}})
    
    # 4. Average Processing Time
    avg_pipeline = [
        {'$match': {'processing_time': {'$exists': True, '$ne': None}}},
        {'$group': {'_id': None, 'avg_time': {'$avg': '$processing_time'}}}
    ]
    avg_result = list(history_col.aggregate(avg_pipeline))
    avg_time = round(avg_result[0]['avg_time'], 3) if avg_result else 0.0
    
    # System health
    mongo_ok, mongo_msg = check_mongo_connection()
    
    # Recent searches (latest 6)
    recent_searches = list(history_col.find({}).sort('created_at', -1).limit(6))
    
    return render(request, 'dashboard.html', {
        'total_candidates': total_candidates,
        'total_searches': total_searches,
        'today_searches': today_searches,
        'avg_processing_time': avg_time,
        'recent_searches': recent_searches,
        'mongo_ok': mongo_ok,
        'mongo_msg': mongo_msg,
    })


@login_required
def settings_view(request):
    """
    System configuration view for metric and top-k preferences.
    """
    settings_col = get_settings_collection()
    config = settings_col.find_one({'setting_key': 'default_config'}) or {
        'top_k': 10,
        'similarity_metric': 'cosine',
        'detection_threshold': 0.45,
        'theme': 'light'
    }
    
    if request.method == 'POST':
        top_k = int(request.POST.get('top_k', 10))
        metric = request.POST.get('similarity_metric', 'cosine')
        threshold = float(request.POST.get('detection_threshold', 0.45))
        theme = request.POST.get('theme', 'light')
        
        settings_col.update_one(
            {'setting_key': 'default_config'},
            {'$set': {
                'top_k': top_k,
                'similarity_metric': metric,
                'detection_threshold': threshold,
                'theme': theme,
                'updated_at': get_utc_now()
            }},
            upsert=True
        )
        messages.success(request, "System settings updated successfully.")
        return redirect('dashboard:settings')
        
    return render(request, 'settings.html', {
        'config': config
    })


@login_required
def help_view(request):
    """
    User help and step-by-step workflow guide.
    """
    return render(request, 'help.html')


@login_required
def about_view(request):
    """
    About the project, academic background, technology, and ethical notices.
    """
    return render(request, 'about.html')
