import os
import time
import logging
import cv2
import numpy as np
from django.conf import settings
from ml.preprocessing import load_image, preprocess_sketch

logger = logging.getLogger(__name__)

_yunet_detector = None


def get_model_path(filename='face_detection_yunet_2023mar.onnx'):
    if settings.configured:
        base_dir = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'ml', 'models', filename)


def get_face_detector(input_size=(320, 320), conf_threshold=0.5, nms_threshold=0.3):
    global _yunet_detector
    model_path = get_model_path('face_detection_yunet_2023mar.onnx')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"YuNet model not found at {model_path}")
        
    if _yunet_detector is None:
        try:
            _yunet_detector = cv2.FaceDetectorYN_create(
                model=model_path,
                config='',
                input_size=input_size,
                score_threshold=conf_threshold,
                nms_threshold=nms_threshold,
                top_k=5000
            )
        except Exception as e:
            logger.error(f"Error initializing FaceDetectorYN: {e}")
            raise
    else:
        _yunet_detector.setScoreThreshold(conf_threshold)
        _yunet_detector.setNMSThreshold(nms_threshold)
        _yunet_detector.setInputSize(input_size)
        
    return _yunet_detector


def detect_faces(image_source, score_threshold=0.45, is_sketch=False):
    """
    Detect all faces in an image using OpenCV YuNet DNN.
    
    Supports:
    - Multi-face detection (for webcam and group photos)
    - Sketch-specific contrast normalization retry if no face is detected initially
    
    Returns:
        dict: {
            "success": bool,
            "faces_count": int,
            "faces": list of face dicts,
            "detection_time": float (seconds),
            "image_bgr": ndarray,
            "image_w": int,
            "image_h": int,
        }
    """
    t0 = time.perf_counter()
    image_bgr, w, h = load_image(image_source)
    
    detector = get_face_detector(input_size=(w, h), conf_threshold=score_threshold)
    detector.setInputSize((w, h))
    
    _, faces = detector.detect(image_bgr)
    
    # If no face found or if flagged as sketch, attempt enhanced sketch CLAHE pass
    if (faces is None or len(faces) == 0) and (is_sketch or True):
        enhanced_sketch = preprocess_sketch(image_bgr)
        detector.setScoreThreshold(max(0.25, score_threshold - 0.15))
        _, faces = detector.detect(enhanced_sketch)
        # Restore threshold
        detector.setScoreThreshold(score_threshold)
    
    face_list = []
    if faces is not None and len(faces) > 0:
        for idx, f in enumerate(faces):
            # YuNet output: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
            x, y, fw, fh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
            # Clamp bbox to image boundaries
            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            fw = max(1, min(fw, w - x))
            fh = max(1, min(fh, h - y))
            
            landmarks = [
                [float(f[4]), float(f[5])],    # Right eye
                [float(f[6]), float(f[7])],    # Left eye
                [float(f[8]), float(f[9])],    # Nose tip
                [float(f[10]), float(f[11])],  # Right mouth corner
                [float(f[12]), float(f[13])],  # Left mouth corner
            ]
            score = float(f[14])
            
            face_list.append({
                "face_index": idx + 1,
                "bbox": [x, y, fw, fh],
                "confidence": round(score, 4),
                "landmarks": landmarks,
                "raw_face": f.tolist() if hasattr(f, 'tolist') else list(f)
            })

    elapsed = time.perf_counter() - t0
    
    return {
        "success": True,
        "faces_count": len(face_list),
        "faces": face_list,
        "detection_time": round(elapsed, 4),
        "image_bgr": image_bgr,
        "image_w": w,
        "image_h": h,
    }


def draw_bounding_boxes(image_bgr, faces, labels=None):
    """
    Draw bounding boxes, landmark points, and labels on image.
    Returns a copy of the image with annotations.
    """
    annotated = image_bgr.copy()
    h, w = annotated.shape[:2]
    
    for idx, face in enumerate(faces):
        bbox = face['bbox']
        x, y, bw, bh = bbox
        
        # Color: teal/cyan for bounding box
        color = (255, 180, 0) # BGR
        cv2.rectangle(annotated, (x, y), (x + bw, y + bh), color, 2)
        
        # Draw corner accents for professional HUD aesthetic
        corner_len = min(15, bw // 4, bh // 4)
        corner_color = (0, 255, 255)
        # Top-left
        cv2.line(annotated, (x, y), (x + corner_len, y), corner_color, 3)
        cv2.line(annotated, (x, y), (x, y + corner_len), corner_color, 3)
        # Top-right
        cv2.line(annotated, (x + bw, y), (x + bw - corner_len, y), corner_color, 3)
        cv2.line(annotated, (x + bw, y), (x + bw, y + corner_len), corner_color, 3)
        # Bottom-left
        cv2.line(annotated, (x, y + bh), (x + corner_len, y + bh), corner_color, 3)
        cv2.line(annotated, (x, y + bh), (x, y + bh - corner_len), corner_color, 3)
        # Bottom-right
        cv2.line(annotated, (x + bw, y + bh), (x + bw - corner_len, y + bh), corner_color, 3)
        cv2.line(annotated, (x + bw, y + bh), (x + bw, y + bh - corner_len), corner_color, 3)
        
        # Draw 5 landmarks if available
        if 'landmarks' in face:
            for lx, ly in face['landmarks']:
                cv2.circle(annotated, (int(lx), int(ly)), 3, (0, 255, 128), -1)
                
        # Draw label badge
        label_text = f"Face #{face.get('face_index', idx + 1)}"
        if labels and idx < len(labels) and labels[idx]:
            label_text = labels[idx]
        elif 'confidence' in face:
            label_text += f" ({int(face['confidence'] * 100)}%)"
            
        (text_w, text_h), baseline = cv2.getTextSize(
            label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        badge_y = max(y - 5, text_h + 5)
        cv2.rectangle(
            annotated,
            (x, badge_y - text_h - 4),
            (x + text_w + 8, badge_y + 2),
            (20, 20, 20),
            -1
        )
        cv2.rectangle(
            annotated,
            (x, badge_y - text_h - 4),
            (x + text_w + 8, badge_y + 2),
            color,
            1
        )
        cv2.putText(
            annotated,
            label_text,
            (x + 4, badge_y - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )
        
    return annotated
