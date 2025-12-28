"""BFF Dance - Core modules"""
from .pose_detector import (
    Pose,
    Keypoint,
    PoseDetector,
    CameraCapture,
    draw_poses
)
from .pose_comparator import (
    PoseComparator,
    ComparisonResult,
    calculate_pose_similarity
)
from .pose_buffer import (
    PoseBuffer,
    MultiPlayerPoseBuffer,
    TimestampedPose
)

__all__ = [
    "Pose",
    "Keypoint",
    "PoseDetector",
    "CameraCapture",
    "draw_poses",
    "PoseComparator",
    "ComparisonResult",
    "calculate_pose_similarity",
    "PoseBuffer",
    "MultiPlayerPoseBuffer",
    "TimestampedPose",
]
