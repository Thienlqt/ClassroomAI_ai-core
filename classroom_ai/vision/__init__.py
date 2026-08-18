"""Optional vision and biometric components."""

from classroom_ai.vision.face_store import FaceEmbeddingStore, FaceMatch
from classroom_ai.vision.base import (
    FaceRecognitionService,
    FaceRecognitionUnavailableError,
)
from classroom_ai.vision.face_recognition import OpenCVFaceRecognition
from classroom_ai.vision.schemas import (
    BoundingBox,
    FaceEnrollmentRequest,
    FaceEnrollmentResult,
    RecognizedFace,
)

__all__ = [
    "BoundingBox",
    "FaceEmbeddingStore",
    "FaceEnrollmentRequest",
    "FaceEnrollmentResult",
    "FaceMatch",
    "FaceRecognitionService",
    "FaceRecognitionUnavailableError",
    "OpenCVFaceRecognition",
    "RecognizedFace",
]
