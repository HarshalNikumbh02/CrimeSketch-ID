import os
import json
import time
import uuid
from datetime import datetime
import cv2
import numpy as np
from django.conf import settings

from utils.mongodb import get_utc_now, get_candidates_collection, get_evaluation_collection
from ml.face_detection import detect_faces
from ml.embeddings import extract_face_embedding
from ml.matching import rank_candidates


def get_dataset_dir():
    return os.path.join(settings.MEDIA_ROOT, 'eval_dataset')


def is_dataset_configured():
    dataset_dir = get_dataset_dir()
    gt_file = os.path.join(dataset_dir, 'ground_truth.json')
    return os.path.exists(gt_file)


def run_system_evaluation(dataset_name="Default Benchmark"):
    """
    Run genuine evaluation benchmark against probe dataset and gallery database.
    Computes Rank-1, Rank-5, Rank-10 accuracy, precision, recall, F1, and mean search time.
    """
    dataset_dir = get_dataset_dir()
    gt_file = os.path.join(dataset_dir, 'ground_truth.json')
    
    if not os.path.exists(gt_file):
        raise FileNotFoundError("Evaluation dataset not configured. Missing ground_truth.json.")
        
    with open(gt_file, 'r', encoding='utf-8') as f:
        ground_truth = json.load(f)
        
    candidates_col = get_candidates_collection()
    gallery = list(candidates_col.find({'status': {'$ne': 'Archived'}}))
    
    if not gallery:
        raise ValueError("Cannot evaluate: Candidate gallery database is empty.")
        
    total_queries = len(ground_truth)
    if total_queries == 0:
        raise ValueError("Evaluation ground truth contains 0 test queries.")
        
    top1_hits = 0
    top5_hits = 0
    top10_hits = 0
    tp = 0
    fp = 0
    fn = 0
    total_search_time = 0.0
    
    details = []

    for item in ground_truth:
        probe_rel = item.get('probe_image')
        target_id = item.get('target_candidate_id')
        
        probe_path = os.path.join(dataset_dir, probe_rel)
        if not os.path.exists(probe_path):
            continue
            
        t0 = time.perf_counter()
        
        # 1. Detect face
        det = detect_faces(probe_path, score_threshold=0.40, is_sketch=True)
        if det['faces_count'] == 0:
            fn += 1
            continue
            
        # 2. Extract embedding
        emb_res = extract_face_embedding(probe_path, face_info=det['faces'][0])
        query_emb = emb_res['embedding']
        
        # 3. Rank against gallery
        ranked = rank_candidates(query_emb, gallery, metric='cosine', top_k=10)
        q_time = time.perf_counter() - t0
        total_search_time += q_time
        
        top_matches = ranked['top_candidates']
        top_ids = [m['candidate_id'] for m in top_matches]
        
        # Rank-1 check
        if top_ids and top_ids[0] == target_id:
            top1_hits += 1
            
        # Rank-5 check
        if target_id in top_ids[:5]:
            top5_hits += 1
            
        # Rank-10 check
        if target_id in top_ids[:10]:
            top10_hits += 1
            
        # Similarity threshold classification (threshold = 65%)
        matched_above_thresh = [m for m in top_matches if m['similarity'] >= 65.0]
        if matched_above_thresh and matched_above_thresh[0]['candidate_id'] == target_id:
            tp += 1
        elif matched_above_thresh and matched_above_thresh[0]['candidate_id'] != target_id:
            fp += 1
        else:
            fn += 1
            
        details.append({
            'probe_image': probe_rel,
            'target_candidate_id': target_id,
            'predicted_top_1': top_ids[0] if top_ids else None,
            'top_1_similarity': top_matches[0]['similarity'] if top_matches else 0.0,
            'search_time': round(q_time, 4),
        })

    eval_count = len(details) if details else 1
    top1_acc = round((top1_hits / eval_count) * 100.0, 2)
    top5_acc = round((top5_hits / eval_count) * 100.0, 2)
    top10_acc = round((top10_hits / eval_count) * 100.0, 2)
    
    precision = round((tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 0.0, 2)
    recall = round((tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 0.0, 2)
    f1 = round((2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0, 2)
    avg_time = round(total_search_time / eval_count, 4)

    run_id = f"EVAL-{get_utc_now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
    run_doc = {
        'run_id': run_id,
        'timestamp': get_utc_now(),
        'dataset_name': dataset_name,
        'total_queries': total_queries,
        'evaluated_queries': eval_count,
        'top1_accuracy': top1_acc,
        'top5_accuracy': top5_acc,
        'top10_accuracy': top10_acc,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'avg_search_time': avg_time,
        'query_details': details,
    }

    eval_col = get_evaluation_collection()
    eval_col.insert_one(run_doc)
    
    return run_doc


def create_demo_benchmark():
    """
    Create a controlled demo benchmark dataset from current candidates in the database
    by generating sketch versions using edge detection and pencil sketch filtering.
    """
    dataset_dir = get_dataset_dir()
    os.makedirs(dataset_dir, exist_ok=True)
    
    candidates_col = get_candidates_collection()
    candidates = list(candidates_col.find({'status': {'$ne': 'Archived'}}).limit(6))
    
    if not candidates:
        raise ValueError("Cannot initialize demo benchmark: Add some candidates first.")
        
    ground_truth = []
    
    for idx, c in enumerate(candidates):
        img_path = c.get('image_path')
        if not img_path or not os.path.exists(img_path):
            continue
            
        orig_bgr = cv2.imread(img_path)
        if orig_bgr is None:
            continue
            
        # Convert photo into pencil sketch using OpenCV pencilSketch
        gray_sketch, _ = cv2.pencilSketch(orig_bgr, sigma_s=50, sigma_r=0.07, shade_factor=0.04)
        
        sketch_filename = f"probe_sketch_{c['candidate_id']}.jpg"
        sketch_path = os.path.join(dataset_dir, sketch_filename)
        cv2.imwrite(sketch_path, gray_sketch)
        
        ground_truth.append({
            'probe_image': sketch_filename,
            'target_candidate_id': c['candidate_id'],
            'candidate_name': c['name']
        })
        
    gt_file = os.path.join(dataset_dir, 'ground_truth.json')
    with open(gt_file, 'w', encoding='utf-8') as f:
        json.dump(ground_truth, f, indent=2)
        
    return len(ground_truth)
