import os
import time
import logging
import cv2
import numpy as np
from django.conf import settings
from ml.preprocessing import load_image, crop_face_region

logger = logging.getLogger(__name__)

_sface_recognizer = None


def get_sface_model_path():
    if settings.configured:
        base_dir = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'ml', 'models', 'face_recognition_sface_2021dec.onnx')


def get_face_recognizer():
    global _sface_recognizer
    model_path = get_sface_model_path()
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"SFace model file not found at {model_path}")
    if _sface_recognizer is None:
        try:
            _sface_recognizer = cv2.FaceRecognizerSF_create(model=model_path, config='')
        except Exception as e:
            logger.error(f"Failed to initialize SFace recognizer: {e}")
            raise
    return _sface_recognizer


def extract_face_embedding(image_source, face_info=None):
    """
    Extract a normalized 128-dimensional embedding vector from a face.
    
    Parameters:
        image_source: image filepath, ndarray, or bytes
        face_info: dict with 'raw_face' (YuNet output) or 'bbox' [x, y, w, h]
        
    Returns:
        dict: {
            "embedding": list of 128 floats (L2 normalized),
            "aligned_face": ndarray (112x112 crop),
            "embedding_time": float (seconds),
            "vector_dim": 128
        }
    """
    t0 = time.perf_counter()
    image_bgr, w, h = load_image(image_source)
    recognizer = get_face_recognizer()
    
    aligned_face = None
    
    if face_info and 'raw_face' in face_info and face_info['raw_face']:
        raw_arr = np.array(face_info['raw_face'], dtype=np.float32)
        try:
            aligned_face = recognizer.alignCrop(image_bgr, raw_arr)
        except Exception as e:
            logger.warning(f"SFace alignCrop failed: {e}. Falling back to bbox crop.")
            
    if aligned_face is None:
        if face_info and 'bbox' in face_info:
            crop, _ = crop_face_region(image_bgr, face_info['bbox'])
            if crop.size > 0:
                aligned_face = cv2.resize(crop, (112, 112))
        else:
            # Whole image resized to standard face canvas
            aligned_face = cv2.resize(image_bgr, (112, 112))
            
    # Extract feature representation
    feature = recognizer.feature(aligned_face) # Shape (1, 128)
    
    if feature is not None and feature.size > 0:
        emb_arr = feature.flatten().astype(np.float64)
        # Ensure L2 normalization
        norm = np.linalg.norm(emb_arr)
        if norm > 0:
            emb_arr = emb_arr / norm
        embedding = emb_arr.tolist()
    else:
        raise ValueError("Failed to compute face feature embedding")
        
    elapsed = time.perf_counter() - t0
    
    return {
        "embedding": [round(float(val), 6) for val in embedding],
        "aligned_face": aligned_face,
        "embedding_time": round(elapsed, 4),
        "vector_dim": len(embedding)
    }
