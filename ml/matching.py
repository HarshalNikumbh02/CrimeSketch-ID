import time
from ml.similarity import calculate_similarity_and_distance


def rank_candidates(query_embedding, candidates, metric='cosine', top_k=10):
    """
    Compare a query embedding vector against a collection of reference candidates.
    Calculates exact distances and similarities, sorts descending, and returns top-K candidates.
    
    Parameters:
        query_embedding: list of 128 floats
        candidates: iterable of candidate dictionaries (from MongoDB)
        metric: 'cosine' or 'euclidean'
        top_k: int
        
    Returns:
        dict: {
            "top_candidates": list of ranked match dicts,
            "total_evaluated": int,
            "matching_time": float (seconds),
            "metric": str
        }
    """
    t0 = time.perf_counter()
    ranked = []
    
    total_evaluated = 0
    for cand in candidates:
        emb = cand.get('embedding')
        if not emb or not isinstance(emb, list) or len(emb) == 0:
            continue
            
        total_evaluated += 1
        res = calculate_similarity_and_distance(query_embedding, emb, metric=metric)
        
        ranked.append({
            "candidate_id": cand.get('candidate_id', 'UNKNOWN'),
            "name": cand.get('name', 'Unknown Candidate'),
            "age": cand.get('age', '-'),
            "gender": cand.get('gender', '-'),
            "reference_image": cand.get('reference_image', ''),
            "notes": cand.get('notes', ''),
            "status": cand.get('status', 'Active'),
            "similarity": res['similarity_percentage'],
            "distance": res['distance'],
            "confidence": res['confidence'],
            "raw_metric": res['raw_metric'],
            "_id": str(cand.get('_id', ''))
        })
        
    # Sort descending by similarity
    ranked.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Assign ranks
    top_matches = ranked[:top_k]
    for idx, match in enumerate(top_matches):
        match['rank'] = idx + 1
        
    elapsed = time.perf_counter() - t0
    
    return {
        "top_candidates": top_matches,
        "total_evaluated": total_evaluated,
        "matching_time": round(elapsed, 4),
        "metric": metric
    }
