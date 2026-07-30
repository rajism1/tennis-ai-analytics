import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Video Input Path
VIDEO_PATH = os.path.join(BASE_DIR, "match2.mp4")
if not os.path.exists(VIDEO_PATH):
    VIDEO_PATH = os.path.join(BASE_DIR, "match.mp4")

# Model Paths
YOLO_POSE_MODEL = os.path.join(BASE_DIR, "yolo11m-pose.pt")
YOLO_DET_MODEL = os.path.join(BASE_DIR, "yolo11m.pt")

# COCO Keypoints
COCO_KEYPOINTS = {
    0: "nose", 1: "left_eye", 2: "right_eye", 3: "left_ear", 4: "right_ear",
    5: "left_shoulder", 6: "right_shoulder", 7: "left_elbow", 8: "right_elbow",
    9: "left_wrist", 10: "right_wrist", 11: "left_hip", 12: "right_hip",
    13: "left_knee", 14: "right_knee", 15: "left_ankle", 16: "right_ankle"
}

# Standard Tennis Court Real-World Metrics (Meters)
COURT_LENGTH_M = 23.77  # Baseline to baseline
COURT_WIDTH_M = 10.97   # Doubles width
SINGLES_WIDTH_M = 8.23  # Singles width
SERVICE_LINE_M = 6.40   # Net to service line

REAL_COURT_POINTS = {
    "top_left_doubles": (0.0, 0.0),
    "top_right_doubles": (COURT_WIDTH_M, 0.0),
    "bottom_right_doubles": (COURT_WIDTH_M, COURT_LENGTH_M),
    "bottom_left_doubles": (0.0, COURT_LENGTH_M),
    "top_left_singles": (1.37, 0.0),
    "top_right_singles": (COURT_WIDTH_M - 1.37, 0.0),
    "bottom_left_singles": (1.37, COURT_LENGTH_M),
    "bottom_right_singles": (COURT_WIDTH_M - 1.37, COURT_LENGTH_M),
    "top_service_center": (COURT_WIDTH_M / 2.0, 5.49),
    "bottom_service_center": (COURT_WIDTH_M / 2.0, COURT_LENGTH_M - 5.49),
    "net_left": (0.0, COURT_LENGTH_M / 2.0),
    "net_right": (COURT_WIDTH_M, COURT_LENGTH_M / 2.0)
}

# Standard Court Keypoints in 2D Screen Space
DEFAULT_COURT_KEYPOINTS = {
    "top_left": (0.28, 0.22),
    "top_right": (0.72, 0.22),
    "bottom_left": (0.10, 0.90),
    "bottom_right": (0.90, 0.90),
    "net_left": (0.20, 0.50),
    "net_right": (0.80, 0.50)
}

# FPS and Processing Configuration
TARGET_FPS = 30
MAX_FRAMES_TO_PROCESS = 1000

# Physics Thresholds
MIN_BALL_SPEED_KMH = 15.0
MAX_BALL_SPEED_KMH = 260.0
NET_HEIGHT_M = 0.914
