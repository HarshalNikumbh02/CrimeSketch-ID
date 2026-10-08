import os
import io
import base64
import numpy as np
import cv2
from PIL import Image


def load_image(source):
    """
    Load an image from various input types:
    - File path (str)
    - Raw bytes
    - File-like object (e.g. Django UploadedFile)
    - Base64 data URI (data:image/jpeg;base64,...)
    - NumPy ndarray
    
    Returns:
        (image_bgr, width, height)
    """
    if source is None:
        raise ValueError("Image source is None")
        
    if isinstance(source, np.ndarray):
        img = source
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        h, w = img.shape[:2]
        return img, w, h

    if isinstance(source, str):
        # Base64 string
        if source.startswith('data:image'):
            header, encoded = source.split(',', 1)
            raw_bytes = base64.b64decode(encoded)
            nparr = np.frombuffer(raw_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Failed to decode base64 image")
            h, w = img.shape[:2]
            return img, w, h
            
        # File path
        if not os.path.exists(source):
            raise FileNotFoundError(f"Image file not found: {source}")
        img = cv2.imread(source)
        if img is None:
            raise ValueError(f"OpenCV could not read image from {source}")
        h, w = img.shape[:2]
        return img, w, h

    # Bytes or File-like object
    if hasattr(source, 'read'):
        raw_bytes = source.read()
        if hasattr(source, 'seek'):
            source.seek(0)
    elif isinstance(source, bytes):
        raw_bytes = source
    else:
        raise TypeError(f"Unsupported image source type: {type(source)}")

    nparr = np.frombuffer(raw_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        # Fallback using PIL
        try:
            pil_img = Image.open(io.BytesIO(raw_bytes)).convert('RGB')
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            raise ValueError(f"Could not decode image from byte buffer: {e}")
            
    h, w = img.shape[:2]
    return img, w, h


def preprocess_sketch(image_bgr):
    """
    Preprocess sketch or low-contrast facial drawing:
    - Normalizes lighting and contrast via CLAHE (Contrast Limited Adaptive Histogram Equalization).
    - Preserves sharp pencil/charcoal contour lines while smoothing paper grain via bilateral filter.
    """
    if image_bgr is None:
        return None

    # Convert to LAB color space
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # Apply CLAHE to L channel to enhance sketch line contrast
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)

    merged = cv2.merge((cl, a_channel, b_channel))
    enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    # Light bilateral filter to reduce paper texture noise while keeping sharp edges
    smoothed = cv2.bilateralFilter(enhanced, d=5, sigmaColor=35, sigmaSpace=35)
    return smoothed


def crop_face_region(image_bgr, bbox, padding=0.15):
    """
    Crop a face region with optional padding from bounding box [x, y, w, h].
    Clamps within image bounds.
    """
    x, y, w, h = [int(v) for v in bbox]
    img_h, img_w = image_bgr.shape[:2]

    pad_x = int(w * padding)
    pad_y = int(h * padding)

    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(img_w, x + w + pad_x)
    y2 = min(img_h, y + h + pad_y)

    crop = image_bgr[y1:y2, x1:x2]
    return crop, (x1, y1, x2 - x1, y2 - y1)


def image_to_base64(image_bgr, fmt='.jpg'):
    """
    Encode an OpenCV BGR image into a data URI base64 string.
    """
    if image_bgr is None:
        return ""
    success, buffer = cv2.imencode(fmt, image_bgr)
    if not success:
        return ""
    encoded = base64.b64encode(buffer).decode('utf-8')
    mime = "image/jpeg" if fmt in ['.jpg', '.jpeg'] else "image/png"
    return f"data:{mime};base64,{encoded}"


def save_image_to_disk(image_bgr, filepath):
    """
    Save image array to destination file. Creates parent directories if missing.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    return cv2.imwrite(filepath, image_bgr)
