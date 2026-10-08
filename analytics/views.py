from datetime import datetime, timedelta
from django.shortcuts import render
from django.http import JsonResponse
from utils.mongodb import get_utc_now, get_candidates_collection, get_history_collection
from utils.decorators import login_required


@login_required
def analytics_view(request):
    """
    Analytics dashboard providing detailed statistics and chart data.
    """
    candidates_col = get_candidates_collection()
    history_col = get_history_collection()
    
    total_candidates = candidates_col.count_documents({})
    total_searches = history_col.count_documents({})
    sketch_searches = history_col.count_documents({'search_type': 'SKETCH'})
    webcam_searches = history_col.count_documents({'search_type': 'WEBCAM'})
    
    # Average processing time
    avg_pipeline = [
        {'$match': {'processing_time': {'$exists': True, '$ne': None}}},
        {'$group': {'_id': None, 'avg_time': {'$avg': '$processing_time'}}}
    ]
    avg_res = list(history_col.aggregate(avg_pipeline))
    avg_processing_time = round(avg_res[0]['avg_time'], 3) if avg_res else 0.0
    
    # Average similarity
    sim_pipeline = [
        {'$match': {'similarity': {'$exists': True, '$ne': None, '$gt': 0}}},
        {'$group': {'_id': None, 'avg_sim': {'$avg': '$similarity'}}}
    ]
    sim_res = list(history_col.aggregate(sim_pipeline))
    avg_similarity = round(sim_res[0]['avg_sim'], 2) if sim_res else 0.0

    # Searches per day (last 7 days)
    today = get_utc_now().date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    day_labels = [d.strftime("%b %d") for d in days]
    day_counts = []
    
    for d in days:
        start = datetime.combine(d, datetime.min.time())
        end = datetime.combine(d, datetime.max.time())
        cnt = history_col.count_documents({'created_at': {'$gte': start, '$lte': end}})
        day_counts.append(cnt)

    # Similarity bands distribution
    sim_bands = {
        '90-100%': history_col.count_documents({'similarity': {'$gte': 90.0}}),
        '80-89%': history_col.count_documents({'similarity': {'$gte': 80.0, '$lt': 90.0}}),
        '70-79%': history_col.count_documents({'similarity': {'$gte': 70.0, '$lt': 80.0}}),
        '60-69%': history_col.count_documents({'similarity': {'$gte': 60.0, '$lt': 70.0}}),
        '<60%': history_col.count_documents({'similarity': {'$lt': 60.0, '$gt': 0}}),
    }

    return render(request, 'analytics/index.html', {
        'total_candidates': total_candidates,
        'total_searches': total_searches,
        'sketch_searches': sketch_searches,
        'webcam_searches': webcam_searches,
        'avg_processing_time': avg_processing_time,
        'avg_similarity': avg_similarity,
        'day_labels': day_labels,
        'day_counts': day_counts,
        'sim_band_labels': list(sim_bands.keys()),
        'sim_band_counts': list(sim_bands.values()),
    })


@login_required
def api_analytics_data(request):
    """
    JSON API for dynamic chart updates.
    """
    history_col = get_history_collection()
    candidates_col = get_candidates_collection()
    
    total_candidates = candidates_col.count_documents({})
    total_searches = history_col.count_documents({})
    sketch_searches = history_col.count_documents({'search_type': 'SKETCH'})
    webcam_searches = history_col.count_documents({'search_type': 'WEBCAM'})
    
    return JsonResponse({
        'total_candidates': total_candidates,
        'total_searches': total_searches,
        'sketch_searches': sketch_searches,
        'webcam_searches': webcam_searches,
    })
