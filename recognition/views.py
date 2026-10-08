import os
import time
import uuid
import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404
from django.conf import settings

from utils.mongodb import (
    get_utc_now,
    get_candidates_collection,
    get_history_collection,
    get_detected_faces_collection,
    get_settings_collection,
    serialize_doc
)
from utils.decorators import login_required
from ml.face_detection import detect_faces, draw_bounding_boxes
from ml.embeddings import extract_face_embedding
from ml.matching import rank_candidates
from ml.preprocessing import load_image, save_image_to_disk, image_to_base64


def get_system_default_settings():
    try:
        col = get_settings_collection()
        doc = col.find_one({'setting_key': 'default_config'})
        if doc:
            return doc
    except Exception:
        pass
    return {
        'top_k': 10,
        'similarity_metric': 'cosine',
        'detection_threshold': 0.45
    }


@login_required
def sketch_search_view(request):
    """
    Renders sketch/image upload interface and handles search form submission.
    """
    sys_settings = get_system_default_settings()
    
    if request.method == 'GET':
        return render(request, 'sketch_search.html', {
            'default_metric': sys_settings.get('similarity_metric', 'cosine'),
            'default_top_k': sys_settings.get('top_k', 10),
        })

    # POST handling (non-API or fallback standard form submission)
    return process_sketch_search(request)


