import os
import re
import uuid
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import JsonResponse, Http404
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator

from utils.mongodb import get_utc_now, get_candidates_collection, get_history_collection, safe_object_id
from utils.decorators import login_required, admin_required
from ml.face_detection import detect_faces
from ml.embeddings import extract_face_embedding


ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def save_candidate_image(uploaded_file, candidate_id):
    """
    Save uploaded reference image to media/candidates/ with a clean filename.
    Returns relative path from media root.
    """
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"Invalid image format '{ext}'. Allowed: .jpg, .jpeg, .png")
        
    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValueError("Image file exceeds the 10MB limit.")
        
    clean_id = re.sub(r'[^a-zA-Z0-9_-]', '_', candidate_id)
    unique_name = f"can_{clean_id}_{uuid.uuid4().hex[:8]}{ext}"
    
    cand_dir = os.path.join(settings.MEDIA_ROOT, 'candidates')
    os.makedirs(cand_dir, exist_ok=True)
    
    full_path = os.path.join(cand_dir, unique_name)
    with open(full_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
            
    return f"candidates/{unique_name}", full_path


@login_required
def candidate_list_view(request):
    """
    List candidates with search, filter, and pagination.
    """
    candidates_col = get_candidates_collection()
    
    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    gender_filter = request.GET.get('gender', '').strip()
    page_num = request.GET.get('page', 1)
    
    query = {}
    if search_q:
        query['$or'] = [
            {'candidate_id': {'$regex': search_q, '$options': 'i'}},
            {'name': {'$regex': search_q, '$options': 'i'}},
            {'notes': {'$regex': search_q, '$options': 'i'}},
        ]
    if status_filter:
        query['status'] = status_filter
    if gender_filter:
        query['gender'] = gender_filter
        
    total_count = candidates_col.count_documents(query)
    candidates_cursor = candidates_col.find(query).sort('created_at', -1)
    all_candidates = list(candidates_cursor)
    
    paginator = Paginator(all_candidates, 10)
    page_obj = paginator.get_page(page_num)
    
    return render(request, 'candidates/list.html', {
        'page_obj': page_obj,
        'search_q': search_q,
        'status_filter': status_filter,
        'gender_filter': gender_filter,
        'total_count': total_count,
    })


@login_required
def candidate_add_view(request):
    """
    Add a new candidate with reference portrait, detect face,
    and compute SFace embedding.
    """
    candidates_col = get_candidates_collection()
    errors = []
    
    if request.method == 'POST':
        candidate_id = request.POST.get('candidate_id', '').strip()
        name = request.POST.get('name', '').strip()
        age = request.POST.get('age', '').strip()
        gender = request.POST.get('gender', 'Unknown').strip()
        status = request.POST.get('status', 'Active').strip()
        notes = request.POST.get('notes', '').strip()
        image_file = request.FILES.get('reference_image')
        
        if not candidate_id:
            errors.append("Candidate ID is required.")
        elif candidates_col.find_one({'candidate_id': candidate_id}):
            errors.append(f"Candidate ID '{candidate_id}' already exists in database.")
            
        if not name:
            errors.append("Full Name is required.")
            
        if not image_file:
            errors.append("Reference photo is required for face recognition.")
            
        age_int = None
        if age:
            try:
                age_int = int(age)
                if age_int < 0 or age_int > 130:
                    errors.append("Age must be between 0 and 130.")
            except ValueError:
                errors.append("Age must be a valid integer.")
                
        if not errors:
            try:
                rel_path, full_path = save_candidate_image(image_file, candidate_id)
                
                # Run computer vision pipeline: face detection & embedding extraction
                det_res = detect_faces(full_path, score_threshold=0.45)
                
                if det_res['faces_count'] == 0:
                    errors.append(
                        "No face detected in reference photo. Please upload a clear, front-facing portrait."
                    )
                    # Remove invalid image file
                    if os.path.exists(full_path):
                        os.remove(full_path)
                else:
                    # Use best detected face
                    face_info = det_res['faces'][0]
                    emb_res = extract_face_embedding(full_path, face_info=face_info)
                    
                    candidate_doc = {
                        'candidate_id': candidate_id,
                        'name': name,
                        'age': age_int,
                        'gender': gender,
                        'status': status,
                        'reference_image': rel_path,
                        'image_path': full_path,
                        'embedding': emb_res['embedding'],
                        'embedding_dim': emb_res['vector_dim'],
                        'notes': notes,
                        'created_at': get_utc_now(),
                        'updated_at': get_utc_now(),
                    }
                    candidates_col.insert_one(candidate_doc)
                    messages.success(request, f"Candidate '{name}' ({candidate_id}) added successfully with {emb_res['vector_dim']}-d feature embedding.")
                    return redirect('candidates:detail', candidate_id=candidate_id)
            except Exception as e:
                errors.append(f"Processing error: {str(e)}")
                
    return render(request, 'candidates/add.html', {
        'errors': errors,
        'form_data': request.POST,
    })


@login_required
def candidate_detail_view(request, candidate_id):
    """
    View candidate profile, portrait, embedding metrics, and search appearance history.
    """
    candidates_col = get_candidates_collection()
    candidate = candidates_col.find_one({'candidate_id': candidate_id})
    if not candidate:
        raise Http404("Candidate not found.")
        
    # Search history appearances
    history_col = get_history_collection()
    appearances = list(history_col.find({
        'results.candidate_id': candidate_id
    }).sort('created_at', -1).limit(5))
    
    # Embedding preview
    embedding = candidate.get('embedding', [])
    emb_preview = embedding[:12] if embedding else []
    
    return render(request, 'candidates/detail.html', {
        'candidate': candidate,
        'appearances': appearances,
        'emb_preview': emb_preview,
        'emb_length': len(embedding),
    })


@login_required
def candidate_edit_view(request, candidate_id):
    """
    Edit candidate details or replace portrait image (recomputes embedding).
    """
    candidates_col = get_candidates_collection()
    candidate = candidates_col.find_one({'candidate_id': candidate_id})
    if not candidate:
        raise Http404("Candidate not found.")
        
    errors = []
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        age = request.POST.get('age', '').strip()
        gender = request.POST.get('gender', 'Unknown').strip()
        status = request.POST.get('status', 'Active').strip()
        notes = request.POST.get('notes', '').strip()
        new_image = request.FILES.get('reference_image')
        
        if not name:
            errors.append("Full Name is required.")
            
        age_int = None
        if age:
            try:
                age_int = int(age)
            except ValueError:
                errors.append("Age must be an integer.")
                
        if not errors:
            update_data = {
                'name': name,
                'age': age_int,
                'gender': gender,
                'status': status,
                'notes': notes,
                'updated_at': get_utc_now()
            }
            
            if new_image:
                try:
                    rel_path, full_path = save_candidate_image(new_image, candidate_id)
                    det_res = detect_faces(full_path, score_threshold=0.45)
                    if det_res['faces_count'] == 0:
                        errors.append("No face detected in new portrait. Reverted to previous image.")
                        if os.path.exists(full_path):
                            os.remove(full_path)
                    else:
                        emb_res = extract_face_embedding(full_path, face_info=det_res['faces'][0])
                        update_data['reference_image'] = rel_path
                        update_data['image_path'] = full_path
                        update_data['embedding'] = emb_res['embedding']
                        update_data['embedding_dim'] = emb_res['vector_dim']
                except Exception as e:
                    errors.append(f"Image update error: {str(e)}")
                    
            if not errors:
                candidates_col.update_one({'candidate_id': candidate_id}, {'$set': update_data})
                messages.success(request, f"Candidate '{candidate_id}' updated successfully.")
                return redirect('candidates:detail', candidate_id=candidate_id)
                
    return render(request, 'candidates/edit.html', {
        'candidate': candidate,
        'errors': errors,
    })


@admin_required
def candidate_delete_view(request, candidate_id):
    """
    Delete a candidate record and their image file.
    """
    candidates_col = get_candidates_collection()
    candidate = candidates_col.find_one({'candidate_id': candidate_id})
    if not candidate:
        raise Http404("Candidate not found.")
        
    if request.method == 'POST':
        # Remove media image file if it exists
        img_path = candidate.get('image_path')
        if img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except Exception:
                pass
                
        candidates_col.delete_one({'candidate_id': candidate_id})
        messages.success(request, f"Candidate '{candidate_id}' has been permanently deleted.")
        return redirect('candidates:list')
        
    return render(request, 'candidates/delete.html', {
        'candidate': candidate
    })
