import math
import numpy as np


def cosine_similarity(vec_a, vec_b) -> float:
    """
    Calculate mathematical cosine similarity between two feature vectors:
    cos(theta) = (A . B) / (||A|| * ||B||)
    """
    a = np.asarray(vec_a, dtype=np.float64)
    b = np.asarray(vec_b, dtype=np.float64)
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    dot = np.dot(a, b)
    cos_val = float(dot / (norm_a * norm_b))
    # Clamp to [-1.0, 1.0] to avoid float precision overflow
    return max(-1.0, min(1.0, cos_val))


def euclidean_distance(vec_a, vec_b) -> float:
    """
    Calculate standard Euclidean distance between two vectors:
    ||A - B|| = sqrt(sum((Ai - Bi)^2))
    """
    a = np.asarray(vec_a, dtype=np.float64)
    b = np.asarray(vec_b, dtype=np.float64)
    return float(np.linalg.norm(a - b))


def calculate_similarity_and_distance(vec_a, vec_b, metric='cosine'):
    """
    Calculate similarity score, distance metric, and confidence rating
    based on the requested metric ('cosine' or 'euclidean').
    
    Returns:
        dict: {
            "similarity_percentage": float (0-100),
            "distance": float,
            "raw_metric": float,
            "confidence": "High" | "Medium" | "Low"
        }
    """
    cos_val = cosine_similarity(vec_a, vec_b)
    euc_dist = euclidean_distance(vec_a, vec_b)
    
    if metric == 'euclidean':
        # For unit-normalized vectors, max Euclidean distance is 2.0
        distance = round(euc_dist, 4)
        sim_pct = max(0.0, min(100.0, (1.0 - (euc_dist / 2.0)) * 100.0))
        raw_val = euc_dist
    else: # default cosine
        # Cosine distance = 1 - cos(theta)
        distance = round(max(0.0, 1.0 - cos_val), 4)
        # Cosine similarity mapped from [-1, 1] to [0, 100]
        sim_pct = max(0.0, min(100.0, ((cos_val + 1.0) / 2.0) * 100.0))
        raw_val = round(cos_val, 4)
        
    sim_pct = round(sim_pct, 2)
    
    # Probabilistic similarity-based confidence band
    if sim_pct >= 80.0:
        confidence = "High"
    elif sim_pct >= 65.0:
        confidence = "Medium"
    else:
        confidence = "Low"
        
    return {
        "similarity_percentage": sim_pct,
        "distance": distance,
        "raw_metric": raw_val,
        "confidence": confidence
    }
