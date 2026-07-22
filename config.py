"""
Configuration and constants for Tennis AI Computer Vision & Analytics Pipeline
"""

import os

# Base directory for models and logs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Standard ITF Tennis Court Dimensions (in meters)
# Origin (0,0) is placed at top-left corner of doubles court
COURT_LENGTH_M = 23.77      # Total length
COURT_WIDTH_M = 10.97       # Doubles width
SINGLES_WIDTH_M = 8.23      # Singles width
SINGLES_MARGIN_M = (COURT_WIDTH_M - SINGLES_WIDTH_M) / 2.0  # 1.37m
SERVICE_LINE_DIST_M = 6.40  # Distance from net to service line
NET_POSITION_Y_M = COURT_LENGTH_M / 2.0  # 11.885m

# Real 2D Court Reference Points (X in meters [0, 10.97], Y in meters [0, 23.77])
# Standard keypoints mapping (doubles corners, baseline intersections, service line points)
REAL_COURT_POINTS = {
    "top_left_doubles": (0.0, 0.0),
    "top_right_doubles": (COURT_WIDTH_M, 0.0),
    "bottom_left_doubles": (0.0, COURT_LENGTH_M),
    "bottom_right_doubles": (COURT_WIDTH_M, COURT_LENGTH_M),
    "top_left_singles": (SINGLES_MARGIN_M, 0.0),
    "top_right_singles": (COURT_WIDTH_M - SINGLES_MARGIN_M, 0.0),
    "bottom_left_singles": (SINGLES_MARGIN_M, COURT_LENGTH_M),
    "bottom_right_singles": (COURT_WIDTH_M - SINGLES_MARGIN_M, COURT_LENGTH_M),
    "net_left": (0.0, NET_POSITION_Y_M),
    "net_right": (COURT_WIDTH_M, NET_POSITION_Y_M),
    "top_service_center": (COURT_WIDTH_M / 2.0, NET_POSITION_Y_M - SERVICE_LINE_DIST_M),
    "bottom_service_center": (COURT_WIDTH_M / 2.0, NET_POSITION_Y_M + SERVICE_LINE_DIST_M),
}

# Detection & Tracking Model Options
YOLO_PLAYER_MODEL = "yolo11m.pt"
YOLO_POSE_MODEL = "yolo11m-pose.pt"

# Player tracking thresholds
CONF_THRESHOLD_PLAYER = 0.4
MAX_DISAPPEARED_FRAMES = 15

# Pose Estimator COCO Keypoint Map
COCO_KEYPOINTS = {
    0: "nose",
    1: "left_eye", 2: "right_eye",
    3: "left_ear", 4: "right_ear",
    5: "left_shoulder", 6: "right_shoulder",
    7: "left_elbow", 8: "right_elbow",
    9: "left_wrist", 10: "right_wrist",
    11: "left_hip", 12: "right_hip",
    13: "left_knee", 14: "right_knee",
    15: "left_ankle", 16: "right_ankle"
}

# Analytics JSON Schema Default Template
ANALYTICS_EVENT_SCHEMA = {
    "event_id": "",
    "timestamp_sec": 0.0,
    "frame_idx": 0,
    "player": "Player 1", # Player 1 or Player 2
    "event_type": "Hit",  # Serve, Hit, Bounce, Winner, Net, Fault, Ace, Rally End
    "stroke": "Forehand", # Serve, Forehand, Backhand, Volley, Slice, Drop, Smash, Lob
    "speed_kmh": 0.0,
    "ball_height_m": 0.0,
    "spin": "Topspin",
    "court_position_pixel": [0, 0],
    "court_position_meters": [0.0, 0.0],
    "landing_court_position_meters": [0.0, 0.0],
    "body_pose_angles": {},
    "reaction_time_ms": 0,
    "result": "In Play"
}
