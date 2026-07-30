"""
Stroke Classification Engine
Classifies strokes into Serve, Forehand, Backhand, Volley, Slice, Drop, Smash, Lob using pose kinematics and ball contact metrics.
"""

import numpy as np

class StrokeClassifier:
    def __init__(self):
        self.last_stroke_time = {}

    def classify_stroke(self, player_id, pose_data, ball_info):
        if pose_data is None or "keypoints" not in pose_data:
            return "Forehand"

        kpts = pose_data["keypoints"]
        angles = pose_data.get("angles", {})
        
        r_wrist = kpts.get("right_wrist", [0, 0])
        l_wrist = kpts.get("left_wrist", [0, 0])
        r_shoulder = kpts.get("right_shoulder", [0, 0])
        l_shoulder = kpts.get("left_shoulder", [0, 0])
        r_hip = kpts.get("right_hip", [0, 0])
        ball_height = ball_info.get("height_m", 0.8)
        speed = ball_info.get("speed_kmh", 0.0)

        if r_wrist[1] < r_shoulder[1] - 40 and r_wrist[1] > 0:
            if ball_height > 2.0 or speed > 130:
                return "Serve"
            else:
                return "Smash"

        if ball_height > 2.8 and r_wrist[1] > r_shoulder[1]:
            return "Lob"

        if speed > 100 and ball_height > 1.2 and not ball_info.get("is_bounce", False):
            return "Volley"

        if speed < 65 and ball_height < 0.6:
            return "Drop"
        elif r_wrist[1] > r_hip[1] and speed > 70 and speed < 100:
            return "Slice"

        body_center_x = (r_shoulder[0] + l_shoulder[0]) / 2.0 if (r_shoulder[0] > 0 and l_shoulder[0] > 0) else r_shoulder[0]
        
        if r_wrist[0] > body_center_x:
            return "Forehand"
        else:
            return "Backhand"

    def estimate_spin(self, stroke, ball_speed):
        if stroke in ["Serve", "Forehand", "Backhand"]:
            return "Topspin" if ball_speed > 100 else "Flat"
        elif stroke in ["Slice", "Drop"]:
            return "Backspin"
        elif stroke == "Kick Serve":
            return "Topsin-Slice"
        else:
            return "Flat"
