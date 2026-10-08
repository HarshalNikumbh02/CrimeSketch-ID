import csv
import json
from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator

from utils.mongodb import get_history_collection, safe_object_id, serialize_doc
from utils.decorators import login_required, admin_required


@login_required
def history_list_view(request):
    """
    Search history list with filter by search type, search query, and pagination.
    """
    history_col = get_history_collection()
    
    search_type = request.GET.get('type', '').strip().upper()
    query_str = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)
    
    filter_q = {}
    if search_type in ['SKETCH', 'IMAGE', 'WEBCAM']:
        filter_q['search_type'] = search_type
    if query_str:
        filter_q['$or'] = [
            {'search_id': {'$regex': query_str, '$options': 'i'}},
            {'top_candidate': {'$regex': query_str, '$options': 'i'}},
            {'user_id': {'$regex': query_str, '$options': 'i'}},
        ]
        
    total_count = history_col.count_documents(filter_q)
    history_records = list(history_col.find(filter_q).sort('created_at', -1))
    
    paginator = Paginator(history_records, 15)
    page_obj = paginator.get_page(page_num)
    
    return render(request, 'history/list.html', {
        'page_obj': page_obj,
        'search_type': search_type,
        'query_str': query_str,
        'total_count': total_count,
    })


@login_required
def result_detail_view(request, search_id):
    """
    Detailed inspection page for a past search result: /results/<id>/
    """
    history_col = get_history_collection()
    record = history_col.find_one({'search_id': search_id})
    if not record:
        raise Http404(f"Search record '{search_id}' not found.")
        
    return render(request, 'history/detail.html', {
        'record': record,
    })


@admin_required
def history_delete_view(request, search_id):
    """
    Delete a search history entry (Admin authorization required).
    """
    history_col = get_history_collection()
    res = history_col.delete_one({'search_id': search_id})
    if res.deleted_count > 0:
        messages.success(request, f"Search record '{search_id}' deleted.")
    else:
        messages.warning(request, f"Search record '{search_id}' was not found.")
    return redirect('searches:history')


@login_required
def export_history_csv(request):
    """
    Export search history records to downloadable CSV file.
    """
    history_col = get_history_collection()
    records = list(history_col.find({}).sort('created_at', -1))
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="crimesketch_history.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Search ID', 'Search Type', 'User', 'Timestamp', 
        'Faces Detected', 'Top Candidate', 'Top Similarity %', 'Processing Time (s)'
    ])
    
    for r in records:
        writer.writerow([
            r.get('search_id', ''),
            r.get('search_type', ''),
            r.get('user_id', ''),
            r.get('created_at', '').strftime("%Y-%m-%d %H:%M:%S") if hasattr(r.get('created_at'), 'strftime') else str(r.get('created_at', '')),
            r.get('number_of_faces', 0),
            r.get('top_candidate', ''),
            r.get('similarity', 0.0),
            r.get('processing_time', 0.0)
        ])
        
    return response