@login_required
def api_sketch_search(request):
    """
    REST API endpoint for sketch/image search: POST /api/sketch-search/
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed. Use POST.'}, status=405)
        
    return process_sketch_search(request, is_api=True)


def process_sketch_search(request, is_api=False):
    t_start = time.perf_counter()
    image_file = request.FILES.get('sketch_image')
    metric = request.POST.get('metric', 'cosine')
    if metric not in ['cosine', 'euclidean']:
        metric = 'cosine'
        
    try:
        top_k = int(request.POST.get('top_k', 10))
    except (ValueError, TypeError):
        top_k = 10

    if not image_file:
        err = "Please select or upload a facial sketch or photo."
        if is_api:
            return JsonResponse({'success': False, 'error': err}, status=400)
        return render(request, 'sketch_search.html', {'error': err})

    # Validate file extension
    ext = os.path.splitext(image_file.name)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png']:
        err = f"Invalid image format '{ext}'. Supported formats: JPG, JPEG, PNG."
        if is_api:
            return JsonResponse({'success': False, 'error': err}, status=400)
        return render(request, 'sketch_search.html', {'error': err})

    # Save uploaded search image
    search_id = f"SRCH-{get_utc_now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    searches_dir = os.path.join(settings.MEDIA_ROOT, 'searches')
    os.makedirs(searches_dir, exist_ok=True)
    
    input_filename = f"{search_id}_input{ext}"
    input_path = os.path.join(searches_dir, input_filename)
    
    with open(input_path, 'wb+') as dest:
        for chunk in image_file.chunks():
            dest.write(chunk)
            
    rel_input_image = f"searches/{input_filename}"

    # 1. Detection Phase
    t_det_start = time.perf_counter()
    det_res = detect_faces(input_path, score_threshold=0.45, is_sketch=True)
    t_det = round(time.perf_counter() - t_det_start, 4)

    if det_res['faces_count'] == 0:
        err = "No face detected. Please upload a clearer image or sketch with distinct facial features."
        if is_api:
            return JsonResponse({'success': False, 'error': err, 'faces_detected': 0}, status=200)
        return render(request, 'sketch_search.html', {
            'error': err,
            'input_image_url': f"{settings.MEDIA_URL}{rel_input_image}"
        })

    # Retrieve candidate database from MongoDB
    candidates_col = get_candidates_collection()
    candidates = list(candidates_col.find({'status': {'$ne': 'Archived'}}))
    
    if len(candidates) == 0:
        err = "Reference candidate database is empty. Please add candidate reference images first."
        if is_api:
            return JsonResponse({'success': False, 'error': err, 'faces_detected': det_res['faces_count']}, status=200)
        return render(request, 'sketch_search.html', {
            'error': err,
            'faces_detected': det_res['faces_count'],
            'input_image_url': f"{settings.MEDIA_URL}{rel_input_image}"
        })

    # 2. Embedding Extraction & Matching Phase
    t_emb_start = time.perf_counter()
    face_results = []
    annotated_labels = []

    for f_idx, face in enumerate(det_res['faces']):
        emb_res = extract_face_embedding(input_path, face_info=face)
        query_emb = emb_res['embedding']
        
        # 3. Similarity Ranking against reference database
        t_match_start = time.perf_counter()
        ranking_res = rank_candidates(query_emb, candidates, metric=metric, top_k=top_k)
        t_match = ranking_res['matching_time']
        
        top_cand = ranking_res['top_candidates'][0] if ranking_res['top_candidates'] else None
        top_cand_name = top_cand['name'] if top_cand else 'None'
        top_sim = top_cand['similarity'] if top_cand else 0.0
        
        annotated_labels.append(f"{top_cand_name} ({top_sim}%)" if top_cand else f"Face #{f_idx+1}")
        
        face_results.append({
            'face_index': f_idx + 1,
            'bbox': face['bbox'],
            'confidence': face['confidence'],
            'top_matches': ranking_res['top_candidates'],
            'total_evaluated': ranking_res['total_evaluated'],
            'matching_time': t_match,
        })

    t_emb = round(time.perf_counter() - t_emb_start, 4)

    # Annotate image
    annotated_img = draw_bounding_boxes(det_res['image_bgr'], det_res['faces'], labels=annotated_labels)
    annotated_filename = f"{search_id}_annotated.jpg"
    annotated_path = os.path.join(searches_dir, annotated_filename)
    save_image_to_disk(annotated_img, annotated_path)
    rel_annotated_image = f"searches/{annotated_filename}"

    t_total = round(time.perf_counter() - t_start, 4)

    timing_breakdown = {
        'detection_time': t_det,
        'embedding_time': t_emb,
        'matching_time': face_results[0]['matching_time'] if face_results else 0.0,
        'total_time': t_total
    }

    # Primary matches (Face #1 matches)
    primary_matches = face_results[0]['top_matches'] if face_results else []
    top_candidate_name = primary_matches[0]['name'] if primary_matches else 'N/A'
    top_candidate_sim = primary_matches[0]['similarity'] if primary_matches else 0.0

    # Save search record to MongoDB
    history_col = get_history_collection()
    history_doc = {
        'search_id': search_id,
        'user_id': request.mongo_user.get('username') if getattr(request, 'mongo_user', None) else 'anonymous',
        'search_type': 'SKETCH',
        'input_image': rel_input_image,
        'annotated_image': rel_annotated_image,
        'number_of_faces': det_res['faces_count'],
        'top_candidate': top_candidate_name,
        'similarity': top_candidate_sim,
        'results': primary_matches,
        'face_results': face_results,
        'timing_breakdown': timing_breakdown,
        'processing_time': t_total,
        'metric_used': metric,
        'top_k': top_k,
        'created_at': get_utc_now()
    }
    history_col.insert_one(history_doc)

    context_data = {
        'success': True,
        'search_id': search_id,
        'search_type': 'SKETCH',
        'input_image_url': f"{settings.MEDIA_URL}{rel_input_image}",
        'annotated_image_url': f"{settings.MEDIA_URL}{rel_annotated_image}",
        'faces_detected': det_res['faces_count'],
        'timing_breakdown': timing_breakdown,
        'processing_time': t_total,
        'metric_used': metric,
        'face_results': face_results,
        'primary_matches': primary_matches,
    }

    if is_api:
        return JsonResponse(context_data)
        
    return render(request, 'sketch_search.html', context_data)


@login_required
def live_camera_view(request):
    """
    Renders the live camera / multi-face webcam detection page.
    """
    sys_settings = get_system_default_settings()
    return render(request, 'live_camera.html', {
        'default_metric': sys_settings.get('similarity_metric', 'cosine'),
        'default_top_k': sys_settings.get('top_k', 10),
    })


@login_required
def api_webcam_analyze(request):
    """
    REST API endpoint for analyzing a captured webcam frame with multi-face support:
    POST /api/webcam-analyze/
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST method required.'}, status=405)

    t_start = time.perf_counter()
    frame_data = request.POST.get('frame')
    metric = request.POST.get('metric', 'cosine')
    if metric not in ['cosine', 'euclidean']:
        metric = 'cosine'
        
    try:
        top_k = int(request.POST.get('top_k', 5))
    except (ValueError, TypeError):
        top_k = 5

    if not frame_data:
        return JsonResponse({'success': False, 'error': 'No frame data received.'}, status=400)

    try:
        image_bgr, w, h = load_image(frame_data)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Failed to decode webcam frame: {e}"}, status=400)

    # Save raw frame
    search_id = f"WEBCAM-{get_utc_now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    searches_dir = os.path.join(settings.MEDIA_ROOT, 'searches')
    os.makedirs(searches_dir, exist_ok=True)
    
    raw_filename = f"{search_id}_raw.jpg"
    raw_path = os.path.join(searches_dir, raw_filename)
    save_image_to_disk(image_bgr, raw_path)
    rel_raw_image = f"searches/{raw_filename}"

    # 1. Multi-face Detection
    t_det_start = time.perf_counter()
    det_res = detect_faces(raw_path, score_threshold=0.45)
    t_det = round(time.perf_counter() - t_det_start, 4)

    if det_res['faces_count'] == 0:
        return JsonResponse({
            'success': False,
            'faces_detected': 0,
            'message': 'No face detected in webcam view. Please face the camera directly.'
        })

    # Retrieve candidates from MongoDB
    candidates_col = get_candidates_collection()
    candidates = list(candidates_col.find({'status': {'$ne': 'Archived'}}))

    face_results = []
    annotated_labels = []

    t_emb_start = time.perf_counter()
    for f_idx, face in enumerate(det_res['faces']):
        emb_res = extract_face_embedding(raw_path, face_info=face)
        query_emb = emb_res['embedding']
        
        # Rank against reference candidates
        ranking_res = rank_candidates(query_emb, candidates, metric=metric, top_k=top_k)
        
        top_cand = ranking_res['top_candidates'][0] if ranking_res['top_candidates'] else None
        top_name = top_cand['name'] if top_cand else 'No match'
        top_sim = top_cand['similarity'] if top_cand else 0.0
        
        annotated_labels.append(f"Face #{f_idx+1}: {top_name} ({top_sim}%)")
        
        face_results.append({
            'face_index': f_idx + 1,
            'bbox': face['bbox'],
            'confidence': face['confidence'],
            'top_matches': ranking_res['top_candidates'],
            'matching_time': ranking_res['matching_time']
        })

    t_emb = round(time.perf_counter() - t_emb_start, 4)

    # Annotate frame
    annotated_img = draw_bounding_boxes(image_bgr, det_res['faces'], labels=annotated_labels)
    annotated_filename = f"{search_id}_annotated.jpg"
    annotated_path = os.path.join(searches_dir, annotated_filename)
    save_image_to_disk(annotated_img, annotated_path)
    rel_annotated_image = f"searches/{annotated_filename}"

    t_total = round(time.perf_counter() - t_start, 4)

    timing_breakdown = {
        'detection_time': t_det,
        'embedding_time': t_emb,
        'total_time': t_total
    }

    # Top overall match
    top_overall = face_results[0]['top_matches'][0] if (face_results and face_results[0]['top_matches']) else None

    # Log to MongoDB history
    history_col = get_history_collection()
    history_doc = {
        'search_id': search_id,
        'user_id': request.mongo_user.get('username') if getattr(request, 'mongo_user', None) else 'anonymous',
        'search_type': 'WEBCAM',
        'input_image': rel_raw_image,
        'annotated_image': rel_annotated_image,
        'number_of_faces': det_res['faces_count'],
        'top_candidate': top_overall['name'] if top_overall else 'N/A',
        'similarity': top_overall['similarity'] if top_overall else 0.0,
        'results': face_results[0]['top_matches'] if face_results else [],
        'face_results': face_results,
        'timing_breakdown': timing_breakdown,
        'processing_time': t_total,
        'metric_used': metric,
        'top_k': top_k,
        'created_at': get_utc_now()
    }
    history_col.insert_one(history_doc)

    return JsonResponse({
        'success': True,
        'search_id': search_id,
        'faces_detected': det_res['faces_count'],
        'raw_image_url': f"{settings.MEDIA_URL}{rel_raw_image}",
        'annotated_image_url': f"{settings.MEDIA_URL}{rel_annotated_image}",
        'timing_breakdown': timing_breakdown,
        'processing_time': t_total,
        'metric_used': metric,
        'face_results': face_results,
    })
