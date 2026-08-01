"""
Face detection shared by the image and video pipelines.

Two jobs:
1. Accuracy: deepfake-detector models are frequently trained or evaluated
   on face-centric datasets, and even general-purpose classifiers tend to
   do better on a tight, uncluttered view of the subject than a whole
   scene with background noise. Cropping to each detected face first
   (with a little padding) gets the model a cleaner input when a face is
   actually present; this is a safe default that doesn't assume any one
   model's specific training data.
2. Routing: the "no face -> general AI image detector, face -> SigLIP2
   face detector" decision in services/image_detector.py depends entirely
   on this module's answer. Multi-face images are analyzed per-face
   (services/image_detector.py loops over every crop this module returns)
   rather than only ever looking at the single largest face.

Primary detector: MediaPipe Face Detection (short-range BlazeFace model,
bundled with the `mediapipe` package — no separate model download step,
it ships inside the wheel). Falls back automatically to OpenCV's bundled
Haar cascade if mediapipe isn't importable/initializable, so the app still
runs even in environments where mediapipe can't be installed.
"""

import logging
import threading

import cv2
import numpy as np

logger = logging.getLogger("truelens.face_detection")

_face_cascade = None
_mediapipe_detector = None
_mediapipe_load_failed = False
# MediaPipe's Solution graphs (FaceDetection included) are not re-entrant —
# calling .process() on the same instance from more than one thread at a
# time is unsupported and can silently return wrong/corrupted detections
# for one or both callers, rather than raising. Since this module keeps a
# single module-level detector instance, every call is serialized through
# this lock so concurrent requests never race on it.
_mediapipe_lock = threading.Lock()


def _get_cascade():
    global _face_cascade
    if _face_cascade is None:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade


def _get_mediapipe_detector():
    """Lazily builds a MediaPipe FaceDetection instance. Returns None if
    mediapipe isn't available — callers fall back to Haar in that case."""
    global _mediapipe_detector, _mediapipe_load_failed
    if _mediapipe_detector is not None or _mediapipe_load_failed:
        return _mediapipe_detector
    try:
        import mediapipe as mp

        # model_selection=1: "full range" model, better for faces that
        # aren't large/centered (closer to real-world uploads than the
        # short-range default). min_detection_confidence kept moderate so
        # we don't silently miss real faces and fall through to the wrong
        # (general) pipeline.
        _mediapipe_detector = mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.5
        )
    except Exception:  # noqa: BLE001
        logger.warning("mediapipe unavailable, falling back to Haar cascade for face detection.", exc_info=True)
        _mediapipe_load_failed = True
        _mediapipe_detector = None
    return _mediapipe_detector


def _boxes_from_mediapipe(image_bgr) -> list:
    detector = _get_mediapipe_detector()
    if detector is None:
        return None  # signal "try Haar instead"

    height, width = image_bgr.shape[:2]
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    with _mediapipe_lock:
        results = detector.process(image_rgb)
    if not results.detections:
        return []

    boxes = []
    for detection in results.detections:
        rel = detection.location_data.relative_bounding_box
        x = max(int(rel.xmin * width), 0)
        y = max(int(rel.ymin * height), 0)
        w = max(int(rel.width * width), 1)
        h = max(int(rel.height * height), 1)
        score = detection.score[0] if detection.score else None
        boxes.append((x, y, w, h, score))
    return boxes


def _boxes_from_haar(image_bgr) -> list:
    cascade = _get_cascade()
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
    return [(int(x), int(y), int(w), int(h), None) for (x, y, w, h) in faces]


def detect_faces(image_bgr) -> list:
    """
    @returns list of (x, y, w, h, confidence_or_None) boxes, largest-first.
    Empty list if no face found. Tries MediaPipe first, Haar as fallback.
    """
    boxes = _boxes_from_mediapipe(image_bgr)
    if boxes is None:
        boxes = _boxes_from_haar(image_bgr)
    boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
    return boxes


def _crop_with_padding(image_bgr, box, padding_ratio=0.3):
    x, y, w, h, _ = box
    pad_x, pad_y = int(w * padding_ratio), int(h * padding_ratio)
    height, width = image_bgr.shape[:2]
    x0, y0 = max(x - pad_x, 0), max(y - pad_y, 0)
    x1, y1 = min(x + w + pad_x, width), min(y + h + pad_y, height)
    return image_bgr[y0:y1, x0:x1]


def detect_all_faces(image_bgr, padding_ratio: float = 0.3, max_faces: int = 8) -> list:
    """
    Used when every face needs to be analyzed independently (per the
    "if multiple faces exist, analyze every face independently" spec).

    @returns list of {"crop": np.ndarray, "box": (x,y,w,h), "confidence": float|None}
             ordered largest-face-first, capped at max_faces to bound
             inference cost on images with a crowd of faces.
    """
    boxes = detect_faces(image_bgr)[:max_faces]
    faces = []
    for box in boxes:
        crop = _crop_with_padding(image_bgr, box, padding_ratio)
        if crop.size == 0:
            continue
        faces.append({"crop": crop, "box": box[:4], "confidence": box[4]})
    return faces


def detect_and_crop_face(image_bgr, padding_ratio: float = 0.3):
    """
    Backward-compatible single-face API (still used anywhere that only
    cares about "is there a face, and what's the largest one" rather than
    the full per-face list).

    @returns (face_found: bool, crop_bgr_or_None, face_count: int)
    """
    boxes = detect_faces(image_bgr)
    if not boxes:
        return False, None, 0
    crop = _crop_with_padding(image_bgr, boxes[0], padding_ratio)
    return True, crop, len(boxes)
